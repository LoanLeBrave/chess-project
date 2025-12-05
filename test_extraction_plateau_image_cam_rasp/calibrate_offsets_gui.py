#!/usr/bin/env python3
"""
Interface graphique pour calibrer les offsets des coins du plateau.

Permet de déplacer les coins du plateau en drag-and-drop pour ajuster
visuellement les offsets, puis affiche le code Python à copier-coller.

Usage:
    python calibrate_offsets_gui.py                # Mode interactif
    python calibrate_offsets_gui.py [chemin_image] # Avec une image existante
    python calibrate_offsets_gui.py --photo        # Prendre une photo d'abord

Contrôles:
    - Clic gauche + drag: Déplacer un coin du plateau
    - Touche 'r': Reset les offsets à zéro
    - Touche 's': Sauvegarder l'image avec grille
    - Touche 'q' ou Echap: Quitter
"""

import cv2
import numpy as np
import os
import sys
import subprocess
import shutil
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMAGES_DIR = os.path.join(SCRIPT_DIR, "..", "analyse", "images")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Taille de l'image extraite du plateau
EXTRACTED_BOARD_SIZE = 800

# Taille de la fenêtre d'affichage (sera redimensionné si l'image est trop grande)
MAX_DISPLAY_WIDTH = 1200
MAX_DISPLAY_HEIGHT = 800

# Rayon de détection pour le drag-and-drop (en pixels sur l'image affichée)
DRAG_RADIUS = 20

# Dictionnaire ArUco
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# IDs des marqueurs de calibration
CALIBRATION_IDS = {
    32: 'CAL_TL',
    33: 'CAL_TR',
    34: 'CAL_BL',
    35: 'CAL_BR',
}

# Offsets initiaux (seront modifiés interactivement)
OFFSETS = {
    "CAL_TL": {"offset_x": 0, "offset_y": 0},
    "CAL_TR": {"offset_x": 0, "offset_y": 0},
    "CAL_BL": {"offset_x": 0, "offset_y": 0},
    "CAL_BR": {"offset_x": 0, "offset_y": 0}
}

# Couleurs
COLORS = {
    'aruco_marker': (0, 255, 0),
    'aruco_center': (0, 0, 255),
    'board_corner': (255, 0, 255),
    'board_corner_hover': (0, 255, 255),
    'board_outline': (255, 165, 0),
    'offset_line': (255, 255, 0),
    'grid_line': (0, 255, 0),
    'text': (255, 255, 255),
    'panel_bg': (40, 40, 40),
}

# ============================================================
# CONFIGURATION CAMÉRA
# ============================================================
USE_DEFAULT_CAMERA_PARAMS = True
CAMERA_CONFIG = {'timeout': 2000}

def _check_rpicam_available():
    return shutil.which('rpicam-still') is not None or shutil.which('libcamera-still') is not None

