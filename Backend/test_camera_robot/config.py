#!/usr/bin/env python3
"""
Configuration pour test_camera_robot.

Centralise les chemins, mappings et constantes
utilises par les autres modules du package.
"""

import os
import re
import chess

# ---------------------------------------------------------------------------
#  Chemins
# ---------------------------------------------------------------------------

# Racine du projet (chess-project/)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)

# Fichier produit par infinite_chess_vision.py
GAME_STATE_PATH = os.path.join(PROJECT_ROOT, "game_state.json")

# Repertoire manipulation_robot (pour calibration, config)
MANIP_DIR = os.path.join(_BACKEND_DIR, "manipulation_robot")

# ---------------------------------------------------------------------------
#  Mappings de type de piece  (vision -> python-chess)
# ---------------------------------------------------------------------------

VISION_TYPE_TO_CHESS = {
    "Pawn":   chess.PAWN,
    "Knight": chess.KNIGHT,
    "Bishop": chess.BISHOP,
    "Rook":   chess.ROOK,
    "Queen":  chess.QUEEN,
    "King":   chess.KING,
}

# ---------------------------------------------------------------------------
#  Affichage console
# ---------------------------------------------------------------------------

DISPLAY_SYMBOLS = {
    "WK": "K", "WQ": "Q", "WR": "R", "WB": "B", "WN": "N", "WP": "P",
    "BK": "k", "BQ": "q", "BR": "r", "BB": "b", "BN": "n", "BP": "p",
}

# ---------------------------------------------------------------------------
#  Validation de case
# ---------------------------------------------------------------------------

SQUARE_PATTERN = re.compile(r'^[a-h][1-8]$')
