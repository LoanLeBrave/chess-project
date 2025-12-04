#!/usr/bin/env python3
"""
Prise de photo et analyse de l'état du jeu d'échecs
Combine la capture photo et la détection des marqueurs ArUco

Workflow:
1. Prendre une photo -> sauvegardée dans /images
2. Analyser l'état du jeu (détection ArUco)
3. Sauvegarder les résultats dans /results
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import time
import json

# ============================================================
# CONFIGURATION GÉNÉRALE
# ============================================================

# Dimension maximale des images (pour réduire le temps de traitement)
# None = pas de redimensionnement (garde la résolution originale)
# Recommandé: 1500-2000 pour un bon équilibre détection/vitesse
MAX_DIMENSION = None  # ou ex: 2000, 2500, 3000

# Dossiers
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# True = utilise les paramètres par défaut d'OpenCV pour la détection ArUco
# False = utilise nos paramètres personnalisés ci-dessous
USE_DEFAULT_ARUCO_PARAMS = False

# Dictionnaire ArUco (doit correspondre à celui utilisé pour la génération)
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# Paramètres personnalisés de détection ArUco (utilisés si USE_DEFAULT_ARUCO_PARAMS = False)
CUSTOM_ARUCO_PARAMS = {
    'adaptiveThreshWinSizeMin': 3,
    'adaptiveThreshWinSizeMax': 50,        # ↑ Augmente (au lieu de 40)
    'adaptiveThreshWinSizeStep': 0.5,        # ↓ Diminue (au lieu de 5) - teste plus finement LE PLUS BAS POSSIBLE
    'adaptiveThreshConstant': 0.5,           # ↓ Diminue (au lieu de 5) - plus tolérant - MARCHE VRAIMENT PLUS BAS MIEUX
    'minMarkerPerimeterRate': 0.01,        # Garde
    'maxMarkerPerimeterRate': 4.0,
    'polygonalApproxAccuracyRate': 0.001,   # ↑ Augmente (au lieu de 0.05) - LE PLUS BAS POSSIBLE
    'minCornerDistanceRate': 0.002,         # ↓ Diminue (au lieu de 0.05) - accepte des coins plus proches
    'minDistanceToBorder': 1,              # ↓ Diminue (au lieu de 3)
    'minMarkerDistanceRate': 0.02,         # ↓ Diminue (au lieu de 0.05)
    'cornerRefinementMethod': cv2.aruco.CORNER_REFINE_CONTOUR,  # Utilise CONTOUR au lieu de SUBPIX
    'cornerRefinementWinSize': 3,          # ↓ Diminue (au lieu de 5)
    'cornerRefinementMaxIterations': 20,   # ↓ Diminue (au lieu de 30)
    'cornerRefinementMinAccuracy': 0.05,   # ↓ Diminue (au lieu de 0.1)
}

# ============================================================
# CONFIGURATION CAMÉRA RASPBERRY PI
# ============================================================
# Ces paramètres sont utilisés avec rpicam-still sur Raspberry Pi
# Ajustez-les selon vos conditions d'éclairage

# True = utilise les paramètres par défaut de la caméra (auto pour tout)
# False = utilise nos paramètres personnalisés ci-dessous
USE_DEFAULT_CAMERA_PARAMS = True

CAMERA_CONFIG = {
    # --- Résolution ---
    # Taille de l'image capturée (largeur, hauteur) en pixels
    # None = résolution max du capteur (ex: 4608x2592 pour v3, 3280x2464 pour v2)
    # Recommandé: (1920, 1080) ou (2560, 1440) pour bon équilibre détail/vitesse
    'width': None,   # None = max, ou ex: 1920
    'height': None,  # None = max, ou ex: 1080
    
    # --- Exposition ---
    # Temps d'exposition en microsecondes (None = auto)
    # Plus bas = moins de halos lumineux, mais image plus sombre
    # Recommandé: 5000-20000 pour réduire les halos
    'shutter': None,  # None = auto
    
    # --- Gain (sensibilité ISO) ---
    # Multiplicateur de gain (1.0 = minimum, plus = plus lumineux mais plus de bruit)
    # None = auto, Recommandé: 1.0-2.0 pour éviter le bruit
    'gain': None,
    
    # --- Balance des blancs ---
    # Options: 'auto', 'tungsten', 'fluorescent', 'indoor', 'daylight', 'cloudy'
    # None = auto
    'awb': None,
    
    # --- Luminosité ---
    # Ajustement de luminosité (-1.0 à 1.0, 0 = normal)
    # Valeur négative = plus sombre (réduit les halos)
    'brightness': None,
    
    # --- Contraste ---
    # Multiplicateur de contraste (1.0 = normal, >1 = plus de contraste)
    # Recommandé: 1.2-1.5 pour des ArUco plus nets
    'contrast': None,
    
    # --- Saturation ---
    # Saturation des couleurs (1.0 = normal, 0 = noir et blanc)
    'saturation': None,
    
    # --- Netteté ---
    # Niveau de netteté (1.0 = normal, >1 = plus net)
    # Recommandé: 1.5-2.0 pour des bords ArUco plus définis
    'sharpness': None,
    
    # --- Réduction de bruit ---
    # Options: 'auto', 'off', 'cdn_off', 'cdn_fast', 'cdn_hq'
    # 'off' = désactivé (préserve les détails des ArUco)
    'denoise': None,
    
    # --- Timeout ---
    # Temps d'attente pour la stabilisation de la caméra (en ms)
    'timeout': 2000,
}

# ============================================================
# CONFIGURATION PRÉTRAITEMENT IMAGE
# ============================================================
# Optionnel: améliorer l'image avant détection ArUco

PREPROCESS_CONFIG = {
    # Activer le prétraitement
    'enabled': False,
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Améliore le contraste local
    'clahe_enabled': False,
    'clahe_clip_limit': 2.0,
    'clahe_grid_size': 8,
    
    # Réduction de bruit
    'blur_enabled': False,
    'blur_kernel_size': 3,
}

# ============================================================
# MAPPING ID ARUCO -> PIÈCES D'ÉCHECS
# ============================================================

PIECES = {
    # Pièces blanches (IDs 0-15)
    0: {'code': 'WK', 'nom': 'Roi', 'couleur': 'Blanc', 'symbole': '♔'},
    1: {'code': 'WQ', 'nom': 'Dame', 'couleur': 'Blanc', 'symbole': '♕'},
    2: {'code': 'WR1', 'nom': 'Tour 1', 'couleur': 'Blanc', 'symbole': '♖'},
    3: {'code': 'WR2', 'nom': 'Tour 2', 'couleur': 'Blanc', 'symbole': '♖'},
    4: {'code': 'WB1', 'nom': 'Fou 1', 'couleur': 'Blanc', 'symbole': '♗'},
    5: {'code': 'WB2', 'nom': 'Fou 2', 'couleur': 'Blanc', 'symbole': '♗'},
    6: {'code': 'WN1', 'nom': 'Cavalier 1', 'couleur': 'Blanc', 'symbole': '♘'},
    7: {'code': 'WN2', 'nom': 'Cavalier 2', 'couleur': 'Blanc', 'symbole': '♘'},
    8: {'code': 'WP1', 'nom': 'Pion 1', 'couleur': 'Blanc', 'symbole': '♙'},
    9: {'code': 'WP2', 'nom': 'Pion 2', 'couleur': 'Blanc', 'symbole': '♙'},
    10: {'code': 'WP3', 'nom': 'Pion 3', 'couleur': 'Blanc', 'symbole': '♙'},
    11: {'code': 'WP4', 'nom': 'Pion 4', 'couleur': 'Blanc', 'symbole': '♙'},
    12: {'code': 'WP5', 'nom': 'Pion 5', 'couleur': 'Blanc', 'symbole': '♙'},
    13: {'code': 'WP6', 'nom': 'Pion 6', 'couleur': 'Blanc', 'symbole': '♙'},
    14: {'code': 'WP7', 'nom': 'Pion 7', 'couleur': 'Blanc', 'symbole': '♙'},
    15: {'code': 'WP8', 'nom': 'Pion 8', 'couleur': 'Blanc', 'symbole': '♙'},
    # Pièces noires (IDs 16-31)
    16: {'code': 'BK', 'nom': 'Roi', 'couleur': 'Noir', 'symbole': '♚'},
    17: {'code': 'BQ', 'nom': 'Dame', 'couleur': 'Noir', 'symbole': '♛'},
    18: {'code': 'BR1', 'nom': 'Tour 1', 'couleur': 'Noir', 'symbole': '♜'},
    19: {'code': 'BR2', 'nom': 'Tour 2', 'couleur': 'Noir', 'symbole': '♜'},
    20: {'code': 'BB1', 'nom': 'Fou 1', 'couleur': 'Noir', 'symbole': '♝'},
    21: {'code': 'BB2', 'nom': 'Fou 2', 'couleur': 'Noir', 'symbole': '♝'},
    22: {'code': 'BN1', 'nom': 'Cavalier 1', 'couleur': 'Noir', 'symbole': '♞'},
    23: {'code': 'BN2', 'nom': 'Cavalier 2', 'couleur': 'Noir', 'symbole': '♞'},
    24: {'code': 'BP1', 'nom': 'Pion 1', 'couleur': 'Noir', 'symbole': '♟'},
    25: {'code': 'BP2', 'nom': 'Pion 2', 'couleur': 'Noir', 'symbole': '♟'},
    26: {'code': 'BP3', 'nom': 'Pion 3', 'couleur': 'Noir', 'symbole': '♟'},
    27: {'code': 'BP4', 'nom': 'Pion 4', 'couleur': 'Noir', 'symbole': '♟'},
    28: {'code': 'BP5', 'nom': 'Pion 5', 'couleur': 'Noir', 'symbole': '♟'},
    29: {'code': 'BP6', 'nom': 'Pion 6', 'couleur': 'Noir', 'symbole': '♟'},
    30: {'code': 'BP7', 'nom': 'Pion 7', 'couleur': 'Noir', 'symbole': '♟'},
    31: {'code': 'BP8', 'nom': 'Pion 8', 'couleur': 'Noir', 'symbole': '♟'},
    # Calibration (IDs 32-35)
    32: {'code': 'CAL_TL', 'nom': 'Calibration Haut-Gauche', 'couleur': 'Calibration', 'symbole': '📍'},
    33: {'code': 'CAL_TR', 'nom': 'Calibration Haut-Droite', 'couleur': 'Calibration', 'symbole': '📍'},
    34: {'code': 'CAL_BL', 'nom': 'Calibration Bas-Gauche', 'couleur': 'Calibration', 'symbole': '📍'},
    35: {'code': 'CAL_BR', 'nom': 'Calibration Bas-Droite', 'couleur': 'Calibration', 'symbole': '📍'},
    # Robot (ID 36)
    36: {'code': 'ROBOT', 'nom': 'Centre Pince Robot', 'couleur': 'Robot', 'symbole': '🤖'},
}

# ============================================================
# DÉTECTION AUTOMATIQUE DE L'ENVIRONNEMENT CAMÉRA
# ============================================================
# Priorité: 1) rpicam-still (CLI), 2) Picamera2, 3) OpenCV
import subprocess
import shutil

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
    print(f"   📁 Dossier images créé/vérifié: {IMAGES_DIR}")
    
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
        # Lister le contenu du dossier pour debug
        print(f"   📂 Contenu de {IMAGES_DIR}:")
        if os.path.exists(IMAGES_DIR):
            for f in os.listdir(IMAGES_DIR):
                print(f"      - {f}")
        else:
            print(f"      (dossier n'existe pas)")
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
        print("   ⚙️  Utilisation des paramètres caméra par défaut (auto)")
    else:
        print("   ⚙️  Utilisation des paramètres caméra personnalisés")
        
        # Résolution (largeur x hauteur)
        if CAMERA_CONFIG.get('width') is not None and CAMERA_CONFIG.get('height') is not None:
            args.extend(['--width', str(CAMERA_CONFIG['width'])])
            args.extend(['--height', str(CAMERA_CONFIG['height'])])
            print(f"   ⚙️  Résolution: {CAMERA_CONFIG['width']}x{CAMERA_CONFIG['height']}")
        else:
            print(f"   ⚙️  Résolution: max (capteur)")
        
        # Exposition (shutter speed)
        if CAMERA_CONFIG.get('shutter') is not None:
            args.extend(['--shutter', str(CAMERA_CONFIG['shutter'])])
            print(f"   ⚙️  Exposition: {CAMERA_CONFIG['shutter']}µs")
        
        # Gain (sensibilité)
        if CAMERA_CONFIG.get('gain') is not None:
            args.extend(['--gain', str(CAMERA_CONFIG['gain'])])
            print(f"   ⚙️  Gain: {CAMERA_CONFIG['gain']}")
        
        # Balance des blancs
        if CAMERA_CONFIG.get('awb') is not None:
            args.extend(['--awb', str(CAMERA_CONFIG['awb'])])
            print(f"   ⚙️  Balance blancs: {CAMERA_CONFIG['awb']}")
        
        # Luminosité
        if CAMERA_CONFIG.get('brightness') is not None:
            args.extend(['--brightness', str(CAMERA_CONFIG['brightness'])])
            print(f"   ⚙️  Luminosité: {CAMERA_CONFIG['brightness']}")
        
        # Contraste
        if CAMERA_CONFIG.get('contrast') is not None:
            args.extend(['--contrast', str(CAMERA_CONFIG['contrast'])])
            print(f"   ⚙️  Contraste: {CAMERA_CONFIG['contrast']}")
        
        # Saturation
        if CAMERA_CONFIG.get('saturation') is not None:
            args.extend(['--saturation', str(CAMERA_CONFIG['saturation'])])
            print(f"   ⚙️  Saturation: {CAMERA_CONFIG['saturation']}")
        
        # Netteté
        if CAMERA_CONFIG.get('sharpness') is not None:
            args.extend(['--sharpness', str(CAMERA_CONFIG['sharpness'])])
            print(f"   ⚙️  Netteté: {CAMERA_CONFIG['sharpness']}")
        
        # Réduction de bruit
        if CAMERA_CONFIG.get('denoise') is not None:
            args.extend(['--denoise', str(CAMERA_CONFIG['denoise'])])
            print(f"   ⚙️  Débruitage: {CAMERA_CONFIG['denoise']}")
    
    print(f"   🔄 Exécution de {cmd}...")
    print(f"   📝 Commande: {' '.join(args)}")
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"   ⚠️ Stderr: {result.stderr}")
            raise RuntimeError(f"{cmd} a échoué: {result.stderr}")
        print(f"   ✅ Capture terminée avec {cmd}")
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
# FONCTIONS UTILITAIRES
# ============================================================
def create_results_dir(timestamp):
    """Crée le dossier de résultats pour cette analyse"""
    result_dir = os.path.join(RESULTS_DIR, f"analyse_{timestamp}")
    os.makedirs(result_dir, exist_ok=True)
    return result_dir


def save_step(img, output_dir, step_name, base_name):
    """Sauvegarde une étape de traitement"""
    filename = f"{base_name}_{step_name}.png"
    filepath = os.path.join(output_dir, filename)
    
    if isinstance(img, np.ndarray):
        if len(img.shape) == 2:
            Image.fromarray(img).save(filepath)
        else:
            Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(filepath)
    else:
        img.save(filepath)
    
    print(f"   💾 Sauvegardé: {filename}")
    return filepath


def get_piece_info(marker_id):
    """Retourne les informations d'une pièce à partir de son ID ArUco"""
    if marker_id in PIECES:
        return PIECES[marker_id]
    return {'code': f'?{marker_id}', 'nom': 'Inconnu', 'couleur': '?', 'symbole': '?'}