def _check_picamera2_available():
    try:
        from picamera2 import Picamera2
        return True
    except ImportError:
        return False

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
    """Prend une photo"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"calibration_{timestamp}.jpg"
    
    filepath = os.path.join(IMAGES_DIR, filename)
    
    if CAMERA_MODE == 'rpicam':
        cmd = 'rpicam-still' if shutil.which('rpicam-still') else 'libcamera-still'
        args = [cmd, '-n', '-o', filepath, '--timeout', '2000']
        subprocess.run(args, capture_output=True, timeout=30)
    elif CAMERA_MODE == 'picamera2':
        from picamera2 import Picamera2
        import time
        picam2 = Picamera2()
        picam2.configure(picam2.create_still_configuration())
        picam2.start()
        time.sleep(2)
        picam2.capture_file(filepath)
        picam2.stop()
        picam2.close()
    else:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filepath, frame)
        cap.release()
    
    return filepath if os.path.exists(filepath) else None


# ============================================================
# DÉTECTION ARUCO
# ============================================================
def detect_calibration_markers(img_np):
    """Détecte les marqueurs ArUco de calibration"""
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY) if len(img_np.shape) == 3 else img_np
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = cv2.aruco.DetectorParameters()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_CONTOUR
    
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, _ = detector.detectMarkers(gray)
    
    calibration_markers = {}
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id in CALIBRATION_IDS:
                marker_corners = corners[i][0]
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                calibration_markers[marker_id] = {
                    'center': (center_x, center_y),
                    'corners': marker_corners,
                    'code': CALIBRATION_IDS[marker_id]
                }
    
    return calibration_markers


# ============================================================
# CLASSE PRINCIPALE: CALIBRATEUR INTERACTIF
# ============================================================
class OffsetCalibrator:
    def __init__(self, image_path):
        self.image_path = image_path
        self.img_original = cv2.imread(image_path)
        if self.img_original is None:
            raise ValueError(f"Impossible de charger: {image_path}")
        
        self.img_h, self.img_w = self.img_original.shape[:2]
        
        # Calculer le facteur d'échelle pour l'affichage
        self.scale = min(MAX_DISPLAY_WIDTH / self.img_w, MAX_DISPLAY_HEIGHT / self.img_h, 1.0)
        self.display_w = int(self.img_w * self.scale)
        self.display_h = int(self.img_h * self.scale)
        
        # Largeur du panneau latéral
        self.panel_width = 400
        
        # Détecter les ArUcos
        self.calibration_markers = detect_calibration_markers(self.img_original)
        
        # Initialiser les offsets
        self.offsets = {
            "CAL_TL": {"offset_x": 0, "offset_y": 0},
            "CAL_TR": {"offset_x": 0, "offset_y": 0},
            "CAL_BL": {"offset_x": 0, "offset_y": 0},
            "CAL_BR": {"offset_x": 0, "offset_y": 0}
        }
        
        # État du drag-and-drop
        self.dragging = None  # Code du coin en cours de déplacement
        self.hover = None     # Code du coin survolé
        
        # Calculer les coins du plateau
        self.board_corners = {}
        self.update_board_corners()
        
        # Nom de la fenêtre
        self.window_name = "Calibration des Offsets - Drag & Drop"
    
    def update_board_corners(self):
        """Met à jour les coins du plateau avec les offsets actuels"""
        self.board_corners = {}
        for marker_id, marker_data in self.calibration_markers.items():
            code = marker_data['code']
            center = marker_data['center']
            offset = self.offsets[code]
            self.board_corners[code] = (
                center[0] + offset['offset_x'],
                center[1] + offset['offset_y']
            )
        
        # Estimer les coins manquants
        self.estimate_missing_corners()
    
    def estimate_missing_corners(self):
        """Estime les coins manquants"""
        codes = ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']
        detected = list(self.board_corners.keys())
        missing = [c for c in codes if c not in detected]
        
        self.estimated_codes = []
        
        if len(missing) == 1:
            m = missing[0]
            if m == 'CAL_TL' and all(c in detected for c in ['CAL_TR', 'CAL_BL', 'CAL_BR']):
                tr, bl, br = self.board_corners['CAL_TR'], self.board_corners['CAL_BL'], self.board_corners['CAL_BR']
                self.board_corners['CAL_TL'] = (tr[0] + bl[0] - br[0], tr[1] + bl[1] - br[1])
                self.estimated_codes.append('CAL_TL')
            elif m == 'CAL_TR' and all(c in detected for c in ['CAL_TL', 'CAL_BL', 'CAL_BR']):
                tl, bl, br = self.board_corners['CAL_TL'], self.board_corners['CAL_BL'], self.board_corners['CAL_BR']
                self.board_corners['CAL_TR'] = (tl[0] + br[0] - bl[0], tl[1] + br[1] - bl[1])
                self.estimated_codes.append('CAL_TR')
            elif m == 'CAL_BL' and all(c in detected for c in ['CAL_TL', 'CAL_TR', 'CAL_BR']):
                tl, tr, br = self.board_corners['CAL_TL'], self.board_corners['CAL_TR'], self.board_corners['CAL_BR']
                self.board_corners['CAL_BL'] = (tl[0] + br[0] - tr[0], tl[1] + br[1] - tr[1])
                self.estimated_codes.append('CAL_BL')
            elif m == 'CAL_BR' and all(c in detected for c in ['CAL_TL', 'CAL_TR', 'CAL_BL']):
                tl, tr, bl = self.board_corners['CAL_TL'], self.board_corners['CAL_TR'], self.board_corners['CAL_BL']
                self.board_corners['CAL_BR'] = (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1])
                self.estimated_codes.append('CAL_BR')
    
    def get_corner_at_pos(self, x, y):
        """Retourne le code du coin proche de la position (x, y) en coordonnées affichage"""
        # Convertir en coordonnées image originale
        img_x = x / self.scale
        img_y = y / self.scale
        
        # Chercher le coin le plus proche (parmi ceux qui ont un ArUco détecté)
        for marker_id, marker_data in self.calibration_markers.items():
            code = marker_data['code']
            if code in self.board_corners:
                corner = self.board_corners[code]
                dist = np.sqrt((corner[0] - img_x)**2 + (corner[1] - img_y)**2)
                if dist * self.scale < DRAG_RADIUS:
                    return code
        return None
    
    def mouse_callback(self, event, x, y, flags, param):
        """Callback pour les événements souris"""
        if event == cv2.EVENT_MOUSEMOVE:
            if self.dragging:
                # Déplacer le coin
                img_x = x / self.scale
                img_y = y / self.scale
                
                # Trouver le centre ArUco correspondant
                for marker_id, marker_data in self.calibration_markers.items():
                    if marker_data['code'] == self.dragging:
                        center = marker_data['center']
                        self.offsets[self.dragging]['offset_x'] = int(img_x - center[0])
                        self.offsets[self.dragging]['offset_y'] = int(img_y - center[1])
                        self.update_board_corners()
                        break
            else:
                # Mettre à jour le survol
                self.hover = self.get_corner_at_pos(x, y)
        
        elif event == cv2.EVENT_LBUTTONDOWN:
            corner = self.get_corner_at_pos(x, y)
            if corner and corner not in self.estimated_codes:
                self.dragging = corner
        
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = None
    
    def draw_frame(self):
        """Dessine l'image avec les annotations et le panneau latéral"""
        # Redimensionner l'image pour l'affichage
        img_display = cv2.resize(self.img_original, (self.display_w, self.display_h))
        
        # Dessiner les ArUcos détectés
        for marker_id, marker_data in self.calibration_markers.items():
            corners = marker_data['corners'] * self.scale
            pts = corners.astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(img_display, [pts], True, COLORS['aruco_marker'], 2)
            
            cx = int(marker_data['center'][0] * self.scale)
            cy = int(marker_data['center'][1] * self.scale)
            cv2.circle(img_display, (cx, cy), 6, COLORS['aruco_center'], -1)
            
            label = f"ID:{marker_id}"
            cv2.putText(img_display, label, (cx - 20, cy - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text'], 1)
        
        # Dessiner les lignes d'offset
        for marker_id, marker_data in self.calibration_markers.items():
            code = marker_data['code']
            if code in self.board_corners:
                aruco_center = marker_data['center']
                board_corner = self.board_corners[code]
                pt1 = (int(aruco_center[0] * self.scale), int(aruco_center[1] * self.scale))
                pt2 = (int(board_corner[0] * self.scale), int(board_corner[1] * self.scale))
                cv2.line(img_display, pt1, pt2, COLORS['offset_line'], 2)
        
        # Dessiner les coins du plateau
        for code, corner in self.board_corners.items():
            cx = int(corner[0] * self.scale)
            cy = int(corner[1] * self.scale)
            
            # Couleur selon l'état
            if code == self.dragging:
                color = (0, 255, 255)  # Jaune si en cours de déplacement
                radius = 15
            elif code == self.hover:
                color = COLORS['board_corner_hover']
                radius = 12
            elif code in self.estimated_codes:
                color = (128, 128, 255)  # Rose si estimé
                radius = 8
            else:
                color = COLORS['board_corner']
                radius = 10
            
            # Dessiner le coin (croix + cercle)
            cv2.line(img_display, (cx - 12, cy), (cx + 12, cy), color, 2)
            cv2.line(img_display, (cx, cy - 12), (cx, cy + 12), color, 2)
            cv2.circle(img_display, (cx, cy), radius, color, 2)
            
            # Label
            label = code.replace('CAL_', '')
            if code in self.estimated_codes:
                label += " (est.)"
            cv2.putText(img_display, label, (cx + 15, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Dessiner le contour du plateau
        if len(self.board_corners) == 4:
            adjacencies = [('CAL_TL', 'CAL_TR'), ('CAL_TR', 'CAL_BR'),
                          ('CAL_BR', 'CAL_BL'), ('CAL_BL', 'CAL_TL')]
            for c1, c2 in adjacencies:
                if c1 in self.board_corners and c2 in self.board_corners:
                    pt1 = (int(self.board_corners[c1][0] * self.scale),
                           int(self.board_corners[c1][1] * self.scale))
                    pt2 = (int(self.board_corners[c2][0] * self.scale),
                           int(self.board_corners[c2][1] * self.scale))
                    cv2.line(img_display, pt1, pt2, COLORS['board_outline'], 2)
        
        # Créer le panneau latéral
        panel = np.ones((self.display_h, self.panel_width, 3), dtype=np.uint8) * 40
        
        # Titre
        cv2.putText(panel, "CALIBRATION OFFSETS", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.line(panel, (20, 45), (self.panel_width - 20, 45), (100, 100, 100), 1)
        
        # Instructions
        y = 70
        instructions = [
            "Controles:",
            "  - Clic + drag: Deplacer coin",
            "  - R: Reset offsets",
            "  - S: Sauvegarder image",
            "  - G: Afficher grille 8x8",
            "  - Q/Echap: Quitter",
        ]
        for text in instructions:
            cv2.putText(panel, text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            y += 20
        
        # Séparateur
        y += 10
        cv2.line(panel, (20, y), (self.panel_width - 20, y), (100, 100, 100), 1)
        y += 25
        
        # Statut ArUcos
        cv2.putText(panel, f"ArUcos detectes: {len(self.calibration_markers)}/4", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 100), 1)
        y += 25
        
        for marker_id in [32, 33, 34, 35]:
            code = CALIBRATION_IDS[marker_id]
            if marker_id in self.calibration_markers:
                status = "OK"
                color = (0, 255, 0)
            else:
                status = "NON DETECTE"
                color = (0, 0, 255)
            cv2.putText(panel, f"  {code}: {status}", (20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            y += 18
        
        # Séparateur
        y += 15
        cv2.line(panel, (20, y), (self.panel_width - 20, y), (100, 100, 100), 1)
        y += 25
        
        # Code Python à copier
        cv2.putText(panel, "CODE A COPIER:", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        y += 30
        
        # Afficher le code des offsets
        cv2.putText(panel, "OFFSETS = {", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        y += 20
        
        for code in ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']:
            ox = self.offsets[code]['offset_x']
            oy = self.offsets[code]['offset_y']
            
            # Couleur selon le coin actif
            if code == self.dragging:
                text_color = (0, 255, 255)
            elif code == self.hover:
                text_color = (255, 200, 100)
            else:
                text_color = (200, 200, 200)
            
            line = f'  "{code}": {{"offset_x": {ox}, "offset_y": {oy}}},'
            cv2.putText(panel, line, (20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, text_color, 1)
            y += 18
        
        cv2.putText(panel, "}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        y += 30
        
        # Afficher les valeurs individuelles
        cv2.line(panel, (20, y), (self.panel_width - 20, y), (100, 100, 100), 1)
        y += 25
        
        cv2.putText(panel, "VALEURS ACTUELLES:", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 100), 1)
        y += 25
        
        for code in ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']:
            ox = self.offsets[code]['offset_x']
            oy = self.offsets[code]['offset_y']
            short = code.replace('CAL_', '')
            
            # Indicateur de direction
            dir_x = "droite" if ox >= 0 else "gauche"
            dir_y = "bas" if oy >= 0 else "haut"
            
            line1 = f"{short}: ({ox:+d}, {oy:+d})"
            line2 = f"     -> {dir_x}, {dir_y}"
            
            color = (0, 255, 255) if code == self.dragging else (200, 200, 200)
            cv2.putText(panel, line1, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            y += 16
            cv2.putText(panel, line2, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
            y += 22
        
        # Combiner image et panneau
        frame = np.hstack([img_display, panel])
        
        return frame
    
    def extract_board(self):
        """Extrait le plateau avec les offsets actuels"""
        if len(self.board_corners) < 4:
            return None
        
        src_points = np.array([
            [self.board_corners['CAL_TL'][0], self.board_corners['CAL_TL'][1]],
            [self.board_corners['CAL_TR'][0], self.board_corners['CAL_TR'][1]],
            [self.board_corners['CAL_BR'][0], self.board_corners['CAL_BR'][1]],
            [self.board_corners['CAL_BL'][0], self.board_corners['CAL_BL'][1]],
        ], dtype=np.float32)
        
        size = EXTRACTED_BOARD_SIZE
        dst_points = np.array([
            [0, 0], [size - 1, 0], [size - 1, size - 1], [0, size - 1]
        ], dtype=np.float32)
        
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        return cv2.warpPerspective(self.img_original, matrix, (size, size))
    
    def draw_grid_on_board(self, board_img):
        """Dessine la grille 8x8 sur le plateau extrait"""
        if board_img is None:
            return None
        
        img = board_img.copy()
        h, w = img.shape[:2]
        cell_w, cell_h = w / 8, h / 8
        
        for i in range(9):
            x = int(i * cell_w)
            cv2.line(img, (x, 0), (x, h), COLORS['grid_line'], 2)
            y = int(i * cell_h)
            cv2.line(img, (0, y), (w, y), COLORS['grid_line'], 2)
        
        # Labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        for i, col in enumerate(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']):
            x = int((i + 0.5) * cell_w) - 8
            cv2.putText(img, col, (x, h - 10), font, 0.6, (0, 0, 0), 3)
            cv2.putText(img, col, (x, h - 10), font, 0.6, (255, 255, 255), 1)
        
        for i, row in enumerate(['8', '7', '6', '5', '4', '3', '2', '1']):
            y = int((i + 0.5) * cell_h) + 8
            cv2.putText(img, row, (10, y), font, 0.6, (0, 0, 0), 3)
            cv2.putText(img, row, (10, y), font, 0.6, (255, 255, 255), 1)
        
        return img
    
    def run(self):
        """Lance l'interface de calibration"""
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        show_grid = False
        grid_window_name = "Plateau Extrait avec Grille"
        
        print("\n" + "="*60)
        print("🎯 CALIBRATION INTERACTIVE DES OFFSETS")
        print("="*60)
        print(f"   Image: {os.path.basename(self.image_path)}")
        print(f"   ArUcos détectés: {len(self.calibration_markers)}/4")
        print("\n   Contrôles:")
        print("   - Clic + drag sur un coin: Déplacer")
        print("   - R: Reset les offsets à zéro")
        print("   - S: Sauvegarder l'image")
        print("   - G: Afficher/masquer grille 8x8")
        print("   - Q ou Echap: Quitter")
        print("="*60 + "\n")
        
        while True:
            frame = self.draw_frame()
            cv2.imshow(self.window_name, frame)
            
            # Mettre à jour la fenêtre de grille si ouverte
            if show_grid:
                board_img = self.extract_board()
                if board_img is not None:
                    grid_img = self.draw_grid_on_board(board_img)
                    cv2.imshow(grid_window_name, grid_img)
            
            key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q') or key == 27:  # Q ou Echap
                break
            
            elif key == ord('r'):  # Reset
                for code in self.offsets:
                    self.offsets[code] = {"offset_x": 0, "offset_y": 0}
                self.update_board_corners()
                print("🔄 Offsets réinitialisés à zéro")
            
            elif key == ord('s'):  # Sauvegarder
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Sauvegarder le plateau extrait avec grille
                board_img = self.extract_board()
                if board_img is not None:
                    grid_img = self.draw_grid_on_board(board_img)
                    output_path = os.path.join(OUTPUT_DIR, f"calibrated_board_{timestamp}.jpg")
                    cv2.imwrite(output_path, grid_img)
                    print(f"💾 Image sauvegardée: {output_path}")
                
                # Afficher le code à copier
                self.print_offsets_code()
            
            elif key == ord('g'):  # Toggle grille
                show_grid = not show_grid
                if show_grid:
                    board_img = self.extract_board()
                    if board_img is not None:
                        grid_img = self.draw_grid_on_board(board_img)
                        cv2.imshow(grid_window_name, grid_img)
                else:
                    cv2.destroyWindow(grid_window_name)
        
        cv2.destroyAllWindows()
        
        # Afficher le code final
        print("\n" + "="*60)
        print("📋 CODE FINAL À COPIER DANS detect_board_corners.py:")
        print("="*60)
        self.print_offsets_code()
        print("="*60 + "\n")
    
    def print_offsets_code(self):
        """Affiche le code Python des offsets à copier"""
        print("\nOFFSETS = {")
        for i, code in enumerate(['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']):
            ox = self.offsets[code]['offset_x']
            oy = self.offsets[code]['offset_y']
            
            # Commentaire de direction
            dir_x = "+x vers droite" if ox >= 0 else "-x vers gauche"
            dir_y = "+y vers bas" if oy >= 0 else "-y vers haut"
            comment = f"# {dir_x}, {dir_y}"
            
            comma = "," if i < 3 else ""
            print(f'    "{code}": {{"offset_x": {ox}, "offset_y": {oy}}}{comma}     {comment}')
        print("}")


# ============================================================
# SÉLECTION D'IMAGE
# ============================================================
def select_image():
    """Sélectionne une image"""
    import glob
    
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


# ============================================================
# POINT D'ENTRÉE
# ============================================================
if __name__ == "__main__":
    print("="*60)
    print("🎯 CALIBRATION INTERACTIVE DES OFFSETS")
    print("   Déplacez les coins avec la souris (drag & drop)")
    print(f"   Mode caméra: {CAMERA_MODE}")
    print("="*60)
    
    image_path = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--photo' or arg == '-p':
            print("\n📷 Prise de photo...")
            image_path = take_photo()
            if image_path:
                print(f"✅ Photo enregistrée: {image_path}")
        elif os.path.exists(arg):
            image_path = arg
        else:
            print(f"❌ Image non trouvée: {arg}")
    else:
        print("\nChoisissez une option:")
        print("  1. Prendre une photo")
        print("  2. Utiliser une image existante")
        print("  q. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == '1':
            print("\n📷 Prise de photo...")
            image_path = take_photo()
            if image_path:
                print(f"✅ Photo enregistrée: {image_path}")
        elif choice == '2':
            image_path = select_image()
        elif choice.lower() == 'q':
            print("Au revoir!")
            sys.exit(0)
    
    if image_path and os.path.exists(image_path):
        try:
            calibrator = OffsetCalibrator(image_path)
            calibrator.run()
        except Exception as e:
            print(f"❌ Erreur: {e}")
    else:
        print("❌ Aucune image sélectionnée.")
