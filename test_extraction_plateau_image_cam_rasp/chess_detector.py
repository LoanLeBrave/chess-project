#!/usr/bin/env python3
"""
Chess Detector - Script optimisé pour la détection en temps réel
Génère les images et JSON en écrasant les précédents à chaque exécution.

Fichiers de sortie (dans OUTPUT_DIR):
    - board_extracted.jpg : Plateau extrait et redressé
    - pieces_detected.jpg : Plateau avec ArUcos détectés et IDs
    - game_state.json : Coordonnées des pièces (x, y dans repère -10/+10)
    - board_state.json : État du plateau (format chess: {"a8": "BR", ...})
"""

import os
import cv2
import json
import numpy as np
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "realtime_output")

# Taille du plateau extrait
BOARD_SIZE = 800

# Dictionnaire ArUco
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# IDs des marqueurs de calibration (coins du plateau)
CALIBRATION_IDS = {
    32: 'CAL_TL',  # Top-Left
    33: 'CAL_TR',  # Top-Right
    34: 'CAL_BL',  # Bottom-Left
    35: 'CAL_BR',  # Bottom-Right
}

# Offsets des coins (mêmes valeurs que detect_board_corners.py)
# Convention:
#   - offset_x positif = décaler vers la DROITE
#   - offset_x négatif = décaler vers la GAUCHE
#   - offset_y positif = décaler vers le BAS
#   - offset_y négatif = décaler vers le HAUT
OFFSETS = {
    "CAL_TL": {"offset_x": 0, "offset_y": 0},
    "CAL_TR": {"offset_x": 54, "offset_y": -86},
    "CAL_BL": {"offset_x": -90, "offset_y": 112},
    "CAL_BR": {"offset_x": 53, "offset_y": 86}
}

# Configuration des pièces (IDs 0-31)
PIECE_IDS = {
    # Blanches (0-15)
    0: ('white', 'Pawn'), 1: ('white', 'Pawn'), 2: ('white', 'Pawn'), 3: ('white', 'Pawn'),
    4: ('white', 'Pawn'), 5: ('white', 'Pawn'), 6: ('white', 'Pawn'), 7: ('white', 'Pawn'),
    8: ('white', 'Rook'), 9: ('white', 'Rook'), 10: ('white', 'Knight'), 11: ('white', 'Knight'),
    12: ('white', 'Bishop'), 13: ('white', 'Bishop'), 14: ('white', 'Queen'), 15: ('white', 'King'),
    # Noires (16-31)
    16: ('black', 'Pawn'), 17: ('black', 'Pawn'), 18: ('black', 'Pawn'), 19: ('black', 'Pawn'),
    20: ('black', 'Pawn'), 21: ('black', 'Pawn'), 22: ('black', 'Pawn'), 23: ('black', 'Pawn'),
    24: ('black', 'Rook'), 25: ('black', 'Rook'), 26: ('black', 'Knight'), 27: ('black', 'Knight'),
    28: ('black', 'Bishop'), 29: ('black', 'Bishop'), 30: ('black', 'Queen'), 31: ('black', 'King'),
}

# Codes des pièces pour le JSON
PIECE_CODES = {'King': 'K', 'Queen': 'Q', 'Rook': 'R', 'Bishop': 'B', 'Knight': 'N', 'Pawn': 'P'}


# ============================================================
# FONCTIONS DE DÉTECTION (même logique que detect_board_corners.py)
# ============================================================

def create_aruco_detector():
    """
    Crée un détecteur ArUco avec les paramètres optimisés.
    """
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
    
    return cv2.aruco.ArucoDetector(aruco_dict, parameters)