# ============================================================
# DÉTECTION ARUCO
# ============================================================
def detect_aruco_markers(img_np):
    """
    Détecte tous les marqueurs ArUco dans une image.
    Retourne une liste de détections avec ID, position, etc.
    """
    detections = []
    
    # Conversion en niveaux de gris
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    # Charger le dictionnaire ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    
    # Paramètres de détection
    parameters = cv2.aruco.DetectorParameters()
    
    # Appliquer les paramètres personnalisés si USE_DEFAULT_ARUCO_PARAMS = False
    if not USE_DEFAULT_ARUCO_PARAMS:
        print("   ⚙️  Utilisation des paramètres ArUco personnalisés")
        parameters.adaptiveThreshWinSizeMin = CUSTOM_ARUCO_PARAMS['adaptiveThreshWinSizeMin']
        parameters.adaptiveThreshWinSizeMax = CUSTOM_ARUCO_PARAMS['adaptiveThreshWinSizeMax']
        parameters.adaptiveThreshWinSizeStep = CUSTOM_ARUCO_PARAMS['adaptiveThreshWinSizeStep']
        parameters.adaptiveThreshConstant = CUSTOM_ARUCO_PARAMS['adaptiveThreshConstant']
        parameters.minMarkerPerimeterRate = CUSTOM_ARUCO_PARAMS['minMarkerPerimeterRate']
        parameters.maxMarkerPerimeterRate = CUSTOM_ARUCO_PARAMS['maxMarkerPerimeterRate']
        parameters.polygonalApproxAccuracyRate = CUSTOM_ARUCO_PARAMS['polygonalApproxAccuracyRate']
        parameters.minCornerDistanceRate = CUSTOM_ARUCO_PARAMS['minCornerDistanceRate']
        parameters.minDistanceToBorder = CUSTOM_ARUCO_PARAMS['minDistanceToBorder']
        parameters.minMarkerDistanceRate = CUSTOM_ARUCO_PARAMS['minMarkerDistanceRate']
        parameters.cornerRefinementMethod = CUSTOM_ARUCO_PARAMS['cornerRefinementMethod']
        parameters.cornerRefinementWinSize = CUSTOM_ARUCO_PARAMS['cornerRefinementWinSize']
        parameters.cornerRefinementMaxIterations = CUSTOM_ARUCO_PARAMS['cornerRefinementMaxIterations']
        parameters.cornerRefinementMinAccuracy = CUSTOM_ARUCO_PARAMS['cornerRefinementMinAccuracy']
    else:
        print("   ⚙️  Utilisation des paramètres ArUco par défaut OpenCV")
    
    # Créer le détecteur
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Détecter les marqueurs
    corners, ids, rejected = detector.detectMarkers(gray)
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            # Coins du marqueur (4 points)
            marker_corners = corners[i][0]
            
            # Convertir en liste
            position = [[int(c[0]), int(c[1])] for c in marker_corners]
            
            # Centre du marqueur
            center_x = sum(c[0] for c in marker_corners) / 4
            center_y = sum(c[1] for c in marker_corners) / 4
            
            # Informations de la pièce
            piece_info = get_piece_info(marker_id)
            
            detections.append({
                'id': int(marker_id),
                'code': piece_info['code'],
                'piece': piece_info,
                'position': position,
                'center': (center_x, center_y),
                'corners': marker_corners
            })
    
    return detections, rejected


