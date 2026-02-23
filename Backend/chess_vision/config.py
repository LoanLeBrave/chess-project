#!/usr/bin/env python3
"""
Configuration centralisée pour le système de vision échecs.
Toutes les constantes et paramètres sont définis ici pour faciliter la maintenance.

Modules:
    - ArUco: Dictionnaire et IDs
    - Calibration: Offsets pour les coins du plateau
    - Pièces: Mapping ID → information pièce
    - Caméra: Paramètres de capture
    - Détection: Paramètres ArUco optimisés
"""

import cv2
import os

# ============================================================
# CHEMINS ET DOSSIERS
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
CALIBRATION_FILE = os.path.join(SCRIPT_DIR, "board_calibration.json")

# ============================================================
# CONFIGURATION ARUCO
# ============================================================
# Dictionnaire ArUco utilisé (doit correspondre aux marqueurs imprimés)
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50

# IDs des marqueurs de calibration (coins du plateau)
CALIBRATION_IDS = {
    32: 'TL',  # Top-Left (Haut-Gauche)
    33: 'TR',  # Top-Right (Haut-Droite)
    34: 'BL',  # Bottom-Left (Bas-Gauche)
    35: 'BR',  # Bottom-Right (Bas-Droite)
}

# Codes complets pour la calibration
CALIBRATION_CODES = {
    32: 'CAL_TL',
    33: 'CAL_TR',
    34: 'CAL_BL',
    35: 'CAL_BR',
}

# ============================================================
# CALIBRATION DU PLATEAU (COINS FIXES)
# ============================================================
# Les coins du plateau sont définis par calibration manuelle.
# Lancer: python -m chess_vision.calibrate_board
# Le fichier board_calibration.json est généré automatiquement.
#
# ⚠️ Ne pas déplacer la caméra après calibration!

import json as _json

