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
        """Retourne le meilleur coup pour le joueur actuel"""
        if not self.engine:
            return {"success": False, "error": "Stockfish non disponible"}

        try:
            self.engine.configure({"Skill Level": 20})

            info = self.engine.analyse(
                self.board,
                chess.engine.Limit(depth=15, time=1.0)
            )

            move = info.get("pv", [None])[0]
            if not move:
                return {"success": False, "error": "Pas de coup trouvé"}

            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)

            return {
                "success": True,
                "from": from_sq,
                "to": to_sq
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

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
                    captured_piece = self.board.piece_at(ep_square - 8 if piece.color == chess.WHITE else ep_square + 8)

        # Définir la pièce courante pour le robot
        if piece:
            self.robot.piece_courante = piece.piece_type

        # Exécuter sur le robot
        self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")
        await self.robot.execute_move(from_sq, to_sq, is_capture, captured_piece)

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

    async def play_robot_move(self):
        """Calcule et joue le coup du robot"""
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
                                ep_square - 8 if piece.color == chess.WHITE else ep_square + 8)

            # Définir la pièce courante pour le robot
            piece = self.board.piece_at(move.from_square)
            if piece:
                self.robot.piece_courante = piece.piece_type

            # Évaluation
            score = info.get("score")
            evaluation = 0.0
            if score and score.relative.score():
                evaluation = score.relative.score() / 100

            await self.log("robot", f"Coup choisi: {from_sq} → {to_sq} (eval: {evaluation:+.2f})")

            # Exécuter sur le robot
            self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")
            await self.robot.execute_move(from_sq, to_sq, is_capture, captured_piece)

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
                return {"success": True, "from": from_sq, "to": to_sq, "san": san, "game_over": True, "result": result}

            return {"success": True, "from": from_sq, "to": to_sq, "san": san, "evaluation": evaluation}

        except Exception as e:
            self.set_status("error", str(e))
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
        result = await self.robot.reset_plateau()
        
        if result.get("success"):
            # Replacer les pièces déplacées
            await self._replacer_pieces_deplacees()
            self.board.reset()
        
        return result

    async def _replacer_pieces_deplacees(self):
        """Replace les pièces encore sur le plateau à leur position initiale"""
        for case_init, (piece_symbol, color) in POSITION_INITIALE.items():
            square = chess.parse_square(case_init)
            piece_actuelle = self.board.piece_at(square)

            if piece_actuelle is None or piece_actuelle.symbol().upper() != piece_symbol.upper():
                case_actuelle = self._trouver_piece_sur_plateau(piece_symbol, color, self.board)

                if case_actuelle and case_actuelle != case_init:
                    await self.log("robot", f"Déplacement {piece_symbol} de {case_actuelle} → {case_init}")
                    await self.robot._prendre_piece(case_actuelle)
                    self.robot.piece_courante = PIECE_TYPE_MAP.get(piece_symbol.upper(), chess.PAWN)
                    await self.robot._poser_piece(case_init)

    def _trouver_piece_sur_plateau(self, piece_symbol: str, color: bool, board: chess.Board):
        """Trouve la position actuelle d'une pièce sur le plateau"""
        piece_type = PIECE_TYPE_MAP.get(piece_symbol.upper())
        if not piece_type:
            return None

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == piece_type and piece.color == color:
                case_name = chess.square_name(square)
                if case_name in POSITION_INITIALE:
                    init_piece, init_color = POSITION_INITIALE[case_name]
                    if init_piece.upper() == piece_symbol.upper() and init_color == color:
                        continue
                return case_name
        return None

    def close(self):
        """Ferme Stockfish"""
        if self.engine:
            self.engine.quit()
