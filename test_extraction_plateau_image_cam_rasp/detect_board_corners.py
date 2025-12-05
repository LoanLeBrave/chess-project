#!/usr/bin/env python3
"""
Détection des 4 coins du plateau d'échecs via ArUcos de calibration
et visualisation du plateau avec offsets configurables.

Les ArUcos de calibration sont placés à l'extérieur du plateau,
donc on applique des offsets pour définir les vrais coins du plateau.

Usage:
    python detect_board_corners.py                # Mode interactif (photo ou image existante)
    python detect_board_corners.py [chemin_image] # Analyser une image existante
    python detect_board_corners.py --photo        # Prendre une photo et analyser
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import subprocess
import shutil
import json
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Dossiers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMAGES_DIR = os.path.join(SCRIPT_DIR, "..", "analyse", "images")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Taille de l'image extraite du plateau (en pixels)
# L'image sera un carré de cette dimension
EXTRACTED_BOARD_SIZE = 800

# ============================================================
# CONFIGURATION CAMÉRA RASPBERRY PI
# ============================================================
# True = utilise les paramètres par défaut de la caméra (auto pour tout)
# False = utilise nos paramètres personnalisés ci-dessous
USE_DEFAULT_CAMERA_PARAMS = True

CAMERA_CONFIG = {
    'width': None,       # None = max, ou ex: 1920
    'height': None,      # None = max, ou ex: 1080
    'shutter': None,     # Temps d'exposition en µs (None = auto)
    'gain': None,        # Gain (1.0 = minimum)
    'awb': None,         # Balance blancs: 'auto', 'tungsten', 'daylight', etc.
    'brightness': None,  # -1.0 à 1.0
    'contrast': None,    # 1.0 = normal
    'saturation': None,  # 1.0 = normal
    'sharpness': None,   # 1.0 = normal
    'denoise': None,     # 'auto', 'off', 'cdn_off', 'cdn_fast', 'cdn_hq'
    'timeout': 2000,     # Temps stabilisation caméra (ms)
}

# Dictionnaire ArUco (doit correspondre à celui utilisé pour la génération)
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# IDs des marqueurs de calibration
CALIBRATION_IDS = {
    32: 'CAL_TL',  # Top-Left (Haut-Gauche)
    33: 'CAL_TR',  # Top-Right (Haut-Droite)
    34: 'CAL_BL',  # Bottom-Left (Bas-Gauche)
    35: 'CAL_BR',  # Bottom-Right (Bas-Droite)
}

# ============================================================
# CONFIGURATION DES PIÈCES D'ÉCHECS (ArUcos IDs 0-31)
# ============================================================
# Pièces blanches: IDs 0-15
# Pièces noires: IDs 16-31
#
# Convention:
#   - Pions: 0-7 (blanc), 16-23 (noir) -> Pawn_A à Pawn_H
#   - Tours: 8, 9 (blanc), 24, 25 (noir) -> Rook_A, Rook_H
#   - Cavaliers: 10, 11 (blanc), 26, 27 (noir) -> Knight_B, Knight_G
#   - Fous: 12, 13 (blanc), 28, 29 (noir) -> Bishop_C, Bishop_F
#   - Dame: 14 (blanc), 30 (noir) -> Queen
#   - Roi: 15 (blanc), 31 (noir) -> King

PIECE_IDS = {
    # Pièces blanches
    0: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_A'},
    1: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_B'},
    2: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_C'},
    3: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_D'},
    4: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_E'},
    5: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_F'},
    6: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_G'},
    7: {'color': 'white', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_H'},
    8: {'color': 'white', 'piece_type': 'Rook', 'initial_piece': 'Rook_A'},
    9: {'color': 'white', 'piece_type': 'Rook', 'initial_piece': 'Rook_H'},
    10: {'color': 'white', 'piece_type': 'Knight', 'initial_piece': 'Knight_B'},
    11: {'color': 'white', 'piece_type': 'Knight', 'initial_piece': 'Knight_G'},
    12: {'color': 'white', 'piece_type': 'Bishop', 'initial_piece': 'Bishop_C'},
    13: {'color': 'white', 'piece_type': 'Bishop', 'initial_piece': 'Bishop_F'},
    14: {'color': 'white', 'piece_type': 'Queen', 'initial_piece': 'Queen'},
    15: {'color': 'white', 'piece_type': 'King', 'initial_piece': 'King'},
    # Pièces noires
    16: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_A'},
    17: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_B'},
    18: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_C'},
    19: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_D'},
    20: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_E'},
    21: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_F'},
    22: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_G'},
    23: {'color': 'black', 'piece_type': 'Pawn', 'initial_piece': 'Pawn_H'},
    24: {'color': 'black', 'piece_type': 'Rook', 'initial_piece': 'Rook_A'},
    25: {'color': 'black', 'piece_type': 'Rook', 'initial_piece': 'Rook_H'},
    26: {'color': 'black', 'piece_type': 'Knight', 'initial_piece': 'Knight_B'},
    27: {'color': 'black', 'piece_type': 'Knight', 'initial_piece': 'Knight_G'},
    28: {'color': 'black', 'piece_type': 'Bishop', 'initial_piece': 'Bishop_C'},
    29: {'color': 'black', 'piece_type': 'Bishop', 'initial_piece': 'Bishop_F'},
    30: {'color': 'black', 'piece_type': 'Queen', 'initial_piece': 'Queen'},
    31: {'color': 'black', 'piece_type': 'King', 'initial_piece': 'King'},
}

# ============================================================
# REPÈRE DE COORDONNÉES
# ============================================================
# Le plateau est mappé sur un repère avec:
#   - Centre à (0, 0)
#   - Top-Right: (+10, +10)
#   - Top-Left: (-10, +10)
#   - Bottom-Right: (+10, -10)
#   - Bottom-Left: (-10, -10)
#
# Colonne A = x proche de -10, Colonne H = x proche de +10
# Rangée 1 = y proche de -10, Rangée 8 = y proche de +10

BOARD_COORD_MIN = -10
BOARD_COORD_MAX = 10
BOARD_COORD_RANGE = BOARD_COORD_MAX - BOARD_COORD_MIN  # 20

# ============================================================
# OFFSETS DE CALIBRATION
# ============================================================
# Les ArUcos sont à l'EXTÉRIEUR du plateau.
# Ces offsets définissent la distance entre le CENTRE de l'ArUco
# et le COIN RÉEL du plateau.
#
# Unité: pixels (à ajuster selon votre image)
#
# Convention:
#   - offset_x positif = décaler vers la DROITE
#   - offset_x négatif = décaler vers la GAUCHE
#   - offset_y positif = décaler vers le BAS
#   - offset_y négatif = décaler vers le HAUT
#
# Schéma (vue de dessus, caméra en dessous regardant vers le haut):
#
#     [ArUco TL]          [ArUco TR]
#         ↘                  ↙
#         +------------------+
#         |                  |
#         |    PLATEAU       |
#         |    D'ÉCHECS      |
#         |                  |
#         +------------------+
#         ↗                  ↖
#     [ArUco BL]          [ArUco BR]
#
# OFFSETS: pour faire converger les coins vers l'intérieur (plateau plus petit que les ArUcos)
#   - CAL_TL (top-left):     +x (droite), +y (bas)
#   - CAL_TR (top-right):    -x (gauche), +y (bas)
#   - CAL_BL (bottom-left):  +x (droite), -y (haut)
#   - CAL_BR (bottom-right): -x (gauche), -y (haut)
OFFSETS = {
    "CAL_TL": {"offset_x": 0, "offset_y": 0},      # +x vers droite, +y vers bas
    "CAL_TR": {"offset_x": 54, "offset_y": -86},     # -x vers gauche, +y vers bas
    "CAL_BL": {"offset_x": -90, "offset_y": 112},     # +x vers droite, -y vers haut
    "CAL_BR": {"offset_x": 53, "offset_y": 86}     # -x vers gauche, -y vers haut
}

# Couleurs pour la visualisation (BGR pour OpenCV)
COLORS = {
    'aruco_marker': (0, 255, 0),      # Vert - contour des ArUcos détectés
    'aruco_center': (0, 0, 255),      # Rouge - centre des ArUcos
    'board_corner': (255, 0, 255),    # Magenta - coins calculés du plateau
    'board_outline': (255, 165, 0),   # Orange - contour du plateau
    'offset_line': (255, 255, 0),     # Cyan - ligne ArUco → coin plateau
    'text_bg': (255, 255, 255),       # Blanc - fond du texte
}


# ============================================================
# DÉTECTION AUTOMATIQUE DE L'ENVIRONNEMENT CAMÉRA
# ============================================================
def _check_rpicam_available():
    """Vérifie si rpicam-still est disponible"""
    return shutil.which('rpicam-still') is not None or shutil.which('libcamera-still') is not None

def _check_picamera2_available():
    """Vérifie si Picamera2 est disponible"""
    try:
        from picamera2 import Picamera2
        return True
    except ImportError:
        return False

# Déterminer le mode caméra
if _check_rpicam_available():
    CAMERA_MODE = 'rpicam'
elif _check_picamera2_available():
    CAMERA_MODE = 'picamera2'
else:
    CAMERA_MODE = 'opencv'


# ============================================================
# PRISE DE PHOTO
# ============================================================
def take_photo(filename=None):
    """
    Prend une photo et l'enregistre dans le dossier images/
    
    Args:
        filename: Nom du fichier (optionnel). Si non spécifié, utilise un timestamp.
    
    Returns:
        str: Chemin complet du fichier enregistré
    """
    # Créer le dossier images s'il n'existe pas
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"   📁 Dossier images: {IMAGES_DIR}")
    
    # Générer un nom de fichier si non spécifié
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
    
    filepath = os.path.join(IMAGES_DIR, filename)
    print(f"   📄 Fichier cible: {filepath}")
    
    if CAMERA_MODE == 'rpicam':
        print(f"   🎥 Mode caméra: rpicam-still (CLI Raspberry Pi)")
        _capture_with_rpicam(filepath)
    elif CAMERA_MODE == 'picamera2':
        print(f"   🎥 Mode caméra: Picamera2 (Python Raspberry Pi)")
        _capture_with_picamera2(filepath)
    else:
        print(f"   🎥 Mode caméra: OpenCV (Webcam)")
        _capture_with_opencv(filepath)
    
    # Vérifier que le fichier a bien été créé
    if not os.path.exists(filepath):
        print(f"   ❌ ERREUR: Le fichier n'existe pas après capture!")
        raise RuntimeError(f"Échec de la capture: {filepath} n'a pas été créé")
    else:
        file_size = os.path.getsize(filepath)
        print(f"   ✅ Fichier créé: {filepath} ({file_size} bytes)")
    
    print(f"📷 Photo enregistrée: {filepath}")
    return filepath


def _capture_with_rpicam(filepath):
    """Capture avec rpicam-still ou libcamera-still (CLI)"""
    # Déterminer la commande disponible
    if shutil.which('rpicam-still'):
        cmd = 'rpicam-still'
    else:
        cmd = 'libcamera-still'
    
    # Construire la commande avec les paramètres de configuration
    args = [cmd, '-n', '-o', filepath]
    
    # Timeout (toujours appliqué)
    timeout_ms = CAMERA_CONFIG.get('timeout', 2000)
    args.extend(['--timeout', str(timeout_ms)])
    
    # Si USE_DEFAULT_CAMERA_PARAMS = True, on utilise les paramètres par défaut (auto)
    if USE_DEFAULT_CAMERA_PARAMS:
        print("   ⚙️  Paramètres caméra: par défaut (auto)")
    else:
        print("   ⚙️  Paramètres caméra: personnalisés")
        
        if CAMERA_CONFIG.get('width') and CAMERA_CONFIG.get('height'):
            args.extend(['--width', str(CAMERA_CONFIG['width'])])
            args.extend(['--height', str(CAMERA_CONFIG['height'])])
        
        if CAMERA_CONFIG.get('shutter'):
            args.extend(['--shutter', str(CAMERA_CONFIG['shutter'])])
        
        if CAMERA_CONFIG.get('gain'):
            args.extend(['--gain', str(CAMERA_CONFIG['gain'])])
        
        if CAMERA_CONFIG.get('awb'):
            args.extend(['--awb', str(CAMERA_CONFIG['awb'])])
        
        if CAMERA_CONFIG.get('brightness'):
            args.extend(['--brightness', str(CAMERA_CONFIG['brightness'])])
        
        if CAMERA_CONFIG.get('contrast'):
            args.extend(['--contrast', str(CAMERA_CONFIG['contrast'])])
        
        if CAMERA_CONFIG.get('saturation'):
            args.extend(['--saturation', str(CAMERA_CONFIG['saturation'])])
        
        if CAMERA_CONFIG.get('sharpness'):
            args.extend(['--sharpness', str(CAMERA_CONFIG['sharpness'])])
        
        if CAMERA_CONFIG.get('denoise'):
            args.extend(['--denoise', str(CAMERA_CONFIG['denoise'])])
    
    print(f"   🔄 Exécution: {' '.join(args)}")
    
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"   ⚠️ Stderr: {result.stderr}")
            raise RuntimeError(f"{cmd} a échoué: {result.stderr}")
        print(f"   ✅ Capture terminée")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{cmd} timeout après 30 secondes")
    except FileNotFoundError:
        raise RuntimeError(f"{cmd} non trouvé")


def _capture_with_picamera2(filepath):
    """Capture avec Picamera2 (Python)"""
    from picamera2 import Picamera2
    import time as cam_time
    
    try:
        print("   🔄 Initialisation Picamera2...")
        picam2 = Picamera2()
        config = picam2.create_still_configuration()
        picam2.configure(config)
        print("   🔄 Démarrage de la caméra...")
        picam2.start()
        print("   ⏳ Attente stabilisation (2s)...")
        cam_time.sleep(2)
        print("   📸 Capture en cours...")
        picam2.capture_file(filepath)
        print("   🛑 Arrêt de la caméra...")
        picam2.stop()
        picam2.close()
        print("   ✅ Capture terminée")
    except Exception as e:
        print(f"   ❌ Erreur Picamera2: {e}")
        raise RuntimeError(f"Erreur Picamera2: {e}")


def _capture_with_opencv(filepath):
    """Capture avec OpenCV (webcam)"""
    print("   🔄 Ouverture webcam OpenCV...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("   ❌ Impossible d'ouvrir la caméra")
        raise RuntimeError("Impossible d'ouvrir la caméra")
    print("   📸 Capture frame...")
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filepath, frame)
        print(f"   ✅ Image sauvegardée")
    else:
        print("   ❌ Échec de lecture de la frame")
        cap.release()
        raise RuntimeError("Échec de lecture de la frame OpenCV")
    cap.release()


# ============================================================
# DÉTECTION ARUCO
# ============================================================
def detect_calibration_markers(img_np):
    """
    Détecte les marqueurs ArUco de calibration (IDs 32-35).
    
    Args:
        img_np: Image numpy (BGR ou RGB)
    
    Returns:
        dict: {id: {'center': (x, y), 'corners': [...], 'code': 'CAL_XX'}}
    """
    # Conversion en niveaux de gris
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_np
    
    # Charger le dictionnaire ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    
    # Paramètres de détection optimisés
    parameters = cv2.aruco.DetectorParameters()
    parameters.adaptiveThreshWinSizeMin = 3
    parameters.adaptiveThreshWinSizeMax = 50
    parameters.adaptiveThreshWinSizeStep = 2
    parameters.minMarkerPerimeterRate = 0.01
    parameters.maxMarkerPerimeterRate = 4.0
    parameters.polygonalApproxAccuracyRate = 0.01
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_CONTOUR
    
    # Créer le détecteur
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Détecter les marqueurs
    corners, ids, rejected = detector.detectMarkers(gray)
    
    calibration_markers = {}
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id in CALIBRATION_IDS:
                marker_corners = corners[i][0]
                
                # Centre du marqueur
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                
                calibration_markers[marker_id] = {
                    'center': (center_x, center_y),
                    'corners': marker_corners,
                    'code': CALIBRATION_IDS[marker_id]
                }
    
    return calibration_markers


def calculate_board_corners(calibration_markers):
    """
    Calcule les coins du plateau en appliquant les offsets aux ArUcos détectés.
    
    Args:
        calibration_markers: dict des marqueurs de calibration détectés
    
    Returns:
        dict: {code: (x, y)} pour chaque coin du plateau
        dict: {code: (aruco_center, board_corner)} pour visualiser les offsets
    """
    board_corners = {}
    offset_lines = {}
    
    for marker_id, marker_data in calibration_markers.items():
        code = marker_data['code']
        center = marker_data['center']
        
        # Appliquer l'offset
        offset = OFFSETS[code]
        board_x = center[0] + offset['offset_x']
        board_y = center[1] + offset['offset_y']
        
        board_corners[code] = (board_x, board_y)
        offset_lines[code] = (center, (board_x, board_y))
    
    return board_corners, offset_lines


def estimate_missing_corners(board_corners):
    """
    Estime les coins manquants si seulement 2 ou 3 ArUcos sont détectés.
    Utilise la géométrie du plateau (supposé rectangulaire).
    
    Args:
        board_corners: dict des coins déjà calculés
    
    Returns:
        dict: coins complétés (estimés si nécessaire)
        list: codes des coins estimés
    """
    codes = ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']
    detected = list(board_corners.keys())
    missing = [c for c in codes if c not in detected]
    
    if len(missing) == 0:
        return board_corners, []
    
    estimated_corners = board_corners.copy()
    estimated_codes = []
    
    # Cas avec 3 coins détectés: on peut estimer le 4ème
    if len(missing) == 1:
        m = missing[0]
        if m == 'CAL_TL' and all(c in detected for c in ['CAL_TR', 'CAL_BL', 'CAL_BR']):
            # TL = TR + BL - BR
            tr, bl, br = board_corners['CAL_TR'], board_corners['CAL_BL'], board_corners['CAL_BR']
            estimated_corners['CAL_TL'] = (tr[0] + bl[0] - br[0], tr[1] + bl[1] - br[1])
            estimated_codes.append('CAL_TL')
        elif m == 'CAL_TR' and all(c in detected for c in ['CAL_TL', 'CAL_BL', 'CAL_BR']):
            tl, bl, br = board_corners['CAL_TL'], board_corners['CAL_BL'], board_corners['CAL_BR']
            estimated_corners['CAL_TR'] = (tl[0] + br[0] - bl[0], tl[1] + br[1] - bl[1])
            estimated_codes.append('CAL_TR')
        elif m == 'CAL_BL' and all(c in detected for c in ['CAL_TL', 'CAL_TR', 'CAL_BR']):
            tl, tr, br = board_corners['CAL_TL'], board_corners['CAL_TR'], board_corners['CAL_BR']
            estimated_corners['CAL_BL'] = (tl[0] + br[0] - tr[0], tl[1] + br[1] - tr[1])
            estimated_codes.append('CAL_BL')
        elif m == 'CAL_BR' and all(c in detected for c in ['CAL_TL', 'CAL_TR', 'CAL_BL']):
            tl, tr, bl = board_corners['CAL_TL'], board_corners['CAL_TR'], board_corners['CAL_BL']
            estimated_corners['CAL_BR'] = (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1])
            estimated_codes.append('CAL_BR')
    
    # Cas avec 2 coins détectés: on peut estimer si on a une paire adjacente ou diagonale
    elif len(missing) == 2 and len(detected) == 2:
        # Diagonale TL-BR détectée
        if 'CAL_TL' in detected and 'CAL_BR' in detected:
            tl, br = board_corners['CAL_TL'], board_corners['CAL_BR']
            # Estimer TR et BL en supposant un rectangle
            estimated_corners['CAL_TR'] = (br[0], tl[1])
            estimated_corners['CAL_BL'] = (tl[0], br[1])
            estimated_codes.extend(['CAL_TR', 'CAL_BL'])
        
        # Diagonale TR-BL détectée
        elif 'CAL_TR' in detected and 'CAL_BL' in detected:
            tr, bl = board_corners['CAL_TR'], board_corners['CAL_BL']
            # Estimer TL et BR en supposant un rectangle
            estimated_corners['CAL_TL'] = (bl[0], tr[1])
            estimated_corners['CAL_BR'] = (tr[0], bl[1])
            estimated_codes.extend(['CAL_TL', 'CAL_BR'])
        
        # Ligne du haut TL-TR détectée
        elif 'CAL_TL' in detected and 'CAL_TR' in detected:
            tl, tr = board_corners['CAL_TL'], board_corners['CAL_TR']
            # Estimer BL et BR en supposant un carré (hauteur = largeur)
            width = tr[0] - tl[0]
            estimated_corners['CAL_BL'] = (tl[0], tl[1] + abs(width))
            estimated_corners['CAL_BR'] = (tr[0], tr[1] + abs(width))
            estimated_codes.extend(['CAL_BL', 'CAL_BR'])
        
        # Ligne du bas BL-BR détectée
        elif 'CAL_BL' in detected and 'CAL_BR' in detected:
            bl, br = board_corners['CAL_BL'], board_corners['CAL_BR']
            # Estimer TL et TR en supposant un carré
            width = br[0] - bl[0]
            estimated_corners['CAL_TL'] = (bl[0], bl[1] - abs(width))
            estimated_corners['CAL_TR'] = (br[0], br[1] - abs(width))
            estimated_codes.extend(['CAL_TL', 'CAL_TR'])
        
        # Ligne gauche TL-BL détectée
        elif 'CAL_TL' in detected and 'CAL_BL' in detected:
            tl, bl = board_corners['CAL_TL'], board_corners['CAL_BL']
            # Estimer TR et BR en supposant un carré
            height = bl[1] - tl[1]
            estimated_corners['CAL_TR'] = (tl[0] + abs(height), tl[1])
            estimated_corners['CAL_BR'] = (bl[0] + abs(height), bl[1])
            estimated_codes.extend(['CAL_TR', 'CAL_BR'])
        
        # Ligne droite TR-BR détectée
        elif 'CAL_TR' in detected and 'CAL_BR' in detected:
            tr, br = board_corners['CAL_TR'], board_corners['CAL_BR']
            # Estimer TL et BL en supposant un carré
            height = br[1] - tr[1]
            estimated_corners['CAL_TL'] = (tr[0] - abs(height), tr[1])
            estimated_corners['CAL_BL'] = (br[0] - abs(height), br[1])
            estimated_codes.extend(['CAL_TL', 'CAL_BL'])
    
    return estimated_corners, estimated_codes


# ============================================================
# VISUALISATION
# ============================================================
def draw_visualization(img_np, calibration_markers, board_corners, offset_lines, estimated_codes=None):
    """
    Dessine la visualisation sur l'image:
    - Contours des ArUcos détectés
    - Centres des ArUcos
    - Lignes d'offset (ArUco → coin plateau)
    - Coins du plateau
    - Contour du plateau
    
    Args:
        img_np: Image numpy (BGR)
        calibration_markers: dict des marqueurs détectés
        board_corners: dict des coins du plateau
        offset_lines: dict des lignes d'offset
        estimated_codes: liste des codes estimés (non détectés)
    
    Returns:
        Image annotée
    """
    if estimated_codes is None:
        estimated_codes = []
    
    img_annotated = img_np.copy()
    
    # 1. Dessiner les contours des ArUcos détectés
    for marker_id, marker_data in calibration_markers.items():
        corners = marker_data['corners']
        pts = corners.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_annotated, [pts], True, COLORS['aruco_marker'], 2)
        
        # Centre de l'ArUco
        cx, cy = int(marker_data['center'][0]), int(marker_data['center'][1])
        cv2.circle(img_annotated, (cx, cy), 8, COLORS['aruco_center'], -1)
        cv2.circle(img_annotated, (cx, cy), 10, COLORS['aruco_center'], 2)
        
        # Label ArUco
        label = f"ID:{marker_id} ({marker_data['code']})"
        cv2.putText(img_annotated, label, (cx - 60, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['text_bg'], 3)
        cv2.putText(img_annotated, label, (cx - 60, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['aruco_marker'], 2)
    
    # 2. Dessiner les lignes d'offset (ArUco → coin plateau)
    for code, (aruco_center, board_corner) in offset_lines.items():
        pt1 = (int(aruco_center[0]), int(aruco_center[1]))
        pt2 = (int(board_corner[0]), int(board_corner[1]))
        cv2.line(img_annotated, pt1, pt2, COLORS['offset_line'], 2, cv2.LINE_AA)
    
    # 3. Dessiner les coins du plateau
    for code, (bx, by) in board_corners.items():
        bx_int, by_int = int(bx), int(by)
        
        # Couleur différente pour les coins estimés
        if code in estimated_codes:
            color = (128, 128, 255)  # Rose clair pour estimé
            label_suffix = " (estimé)"
        else:
            color = COLORS['board_corner']
            label_suffix = ""
        
        # Croix au coin du plateau
        size = 15
        cv2.line(img_annotated, (bx_int - size, by_int), (bx_int + size, by_int), color, 3)
        cv2.line(img_annotated, (bx_int, by_int - size), (bx_int, by_int + size), color, 3)
        cv2.circle(img_annotated, (bx_int, by_int), 5, color, -1)
        
        # Label coin plateau
        label = f"Coin {code.replace('CAL_', '')}{label_suffix}"
        cv2.putText(img_annotated, label, (bx_int + 10, by_int - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_bg'], 2)
        cv2.putText(img_annotated, label, (bx_int + 10, by_int - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # 4. Dessiner le contour du plateau
    # On dessine TOUJOURS les lignes entre les coins adjacents disponibles
    corner_order = ['CAL_TL', 'CAL_TR', 'CAL_BR', 'CAL_BL']
    adjacencies = [
        ('CAL_TL', 'CAL_TR'),  # Haut
        ('CAL_TR', 'CAL_BR'),  # Droite
        ('CAL_BR', 'CAL_BL'),  # Bas
        ('CAL_BL', 'CAL_TL'),  # Gauche
    ]
    
    for c1, c2 in adjacencies:
        if c1 in board_corners and c2 in board_corners:
            pt1 = (int(board_corners[c1][0]), int(board_corners[c1][1]))
            pt2 = (int(board_corners[c2][0]), int(board_corners[c2][1]))
            cv2.line(img_annotated, pt1, pt2, COLORS['board_outline'], 3, cv2.LINE_AA)
    
    # 5. Si on a les 4 coins, ajouter l'overlay semi-transparent
    if len(board_corners) == 4:
        corner_order = ['CAL_TL', 'CAL_TR', 'CAL_BR', 'CAL_BL']
        pts = np.array([[int(board_corners[c][0]), int(board_corners[c][1])] 
                       for c in corner_order], np.int32)
        pts = pts.reshape((-1, 1, 2))
        
        # Overlay semi-transparent du plateau
        overlay = img_annotated.copy()
        cv2.fillPoly(overlay, [pts], (255, 200, 100))
        cv2.addWeighted(overlay, 0.15, img_annotated, 0.85, 0, img_annotated)
    
    return img_annotated


# ============================================================
# EXTRACTION DU PLATEAU
# ============================================================
def extract_board(img_np, board_corners):
    """
    Extrait et redresse l'image du plateau en utilisant une transformation de perspective.
    
    Les 4 coins du plateau (définis par les ArUcos + offsets) sont mappés vers
    les 4 coins d'une image carrée.
    
    Args:
        img_np: Image numpy (BGR)
        board_corners: dict {code: (x, y)} avec les 4 coins du plateau
    
    Returns:
        Image numpy du plateau extrait et redressé, ou None si pas assez de coins
    """
    if len(board_corners) < 4:
        print("   ⚠️  Impossible d'extraire le plateau: besoin de 4 coins")
        return None
    
    # Points source (coins du plateau dans l'image originale)
    # Ordre: TL, TR, BR, BL (sens horaire)
    src_points = np.array([
        [board_corners['CAL_TL'][0], board_corners['CAL_TL'][1]],
        [board_corners['CAL_TR'][0], board_corners['CAL_TR'][1]],
        [board_corners['CAL_BR'][0], board_corners['CAL_BR'][1]],
        [board_corners['CAL_BL'][0], board_corners['CAL_BL'][1]],
    ], dtype=np.float32)
    
    # Points destination (coins de l'image carrée de sortie)
    # L'image de sortie sera un carré de EXTRACTED_BOARD_SIZE x EXTRACTED_BOARD_SIZE
    size = EXTRACTED_BOARD_SIZE
    dst_points = np.array([
        [0, 0],           # TL -> coin haut-gauche
        [size - 1, 0],    # TR -> coin haut-droite
        [size - 1, size - 1],  # BR -> coin bas-droite
        [0, size - 1],    # BL -> coin bas-gauche
    ], dtype=np.float32)
    
    # Calculer la matrice de transformation perspective
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    
    # Appliquer la transformation
    board_img = cv2.warpPerspective(img_np, matrix, (size, size))
    
    return board_img


def draw_chess_grid(board_img, grid_color=(0, 255, 0), line_thickness=2):
    """
    Dessine une grille 8x8 sur l'image du plateau extrait.
    
    Args:
        board_img: Image numpy du plateau extrait (carré)
        grid_color: Couleur des lignes (BGR), par défaut vert
        line_thickness: Épaisseur des lignes
    
    Returns:
        Image numpy avec la grille dessinée
    """
    if board_img is None:
        return None
    
    img_with_grid = board_img.copy()
    h, w = img_with_grid.shape[:2]
    
    # Taille d'une case
    cell_width = w / 8
    cell_height = h / 8
    
    # Dessiner les lignes verticales (9 lignes pour 8 colonnes)
    for i in range(9):
        x = int(i * cell_width)
        cv2.line(img_with_grid, (x, 0), (x, h), grid_color, line_thickness)
    
    # Dessiner les lignes horizontales (9 lignes pour 8 rangées)
    for i in range(9):
        y = int(i * cell_height)
        cv2.line(img_with_grid, (0, y), (w, y), grid_color, line_thickness)
    
    # Ajouter les labels des colonnes (a-h) en bas
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = cell_width / 100  # Adapter la taille au plateau
    font_thickness = max(1, int(font_scale * 2))
    
    columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    for i, col in enumerate(columns):
        x = int((i + 0.5) * cell_width)
        y = h - 5
        # Fond pour meilleure lisibilité
        cv2.putText(img_with_grid, col, (x - 8, y), font, font_scale, (0, 0, 0), font_thickness + 2)
        cv2.putText(img_with_grid, col, (x - 8, y), font, font_scale, (255, 255, 255), font_thickness)
    
    # Ajouter les labels des rangées (1-8) à gauche
    rows = ['8', '7', '6', '5', '4', '3', '2', '1']  # 8 en haut, 1 en bas
    for i, row in enumerate(rows):
        x = 5
        y = int((i + 0.5) * cell_height) + 5
        cv2.putText(img_with_grid, row, (x, y), font, font_scale, (0, 0, 0), font_thickness + 2)
        cv2.putText(img_with_grid, row, (x, y), font, font_scale, (255, 255, 255), font_thickness)
    
    return img_with_grid


def get_cell_coordinates(board_size=EXTRACTED_BOARD_SIZE):
    """
    Retourne les coordonnées de chaque case de l'échiquier.
    
    Args:
        board_size: Taille de l'image du plateau extrait
    
    Returns:
        dict: {case: {'x': (x_min, x_max), 'y': (y_min, y_max), 'center': (cx, cy)}}
              où case est une notation d'échecs (ex: 'a1', 'e4')
    """
    cell_size = board_size / 8
    cells = {}
    
    columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    rows = ['8', '7', '6', '5', '4', '3', '2', '1']  # 8 en haut (y=0), 1 en bas
    
    for col_idx, col in enumerate(columns):
        for row_idx, row in enumerate(rows):
            case = f"{col}{row}"
            x_min = int(col_idx * cell_size)
            x_max = int((col_idx + 1) * cell_size)
            y_min = int(row_idx * cell_size)
            y_max = int((row_idx + 1) * cell_size)
            center_x = int((col_idx + 0.5) * cell_size)
            center_y = int((row_idx + 0.5) * cell_size)
            
            cells[case] = {
                'x': (x_min, x_max),
                'y': (y_min, y_max),
                'center': (center_x, center_y),
                'col_idx': col_idx,
                'row_idx': row_idx
            }
    
    return cells


def get_cell_at_position(x, y, board_size=EXTRACTED_BOARD_SIZE):
    """
    Retourne la case d'échecs correspondant à une position en pixels.
    
    Args:
        x, y: Coordonnées en pixels dans l'image du plateau extrait
        board_size: Taille de l'image du plateau
    
    Returns:
        str: Notation de la case (ex: 'e4') ou None si hors plateau
    """
    if x < 0 or x >= board_size or y < 0 or y >= board_size:
        return None
    
    cell_size = board_size / 8
    col_idx = int(x / cell_size)
    row_idx = int(y / cell_size)
    
    columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    rows = ['8', '7', '6', '5', '4', '3', '2', '1']
    
    if 0 <= col_idx < 8 and 0 <= row_idx < 8:
        return f"{columns[col_idx]}{rows[row_idx]}"
    return None


# ============================================================
# DÉTECTION DES PIÈCES D'ÉCHECS
# ============================================================
def detect_chess_pieces(img_np):
    """
    Détecte les pièces d'échecs via leurs marqueurs ArUco (IDs 0-31).
    
    Args:
        img_np: Image numpy (BGR)
    
    Returns:
        dict: {id: {'center': (x, y), 'corners': [...], 'piece_info': {...}}}
    """
    # Conversion en niveaux de gris
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_np
    
    # Charger le dictionnaire ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    
    # Paramètres de détection
    parameters = cv2.aruco.DetectorParameters()
    parameters.adaptiveThreshWinSizeMin = 3
    parameters.adaptiveThreshWinSizeMax = 50
    parameters.adaptiveThreshWinSizeStep = 2
    parameters.minMarkerPerimeterRate = 0.01
    parameters.maxMarkerPerimeterRate = 4.0
    parameters.polygonalApproxAccuracyRate = 0.01
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_CONTOUR
    
    # Créer le détecteur
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Détecter les marqueurs
    corners, ids, rejected = detector.detectMarkers(gray)
    
    pieces = {}
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            # Seulement les pièces (IDs 0-31)
            if marker_id in PIECE_IDS:
                marker_corners = corners[i][0]
                
                # Centre du marqueur
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                
                pieces[marker_id] = {
                    'center': (center_x, center_y),
                    'corners': marker_corners,
                    'piece_info': PIECE_IDS[marker_id]
                }
    
    return pieces


def pixel_to_board_coords(pixel_x, pixel_y, board_size=EXTRACTED_BOARD_SIZE):
    """
    Convertit des coordonnées pixels (dans l'image du plateau extrait)
    en coordonnées du repère de jeu (-10 à +10).
    
    Convention:
        - Pixel (0, 0) = coin Top-Left du plateau = (-10, +10)
        - Pixel (board_size, 0) = coin Top-Right = (+10, +10)
        - Pixel (0, board_size) = coin Bottom-Left = (-10, -10)
        - Pixel (board_size, board_size) = coin Bottom-Right = (+10, -10)
    
    Args:
        pixel_x, pixel_y: Coordonnées en pixels
        board_size: Taille de l'image du plateau
    
    Returns:
        tuple: (x, y) dans le repère -10 à +10
    """
    # Normaliser les pixels (0 à 1)
    norm_x = pixel_x / board_size
    norm_y = pixel_y / board_size
    
    # Convertir en coordonnées du repère
    # X: 0 -> -10, 1 -> +10
    coord_x = BOARD_COORD_MIN + norm_x * BOARD_COORD_RANGE
    
    # Y: 0 -> +10 (haut), 1 -> -10 (bas) - INVERSÉ car Y pixel augmente vers le bas
    coord_y = BOARD_COORD_MAX - norm_y * BOARD_COORD_RANGE
    
    return (round(coord_x, 2), round(coord_y, 2))


def get_chess_notation_from_coords(x, y):
    """
    Convertit des coordonnées du repère (-10 à +10) en notation d'échecs.
    
    Args:
        x, y: Coordonnées dans le repère
    
    Returns:
        str: Notation d'échecs (ex: 'e4') ou None si hors plateau
    """
    # Convertir X en colonne (a-h)
    # X va de -10 (colonne a) à +10 (colonne h)
    col_idx = int((x - BOARD_COORD_MIN) / BOARD_COORD_RANGE * 8)
    col_idx = max(0, min(7, col_idx))
    
    # Convertir Y en rangée (1-8)
    # Y va de -10 (rangée 1) à +10 (rangée 8)
    row_idx = int((y - BOARD_COORD_MIN) / BOARD_COORD_RANGE * 8)
    row_idx = max(0, min(7, row_idx))
    
    columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    rows = ['1', '2', '3', '4', '5', '6', '7', '8']
    
    return f"{columns[col_idx]}{rows[row_idx]}"


def detect_pieces_on_board(board_img, original_img, board_corners):
    """
    Détecte les pièces sur le plateau extrait et calcule leurs coordonnées.
    
    Args:
        board_img: Image du plateau extrait (redressé)
        original_img: Image originale
        board_corners: Coins du plateau dans l'image originale
    
    Returns:
        list: Liste des pièces détectées avec leurs coordonnées
    """
    if board_img is None:
        return []
    
    # Détecter les pièces sur l'image du plateau extrait
    pieces = detect_chess_pieces(board_img)
    
    pieces_list = []
    
    for marker_id, piece_data in pieces.items():
        pixel_x, pixel_y = piece_data['center']
        piece_info = piece_data['piece_info']
        
        # Convertir en coordonnées du repère
        coord_x, coord_y = pixel_to_board_coords(pixel_x, pixel_y)
        
        # Obtenir la case d'échecs
        chess_square = get_cell_at_position(pixel_x, pixel_y)
        
        pieces_list.append({
            'id': int(marker_id),  # Convertir numpy.int32 en int Python
            'color': piece_info['color'],
            'piece_type': piece_info['piece_type'],
            'x': float(coord_x),  # Convertir numpy.float en float Python
            'y': float(coord_y),
            'initial_piece': piece_info['initial_piece'],
            'chess_square': chess_square,
            'pixel_center': (int(pixel_x), int(pixel_y))
        })
    
    return pieces_list


def generate_game_state_json(pieces_list, move_count=0, turn="white"):
    """
    Génère le JSON de l'état du jeu.
    
    Args:
        pieces_list: Liste des pièces détectées
        move_count: Nombre de coups joués
        turn: Joueur dont c'est le tour ('white' ou 'black')
    
    Returns:
        dict: État du jeu au format JSON
    """
    # Formater les coordonnées pour le JSON
    coordinates = []
    for piece in pieces_list:
        coordinates.append({
            'id': piece['id'],
            'color': piece['color'],
            'piece_type': piece['piece_type'],
            'x': piece['x'],
            'y': piece['y'],
            'initial_piece': piece['initial_piece']
        })
    
    # Trier par ID pour un affichage cohérent
    coordinates.sort(key=lambda p: p['id'])
    
    game_state = {
        'coordinates': coordinates,
        'game_metadata': {
            'turn': turn,
            'move_count': move_count,
            'pieces_detected': len(coordinates),
            'timestamp': datetime.now().isoformat()
        }
    }
    
    return game_state


def draw_detected_pieces_aruco(board_img, pieces_list):
    """
    Dessine les ArUcos détectés sur le plateau avec leurs IDs et infos.
    Montre clairement quels marqueurs ont été détectés.
    
    Args:
        board_img: Image du plateau extrait
        pieces_list: Liste des pièces détectées
    
    Returns:
        Image annotée avec les ArUcos détectés
    """
    if board_img is None:
        return None
    
    img_annotated = board_img.copy()
    
    # Détecter à nouveau les ArUcos pour dessiner leurs contours
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, rejected = detector.detectMarkers(img_annotated)
    
    # Dessiner les contours des marqueurs détectés
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(img_annotated, corners, ids)
    
    # Ajouter les informations sur chaque pièce
    for piece in pieces_list:
        px, py = piece['pixel_center']
        
        # Couleur selon la pièce
        if piece['color'] == 'white':
            box_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            box_color = (50, 50, 50)
            text_color = (255, 255, 255)
        
        # Dessiner un fond pour le texte
        info_text = f"ID:{piece['id']} {piece['piece_type'][0]}"
        if piece['piece_type'] == 'Knight':
            info_text = f"ID:{piece['id']} N"
        
        # Position du texte (en dessous du marqueur)
        text_x = px - 35
        text_y = py + 40
        
        # Rectangle de fond
        (text_w, text_h), _ = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img_annotated, (text_x - 2, text_y - text_h - 2), 
                     (text_x + text_w + 2, text_y + 4), box_color, -1)
        cv2.rectangle(img_annotated, (text_x - 2, text_y - text_h - 2), 
                     (text_x + text_w + 2, text_y + 4), (0, 255, 0), 1)
        
        # Texte
        cv2.putText(img_annotated, info_text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        
        # Ligne vers le centre du marqueur
        cv2.line(img_annotated, (px, py + 20), (text_x + text_w // 2, text_y - text_h - 5),
                 (0, 255, 0), 1)
    
    # Ajouter un titre
    cv2.putText(img_annotated, f"Pieces ArUco detectees: {len(pieces_list)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Légende
    white_count = len([p for p in pieces_list if p['color'] == 'white'])
    black_count = len([p for p in pieces_list if p['color'] == 'black'])
    cv2.putText(img_annotated, f"Blanches: {white_count} | Noires: {black_count}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    return img_annotated


def draw_pieces_on_board(board_img, pieces_list):
    """
    Dessine les pièces détectées sur l'image du plateau.
    
    Args:
        board_img: Image du plateau
        pieces_list: Liste des pièces
    
    Returns:
        Image annotée
    """
    if board_img is None:
        return None
    
    img_annotated = board_img.copy()
    
    for piece in pieces_list:
        px, py = piece['pixel_center']
        color_bgr = (255, 255, 255) if piece['color'] == 'white' else (0, 0, 0)
        outline_color = (0, 0, 0) if piece['color'] == 'white' else (255, 255, 255)
        
        # Cercle pour la pièce
        cv2.circle(img_annotated, (px, py), 25, outline_color, 3)
        cv2.circle(img_annotated, (px, py), 22, color_bgr, -1)
        
        # Texte de la pièce
        text = piece['piece_type'][0]  # Première lettre
        if piece['piece_type'] == 'Knight':
            text = 'N'  # Knight = N en notation
        
        cv2.putText(img_annotated, text, (px - 8, py + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, outline_color, 2)
        
        # Coordonnées
        coord_text = f"({piece['x']:.1f},{piece['y']:.1f})"
        cv2.putText(img_annotated, coord_text, (px - 30, py + 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)
    
    return img_annotated


def draw_info_panel(img_np, calibration_markers, board_corners, estimated_codes):
    """
    Ajoute un panneau d'information sur l'image
    """
    h, w = img_np.shape[:2]
    
    # Créer un panneau en haut
    panel_height = 120
    panel = np.ones((panel_height, w, 3), dtype=np.uint8) * 40  # Gris foncé
    
    # Titre
    cv2.putText(panel, "DETECTION DES COINS DU PLATEAU", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Statut des ArUcos
    y_pos = 60
    detected_ids = list(calibration_markers.keys())
    for marker_id, code in CALIBRATION_IDS.items():
        status = "OK" if marker_id in detected_ids else "NON DETECTE"
        color = (0, 255, 0) if marker_id in detected_ids else (0, 0, 255)
        text = f"ArUco {marker_id} ({code}): {status}"
        cv2.putText(panel, text, (20 + (marker_id - 32) * 280, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # Offsets actuels
    y_pos = 90
    cv2.putText(panel, f"Offsets: TL({OFFSETS['CAL_TL']['offset_x']},{OFFSETS['CAL_TL']['offset_y']}) "
                f"TR({OFFSETS['CAL_TR']['offset_x']},{OFFSETS['CAL_TR']['offset_y']}) "
                f"BL({OFFSETS['CAL_BL']['offset_x']},{OFFSETS['CAL_BL']['offset_y']}) "
                f"BR({OFFSETS['CAL_BR']['offset_x']},{OFFSETS['CAL_BR']['offset_y']})",
                (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    
    # Résumé
    cv2.putText(panel, f"Detectes: {len(calibration_markers)}/4 | "
                f"Coins plateau: {len(board_corners)}/4 | "
                f"Estimes: {len(estimated_codes)}",
                (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 100), 1)
    
    # Combiner le panneau avec l'image
    result = np.vstack([panel, img_np])
    
    return result


# ============================================================
# FONCTIONS PRINCIPALES
# ============================================================
def process_image(image_path):
    """
    Traite une image: détection des coins et visualisation.
    
    Args:
        image_path: Chemin vers l'image
    
    Returns:
        dict avec les résultats
    """
    print(f"\n{'='*60}")
    print(f"📸 Traitement de: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    # Charger l'image
    img_np = cv2.imread(image_path)
    if img_np is None:
        print(f"❌ Impossible de charger l'image: {image_path}")
        return None
    
    h, w = img_np.shape[:2]
    print(f"   📐 Dimensions: {w}x{h}")
    
    # Détecter les marqueurs de calibration
    print(f"\n🎯 Détection des ArUcos de calibration...")
    calibration_markers = detect_calibration_markers(img_np)
    
    print(f"   ✅ Marqueurs détectés: {len(calibration_markers)}/4")
    for marker_id, data in calibration_markers.items():
        print(f"      ID {marker_id} ({data['code']}): centre = ({data['center'][0]:.1f}, {data['center'][1]:.1f})")
    
    # Vérifier qu'on a au moins 2 marqueurs
    if len(calibration_markers) < 2:
        print(f"\n❌ ERREUR: Besoin d'au moins 2 ArUcos de calibration (détectés: {len(calibration_markers)})")
        return None
    
    # Calculer les coins du plateau avec offsets
    print(f"\n📐 Calcul des coins du plateau (avec offsets)...")
    board_corners, offset_lines = calculate_board_corners(calibration_markers)
    
    for code, corner in board_corners.items():
        offset = OFFSETS[code]
        print(f"   {code}: ArUco → offset ({offset['offset_x']:+d}, {offset['offset_y']:+d}) → coin plateau ({corner[0]:.1f}, {corner[1]:.1f})")
    
    # Estimer les coins manquants si possible
    estimated_codes = []
    if len(board_corners) < 4:
        print(f"\n🔮 Estimation des coins manquants...")
        board_corners, estimated_codes = estimate_missing_corners(board_corners)
        if estimated_codes:
            for code in estimated_codes:
                print(f"   ⚠️  {code} estimé: ({board_corners[code][0]:.1f}, {board_corners[code][1]:.1f})")
        else:
            print(f"   ⚠️  Impossible d'estimer (besoin d'au moins 3 coins)")
    
    # Créer la visualisation
    print(f"\n🎨 Création de la visualisation...")
    img_annotated = draw_visualization(img_np, calibration_markers, board_corners, offset_lines, estimated_codes)
    img_with_panel = draw_info_panel(img_annotated, calibration_markers, board_corners, estimated_codes)
    
    # Créer un dossier pour cette détection
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detection_dir = os.path.join(OUTPUT_DIR, f"detection_{timestamp}")
    os.makedirs(detection_dir, exist_ok=True)
    print(f"\n📁 Dossier de sortie: {detection_dir}")
    
    # 1. Sauvegarder l'image originale
    original_filename = "1_original.jpg"
    original_path = os.path.join(detection_dir, original_filename)
    cv2.imwrite(original_path, img_np)
    print(f"   💾 1. Image originale: {original_filename}")
    
    # 2. Sauvegarder l'image avec détection des coins
    corners_filename = "2_corners_detection.jpg"
    output_path = os.path.join(detection_dir, corners_filename)
    cv2.imwrite(output_path, img_with_panel)
    print(f"   💾 2. Détection des coins: {corners_filename}")
    
    # Extraire et sauvegarder l'image du plateau (si 4 coins disponibles)
    board_extracted_path = None
    board_grid_path = None
    board_img = None
    board_img_with_grid = None
    cell_coords = None
    pieces_detected = []
    game_state = None
    json_path = None
    pieces_path = None
    
    if len(board_corners) == 4:
        print(f"\n🔲 Extraction du plateau...")
        board_img = extract_board(img_np, board_corners)
        if board_img is not None:
            # 3. Sauvegarder le plateau extrait (sans grille)
            board_extracted_filename = "3_board_extracted.jpg"
            board_extracted_path = os.path.join(detection_dir, board_extracted_filename)
            cv2.imwrite(board_extracted_path, board_img)
            print(f"   💾 3. Plateau extrait: {board_extracted_filename}")
            print(f"      📐 Dimensions: {EXTRACTED_BOARD_SIZE}x{EXTRACTED_BOARD_SIZE} pixels")
            
            # 4. Dessiner la grille 8x8 et sauvegarder
            print(f"\n📊 Création de la grille 8x8...")
            board_img_with_grid = draw_chess_grid(board_img)
            board_grid_filename = "4_board_grid.jpg"
            board_grid_path = os.path.join(detection_dir, board_grid_filename)
            cv2.imwrite(board_grid_path, board_img_with_grid)
            print(f"   💾 4. Plateau avec grille: {board_grid_filename}")
            
            # Calculer les coordonnées des cases
            cell_coords = get_cell_coordinates()
            print(f"      ✅ 64 cases calculées (a1 à h8)")
            print(f"      📐 Taille d'une case: {EXTRACTED_BOARD_SIZE // 8}x{EXTRACTED_BOARD_SIZE // 8} pixels")
            
            # === DÉTECTION DES PIÈCES ===
            print(f"\n♟️  Détection des pièces d'échecs...")
            pieces_detected = detect_pieces_on_board(board_img, img_np, board_corners)
            
            if pieces_detected:
                print(f"   ✅ {len(pieces_detected)} pièce(s) détectée(s):")
                for piece in pieces_detected:
                    print(f"      ID {piece['id']}: {piece['color']} {piece['piece_type']} "
                          f"({piece['initial_piece']}) à ({piece['x']:.2f}, {piece['y']:.2f}) "
                          f"[{piece['chess_square']}]")
                
                # 5. Image avec les ArUcos des pièces détectées (sur plateau extrait)
                board_with_aruco = draw_detected_pieces_aruco(board_img.copy(), pieces_detected)
                aruco_filename = "5_pieces_aruco_detected.jpg"
                aruco_path = os.path.join(detection_dir, aruco_filename)
                cv2.imwrite(aruco_path, board_with_aruco)
                print(f"   💾 5. Pièces ArUco détectées: {aruco_filename}")
                
                # 6. Dessiner les pièces sur l'image de la grille avec coordonnées
                board_img_with_pieces = draw_pieces_on_board(board_img_with_grid.copy(), pieces_detected)
                pieces_filename = "6_board_pieces_coords.jpg"
                pieces_path = os.path.join(detection_dir, pieces_filename)
                cv2.imwrite(pieces_path, board_img_with_pieces)
                print(f"   💾 6. Plateau avec pièces et coordonnées: {pieces_filename}")
                
                # 7. Générer et sauvegarder le JSON
                game_state = generate_game_state_json(pieces_detected)
                json_filename = "game_state.json"
                json_path = os.path.join(detection_dir, json_filename)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(game_state, f, indent=2, ensure_ascii=False)
                print(f"   💾 7. État du jeu (JSON): {json_filename}")
            else:
                print(f"   ⚠️  Aucune pièce détectée")
    
    # Résumé
    print(f"\n{'='*60}")
    print(f"📋 RÉSUMÉ")
    print(f"{'='*60}")
    print(f"   📁 Dossier de sortie: {detection_dir}")
    print(f"   ArUcos calibration détectés: {len(calibration_markers)}/4")
    print(f"   Coins du plateau: {len(board_corners)}/4")
    if estimated_codes:
        print(f"   Coins estimés: {', '.join(estimated_codes)}")
    
    if len(board_corners) == 4:
        print(f"\n   ✅ Plateau complet détecté!")
        print(f"\n   📍 Coins du plateau (en pixels):")
        for code in ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']:
            if code in board_corners:
                suffix = " (estimé)" if code in estimated_codes else ""
                print(f"      {code.replace('CAL_', '')}: ({board_corners[code][0]:.1f}, {board_corners[code][1]:.1f}){suffix}")
        
        # Résumé des pièces
        if pieces_detected:
            white_pieces = [p for p in pieces_detected if p['color'] == 'white']
            black_pieces = [p for p in pieces_detected if p['color'] == 'black']
            print(f"\n   ♟️  Pièces détectées: {len(pieces_detected)} total")
            print(f"      ⬜ Blanches: {len(white_pieces)}")
            print(f"      ⬛ Noires: {len(black_pieces)}")
        
        # Liste des fichiers générés
        print(f"\n   📄 Fichiers générés:")
        print(f"      1. 1_original.jpg - Image originale")
        print(f"      2. 2_corners_detection.jpg - Détection des coins")
        if board_extracted_path:
            print(f"      3. 3_board_extracted.jpg - Plateau extrait")
        if board_grid_path:
            print(f"      4. 4_board_grid.jpg - Plateau avec grille")
        if pieces_detected:
            print(f"      5. 5_pieces_aruco_detected.jpg - ArUcos pièces détectées")
            print(f"      6. 6_board_pieces_coords.jpg - Pièces avec coordonnées")
            print(f"      7. game_state.json - État du jeu")
    else:
        print(f"\n   ⚠️  Plateau incomplet - ajustez les ArUcos ou les paramètres")
    
    return {
        'detection_dir': detection_dir,
        'calibration_markers': calibration_markers,
        'board_corners': board_corners,
        'estimated_codes': estimated_codes,
        'output_path': output_path,
        'board_extracted_path': board_extracted_path,
        'board_grid_path': board_grid_path,
        'board_image': board_img,
        'board_image_with_grid': board_img_with_grid,
        'cell_coordinates': cell_coords,
        'pieces_detected': pieces_detected,
        'game_state': game_state,
        'json_path': json_path
    }


def select_image():
    """Sélectionne une image à traiter"""
    import glob
    
    # Chercher les images
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        images.extend(glob.glob(os.path.join(DEFAULT_IMAGES_DIR, ext)))
        images.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
        images.extend(glob.glob(os.path.join(SCRIPT_DIR, ext)))
    
    images = sorted(set(images))
    
    if not images:
        print("❌ Aucune image trouvée.")
        return None
    
    print("\n📷 Images disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("\nNuméro de l'image (ou 'q' pour quitter): ").strip()
            if choice.lower() == 'q':
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(images):
                return images[choice_num - 1]
        except ValueError:
            pass
        print(f"⚠️  Entrez un numéro entre 1 et {len(images)}")


def photo_and_detect():
    """
    Fonction principale: prend une photo et détecte les coins du plateau
    
    Returns:
        dict: Résultats de la détection
    """
    print("\n" + "-" * 60)
    print("📷 ÉTAPE 1: Prise de photo")
    print("-" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_filename = f"photo_{timestamp}.jpg"
    
    try:
        image_path = take_photo(photo_filename)
    except RuntimeError as e:
        print(f"❌ Erreur lors de la capture: {e}")
        return None
    
    print("\n" + "-" * 60)
    print("🔍 ÉTAPE 2: Détection des coins du plateau")
    print("-" * 60)
    
    result = process_image(image_path)
    
    return result


# ============================================================
# POINT D'ENTRÉE
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🎯 DÉTECTION DES COINS DU PLATEAU D'ÉCHECS")
    print("   via ArUcos de calibration (IDs 32-35)")
    print(f"   Mode caméra: {CAMERA_MODE}")
    print("=" * 60)
    
    # Vérifier les arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == '--photo' or arg == '-p':
            # Mode: prendre une photo et analyser
            result = photo_and_detect()
            if result:
                print(f"\n✅ Traitement terminé!")
                print(f"\n💡 Pour ajuster les offsets, modifiez la section OFFSETS en haut du script.")
        elif os.path.exists(arg):
            # Mode: analyser une image existante passée en argument
            result = process_image(arg)
            if result:
                print(f"\n✅ Traitement terminé!")
                print(f"\n💡 Pour ajuster les offsets, modifiez la section OFFSETS en haut du script.")
        else:
            print(f"❌ Image non trouvée: {arg}")
    else:
        # Mode interactif
        print("\nChoisissez une option:")
        print("  1. Prendre une photo et analyser")
        print("  2. Analyser une image existante")
        print("  q. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == '1':
            result = photo_and_detect()
            if result:
                print(f"\n✅ Traitement terminé!")
                print(f"\n💡 Pour ajuster les offsets, modifiez la section OFFSETS en haut du script.")
        elif choice == '2':
            image_path = select_image()
            if image_path and os.path.exists(image_path):
                result = process_image(image_path)
                if result:
                    print(f"\n✅ Traitement terminé!")
                    print(f"\n💡 Pour ajuster les offsets, modifiez la section OFFSETS en haut du script.")
            else:
                print("❌ Image non trouvée ou non sélectionnée.")
        elif choice.lower() == 'q':
            print("Au revoir!")
        else:
            print("Option invalide. Au revoir!")
