#!/usr/bin/env python3
"""
Configuration et constantes pour le robot d'échecs
"""

import chess

# ============================================================================
#                         CONFIGURATION ROBOT
# ============================================================================

ROBOT_IP = "192.168.0.11"
VITESSE = 0.2          # Légèrement augmentée pour fluidité
ACCELERATION = 0.4
GRIPPER_OUVERTURE = 25
DELTA_APPROCHE = 0.03  # 3cm - hauteur d'approche avant descente
DELTA_TRANSIT = 0.12   # 12cm - hauteur de déplacement à vide
DELTA_RELACHE_BASE = 0.001  # 1mm - hauteur de relâche
ESPACEMENT_ELIMINATION = 0.02  # 2cm entre les pièces éliminées

# ============================================================================
#                         FICHIERS DE DONNÉES
# ============================================================================

FICHIER_POSITION_DEPART = "position_depart_robot.json"
# FICHIER_MAPPING est supprimé car remplacé par la calibration dynamique
FICHIER_CALIBRATION = "robot_calibration.json"

# ============================================================================
#                         DIMENSIONS & CALIBRATION
# ============================================================================

# Distance physique entre le bord de la case (A8 ou H1) et le centre du trou de calibration
OFFSET_TROU_MM = 10.0
OFFSET_TROU_M = 0.010

# ============================================================================
#                         HAUTEURS PAR TYPE DE PIÈCE
# ============================================================================

HAUTEUR_PIECES = {
    chess.PAWN: 0.005,
    chess.KNIGHT: 0.010,
    chess.BISHOP: 0.012,
    chess.ROOK: 0.008,
    chess.QUEEN: 0.015,
    chess.KING: 0.018,
}

# ============================================================================
#                         NIVEAUX DE DIFFICULTÉ
# ============================================================================

DIFFICULTY_PRESETS = {
    'beginner': {'skill_level': 3, 'depth': 8, 'time_limit': 0.5},
    'intermediate': {'skill_level': 10, 'depth': 12, 'time_limit': 1.0},
    'advanced': {'skill_level': 18, 'depth': 18, 'time_limit': 2.0},
}

# ============================================================================
#                         POSITION INITIALE
# ============================================================================

POSITION_INITIALE = {
    'a1': ('R', chess.WHITE), 'b1': ('N', chess.WHITE), 'c1': ('B', chess.WHITE), 'd1': ('Q', chess.WHITE),
    'e1': ('K', chess.WHITE), 'f1': ('B', chess.WHITE), 'g1': ('N', chess.WHITE), 'h1': ('R', chess.WHITE),
    'a2': ('P', chess.WHITE), 'b2': ('P', chess.WHITE), 'c2': ('P', chess.WHITE), 'd2': ('P', chess.WHITE),
    'e2': ('P', chess.WHITE), 'f2': ('P', chess.WHITE), 'g2': ('P', chess.WHITE), 'h2': ('P', chess.WHITE),
    'a7': ('p', chess.BLACK), 'b7': ('p', chess.BLACK), 'c7': ('p', chess.BLACK), 'd7': ('p', chess.BLACK),
    'e7': ('p', chess.BLACK), 'f7': ('p', chess.BLACK), 'g7': ('p', chess.BLACK), 'h7': ('p', chess.BLACK),
    'a8': ('r', chess.BLACK), 'b8': ('n', chess.BLACK), 'c8': ('b', chess.BLACK), 'd8': ('q', chess.BLACK),
    'e8': ('k', chess.BLACK), 'f8': ('b', chess.BLACK), 'g8': ('n', chess.BLACK), 'h8': ('r', chess.BLACK),
}

# ============================================================================
#                         MAPPING SYMBOLE -> TYPE
# ============================================================================

PIECE_TYPE_MAP = {
    'P': chess.PAWN, 'p': chess.PAWN,
    'N': chess.KNIGHT, 'n': chess.KNIGHT,
    'B': chess.BISHOP, 'b': chess.BISHOP,
    'R': chess.ROOK, 'r': chess.ROOK,
    'Q': chess.QUEEN, 'q': chess.QUEEN,
    'K': chess.KING, 'k': chess.KING,
}

# ============================================================================
#                         CHEMINS STOCKFISH
# ============================================================================

STOCKFISH_PATHS = [
    '/usr/games/stockfish',
    '/usr/bin/stockfish',
    '/usr/local/bin/stockfish',
    '/opt/homebrew/bin/stockfish',
    '/opt/homebrew/Cellar/stockfish/17/bin/stockfish',
    'stockfish'
]