#!/usr/bin/env python3
"""
Configuration et constantes pour le robot d'échecs
"""

import os
import chess
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# ============================================================================
#                         SÉCURITÉ & ACCÈS
# ============================================================================

# Code d'accès par défaut si non spécifié dans le .env
ACCESS_PIN = os.getenv("ACCESS_PIN", "1303")


ROBOT_IP = "192.168.0.11"
VITESSE = 0.8
ACCELERATION = 0.8
GRIPPER_OUVERTURE = 25
GRIPPER_OUVERTURE_CHEVALIER = 28  # ouverture élargie pour le chevalier (65% vs 55%)
DELTA_APPROCHE = 0.03   # 3cm
DELTA_TRANSIT = 0.15    # 15cm
DELTA_RELACHE_BASE = 0.001

# ============================================================================
#                         CIMETIÈRE (grille 10x10 étendue)
# ============================================================================

# Cases du cimetière pour les blancs capturés (rangée 0, puis colonne gauche)
CIMETIERE_BLANCS = [
    "a0", "b0", "c0", "d0", "e0", "f0", "g0", "h0",  # Rangée 0 — colonnes A-H
    "00", "90",                                         # Coins bas gauche / bas droit
    "01", "02", "03", "04", "05", "06", "07", "08",    # Colonne 0 — rangées 1-8
]

# Cases du cimetière pour les noirs capturés (rangée 9, puis colonne droite)
CIMETIERE_NOIRS = [
    "a9", "b9", "c9", "d9", "e9", "f9", "g9", "h9",  # Rangée 9 — colonnes A-H
    "09", "99",                                         # Coins haut gauche / haut droit
    "91", "92", "93", "94", "95", "96", "97", "98",    # Colonne 9 — rangées 1-8
]

# ============================================================================
#                         FICHIERS DE DONNÉES
# ============================================================================

FICHIER_POSITION_DEPART = "position_depart_robot.json"
FICHIER_CALIBRATION = "robot_calibration.json"

# ============================================================================
#                         DIMENSIONS & CALIBRATION
# ============================================================================

# CORRECTION DU DÉCALAGE 18MM
# Le robot allait 18mm trop loin (Total largeur erreur = 36mm).
# Ancien Offset (10mm) - Erreur (18mm) = -8.0mm
# Cela va "rétrécir" la grille virtuelle du robot pour qu'elle colle à la réalité.
OFFSET_TROU_MM = 0
OFFSET_TROU_M = 0

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
    'intermediate': {'skill_level': 10, 'depth': 12, 'time_limit': 0.5},
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