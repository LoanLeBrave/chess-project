#!/usr/bin/env python3
"""
Gestionnaire de jeu d'échecs
Gère la logique du jeu et Stockfish
"""

import chess
import chess.engine
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import asyncio
import time

from config import DIFFICULTY_PRESETS, POSITION_INITIALE, PIECE_TYPE_MAP, STOCKFISH_PATHS, DELTA_TRANSIT
from robot_controller import RobotController


class ChessManager:
    """Gestionnaire de la logique d'échecs et de l'IA"""

    _PIECE_NAMES_FR = {
        chess.PAWN: "Pion",
        chess.KNIGHT: "Cavalier",
        chess.BISHOP: "Fou",
        chess.ROOK: "Tour",
        chess.QUEEN: "Dame",
        chess.KING: "Roi",
    }

    def __init__(self, robot_controller: RobotController):
        self.board = chess.Board()
        self.engine = None
        self.difficulty = "intermediate"
        self.robot = robot_controller

        # Callback pour broadcast
        self.broadcast_callback = None
        self.log_callback = None
        self.status_callback = None
        self.is_paused = False

        # Reference au VisionService (injectee depuis api.py)
        self.vision_service = None

        # Gestion de la promotion physique
        self._promotion_event: Optional[asyncio.Event] = None
        self._promotion_from_sq: Optional[str] = None

        # Gestion de la reprise après pause
        self._interrupted_move: Optional[dict] = None
        self._resume_event: Optional[asyncio.Event] = None

        # Calcul ACPL : évaluation de la position avant le coup humain (centipawns, perspective blancs)
        self._pre_human_eval: Optional[float] = None

    def set_broadcast_callback(self, callback):
        """Définit le callback pour le broadcast"""
        self.broadcast_callback = callback

    def set_log_callback(self, callback):
        """Définit le callback pour les logs"""
        self.log_callback = callback

    def set_status_callback(self, callback):
        """Définit le callback pour le statut"""
        self.status_callback = callback

    async def broadcast(self, message: dict):
        """Envoie un message via le callback"""
        if self.broadcast_callback:
            await self.broadcast_callback(message)

    async def log(self, log_type: str, message: str):
        """Envoie un log via le callback"""
        if self.log_callback:
            await self.log_callback(log_type, message)

    def set_status(self, status: str, message: str = ""):
        """Met à jour le statut"""
        if self.status_callback:
            self.status_callback(status, message)

    async def _wait_with_pause_check(self, duration):
        """Attend avec vérifications fréquentes de la pause (toutes les 10ms)"""
        start = time.time()
        while time.time() - start < duration:
            if self.is_paused:
                return False
            await asyncio.sleep(0.01)  # Vérifier toutes les 10ms
        return True

    def init_stockfish(self):
        """Initialise Stockfish"""
        for path in STOCKFISH_PATHS:
            if Path(path).exists():
                try:
                    self.engine = chess.engine.SimpleEngine.popen_uci(path)
                    print(f"✓ Stockfish: {path}")
                    return True
                except:
                    pass
        print("⚠ Stockfish non trouvé")
        return False

    def new_game(self, difficulty: str = "intermediate"):
        """Démarre une nouvelle partie"""
        self.board.reset()
        self.difficulty = difficulty
        self.robot.reset_tracking()
        self.is_paused = False
        self.set_status("idle")
        return {"success": True, "fen": self.board.fen()}

    def get_legal_moves(self, square: str):
        """Retourne les coups légaux pour une case"""
        try:
            sq = chess.parse_square(square.lower())
            piece = self.board.piece_at(sq)

            if not piece:
                return []

            legal_destinations = []
            for move in self.board.legal_moves:
                if move.from_square == sq:
                    legal_destinations.append(chess.square_name(move.to_square))

            return legal_destinations
        except:
            return []

    def get_best_move(self):
        """Retourne le meilleur coup pour le joueur actuel avec évaluation"""
        if not self.engine:
            return {"success": False, "error": "Stockfish non disponible"}

        try:
            # Utiliser le niveau maximum pour les suggestions
            self.engine.configure({"Skill Level": 20})

            info = self.engine.analyse(
                self.board,
                chess.engine.Limit(depth=15, time=1.0)
            )

            move = info.get("pv", [None])[0]
            if not move:
                return {"success": False, "error": "Pas de coup trouvé"}

            # Calculer l'évaluation
            score = info.get("score")
            if score:
                if score.is_mate():
                    # Mat forcé
                    mate_in = score.relative.mate()
                    evaluation = f"M{mate_in}"
                else:
                    # Score en centipawns converti en pawns
                    evaluation = round(score.relative.score() / 100.0, 2)
            else:
                evaluation = 0.0

            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)

            return {
                "success": True,
                "from": from_sq,
                "to": to_sq,
                "evaluation": evaluation,
                "san": self.board.san(move)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def toggle_pause(self):
        """Bascule l'état de pause (arrêt d'urgence)"""
        if not self.is_paused:
            # PAUSE D'URGENCE — stopper le script robot (non-bloquant)
            self.is_paused = True
            loop = asyncio.get_running_loop()
            if self.robot.connected and self.robot.rtde_c:
                try:
                    await asyncio.wait_for(
                        loop.run_in_executor(None, self.robot.rtde_c.stopScript),
                        timeout=3.0
                    )
                except Exception as e:
                    print(f"Erreur stopScript pause: {e}")
            self.robot.is_paused = True
            await self.log("warning", "PAUSE D'URGENCE - Robot arrêté immédiatement!")
            self.set_status("paused", "PAUSE D'URGENCE")
            return {"success": True, "paused": True, "message": "PAUSE D'URGENCE - Robot arrêté!"}
        else:
            # Reprise — is_paused sera mis à False par _resume_process() une fois le robot prêt
            asyncio.create_task(self._resume_process())
            await self.log("info", "Reprise en cours...")
            return {"success": True, "paused": False, "message": "Reprise en cours..."}

    async def _resume_process(self):
        """Réactive le robot, relâche la pince et demande confirmation si un coup était en cours."""
        loop = asyncio.get_running_loop()

        # 1. Réactiver le script robot
        if self.robot.connected and self.robot.rtde_c:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, self.robot.rtde_c.reuploadScript),
                    timeout=3.0
                )
                await asyncio.sleep(0.2)
            except Exception as e:
                await self.log("error", f"Erreur réactivation robot: {e}")
        self.robot.is_paused = False
        self.is_paused = False

        # 2. Ouvrir le gripper (relâcher toute pièce tenue)
        await self.robot._gripper_open()
        await self.log("info", "Pince relâchée")

        # 3. Si aucun coup interrompu, reprendre directement
        if not self._interrupted_move:
            self.set_status("idle", "Partie reprise")
            await self.log("info", "Partie reprise")
            return

        # 4. Informer le joueur du coup interrompu
        move_info = self._interrupted_move
        piece_name = self._PIECE_NAMES_FR.get(move_info.get("piece_type"), "Pièce")
        from_sq = move_info.get("from_sq", "?")
        to_sq = move_info.get("to_sq", "?")

        await self.log("info", f"Coup interrompu : {piece_name} {from_sq} → {to_sq}")
        await self.broadcast({
            "type": "resume_confirmation_needed",
            "piece_name": piece_name,
            "from_sq": from_sq,
            "to_sq": to_sq,
            "player": move_info.get("player", "unknown"),
        })

        # 5. Attendre la confirmation du joueur (10 min max)
        self._resume_event = asyncio.Event()
        self.set_status("moving", f"En attente — Replacez le {piece_name} en {to_sq}")

        try:
            await asyncio.wait_for(self._resume_event.wait(), timeout=600.0)
        except asyncio.TimeoutError:
            await self.log("error", "Timeout reprise — aucune confirmation reçue dans les 10 minutes")
            self._interrupted_move = None
            self._resume_event = None
            self.set_status("idle")
            return

        self._resume_event = None

        # 6. Confirmation reçue → pousser le coup sur le plateau virtuel
        move = move_info.get("move")
        player = move_info.get("player", "robot")

        if move and move in self.board.legal_moves:
            san = move_info.get("san") or self.board.san(move)
            is_capture = move_info.get("is_capture", False)
            self.board.push(move)

            # Mettre à jour la référence vision après le coup confirmé
            if self.vision_service:
                self.vision_service.update_reference_after_move(from_sq, to_sq, is_capture=is_capture)

            await self.broadcast({
                "type": "move",
                "player": player,
                "from": from_sq,
                "to": to_sq,
                "san": san,
                "evaluation": move_info.get("evaluation"),
                "fen": self.board.fen(),
            })
            await self.log("info", f"Coup validé manuellement : {san}")

            # Libérer _interrupted_move avant de déclencher un éventuel coup robot
            self._interrupted_move = None

            # Retourner le robot en position de départ avant tout nouveau mouvement
            if self.robot.position_depart and not self.robot.is_paused:
                await self.robot._move_tcp(self.robot.position_depart)

            if self.board.is_game_over():
                result = self.get_game_result()
                await self.broadcast({"type": "game_over", "result": result})
            elif player == "human":
                self.set_status("thinking", "Tour du robot...")
                await self.play_robot_move()
        else:
            await self.log("error", "Coup non applicable après reprise — position modifiée ?")
            self._interrupted_move = None

        self.set_status("idle")
        await self.log("info", "Partie reprise")

    def confirm_resume(self) -> bool:
        """Appelée par l'API quand le joueur confirme que la pièce est replacée."""
        if self._resume_event and not self._resume_event.is_set():
            self._resume_event.set()
            return True
        return False

    async def undo_last_move(self) -> dict:
        """
        Annule le(s) dernier(s) coup(s) :
        - Si c'est le tour des blancs (humain), le robot a joué en dernier → annule robot + humain.
        - Si c'est le tour des noirs (robot), seul le coup humain est annulé.
        Met à jour la vision si disponible.
        """
        if not self.board.move_stack:
            return {"success": False, "error": "Aucun coup à annuler"}

        moves_undone = []

        # Si c'est le tour des blancs, le robot a joué en dernier → annuler son coup d'abord
        if self.board.turn == chess.WHITE:
            last = self.board.peek()
            moves_undone.append(
                (chess.square_name(last.from_square), chess.square_name(last.to_square))
            )
            self.board.pop()

        # Annuler le coup humain si la pile n'est pas vide
        if self.board.move_stack:
            last = self.board.peek()
            moves_undone.append(
                (chess.square_name(last.from_square), chess.square_name(last.to_square))
            )
            self.board.pop()

        # Inverser la mise à jour vision pour chaque coup annulé
        if self.vision_service:
            for from_sq, to_sq in moves_undone:
                self.vision_service.reverse_last_move(from_sq, to_sq)

        # Réinitialiser les états en cours
        self._interrupted_move = None
        self._pre_human_eval = None
        self.set_status("idle")

        n = len(moves_undone)
        await self.log("info", f"{n} coup(s) annulé(s) — retour à la position précédente")
        await self.broadcast({"type": "move_undone", "fen": self.board.fen(), "moves_undone": n})
        return {"success": True, "fen": self.board.fen(), "moves_undone": n}

    def _get_precise_coords(self, square: str):
        """
        Retourne les coordonnees precises (x, y) de la piece sur `square`
        via la vision camera, ou None si non disponible.
        """
        if not self.vision_service:
            return None
        piece_data = self.vision_service.find_piece_at(square)
        if not piece_data:
            return None
        board_pos = piece_data.get("position", {}).get("board")
        if not board_pos or "x" not in board_pos or "y" not in board_pos:
            return None
        return (board_pos["x"], board_pos["y"])

    async def play_human_move(self, from_sq: str, to_sq: str):
        """Joue le coup du joueur humain"""
        try:
            move = chess.Move.from_uci(f"{from_sq}{to_sq}")

            # Vérifier promotion
            piece = self.board.piece_at(chess.parse_square(from_sq))
            if piece and piece.piece_type == chess.PAWN:
                to_rank = to_sq[1]
                if (piece.color == chess.WHITE and to_rank == '8') or \
                        (piece.color == chess.BLACK and to_rank == '1'):
                    move = chess.Move.from_uci(f"{from_sq}{to_sq}q")

            if move not in self.board.legal_moves:
                move = chess.Move.from_uci(f"{from_sq}{to_sq}q")
                if move not in self.board.legal_moves:
                    return {"success": False, "error": "Coup illégal"}
        except:
            return {"success": False, "error": "Format de coup invalide"}

        is_capture = self.board.is_capture(move)

        # Récupérer la pièce capturée AVANT de jouer le coup
        captured_piece = None
        capture_sq = to_sq  # Par défaut, la pièce capturée est sur to_sq
        if is_capture:
            to_square = chess.parse_square(to_sq)
            captured_piece = self.board.piece_at(to_square)
            # En passant : le pion capturé est sur une case DIFFÉRENTE de to_sq
            if captured_piece is None and piece and piece.piece_type == chess.PAWN:
                ep_square = self.board.ep_square
                if ep_square:
                    ep_pawn_sq = ep_square - 8 if piece.color == chess.WHITE else ep_square + 8
                    captured_piece = self.board.piece_at(ep_pawn_sq)
                    if captured_piece:
                        capture_sq = chess.square_name(ep_pawn_sq)
                        await self.log("info", f"En passant — pion capturé en {capture_sq} (et non {to_sq})")

        # Définir la pièce courante pour le robot
        if piece:
            self.robot.piece_courante = piece.piece_type

        # Coordonnees precises de la camera si disponibles
        precise_coords = self._get_precise_coords(from_sq)

        # Détection du roque — calculer les positions de la tour
        castling_rook = None
        if self.board.is_castling(move):
            rank = to_sq[1]  # '1' pour les blancs, '8' pour les noirs
            if to_sq[0] == 'g':  # Petit roque (côté roi)
                castling_rook = (f'h{rank}', f'f{rank}')
            else:              # Grand roque (côté dame)
                castling_rook = (f'a{rank}', f'd{rank}')
            await self.log("info", f"Roque {'petit' if to_sq[0] == 'g' else 'grand'} — Tour: {castling_rook[0]} → {castling_rook[1]}")

        # Evaluation de la position AVANT le coup humain (pour calcul ACPL)
        if self.engine:
            try:
                pre_info = self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
                pre_score = pre_info.get("score")
                self._pre_human_eval = pre_score.white().score() if pre_score else None
            except Exception:
                self._pre_human_eval = None

        # Enregistrer le coup en cours (pour reprise après pause éventuelle)
        san_preview = self.board.san(move)
        self._interrupted_move = {
            "move": move,
            "from_sq": from_sq,
            "to_sq": to_sq,
            "piece_type": piece.piece_type if piece else None,
            "player": "human",
            "san": san_preview,
            "evaluation": None,
            "is_capture": is_capture,
        }

        # Exécuter sur le robot
        self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")
        success = await self.robot.execute_move(
            from_sq, to_sq, is_capture, captured_piece,
            precise_pick_coords=precise_coords,
            castling_rook=castling_rook,
            capture_sq=capture_sq,
        )

        if not success:
            await self.log("warning", "Mouvement interrompu par PAUSE")
            return {"success": False, "error": "Mouvement interrompu"}

        self._interrupted_move = None

        # Promotion physique : retirer le pion, attendre que le joueur place la dame
        if move.promotion is not None and piece:
            await self._handle_promotion(to_sq, piece.color)

        # Jouer sur le plateau virtuel
        san = self.board.san(move)
        self.board.push(move)

        await self.broadcast({
            "type": "move",
            "player": "human",
            "from": from_sq,
            "to": to_sq,
            "san": san,
            "fen": self.board.fen()
        })

        self.set_status("idle")

        # Vérifier fin de partie
        if self.board.is_game_over():
            result = self.get_game_result()
            await self.broadcast({"type": "game_over", "result": result})
            return {"success": True, "san": san, "game_over": True, "result": result}

        return {"success": True, "san": san}

    async def play_vision_move(self, from_sq: str, to_sq: str):
        """
        Enregistre un coup humain detecte par la camera.
        Le joueur a DEJA bouge la piece physiquement, donc le robot ne la deplace pas.
        Apres enregistrement, enchaine automatiquement avec le coup du robot.
        """
        try:
            move = chess.Move.from_uci(f"{from_sq}{to_sq}")

            # Verifier promotion
            piece = self.board.piece_at(chess.parse_square(from_sq))
            if piece and piece.piece_type == chess.PAWN:
                to_rank = to_sq[1]
                if (piece.color == chess.WHITE and to_rank == '8') or \
                        (piece.color == chess.BLACK and to_rank == '1'):
                    move = chess.Move.from_uci(f"{from_sq}{to_sq}q")

            if move not in self.board.legal_moves:
                move = chess.Move.from_uci(f"{from_sq}{to_sq}q")
                if move not in self.board.legal_moves:
                    return {"success": False, "error": "Coup illegal"}
        except Exception:
            return {"success": False, "error": "Format de coup invalide"}

        # Evaluation de la position AVANT le coup humain (pour calcul ACPL)
        if self.engine:
            try:
                pre_info = self.engine.analyse(self.board, chess.engine.Limit(time=0.1))
                pre_score = pre_info.get("score")
                self._pre_human_eval = pre_score.white().score() if pre_score else None
            except Exception:
                self._pre_human_eval = None

        # Enregistrer le coup dans Stockfish (PAS de mouvement robot)
        san = self.board.san(move)
        self.board.push(move)

        await self.log("player", f"Coup vision detecte: {san} ({from_sq} -> {to_sq})")

        await self.broadcast({
            "type": "move",
            "player": "human",
            "from": from_sq,
            "to": to_sq,
            "san": san,
            "fen": self.board.fen()
        })

        # Verifier fin de partie
        if self.board.is_game_over():
            result = self.get_game_result()
            await self.broadcast({"type": "game_over", "result": result})
            return {"success": True, "san": san, "game_over": True, "result": result}

        # Enchainer avec le coup du robot
        robot_result = await self.play_robot_move()
        return {"success": True, "san": san, "robot_response": robot_result}

    async def play_robot_move(self):
        """Calcule et joue le coup du robot avec évaluation"""
        if not self.engine:
            return {"success": False, "error": "Stockfish non disponible"}

        self.set_status("thinking", "Analyse de la position...")
        await self.log("robot", "Robot analyse la position...")

        preset = DIFFICULTY_PRESETS.get(self.difficulty, DIFFICULTY_PRESETS['intermediate'])
        self.engine.configure({"Skill Level": preset['skill_level']})

        try:
            info = self.engine.analyse(
                self.board,
                chess.engine.Limit(depth=preset['depth'], time=preset['time_limit'])
            )

            move = info.get("pv", [None])[0]
            if not move:
                return {"success": False, "error": "Pas de coup trouvé"}

            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)
            is_capture = self.board.is_capture(move)

            # Récupérer la pièce capturée AVANT de jouer le coup
            captured_piece = None
            capture_sq = to_sq  # Par défaut, pièce capturée sur to_sq
            if is_capture:
                captured_piece = self.board.piece_at(move.to_square)
                # En passant : le pion capturé est sur une case DIFFÉRENTE de to_sq
                if captured_piece is None:
                    moving_piece = self.board.piece_at(move.from_square)
                    if moving_piece and moving_piece.piece_type == chess.PAWN:
                        ep_square = self.board.ep_square
                        if ep_square:
                            ep_pawn_sq = ep_square - 8 if moving_piece.color == chess.WHITE else ep_square + 8
                            captured_piece = self.board.piece_at(ep_pawn_sq)
                            if captured_piece:
                                capture_sq = chess.square_name(ep_pawn_sq)
                                await self.log("info", f"En passant — pion capturé en {capture_sq} (et non {to_sq})")

            # Définir la pièce courante pour le robot
            piece = self.board.piece_at(move.from_square)
            if piece:
                self.robot.piece_courante = piece.piece_type

            # Calculer l'évaluation
            score = info.get("score")
            if score:
                if score.is_mate():
                    # Mat forcé - retourne une string (ex: "M3" ou "-M2")
                    mate_in = score.relative.mate()
                    evaluation = f"M{mate_in}"
                else:
                    # Score en centipawns converti en pawns
                    evaluation = round(score.relative.score() / 100.0, 2)
            else:
                evaluation = 0.0

            # Calculer le CPL (Centipawn Loss) du coup humain précédent
            # _pre_human_eval = meilleur score blanc AVANT le coup humain (centipawns)
            # score.white().score() = score blanc APRÈS le coup humain (centipawns)
            # CPL = max(0, pre - post) : positif si l'humain a perdu des centipawns
            cpl = None
            if self._pre_human_eval is not None and score and not score.is_mate():
                post_eval_white = score.white().score()
                if post_eval_white is not None:
                    cpl = max(0, self._pre_human_eval - post_eval_white)
            self._pre_human_eval = None

            await self.log("robot", f"Coup choisi: {from_sq} → {to_sq} (eval: {evaluation})")

            # Coordonnees precises de la camera si disponibles
            precise_coords = self._get_precise_coords(from_sq)

            # Détection du roque — calculer les positions de la tour
            castling_rook = None
            if self.board.is_castling(move):
                rank = to_sq[1]  # '1' pour les blancs, '8' pour les noirs
                if to_sq[0] == 'g':  # Petit roque (côté roi)
                    castling_rook = (f'h{rank}', f'f{rank}')
                else:              # Grand roque (côté dame)
                    castling_rook = (f'a{rank}', f'd{rank}')
                await self.log("info", f"Roque {'petit' if to_sq[0] == 'g' else 'grand'} — Tour: {castling_rook[0]} → {castling_rook[1]}")

            # Enregistrer le coup en cours (pour reprise après pause éventuelle)
            san_preview = self.board.san(move)
            self._interrupted_move = {
                "move": move,
                "from_sq": from_sq,
                "to_sq": to_sq,
                "piece_type": piece.piece_type if piece else None,
                "player": "robot",
                "san": san_preview,
                "evaluation": evaluation,
                "is_capture": is_capture,
            }

            # Exécuter sur le robot
            self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")
            success = await self.robot.execute_move(
                from_sq, to_sq, is_capture, captured_piece,
                precise_pick_coords=precise_coords,
                castling_rook=castling_rook,
                capture_sq=capture_sq,
            )

            if not success:
                await self.log("warning", "Mouvement interrompu par PAUSE")
                self.set_status("paused")
                return {"success": False, "error": "Mouvement interrompu"}

            self._interrupted_move = None

            # Promotion physique : retirer le pion, attendre que le joueur place la dame
            if move.promotion is not None and piece:
                await self._handle_promotion(to_sq, piece.color)

            # Jouer sur le plateau virtuel
            san = self.board.san(move)
            self.board.push(move)

            await self.broadcast({
                "type": "move",
                "player": "robot",
                "from": from_sq,
                "to": to_sq,
                "san": san,
                "evaluation": evaluation,
                "cpl": cpl,
                "fen": self.board.fen()
            })

            self.set_status("idle")

            # Vérifier fin de partie
            if self.board.is_game_over():
                result = self.get_game_result()
                await self.broadcast({"type": "game_over", "result": result})
                return {
                    "success": True,
                    "from": from_sq,
                    "to": to_sq,
                    "san": san,
                    "evaluation": evaluation,
                    "cpl": cpl,
                    "game_over": True,
                    "result": result
                }

            return {
                "success": True,
                "from": from_sq,
                "to": to_sq,
                "san": san,
                "evaluation": evaluation,
                "cpl": cpl,
            }

        except Exception as e:
            self.set_status("error", str(e))
            await self.log("error", f"Erreur lors du calcul du coup: {e}")
            return {"success": False, "error": str(e)}

    def get_game_result(self):
        """Retourne le résultat de la partie"""
        if self.board.is_checkmate():
            winner = "Noirs" if self.board.turn == chess.WHITE else "Blancs"
            return f"Échec et mat! {winner} gagnent"
        elif self.board.is_stalemate():
            return "Pat - Nulle"
        elif self.board.is_insufficient_material():
            return "Matériel insuffisant - Nulle"
        elif self.board.is_fifty_moves():
            return "Règle des 50 coups - Nulle"
        elif self.board.is_repetition():
            return "Répétition - Nulle"
        return "Partie en cours"

    async def _handle_promotion(self, to_sq: str, pawn_color: chess.Color) -> bool:
        """
        Gère physiquement la promotion d'un pion :
        1. Retire le pion de la case de promotion → cimetière
        2. Demande au joueur de placer la pièce promue (dame) quelque part d'accessible
        3. Attend la confirmation via confirm_promotion()
        4. Robot récupère la dame et la pose sur la case de promotion
        """
        # 1. Retirer le pion vers le cimetière
        self.robot.piece_courante = chess.PAWN
        pawn_obj = chess.Piece(chess.PAWN, pawn_color)
        cx, cy = self.robot.get_square_center(to_sq)
        p_pawn_pos = self.robot.cam_to_robot(cx, cy, use_piece_height=True)

        color_str = "blanche" if pawn_color == chess.WHITE else "noire"
        await self.log("robot", f"Promotion — retrait du pion {color_str} de {to_sq} vers le cimetière")
        self.set_status("moving", "Promotion — retrait du pion")

        success = await self.robot._sequence_elimination(p_pawn_pos, pawn_obj, to_sq)
        if not success:
            self.set_status("idle")
            return False

        # 2. Demander au joueur de placer la dame
        await self.log("info", f"PROMOTION — Placez une dame {color_str} sur une case accessible et confirmez sa position")
        await self.broadcast({
            "type": "promotion_required",
            "square": to_sq,
            "color": "white" if pawn_color == chess.WHITE else "black",
        })

        # 3. Attendre la confirmation (timeout 5 minutes)
        self._promotion_event = asyncio.Event()
        self._promotion_from_sq = None
        self.set_status("moving", "En attente de la pièce de promotion")

        try:
            await asyncio.wait_for(self._promotion_event.wait(), timeout=300.0)
        except asyncio.TimeoutError:
            await self.log("error", "Timeout promotion — aucune confirmation reçue dans les 5 minutes")
            self._promotion_event = None
            self.set_status("idle")
            return False

        if not self._promotion_from_sq:
            self._promotion_event = None
            self.set_status("idle")
            return False

        # 4. Placer la dame sur la case de promotion
        self.robot.piece_courante = chess.QUEEN
        from_sq_promo = self._promotion_from_sq
        await self.log("robot", f"Promotion — placement de la dame depuis {from_sq_promo} → {to_sq}")

        cx_q, cy_q = self.robot.get_square_center(from_sq_promo)
        p_queen_src = self.robot.cam_to_robot(cx_q, cy_q, use_piece_height=True)
        cx_t, cy_t = self.robot.get_square_center(to_sq)
        p_promo_dest = self.robot.cam_to_robot(cx_t, cy_t, use_piece_height=True)

        success = await self.robot._sequence_pick_and_place(p_queen_src, p_promo_dest)

        # Retour en position de sécurité puis home
        if success:
            p_safe = list(p_promo_dest)
            p_safe[2] = self.robot.calib_origin[2] + DELTA_TRANSIT
            await self.robot._move_tcp(p_safe)
            if self.robot.position_depart and not self.robot.is_paused:
                await self.robot._move_tcp(self.robot.position_depart)

        self._promotion_event = None
        self.set_status("idle")
        return success

    def confirm_promotion(self, from_sq: str) -> bool:
        """
        Appelée par l'API quand le joueur a placé la pièce promue.
        from_sq : case où le joueur a déposé la dame (ex: 'a0', 'h9', '99').
        """
        if self._promotion_event and not self._promotion_event.is_set():
            self._promotion_from_sq = from_sq
            self._promotion_event.set()
            return True
        return False

    async def reset_plateau_with_board(self):
        """Remet le plateau en place et replace les pièces déplacées"""
        await self.log("info", "Début du reset du plateau...")
        result = await self.robot.reset_plateau()
        
        if result.get("success"):
            # Replacer les pièces déplacées
            await self._replacer_pieces_deplacees()
            # Réinitialiser le plateau virtuel
            self.board.reset()
            await self.log("info", "✓ Plateau remis en position initiale")
        else:
            await self.log("error", "Échec du reset du plateau")
        
        return result

    async def _replacer_pieces_deplacees(self):
        """Replace les pièces encore sur le plateau à leur position initiale"""
        await self.log("info", "Replacement des pièces déplacées...")

        for case_init, (piece_symbol, color) in POSITION_INITIALE.items():
            square = chess.parse_square(case_init)
            piece_actuelle = self.board.piece_at(square)

            # Si la case n'a pas la bonne pièce
            if piece_actuelle is None or piece_actuelle.symbol().upper() != piece_symbol.upper():
                # Trouver où est la pièce
                case_actuelle = self._trouver_piece_sur_plateau(piece_symbol, color, self.board)

                if case_actuelle and case_actuelle != case_init:
                    await self.log("robot", f"Déplacement {piece_symbol} de {case_actuelle} → {case_init}")

                    # Bug 2 fix : définir le type de pièce AVANT la prise (hauteur Z correcte)
                    self.robot.piece_courante = PIECE_TYPE_MAP.get(piece_symbol.upper(), chess.PAWN)

                    # Bug 3 fix : vérifier le retour de _prendre_piece
                    success = await self.robot._prendre_piece(case_actuelle)
                    if not success or self.is_paused:
                        return

                    # Bug 3 fix : vérifier le retour de _poser_piece
                    success = await self.robot._poser_piece(case_init)
                    if not success or self.is_paused:
                        return

                    # Bug 1 fix : mettre à jour le board virtuel pour que _trouver_piece_sur_plateau
                    # ne retourne plus cette pièce aux prochaines itérations
                    sq_from = chess.parse_square(case_actuelle)
                    sq_to = chess.parse_square(case_init)
                    piece_obj = self.board.piece_at(sq_from)
                    if piece_obj:
                        self.board.remove_piece_at(sq_from)
                        self.board.set_piece_at(sq_to, piece_obj)

    def _trouver_piece_sur_plateau(self, piece_symbol: str, color: bool, board: chess.Board):
        """Trouve la position actuelle d'une pièce sur le plateau"""
        piece_type = PIECE_TYPE_MAP.get(piece_symbol.upper())
        if not piece_type:
            return None

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == piece_type and piece.color == color:
                case_name = chess.square_name(square)
                
                # Ne pas retourner la pièce si elle est déjà à sa position initiale
                if case_name in POSITION_INITIALE:
                    init_piece, init_color = POSITION_INITIALE[case_name]
                    if init_piece.upper() == piece_symbol.upper() and init_color == color:
                        continue
                
                return case_name
        
        return None

    # ------------------------------------------------------------------
    #  Synchronisation vision camera <-> Stockfish
    # ------------------------------------------------------------------

    def _board_to_map(self) -> dict:
        """Convertit l'etat python-chess en {case: code_piece} pour comparaison."""
        result = {}
        type_map = {
            chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
            chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K",
        }
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece:
                color_char = "W" if piece.color == chess.WHITE else "B"
                type_char = type_map.get(piece.piece_type, "?")
                result[chess.square_name(sq)] = f"{color_char}{type_char}"
        return result

    def sync_with_vision(self, stabilized_board: dict) -> dict:
        """
        Compare l'etat Stockfish avec l'etat camera stabilise.
        Detecte les coups (simples et captures) et retourne les anomalies.
        Ne modifie PAS l'etat de Stockfish.
        """
        expected = self._board_to_map()

        # Cases ou le contenu differe entre Stockfish et camera
        disappeared = {}  # case: code — piece Stockfish absente dans camera
        appeared = {}     # case: code — piece camera absente dans Stockfish
        changed = {}      # case: (expected_code, detected_code)

        for sq in set(list(expected.keys()) + list(stabilized_board.keys())):
            exp = expected.get(sq)
            det = stabilized_board.get(sq)
            if exp and not det:
                disappeared[sq] = exp
            elif det and not exp:
                appeared[sq] = det
            elif exp and det and exp != det:
                changed[sq] = (exp, det)

        result = {
            "in_sync": len(disappeared) == 0 and len(appeared) == 0 and len(changed) == 0,
            "disappeared": disappeared,
            "appeared": appeared,
            "changed": changed,
        }

        if result["in_sync"]:
            return result

        # Tenter de deduire un coup a partir des differences
        # Cas 1 : Coup simple — piece disparait de A, apparait sur B (case vide)
        # Cas 2 : Capture — piece disparait de A, piece adverse disparait de B,
        #         piece attaquante apparait sur B (= changed: expected=adverse, detected=attaquant)

        detected_move = None
        suggestions = []

        # Coup simple : une piece blanche disparait, et apparait sur une case vide
        for sq_from, code_from in disappeared.items():
            if not code_from.startswith("W"):
                continue  # On cherche les coups des blancs
            for sq_to, code_to in appeared.items():
                if code_from == code_to:
                    detected_move = {"from": sq_from, "to": sq_to}
                    break
            if detected_move:
                break

        # Capture : une piece blanche disparait de A, et la case B passe de piece noire a piece blanche
        if not detected_move:
            for sq_from, code_from in disappeared.items():
                if not code_from.startswith("W"):
                    continue
                for sq_to, (exp_code, det_code) in changed.items():
                    # La case avait une piece noire, maintenant a la piece blanche
                    if exp_code.startswith("B") and det_code == code_from:
                        detected_move = {"from": sq_from, "to": sq_to}
                        break
                if detected_move:
                    break

        if detected_move:
            from_sq = detected_move["from"]
            to_sq = detected_move["to"]
            # Verifier la legalite (avec et sans promotion)
            legal = False
            for suffix in ["", "q", "r", "b", "n"]:
                try:
                    move = chess.Move.from_uci(f"{from_sq}{to_sq}{suffix}")
                    if move in self.board.legal_moves:
                        legal = True
                        detected_move["to"] = to_sq  # garder la notation simple
                        break
                except ValueError:
                    continue
            detected_move["legal"] = legal
            result["detected_move"] = detected_move
            state = "legal" if legal else "illegal"
            suggestions.append(f"Coup detecte: {disappeared.get(from_sq, '?')} {from_sq} -> {to_sq} ({state})")
        else:
            for sq, code in disappeared.items():
                suggestions.append(f"Piece manquante: {code} en {sq}")

        result["suggestions"] = suggestions
        return result

    def close(self):
        """Ferme Stockfish"""
        if self.engine:
            self.engine.quit()
