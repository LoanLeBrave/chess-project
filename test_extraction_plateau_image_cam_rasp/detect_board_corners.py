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
    "CAL_TL": {"offset_x": 90, "offset_y": 90},      # +x vers droite, +y vers bas
    "CAL_TR": {"offset_x": -100, "offset_y": 100},     # -x vers gauche, +y vers bas
    "CAL_BL": {"offset_x": 100, "offset_y": -110},     # +x vers droite, -y vers haut
    "CAL_BR": {"offset_x": -100, "offset_y": -120}     # -x vers gauche, -y vers haut
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
    
    # Sauvegarder le résultat annoté
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"board_detection_{timestamp}.jpg"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    cv2.imwrite(output_path, img_with_panel)
    print(f"\n💾 Résultat annoté sauvegardé: {output_path}")
    
    # Extraire et sauvegarder l'image du plateau (si 4 coins disponibles)
    board_extracted_path = None
    board_img = None
    if len(board_corners) == 4:
        print(f"\n🔲 Extraction du plateau...")
        board_img = extract_board(img_np, board_corners)
        if board_img is not None:
            board_extracted_filename = f"board_extracted_{timestamp}.jpg"
            board_extracted_path = os.path.join(OUTPUT_DIR, board_extracted_filename)
            cv2.imwrite(board_extracted_path, board_img)
            print(f"   💾 Plateau extrait sauvegardé: {board_extracted_path}")
            print(f"   📐 Dimensions: {EXTRACTED_BOARD_SIZE}x{EXTRACTED_BOARD_SIZE} pixels")
    
    # Résumé
    print(f"\n{'='*60}")
    print(f"📋 RÉSUMÉ")
    print(f"{'='*60}")
    print(f"   ArUcos détectés: {len(calibration_markers)}/4")
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
        if board_extracted_path:
            print(f"\n   🔲 Image plateau extraite: {board_extracted_path}")
    else:
        print(f"\n   ⚠️  Plateau incomplet - ajustez les ArUcos ou les paramètres")
    
    return {
        'calibration_markers': calibration_markers,
        'board_corners': board_corners,
        'estimated_codes': estimated_codes,
        'output_path': output_path,
        'board_extracted_path': board_extracted_path,
        'board_image': board_img
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