def load_board_corners():
    """
    Charge les coins du plateau depuis board_calibration.json.
    
    Returns:
        Dict {'TL': (x, y), 'TR': (x, y), 'BR': (x, y), 'BL': (x, y)}
        ou None si pas de calibration
    """
    if not os.path.exists(CALIBRATION_FILE):
        return None
    try:
        with open(CALIBRATION_FILE, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        corners = {}
        for code in ['TL', 'TR', 'BR', 'BL']:
            c = data['corners'][code]
            corners[code] = (c['x'], c['y'])
        return corners
    except (KeyError, ValueError, FileNotFoundError) as e:
        print(f"⚠️ Erreur chargement calibration: {e}")
        return None

# Coins du plateau chargés depuis la calibration
FIXED_BOARD_CORNERS = load_board_corners()

# Legacy: anciens offsets (obsolètes, gardés pour compatibilité)
OFFSETS = {
    "TL": {"x": -70, "y": -155},
    "TR": {"x": -96, "y": 47},
    "BL": {"x": 111, "y": -128},
    "BR": {"x": 87, "y": 57}
}

# ============================================================
# CONFIGURATION DU PLATEAU
# ============================================================
# Grille étendue 10x10 : plateau 8x8 + cimetière 1 case autour
GRID_SIZE = 10           # Grille totale (plateau + cimetière)
CHESS_GRID_SIZE = 8      # Plateau d'échecs seul

# Taille de l'image extraite (carré)
# 10 cases x 100px/case = 1000px (résolution identique à l'ancien 800px pour 8 cases)
EXTRACTED_BOARD_SIZE = 1000
CELL_SIZE_PX = EXTRACTED_BOARD_SIZE // GRID_SIZE  # 100px par case

# Repère de coordonnées du plateau central (8x8) - INCHANGE
# Utilisé par le reste du code (robot, traduction coordonnées...)
BOARD_COORD_MIN = -10
BOARD_COORD_MAX = 10
BOARD_COORD_RANGE = BOARD_COORD_MAX - BOARD_COORD_MIN  # 20

# Repère étendu (10x10, plateau + cimetière)
# 10 cases x 2.5 unités/case = 25 unités
EXTENDED_COORD_MIN = -12.5
EXTENDED_COORD_MAX = 12.5
EXTENDED_COORD_RANGE = EXTENDED_COORD_MAX - EXTENDED_COORD_MIN  # 25
CELL_COORD_SIZE = EXTENDED_COORD_RANGE / GRID_SIZE  # 2.5 unités par case

# ============================================================
# NOTATION DES CASES
# ============================================================
# Colonnes : 0, A, B, C, D, E, F, G, H, 9
# Lignes   : 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
# Plateau  : A1-H8 (64 cases)
# Cimetière: toute case avec colonne 0/9 ou ligne 0/9 (36 cases)
GRID_COLUMNS = ['0', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', '9']
GRID_ROWS    = ['9', '8', '7', '6', '5', '4', '3', '2', '1', '0']  # 9 en haut (y=0)
CHESS_COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
CHESS_ROWS    = ['8', '7', '6', '5', '4', '3', '2', '1']

# Ordre de remplissage du cimetière (sens anti-horaire depuis haut-gauche)
CEMETERY_FILL_ORDER = [
    '08', '07', '06', '05', '04', '03', '02', '01',  # colonne gauche (haut → bas)
    '00', 'A0', 'B0', 'C0', 'D0', 'E0', 'F0', 'G0', 'H0',  # ligne bas (gauche → droite)
    '90', '91', '92', '93', '94', '95', '96', '97', '98',    # colonne droite (bas → haut)
    '99', 'H9', 'G9', 'F9', 'E9', 'D9', 'C9', 'B9', 'A9', '09',  # ligne haut (droite → gauche)
]

# ============================================================
# CONFIGURATION DES PIÈCES D'ÉCHECS
# ============================================================
# Mapping ArUco ID → Information pièce
# Convention utilisée:
#   - IDs 0-15: Pièces blanches
#   - IDs 16-31: Pièces noires
#   - W = White, B = Black
#   - K = King, Q = Queen, R = Rook, B = Bishop, N = Knight, P = Pawn

PIECES = {
    # Pièces blanches (IDs 0-15)
    0: {'code': 'WP1', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_A', 'symbol': '♙'},
    1: {'code': 'WP2', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_B', 'symbol': '♙'},
    2: {'code': 'WP3', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_C', 'symbol': '♙'},
    3: {'code': 'WP4', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_D', 'symbol': '♙'},
    4: {'code': 'WP5', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_E', 'symbol': '♙'},
    5: {'code': 'WP6', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_F', 'symbol': '♙'},
    6: {'code': 'WP7', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_G', 'symbol': '♙'},
    7: {'code': 'WP8', 'color': 'white', 'type': 'Pawn', 'initial': 'Pawn_H', 'symbol': '♙'},
    8: {'code': 'WR1', 'color': 'white', 'type': 'Rook', 'initial': 'Rook_A', 'symbol': '♖'},
    9: {'code': 'WR2', 'color': 'white', 'type': 'Rook', 'initial': 'Rook_H', 'symbol': '♖'},
    10: {'code': 'WN1', 'color': 'white', 'type': 'Knight', 'initial': 'Knight_B', 'symbol': '♘'},
    11: {'code': 'WN2', 'color': 'white', 'type': 'Knight', 'initial': 'Knight_G', 'symbol': '♘'},
    12: {'code': 'WB1', 'color': 'white', 'type': 'Bishop', 'initial': 'Bishop_C', 'symbol': '♗'},
    13: {'code': 'WB2', 'color': 'white', 'type': 'Bishop', 'initial': 'Bishop_F', 'symbol': '♗'},
    14: {'code': 'WQ', 'color': 'white', 'type': 'Queen', 'initial': 'Queen', 'symbol': '♕'},
    15: {'code': 'WK', 'color': 'white', 'type': 'King', 'initial': 'King', 'symbol': '♔'},
    
    # Pièces noires (IDs 16-31)
    16: {'code': 'BP1', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_A', 'symbol': '♟'},
    17: {'code': 'BP2', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_B', 'symbol': '♟'},
    18: {'code': 'BP3', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_C', 'symbol': '♟'},
    19: {'code': 'BP4', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_D', 'symbol': '♟'},
    20: {'code': 'BP5', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_E', 'symbol': '♟'},
    21: {'code': 'BP6', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_F', 'symbol': '♟'},
    22: {'code': 'BP7', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_G', 'symbol': '♟'},
    23: {'code': 'BP8', 'color': 'black', 'type': 'Pawn', 'initial': 'Pawn_H', 'symbol': '♟'},
    24: {'code': 'BR1', 'color': 'black', 'type': 'Rook', 'initial': 'Rook_A', 'symbol': '♜'},
    25: {'code': 'BR2', 'color': 'black', 'type': 'Rook', 'initial': 'Rook_H', 'symbol': '♜'},
    26: {'code': 'BN1', 'color': 'black', 'type': 'Knight', 'initial': 'Knight_B', 'symbol': '♞'},
    27: {'code': 'BN2', 'color': 'black', 'type': 'Knight', 'initial': 'Knight_G', 'symbol': '♞'},
    28: {'code': 'BB1', 'color': 'black', 'type': 'Bishop', 'initial': 'Bishop_C', 'symbol': '♝'},
    29: {'code': 'BB2', 'color': 'black', 'type': 'Bishop', 'initial': 'Bishop_F', 'symbol': '♝'},
    30: {'code': 'BQ', 'color': 'black', 'type': 'Queen', 'initial': 'Queen', 'symbol': '♛'},
    31: {'code': 'BK', 'color': 'black', 'type': 'King', 'initial': 'King', 'symbol': '♚'},
}

# IDs des pièces (0-31)
PIECE_IDS = set(range(32))

# ============================================================
# CONFIGURATION CAMÉRA RASPBERRY PI
# ============================================================
USE_DEFAULT_CAMERA_PARAMS = False

CAMERA_CONFIG = {
    'width': None,                    # None = max résolution
    'height': None,                   # None = max résolution
    'shutter': None,                  # Temps exposition µs (None = auto)
    'gain': None,                     # Gain (1.0 = minimum)
    'awb': None,                      # Balance blancs: 'auto', 'tungsten', etc.
    'brightness': None,               # -1.0 à 1.0
    'contrast': None,                 # 1.0 = normal
    'saturation': None,               # 1.0 = normal
    'sharpness': None,                # 1.0 = normal
    'denoise': None,                  # 'auto', 'off', etc.
    'timeout': 50,                    # Temps stabilisation (ms) - ULTRA-RAPIDE (focus manuel)
    'stabilization_delay': 0.3,       # Délai stabilisation Picamera2 (s) - Réduit: 2.0→0.3
    'autofocus_mode': 'manual',       # 'auto', 'manual', 'continuous'
    'lens_position': 9.0,            # Position focus manuel (0.0-10.0) - Optimisé pour ArUco
    'autofocus_on_capture': False,    # Force autofocus avant capture
}

# ============================================================
# PARAMÈTRES DE DÉTECTION ARUCO
# ============================================================
# True = utilise les paramètres par défaut d'OpenCV
# False = utilise les paramètres personnalisés ci-dessous
USE_DEFAULT_ARUCO_PARAMS = False

# Paramètres personnalisés (optimisés pour lumière non uniforme + bords blancs)
ARUCO_PARAMS = {
    'adaptiveThreshWinSizeMin': 5,            # Augmenté: 3→5 (fenêtre plus large = lisse variations lumière)
    'adaptiveThreshWinSizeMax': 100,          # Augmenté: 50→100 (gère grandes zones lumineuses)
    'adaptiveThreshWinSizeStep': 3,           # Réduit: 5→3 (plus de tests entre min/max)
    'adaptiveThreshConstant': 15,             # Augmenté: 10→15 (très tolérant aux variations)
    'minMarkerPerimeterRate': 0.015,          # Réduit: 0.02→0.015 (lumière change périmètre apparent)
    'maxMarkerPerimeterRate': 5.0,            # Augmenté: 4.0→5.0 (accepte marqueurs paraissant plus grands)
    'polygonalApproxAccuracyRate': 0.12,      # Augmenté: 0.08→0.12 (lumière déforme contours)
    'minCornerDistanceRate': 0.03,            # Réduit: 0.05→0.03 (coins peuvent sembler plus proches)
    'minDistanceToBorder': 0,                 # Permet détection près des bords
    'minMarkerDistanceRate': 0.03,            # Réduit: 0.05→0.03 (marqueurs proches OK)
    'cornerRefinementMethod': cv2.aruco.CORNER_REFINE_SUBPIX,  # Raffinement subpixel
    'cornerRefinementWinSize': 7,             # Augmenté: 5→7 (fenêtre raffinement plus large)
    'cornerRefinementMaxIterations': 50,      # Augmenté: 30→50 (plus d'itérations pour converger)
    'cornerRefinementMinAccuracy': 0.15,      # Augmenté: 0.1→0.15 (accepte raffinement imparfait)
}

# ============================================================
# PIPELINE DE PRÉTRAITEMENT D'IMAGE
# ============================================================
# Chaque step est appliquée dans l'ordre avant la détection ArUco.
# Mettre enabled=True pour activer, False pour désactiver.
#
# Steps disponibles (voir modules/preprocessing.py) :
#   clahe     - Contraste adaptatif local (lumière non uniforme)
#   denoise   - Débruitage (bruit capteur)
#   sharpen   - Accentuation des contours
#   gamma     - Correction luminosité (< 1.0 = éclaircit)
#   bilateral - Lissage doux (préserve les bords)
#
# Ajouter une step : écrire step_xxx() dans preprocessing.py
#                    puis l'ajouter ici avec enabled=True.

PREPROCESSING_PIPELINE = [
    {
        'name': 'clahe',
        'enabled': False,
        'params': {'clip_limit': 2.0, 'tile_size': 8},
    },
    {
        'name': 'denoise',
        'enabled': False,
        'params': {'strength': 10},
    },
    {
        'name': 'sharpen',
        'enabled': False,
        'params': {'strength': 1.5},
    },
    {
        'name': 'gamma',
        'enabled': False,
        'params': {'gamma': 1.0},
    },
    {
        'name': 'bilateral',
        'enabled': False,
        'params': {'d': 9, 'sigma': 75},
    },
]

# ============================================================
# COULEURS POUR VISUALISATION (BGR pour OpenCV)
# ============================================================
COLORS = {
    'aruco_marker': (0, 255, 0),      # Vert
    'aruco_center': (0, 0, 255),      # Rouge
    'board_corner': (255, 0, 255),    # Magenta
    'board_outline': (255, 165, 0),   # Orange
    'offset_line': (255, 255, 0),     # Cyan
    'grid': (0, 255, 0),              # Vert
    'text_bg': (255, 255, 255),       # Blanc
    'white_piece': (255, 255, 255),   # Blanc
    'black_piece': (50, 50, 50),      # Gris foncé
}


def get_piece_info(marker_id: int) -> dict:
    """
    Retourne les informations d'une pièce à partir de son ID ArUco.
    
    Args:
        marker_id: ID du marqueur ArUco
        
    Returns:
        dict avec code, color, type, initial, symbol
    """
    if marker_id in PIECES:
        return PIECES[marker_id].copy()
    return {
        'code': f'?{marker_id}',
        'color': 'unknown',
        'type': 'Unknown',
        'initial': 'Unknown',
        'symbol': '?'
    }


def get_calibration_code(marker_id: int):
    """
    Retourne le code de calibration pour un ID donné.
    
    Args:
        marker_id: ID du marqueur de calibration (32-35)
        
    Returns:
        Code court (TL, TR, BL, BR) ou None
    """
    return CALIBRATION_IDS.get(marker_id)


def is_calibration_marker(marker_id: int) -> bool:
    """Vérifie si l'ID est un marqueur de calibration."""
    return marker_id in CALIBRATION_IDS


def is_piece_marker(marker_id: int) -> bool:
    """Vérifie si l'ID est un marqueur de pièce."""
    return marker_id in PIECE_IDS


# ============================================================
# CLASSE CONFIG (WRAPPER POUR TESTS)
# ============================================================
class Config:
    """
    Classe wrapper qui expose toutes les constantes de configuration.
    Utile pour les tests et pour passer la config en paramètre.
    """
    
    # Chemins
    SCRIPT_DIR = SCRIPT_DIR
    OUTPUT_DIR = OUTPUT_DIR
    IMAGES_DIR = IMAGES_DIR
    
    # ArUco
    ARUCO_DICT_TYPE = ARUCO_DICT_TYPE
    CALIBRATION_IDS = {v: k for k, v in CALIBRATION_IDS.items()}  # Inversé: 'TL' -> 32
    CALIBRATION_IDS_BY_ID = CALIBRATION_IDS  # Original: 32 -> 'TL'
    CALIBRATION_CODES = CALIBRATION_CODES
    
    # Offsets
    OFFSETS = OFFSETS
    
    # Plateau
    BOARD_OUTPUT_SIZE = EXTRACTED_BOARD_SIZE
    EXTRACTED_BOARD_SIZE = EXTRACTED_BOARD_SIZE
    GRID_SIZE = GRID_SIZE
    CHESS_GRID_SIZE = CHESS_GRID_SIZE
    BOARD_COORD_MIN = BOARD_COORD_MIN
    BOARD_COORD_MAX = BOARD_COORD_MAX
    BOARD_COORD_RANGE = BOARD_COORD_RANGE
    EXTENDED_COORD_MIN = EXTENDED_COORD_MIN
    EXTENDED_COORD_MAX = EXTENDED_COORD_MAX
    EXTENDED_COORD_RANGE = EXTENDED_COORD_RANGE
    CELL_COORD_SIZE = CELL_COORD_SIZE
    
    # Pièces
    PIECES = PIECES
    PIECE_IDS = PIECE_IDS
    
    # Paramètres ArUco
    ARUCO_PARAMS = ARUCO_PARAMS
    
    # Caméra
    CAMERA_CONFIG = CAMERA_CONFIG
    
    @classmethod
    def get_piece_info(cls, marker_id: int):
        """Retourne les informations d'une pièce."""
        return get_piece_info(marker_id)
    
    @classmethod
    def get_calibration_code(cls, marker_id: int):
        """Retourne le code de calibration."""
        return get_calibration_code(marker_id)
    
    @classmethod
    def is_calibration_marker(cls, marker_id: int) -> bool:
        """Vérifie si c'est un marqueur de calibration."""
        return is_calibration_marker(marker_id)
    
    @classmethod
    def is_piece_marker(cls, marker_id: int) -> bool:
        """Vérifie si c'est un marqueur de pièce."""
        return is_piece_marker(marker_id)