def detect_calibration_markers(img, detector):
    """
    Détecte les marqueurs ArUco de calibration (IDs 32-35).
    
    Args:
        img: Image numpy (BGR)
        detector: Détecteur ArUco
    
    Returns:
        dict: {marker_id: {'center': (x, y), 'corners': [...], 'code': 'CAL_XX'}}
    """
    # Conversion en niveaux de gris
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Détecter les marqueurs
    corners, ids, _ = detector.detectMarkers(gray)
    
    calibration_markers = {}
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            marker_id = int(marker_id)
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
    """
    board_corners = {}
    
    for marker_id, marker_data in calibration_markers.items():
        code = marker_data['code']
        center = marker_data['center']
        
        # Appliquer l'offset
        offset = OFFSETS[code]
        board_x = center[0] + offset['offset_x']
        board_y = center[1] + offset['offset_y']
        
        board_corners[code] = (board_x, board_y)
    
    return board_corners


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
    
    # Cas avec 2 coins détectés
    elif len(missing) == 2 and len(detected) == 2:
        # Diagonale TL-BR détectée
        if 'CAL_TL' in detected and 'CAL_BR' in detected:
            tl, br = board_corners['CAL_TL'], board_corners['CAL_BR']
            estimated_corners['CAL_TR'] = (br[0], tl[1])
            estimated_corners['CAL_BL'] = (tl[0], br[1])
            estimated_codes.extend(['CAL_TR', 'CAL_BL'])
        # Diagonale TR-BL détectée
        elif 'CAL_TR' in detected and 'CAL_BL' in detected:
            tr, bl = board_corners['CAL_TR'], board_corners['CAL_BL']
            estimated_corners['CAL_TL'] = (bl[0], tr[1])
            estimated_corners['CAL_BR'] = (tr[0], bl[1])
            estimated_codes.extend(['CAL_TL', 'CAL_BR'])
        # Ligne du haut TL-TR détectée
        elif 'CAL_TL' in detected and 'CAL_TR' in detected:
            tl, tr = board_corners['CAL_TL'], board_corners['CAL_TR']
            width = tr[0] - tl[0]
            estimated_corners['CAL_BL'] = (tl[0], tl[1] + abs(width))
            estimated_corners['CAL_BR'] = (tr[0], tr[1] + abs(width))
            estimated_codes.extend(['CAL_BL', 'CAL_BR'])
        # Ligne du bas BL-BR détectée
        elif 'CAL_BL' in detected and 'CAL_BR' in detected:
            bl, br = board_corners['CAL_BL'], board_corners['CAL_BR']
            width = br[0] - bl[0]
            estimated_corners['CAL_TL'] = (bl[0], bl[1] - abs(width))
            estimated_corners['CAL_TR'] = (br[0], br[1] - abs(width))
            estimated_codes.extend(['CAL_TL', 'CAL_TR'])
        # Ligne gauche TL-BL détectée
        elif 'CAL_TL' in detected and 'CAL_BL' in detected:
            tl, bl = board_corners['CAL_TL'], board_corners['CAL_BL']
            height = bl[1] - tl[1]
            estimated_corners['CAL_TR'] = (tl[0] + abs(height), tl[1])
            estimated_corners['CAL_BR'] = (bl[0] + abs(height), bl[1])
            estimated_codes.extend(['CAL_TR', 'CAL_BR'])
        # Ligne droite TR-BR détectée
        elif 'CAL_TR' in detected and 'CAL_BR' in detected:
            tr, br = board_corners['CAL_TR'], board_corners['CAL_BR']
            height = br[1] - tr[1]
            estimated_corners['CAL_TL'] = (tr[0] - abs(height), tr[1])
            estimated_corners['CAL_BL'] = (br[0] - abs(height), br[1])
            estimated_codes.extend(['CAL_TL', 'CAL_BL'])
    
    return estimated_corners, estimated_codes


def extract_board(img, board_corners):
    """
    Extrait et redresse le plateau d'échecs.
    
    Args:
        img: Image source
        board_corners: dict des 4 coins {CAL_TL, CAL_TR, CAL_BL, CAL_BR}
    
    Returns:
        Image du plateau redressé (BOARD_SIZE x BOARD_SIZE)
    """
    # Points source (coins du plateau dans l'image originale)
    src_pts = np.float32([
        board_corners['CAL_TL'],
        board_corners['CAL_TR'],
        board_corners['CAL_BL'],
        board_corners['CAL_BR']
    ])
    
    # Points destination (image carrée)
    dst_pts = np.float32([
        [0, 0],
        [BOARD_SIZE, 0],
        [0, BOARD_SIZE],
        [BOARD_SIZE, BOARD_SIZE]
    ])
    
    # Transformation perspective
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    board_img = cv2.warpPerspective(img, matrix, (BOARD_SIZE, BOARD_SIZE))
    
    return board_img


def detect_pieces(board_img, detector):
    """
    Détecte les pièces d'échecs sur le plateau extrait.
    
    Args:
        board_img: Image du plateau extrait
        detector: Détecteur ArUco
    
    Returns:
        list: Liste des pièces détectées avec leurs informations
        dict: Dictionnaire case -> code pièce pour board_state.json
    """
    # Conversion en niveaux de gris
    if len(board_img.shape) == 3:
        gray = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = board_img
    
    # Détecter les marqueurs
    corners, ids, _ = detector.detectMarkers(gray)
    
    pieces = []
    pieces_on_board = {}
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            marker_id = int(marker_id)
            if marker_id in PIECE_IDS:
                marker_corners = corners[i][0]
                
                # Centre du marqueur
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                
                color, piece_type = PIECE_IDS[marker_id]
                
                # Coordonnées dans le repère -10/+10
                x = -10 + (center_x / BOARD_SIZE) * 20
                y = 10 - (center_y / BOARD_SIZE) * 20
                
                # Case d'échecs
                col = int(center_x / BOARD_SIZE * 8)
                row = int(center_y / BOARD_SIZE * 8)
                col = max(0, min(7, col))
                row = max(0, min(7, row))
                square = f"{'abcdefgh'[col]}{8 - row}"
                
                pieces.append({
                    'id': marker_id,
                    'color': color,
                    'piece_type': piece_type,
                    'x': round(x, 2),
                    'y': round(y, 2),
                    'square': square,
                    'pixel': (int(center_x), int(center_y))
                })
                
                # Code pour board_state
                color_code = 'W' if color == 'white' else 'B'
                pieces_on_board[square] = f"{color_code}{PIECE_CODES[piece_type]}"
    
    return pieces, pieces_on_board


def draw_pieces_on_board(board_img, pieces, corners_data=None):
    """
    Dessine les pièces détectées sur l'image du plateau.
    
    Args:
        board_img: Image du plateau
        pieces: Liste des pièces détectées
        corners_data: Données des corners ArUco pour les dessiner
    
    Returns:
        Image annotée
    """
    img_annotated = board_img.copy()
    
    # Dessiner les contours ArUco si disponibles
    if corners_data is not None:
        corners, ids = corners_data
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(img_annotated, corners, ids)
    
    # Ajouter les infos sur chaque pièce
    for piece in pieces:
        px, py = piece['pixel']
        
        # Couleurs selon la pièce
        if piece['color'] == 'white':
            box_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            box_color = (50, 50, 50)
            text_color = (255, 255, 255)
        
        # Étiquette avec ID
        label = f"ID:{piece['id']}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        
        # Position de l'étiquette (en dessous du marqueur)
        label_x = px - tw // 2
        label_y = py + 30
        
        # Rectangle de fond
        cv2.rectangle(img_annotated, (label_x - 2, label_y - th - 2),
                     (label_x + tw + 2, label_y + 4), box_color, -1)
        cv2.rectangle(img_annotated, (label_x - 2, label_y - th - 2),
                     (label_x + tw + 2, label_y + 4), (0, 255, 0), 1)
        
        # Texte
        cv2.putText(img_annotated, label, (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
    
    # Compteur en haut
    white_count = len([p for p in pieces if p['color'] == 'white'])
    black_count = len([p for p in pieces if p['color'] == 'black'])
    cv2.putText(img_annotated, f"Pieces: {len(pieces)} (W:{white_count} B:{black_count})",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return img_annotated


def generate_game_state_json(pieces):
    """
    Génère le JSON des coordonnées des pièces.
    """
    return {
        'coordinates': sorted([{
            'id': p['id'],
            'color': p['color'],
            'piece_type': p['piece_type'],
            'x': p['x'],
            'y': p['y']
        } for p in pieces], key=lambda x: x['id']),
        'metadata': {
            'pieces_count': len(pieces),
            'timestamp': datetime.now().isoformat()
        }
    }


def generate_board_state_json(pieces_on_board):
    """
    Génère le JSON de l'état du plateau (format échecs).
    """
    board = {}
    for row in '87654321':
        for col in 'abcdefgh':
            square = f"{col}{row}"
            board[square] = pieces_on_board.get(square, None)
    
    return {'board': board}


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def analyze_board(image_path=None, image_np=None):
    """
    Analyse le plateau d'échecs et génère les fichiers de sortie.
    
    Args:
        image_path: Chemin vers l'image (optionnel si image_np fourni)
        image_np: Image numpy BGR (optionnel si image_path fourni)
    
    Returns:
        dict: Résultats de l'analyse ou None si échec
    """
    # Charger l'image
    if image_np is not None:
        img = image_np.copy()
    elif image_path:
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Impossible de charger: {image_path}")
            return None
    else:
        print("❌ Aucune image fournie")
        return None
    
    # Créer le dossier de sortie
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Créer le détecteur ArUco (paramètres optimisés)
    detector = create_aruco_detector()
    
    # 1. Détecter les marqueurs de calibration
    print("🎯 Détection des marqueurs de calibration...")
    calibration_markers = detect_calibration_markers(img, detector)
    
    print(f"   ✅ Marqueurs de calibration détectés: {len(calibration_markers)}/4")
    for marker_id, data in calibration_markers.items():
        print(f"      ID {marker_id} ({data['code']}): centre = ({data['center'][0]:.1f}, {data['center'][1]:.1f})")
    
    # Vérifier qu'on a au moins 2 marqueurs
    if len(calibration_markers) < 2:
        print(f"❌ Pas assez de marqueurs de calibration ({len(calibration_markers)}/4, minimum 2)")
        return None
    
    # 2. Calculer les coins du plateau avec offsets
    print("\n📐 Calcul des coins du plateau...")
    board_corners = calculate_board_corners(calibration_markers)
    
    for code, corner in board_corners.items():
        print(f"   {code}: ({corner[0]:.1f}, {corner[1]:.1f})")
    
    # 3. Estimer les coins manquants si nécessaire
    estimated_codes = []
    if len(board_corners) < 4:
        print("\n🔮 Estimation des coins manquants...")
        board_corners, estimated_codes = estimate_missing_corners(board_corners)
        if estimated_codes:
            for code in estimated_codes:
                print(f"   ⚠️  {code} estimé: ({board_corners[code][0]:.1f}, {board_corners[code][1]:.1f})")
        else:
            print("   ❌ Impossible d'estimer les coins manquants")
            return None
    
    if len(board_corners) < 4:
        print("❌ Impossible de déterminer les 4 coins du plateau")
        return None
    
    # 4. Extraire le plateau
    print("\n🔲 Extraction du plateau...")
    board_img = extract_board(img, board_corners)
    print(f"   ✅ Plateau extrait: {BOARD_SIZE}x{BOARD_SIZE} pixels")
    
    # 5. Détecter les pièces sur le plateau extrait
    print("\n♟️  Détection des pièces...")
    pieces, pieces_on_board = detect_pieces(board_img, detector)
    
    white_count = len([p for p in pieces if p['color'] == 'white'])
    black_count = len([p for p in pieces if p['color'] == 'black'])
    print(f"   ✅ {len(pieces)} pièces détectées (Blanches: {white_count}, Noires: {black_count})")
    
    for piece in sorted(pieces, key=lambda p: p['id']):
        print(f"      ID {piece['id']}: {piece['color']} {piece['piece_type']} "
              f"à ({piece['x']:.2f}, {piece['y']:.2f}) [{piece['square']}]")
    
    # 6. Créer l'image annotée
    # Re-détecter pour avoir les corners pour le dessin
    gray_board = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    corners_draw, ids_draw, _ = detector.detectMarkers(gray_board)
    img_detected = draw_pieces_on_board(board_img, pieces, (corners_draw, ids_draw))
    
    # 7. Générer les JSONs
    game_state = generate_game_state_json(pieces)
    board_state = generate_board_state_json(pieces_on_board)
    
    # 8. Sauvegarder les fichiers
    print("\n💾 Sauvegarde des fichiers...")
    
    cv2.imwrite(os.path.join(OUTPUT_DIR, "board_extracted.jpg"), board_img)
    print(f"   ✅ board_extracted.jpg")
    
    cv2.imwrite(os.path.join(OUTPUT_DIR, "pieces_detected.jpg"), img_detected)
    print(f"   ✅ pieces_detected.jpg")
    
    with open(os.path.join(OUTPUT_DIR, "game_state.json"), 'w', encoding='utf-8') as f:
        json.dump(game_state, f, indent=2, ensure_ascii=False)
    print(f"   ✅ game_state.json")
    
    with open(os.path.join(OUTPUT_DIR, "board_state.json"), 'w', encoding='utf-8') as f:
        json.dump(board_state, f, indent=2, ensure_ascii=False)
    print(f"   ✅ board_state.json")
    
    print(f"\n📁 Sortie: {OUTPUT_DIR}")
    
    return {
        'pieces': pieces,
        'game_state': game_state,
        'board_state': board_state,
        'board_image': board_img,
        'detected_image': img_detected,
        'board_corners': board_corners,
        'estimated_codes': estimated_codes
    }


def capture_and_analyze():
    """Capture une photo avec la caméra Raspberry Pi et analyse."""
    try:
        from picamera2 import Picamera2
        import time
        
        print("📷 Initialisation de la caméra...")
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": (4056, 3040)})
        picam2.configure(config)
        picam2.start()
        
        print("   ⏳ Stabilisation...")
        time.sleep(1)
        
        print("   📸 Capture...")
        img = picam2.capture_array()
        picam2.stop()
        
        # Convertir RGB -> BGR pour OpenCV
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        return analyze_board(image_np=img_bgr)
        
    except ImportError:
        print("❌ picamera2 non disponible (pas sur Raspberry Pi?)")
        return None


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("♟️  CHESS DETECTOR - Détection temps réel")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Image fournie en argument
        image_path = sys.argv[1]
        print(f"📷 Image: {image_path}")
        result = analyze_board(image_path=image_path)
    else:
        # Essayer la caméra, sinon chercher une image
        result = capture_and_analyze()
        
        if result is None:
            # Chercher une image de test
            import glob
            images = glob.glob(os.path.join(SCRIPT_DIR, "images", "*.jpg"))
            if images:
                print(f"\n📷 Utilisation de: {images[0]}")
                result = analyze_board(image_path=images[0])
            else:
                print("\n❌ Aucune image disponible")
                print("Usage: python chess_detector.py [image.jpg]")
    
    if result:
        print("\n" + "=" * 60)
        print("✅ Analyse terminée avec succès!")
        print("=" * 60)
