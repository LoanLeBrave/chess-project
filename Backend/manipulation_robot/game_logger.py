#!/usr/bin/env python3
"""
Journalisation persistante des parties d'échecs.
Chaque partie génère un fichier horodaté dans le dossier logs/.
"""

import os
import json
import chess
import chess.pgn
import io
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


class GameLogger:
    def __init__(self):
        self._file = None
        self._path = None
        self._move_number = 0
        self._game_ended = False
        os.makedirs(LOGS_DIR, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Cycle de vie de la partie                                           #
    # ------------------------------------------------------------------ #

    def start_game(self, difficulty: str):
        """Ouvre un nouveau fichier de log pour la partie."""
        if self._file:
            self._finalize("abandoned", board=None)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(LOGS_DIR, f"game_{ts}.log")
        self._move_number = 0
        self._game_ended = False
        self._file = open(self._path, "w", encoding="utf-8")

        self._write("=" * 60)
        self._write("  CHESS ROBOT — Journal de partie")
        self._write("=" * 60)
        self._write(f"  Date       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._write(f"  Difficulté : {difficulty}")
        self._write("=" * 60)
        self._write("")

    def end_game(self, result: str, board: chess.Board = None):
        """Appelé à la fin normale ou à l'arrêt manuel. Idempotent."""
        if self._game_ended:
            return
        self._finalize(result, board)

    # ------------------------------------------------------------------ #
    #  Écriture des événements                                             #
    # ------------------------------------------------------------------ #

    def log_message(self, log_type: str, message: str):
        """Écrit un message de log système."""
        if not self._file:
            return
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._write(f"[{ts}] [{log_type.upper():<8s}] {message}")

    def log_move(
        self,
        player: str,
        from_sq: str,
        to_sq: str,
        san: str,
        fen_after: str,
        evaluation=None,
        cpl: int = None,
    ):
        """Écrit un coup joué avec son contexte."""
        if not self._file:
            return
        self._move_number += 1
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        eval_str = f"  éval={evaluation}" if evaluation is not None else ""
        cpl_str = f"  CPL={cpl}" if cpl is not None else ""
        self._write("")
        self._write(f"  ┌── Coup #{self._move_number:>3d}  [{player.upper():<6s}]  {san:<8s}  ({from_sq}→{to_sq}){eval_str}{cpl_str}")
        self._write(f"  │   FEN : {fen_after}")
        self._write(f"  └── [{ts}]")

    def log_vision_snapshot(self, label: str, stable_board: dict, raw_board: dict):
        """Capture l'état brut de la vision au moment d'une détection."""
        if not self._file:
            return
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._write("")
        self._write(f"  [VISION — {ts}] {label}")
        self._write(f"    stable : {json.dumps(stable_board, ensure_ascii=False)}")
        self._write(f"    raw    : {json.dumps(raw_board, ensure_ascii=False)}")

    # ------------------------------------------------------------------ #
    #  Interne                                                             #
    # ------------------------------------------------------------------ #

    def _finalize(self, result: str, board: chess.Board = None):
        if not self._file:
            return
        self._game_ended = True

        self._write("")
        self._write("=" * 60)
        self._write(f"  FIN DE PARTIE : {result}")
        self._write(f"  Heure de fin   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._write(f"  Nombre de coups: {self._move_number}")

        # Export PGN si la board est disponible
        if board and board.move_stack:
            try:
                pgn_game = chess.pgn.Game()
                pgn_game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
                pgn_game.headers["Result"] = self._result_to_pgn(result)
                node = pgn_game
                temp = chess.Board()
                for move in board.move_stack:
                    node = node.add_variation(move)
                    temp.push(move)
                exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
                pgn_str = pgn_game.accept(exporter)
                self._write("")
                self._write("  PGN :")
                self._write(f"  {pgn_str}")
            except Exception as e:
                self._write(f"  (PGN non disponible : {e})")

        self._write("=" * 60)
        self._file.close()
        self._file = None

    def _result_to_pgn(self, result: str) -> str:
        mapping = {"win": "1-0", "lose": "0-1", "draw": "1/2-1/2", "abandoned": "*"}
        return mapping.get(result, "*")

    def _write(self, line: str):
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()
