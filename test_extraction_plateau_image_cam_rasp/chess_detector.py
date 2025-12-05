#!/usr/bin/env python3
"""
Chess Detector - Script optimisé pour la détection en temps réel
Génère les images et JSON en écrasant les précédents à chaque exécution.

Fichiers de sortie (dans OUTPUT_DIR):
    - board_extracted.jpg : Plateau extrait et redressé
    - pieces_detected.jpg : Plateau avec ArUcos détectés et IDs
    - game_state.json : Coordonnées des pièces (x, y dans repère -10/+10)
    - board_state.json : État du plateau (format chess: a8, BR, b8, BN, ...)
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
    32: 'TL',  # Top-Left
    33: 'TR',  # Top-Right
    34: 'BL',  # Bottom-Left
    35: 'BR',  # Bottom-Right
}

# Offsets des coins (à ajuster selon votre configuration)
# Mêmes valeurs que dans detect_board_corners.py
OFFSETS = {
    'TL': {'x': 0, 'y': 0},
    'TR': {'x': 54, 'y': -86},
    'BL': {'x': -90, 'y': 112},
    'BR': {'x': 53, 'y': 86},
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
    
    # 1. Détecter les marqueurs de calibration
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(gray)
    
    if ids is None:
        print("❌ Aucun ArUco détecté sur l'image originale")
        return None
    
    print(f"   🔍 ArUcos détectés sur image originale: {len(ids)} (IDs: {sorted(ids.flatten().tolist())})")
    
    # Extraire les coins de calibration
    cal_markers = {}
    for i, marker_id in enumerate(ids.flatten()):
        marker_id = int(marker_id)
        if marker_id in CALIBRATION_IDS:
            center = corners[i][0].mean(axis=0)
            cal_markers[CALIBRATION_IDS[marker_id]] = center
    
    if len(cal_markers) < 3:
        print(f"❌ Pas assez de marqueurs de calibration ({len(cal_markers)}/4)")
        return None
    
    # 2. Calculer les coins du plateau avec offsets
    board_corners = {}
    for code, center in cal_markers.items():
        offset = OFFSETS[code]
        board_corners[code] = (center[0] + offset['x'], center[1] + offset['y'])
    
    # Estimer le coin manquant si nécessaire
    if len(board_corners) == 3:
        board_corners = _estimate_fourth_corner(board_corners)
    
    if len(board_corners) < 4:
        print("❌ Impossible de déterminer les 4 coins")
        return None
    
    # 3. Extraire le plateau (transformation perspective)
    src_pts = np.float32([
        board_corners['TL'], board_corners['TR'],
        board_corners['BL'], board_corners['BR']
    ])
    dst_pts = np.float32([
        [0, 0], [BOARD_SIZE, 0],
        [0, BOARD_SIZE], [BOARD_SIZE, BOARD_SIZE]
    ])
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    board_img = cv2.warpPerspective(img, matrix, (BOARD_SIZE, BOARD_SIZE))
    
    # 4. Détecter les pièces sur le plateau extrait
    gray_board = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    corners_pieces, ids_pieces, _ = detector.detectMarkers(gray_board)
    
    # Debug: afficher ce qui est détecté sur le plateau extrait
    if ids_pieces is not None:
        print(f"   🔍 ArUcos détectés sur plateau extrait: {len(ids_pieces)} (IDs: {sorted(ids_pieces.flatten().tolist())})")
    else:
        print("   ⚠️  Aucun ArUco détecté sur le plateau extrait")
    
    pieces = []
    pieces_on_board = {}  # Pour board_state.json
    
    if ids_pieces is not None:
        for i, marker_id in enumerate(ids_pieces.flatten()):
            marker_id = int(marker_id)
            if marker_id in PIECE_IDS:
                center = corners_pieces[i][0].mean(axis=0)
                color, piece_type = PIECE_IDS[marker_id]
                
                # Coordonnées dans le repère -10/+10
                x = -10 + (center[0] / BOARD_SIZE) * 20
                y = 10 - (center[1] / BOARD_SIZE) * 20
                
                # Case d'échecs
                col = int(center[0] / BOARD_SIZE * 8)
                row = int(center[1] / BOARD_SIZE * 8)
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
                    'pixel': (int(center[0]), int(center[1]))
                })
                
                # Code pour board_state
                color_code = 'W' if color == 'white' else 'B'
                pieces_on_board[square] = f"{color_code}{PIECE_CODES[piece_type]}"
    
    # 5. Créer l'image avec les ArUcos détectés
    img_detected = board_img.copy()
    if ids_pieces is not None:
        cv2.aruco.drawDetectedMarkers(img_detected, corners_pieces, ids_pieces)
    
    # Ajouter les infos sur chaque pièce
    for piece in pieces:
        px, py = piece['pixel']
        color_bgr = (255, 255, 255) if piece['color'] == 'white' else (50, 50, 50)
        text_color = (0, 0, 0) if piece['color'] == 'white' else (255, 255, 255)
        
        # Étiquette
        label = f"ID:{piece['id']}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(img_detected, (px - 2, py + 25), (px + tw + 2, py + 25 + th + 4), color_bgr, -1)
        cv2.putText(img_detected, label, (px, py + 25 + th), cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
    
    # Compteur
    white_count = len([p for p in pieces if p['color'] == 'white'])
    black_count = len([p for p in pieces if p['color'] == 'black'])
    cv2.putText(img_detected, f"Pieces: {len(pieces)} (W:{white_count} B:{black_count})",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # 6. Générer les JSONs
    # game_state.json - Coordonnées
    game_state = {
        'coordinates': sorted([{
            'id': p['id'], 'color': p['color'], 'piece_type': p['piece_type'],
            'x': p['x'], 'y': p['y']
        } for p in pieces], key=lambda x: x['id']),
        'metadata': {
            'pieces_count': len(pieces),
            'timestamp': datetime.now().isoformat()
        }
    }
    
    # board_state.json - Format chess {"board": {"a8": "BR", ...}}
    board_state = {'board': {}}
    for row in '87654321':
        for col in 'abcdefgh':
            square = f"{col}{row}"
            board_state['board'][square] = pieces_on_board.get(square, None)
    
    # 7. Sauvegarder les fichiers
    cv2.imwrite(os.path.join(OUTPUT_DIR, "board_extracted.jpg"), board_img)
    cv2.imwrite(os.path.join(OUTPUT_DIR, "pieces_detected.jpg"), img_detected)
    
    with open(os.path.join(OUTPUT_DIR, "game_state.json"), 'w') as f:
        json.dump(game_state, f, indent=2)
    
    with open(os.path.join(OUTPUT_DIR, "board_state.json"), 'w') as f:
        json.dump(board_state, f, indent=2)
    
    print(f"✅ Analyse terminée: {len(pieces)} pièces détectées")
    print(f"   📁 Sortie: {OUTPUT_DIR}")
    
    return {
        'pieces': pieces,
        'game_state': game_state,
        'board_state': board_state,
        'board_image': board_img,
        'detected_image': img_detected
    }


def _estimate_fourth_corner(corners):
    """Estime le 4ème coin manquant à partir des 3 autres."""
    codes = list(corners.keys())
    missing = [c for c in ['TL', 'TR', 'BL', 'BR'] if c not in codes][0]
    
    # Logique d'estimation basée sur la géométrie du rectangle
    if missing == 'BR':
        corners['BR'] = (corners['TR'][0] + corners['BL'][0] - corners['TL'][0],
                         corners['TR'][1] + corners['BL'][1] - corners['TL'][1])
    elif missing == 'BL':
        corners['BL'] = (corners['TL'][0] + corners['BR'][0] - corners['TR'][0],
                         corners['TL'][1] + corners['BR'][1] - corners['TR'][1])
    elif missing == 'TR':
        corners['TR'] = (corners['TL'][0] + corners['BR'][0] - corners['BL'][0],
                         corners['TL'][1] + corners['BR'][1] - corners['BL'][1])
    elif missing == 'TL':
        corners['TL'] = (corners['TR'][0] + corners['BL'][0] - corners['BR'][0],
                         corners['TR'][1] + corners['BL'][1] - corners['BR'][1])
    
    return corners


def capture_and_analyze():
    """Capture une photo avec la caméra Raspberry Pi et analyse."""
    try:
        from picamera2 import Picamera2
        
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": (4056, 3040)})
        picam2.configure(config)
        picam2.start()
        
        import time
        time.sleep(1)  # Stabilisation
        
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
    
    if len(sys.argv) > 1:
        # Image fournie en argument
        result = analyze_board(image_path=sys.argv[1])
    else:
        # Essayer la caméra, sinon chercher une image
        result = capture_and_analyze()
        
        if result is None:
            # Chercher une image de test
            import glob
            images = glob.glob(os.path.join(SCRIPT_DIR, "images", "*.jpg"))
            if images:
                print(f"📷 Utilisation de: {images[0]}")
                result = analyze_board(image_path=images[0])
            else:
                print("❌ Aucune image disponible")
                print("Usage: python chess_detector.py [image.jpg]")
