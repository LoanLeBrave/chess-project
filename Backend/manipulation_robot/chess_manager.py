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

from config import DIFFICULTY_PRESETS, POSITION_INITIALE, PIECE_TYPE_MAP, STOCKFISH_PATHS
from robot_controller import RobotController


class ChessManager:
    """Gestionnaire de la logique d'échecs et de l'IA"""

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
        self.is_paused = not self.is_paused

        if self.is_paused:
            # PAUSE D'URGENCE
            self.robot.pause_urgence()
            await self.log("warning", " PAUSE D'URGENCE - Robot arrêté immédiatement!")
            self.set_status("paused", "PAUSE D'URGENCE")
            return {"success": True, "paused": True, "message": "PAUSE D'URGENCE - Robot arrêté!"}
        else:
            # Reprise
            self.robot.reprendre_script()
            await self.log("info", " Partie reprise - Robot réactivé")
            self.set_status("idle", "Partie reprise")
            return {"success": True, "paused": False, "message": "Partie reprise"}

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
        if is_capture:
            to_square = chess.parse_square(to_sq)
            captured_piece = self.board.piece_at(to_square)
            # En passant
            if captured_piece is None and piece and piece.piece_type == chess.PAWN:
                ep_square = self.board.ep_square
                if ep_square:
                    captured_piece = self.board.piece_at(
                        ep_square - 8 if piece.color == chess.WHITE else ep_square + 8
                    )

        # Définir la pièce courante pour le robot
        if piece:
            self.robot.piece_courante = piece.piece_type

        # Coordonnees precises de la camera si disponibles
        precise_coords = self._get_precise_coords(from_sq)

        # Exécuter sur le robot
        self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")
        success = await self.robot.execute_move(from_sq, to_sq, is_capture, captured_piece, precise_pick_coords=precise_coords)

        if not success:
            await self.log("warning", "Mouvement interrompu par PAUSE")
            return {"success": False, "error": "Mouvement interrompu"}

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
            if is_capture:
                captured_piece = self.board.piece_at(move.to_square)
                # En passant
                if captured_piece is None:
                    piece = self.board.piece_at(move.from_square)
                    if piece and piece.piece_type == chess.PAWN:
                        ep_square = self.board.ep_square
                        if ep_square:
                            captured_piece = self.board.piece_at(
                                ep_square - 8 if piece.color == chess.WHITE else ep_square + 8
                            )

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

            await self.log("robot", f"Coup choisi: {from_sq} → {to_sq} (eval: {evaluation})")

            # Coordonnees precises de la camera si disponibles
            precise_coords = self._get_precise_coords(from_sq)

            # Exécuter sur le robot
            self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")
            success = await self.robot.execute_move(from_sq, to_sq, is_capture, captured_piece, precise_pick_coords=precise_coords)
            
            if not success:
                await self.log("warning", "Mouvement interrompu par PAUSE")
                self.set_status("idle")
                return {"success": False, "error": "Mouvement interrompu"}

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
                    "game_over": True,
                    "result": result
                }

            return {
                "success": True,
                "from": from_sq,
                "to": to_sq,
                "san": san,
                "evaluation": evaluation
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
                    
                    # Prendre la pièce
                    await self.robot._prendre_piece(case_actuelle)
                    if self.is_paused:
                        return
                    
                    # Définir le type de pièce
                    self.robot.piece_courante = PIECE_TYPE_MAP.get(piece_symbol.upper(), chess.PAWN)
                    
                    # Poser la pièce
                    await self.robot._poser_piece(case_init)
                    if self.is_paused:
                        return

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