# ============================================================
# ANALYSE DE L'ÉTAT DU JEU
# ============================================================
def analyze_game_state(image_path, result_dir, timestamp):
    """
    Analyse l'état du jeu à partir d'une image
    
    Args:
        image_path: Chemin vers l'image à analyser
        result_dir: Dossier où sauvegarder les résultats
        timestamp: Timestamp pour nommer les fichiers
    
    Returns:
        dict: État du jeu avec toutes les pièces détectées
    """
    base_name = f"analyse_{timestamp}"
    
    print(f"\n🔍 Analyse de l'image: {os.path.basename(image_path)}")
    
    # Charger l'image
    original_img = Image.open(image_path)
    
    # Redimensionnement si nécessaire
    width, height = original_img.size
    if MAX_DIMENSION is not None and max(width, height) > MAX_DIMENSION:
        scale_factor = MAX_DIMENSION / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        original_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"   📐 Image redimensionnée: {width}x{height} → {new_width}x{new_height}")
    else:
        print(f"   📐 Image conservée: {width}x{height}")
    
    # Sauvegarder l'original
    save_step(original_img, result_dir, "00_original", base_name)
    
    # Conversion en numpy array (RGB)
    img_np = np.array(original_img)
    
    # Détection des marqueurs ArUco
    print("\n🎯 Détection des marqueurs ArUco...")
    start_time = time.time()
    
    detections, rejected = detect_aruco_markers(img_np)
    
    detection_time = time.time() - start_time
    print(f"   ⏱️  Temps de détection: {detection_time*1000:.1f} ms")
    print(f"   ✅ Marqueurs détectés: {len(detections)}")
    print(f"   ❌ Candidats rejetés: {len(rejected)}")
    
    # Charger la font
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        font_small = ImageFont.load_default()
        font_large = ImageFont.load_default()
    
    # Dessiner les annotations
    img_annotated = original_img.copy()
    draw = ImageDraw.Draw(img_annotated)
    
    for det in detections:
        position = det['position']
        marker_id = det['id']
        piece = det['piece']
        center = det['center']
        
        # Couleur selon la pièce
        if marker_id < 16:  # Blancs
            color = (0, 180, 0)  # Vert
        else:  # Noirs
            color = (0, 100, 255)  # Bleu
        
        # Dessiner le contour du marqueur
        points = [(int(p[0]), int(p[1])) for p in position]
        draw.polygon(points, outline=color, width=3)
        
        # Dessiner les coins (pour voir l'orientation)
        for j, pt in enumerate(points):
            radius = 6 if j == 0 else 4  # Premier coin plus gros
            draw.ellipse([pt[0]-radius, pt[1]-radius, pt[0]+radius, pt[1]+radius], 
                        fill=color if j == 0 else 'white', outline=color)
        
        # Dessiner le centre
        cx, cy = int(center[0]), int(center[1])
        draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill='red')
        
        # Label
        label = f"{piece['symbole']} {piece['code']} (ID:{marker_id})"
        text_bbox = draw.textbbox((0, 0), label, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position du texte
        top_y = min(p[1] for p in position)
        text_x = int(center[0] - text_width / 2)
        text_y = int(top_y) - text_height - 10
        
        # Fond blanc pour le texte
        draw.rectangle(
            [text_x - 3, text_y - 2, text_x + text_width + 3, text_y + text_height + 2],
            fill='white', outline=color
        )
        draw.text((text_x, text_y), label, fill=color, font=font_large)
    
    # Sauvegarder le résultat annoté
    save_step(img_annotated, result_dir, "99_resultat_final", base_name)
    
    # Préparer l'état du jeu
    whites = [d for d in detections if d['id'] < 16]
    blacks = [d for d in detections if d['id'] >= 16]
    
    all_ids = set(PIECES.keys())
    detected_ids = set(d['id'] for d in detections)
    missing_ids = all_ids - detected_ids
    
    game_state = {
        'timestamp': timestamp,
        'image_path': image_path,
        'detection_time_ms': detection_time * 1000,
        'total_detected': len(detections),
        'whites_detected': len(whites),
        'blacks_detected': len(blacks),
        'missing_count': len(missing_ids),
        'pieces': [],
        'missing_pieces': []
    }
    
    # Ajouter les pièces détectées
    for det in detections:
        game_state['pieces'].append({
            'id': det['id'],
            'code': det['code'],
            'nom': det['piece']['nom'],
            'couleur': det['piece']['couleur'],
            'symbole': det['piece']['symbole'],
            'center_x': float(det['center'][0]),
            'center_y': float(det['center'][1]),
            'corners': [[float(c[0]), float(c[1])] for c in det['position']]
        })
    
    # Ajouter les pièces manquantes
    for marker_id in sorted(missing_ids):
        piece = PIECES[marker_id]
        game_state['missing_pieces'].append({
            'id': marker_id,
            'code': piece['code'],
            'nom': piece['nom'],
            'couleur': piece['couleur'],
            'symbole': piece['symbole']
        })
    
    # Sauvegarder l'état du jeu en JSON
    json_path = os.path.join(result_dir, f"{base_name}_game_state.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(game_state, f, ensure_ascii=False, indent=2)
    print(f"   💾 État du jeu sauvegardé: {os.path.basename(json_path)}")
    
    return game_state, whites, blacks


def print_results(game_state, whites, blacks):
    """Affiche les résultats de l'analyse"""
    print("\n" + "=" * 60)
    print("📋 PIÈCES DÉTECTÉES")
    print("=" * 60)
    
    if whites:
        print("\n⬜ PIÈCES BLANCHES:")
        for piece in sorted(game_state['pieces'], key=lambda x: x['id']):
            if piece['id'] < 16:
                print(f"   ID {piece['id']:2} = {piece['symbole']} {piece['code']:4} @ ({piece['center_x']:.0f}, {piece['center_y']:.0f})")
    
    if blacks:
        print("\n⬛ PIÈCES NOIRES:")
        for piece in sorted(game_state['pieces'], key=lambda x: x['id']):
            if piece['id'] >= 16:
                print(f"   ID {piece['id']:2} = {piece['symbole']} {piece['code']:4} @ ({piece['center_x']:.0f}, {piece['center_y']:.0f})")
    
    # Statistiques
    print("\n" + "=" * 60)
    print("📊 STATISTIQUES")
    print("=" * 60)
    print(f"   Total détecté: {game_state['total_detected']}/32 marqueurs")
    print(f"   Pièces blanches: {game_state['whites_detected']}/16")
    print(f"   Pièces noires: {game_state['blacks_detected']}/16")
    print(f"   Temps de détection: {game_state['detection_time_ms']:.1f} ms")
    
    # Pièces manquantes
    if game_state['missing_pieces']:
        print(f"\n   ⚠️  Pièces manquantes ({game_state['missing_count']}):")
        for piece in game_state['missing_pieces']:
            print(f"      ID {piece['id']:2} - {piece['symbole']} {piece['code']} ({piece['couleur']} {piece['nom']})")
    else:
        print("\n   ✅ Toutes les 32 pièces ont été détectées!")


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================
def photo_and_analyze():
    """
    Fonction principale: prend une photo et analyse l'état du jeu
    
    Returns:
        dict: État du jeu
    """
    print("=" * 60)
    print("📸 PHOTO ET ANALYSE - ÉTAT DU JEU D'ÉCHECS")
    print("   (ArUco Detection)")
    print("=" * 60)
    
    # Générer le timestamp pour cette session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer les dossiers
    os.makedirs(IMAGES_DIR, exist_ok=True)
    result_dir = create_results_dir(timestamp)
    
    print(f"\n📁 Dossier images: {IMAGES_DIR}")
    print(f"📁 Dossier résultats: {result_dir}")
    
    # Prendre la photo
    print("\n" + "-" * 60)
    print("📷 ÉTAPE 1: Prise de photo")
    print("-" * 60)
    
    photo_filename = f"photo_{timestamp}.jpg"
    image_path = take_photo(photo_filename)
    
    # Analyser l'état du jeu
    print("\n" + "-" * 60)
    print("🔍 ÉTAPE 2: Analyse de l'état du jeu")
    print("-" * 60)
    
    game_state, whites, blacks = analyze_game_state(image_path, result_dir, timestamp)
    
    # Afficher les résultats
    print_results(game_state, whites, blacks)
    
    print(f"\n✅ Analyse terminée!")
    print(f"   📷 Photo: {image_path}")
    print(f"   📁 Résultats: {result_dir}")
    
    return game_state


def analyze_existing_image(image_path=None):
    """
    Analyse une image existante (sans prendre de nouvelle photo)
    
    Args:
        image_path: Chemin vers l'image à analyser. Si None, liste les images disponibles.
    
    Returns:
        dict: État du jeu
    """
    print("=" * 60)
    print("🔍 ANALYSE D'IMAGE EXISTANTE - ÉTAT DU JEU D'ÉCHECS")
    print("   (ArUco Detection)")
    print("=" * 60)
    
    # Si pas d'image spécifiée, lister les images disponibles
    if image_path is None:
        image_path = select_image()
        if image_path is None:
            print("❌ Aucune image sélectionnée. Arrêt du programme.")
            return None
    
    # Vérifier que l'image existe
    if not os.path.exists(image_path):
        print(f"❌ Image non trouvée: {image_path}")
        return None
    
    # Générer le timestamp pour cette session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le dossier de résultats
    result_dir = create_results_dir(timestamp)
    print(f"\n📁 Dossier résultats: {result_dir}")
    
    # Analyser l'état du jeu
    game_state, whites, blacks = analyze_game_state(image_path, result_dir, timestamp)
    
    # Afficher les résultats
    print_results(game_state, whites, blacks)
    
    print(f"\n✅ Analyse terminée!")
    print(f"   📷 Image analysée: {image_path}")
    print(f"   📁 Résultats: {result_dir}")
    
    return game_state


def select_image():
    """Liste les images disponibles et demande à l'utilisateur de choisir"""
    import glob
    
    # Chercher dans le dossier images et dans le dossier courant
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    images = []
    
    # Images dans le dossier images/
    if os.path.exists(IMAGES_DIR):
        for ext in extensions:
            images.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
    
    # Images dans le dossier du script
    for ext in extensions:
        images.extend(glob.glob(os.path.join(SCRIPT_DIR, ext)))
    
    if not images:
        print("❌ Aucune image trouvée.")
        return None
    
    images = sorted(set(images))  # Enlever les doublons et trier
    
    print("\n📷 Images disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("\nEntrez le numéro de l'image (ou 'q' pour quitter): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(images):
                return images[choice_num - 1]
            else:
                print(f"⚠️  Veuillez entrer un numéro entre 1 et {len(images)}")
        except ValueError:
            print("⚠️  Veuillez entrer un numéro valide")


# ============================================================
# POINT D'ENTRÉE
# ============================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Mode: analyser une image existante passée en argument
        image_path = sys.argv[1]
        analyze_existing_image(image_path)
    else:
        # Mode interactif
        print("\nChoisissez une option:")
        print("  1. Prendre une photo et analyser")
        print("  2. Analyser une image existante")
        print("  q. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == '1':
            photo_and_analyze()
        elif choice == '2':
            analyze_existing_image()
        elif choice.lower() == 'q':
            print("Au revoir!")
        else:
            print("Option invalide. Au revoir!")
