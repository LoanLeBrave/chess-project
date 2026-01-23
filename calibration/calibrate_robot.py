#!/usr/bin/env python3
"""
Script de calibration du robot via ArUco
Utilise l'ArUco ID 36 sur la pince du robot pour centrer le robot sur le point (0, 0) du repère.

Processus:
1. Prend une photo et détecte l'ArUco 36
2. Calcule la position dans le repère -10/+10
3. Déplace le robot par petits pas vers le centre (0, 0)
4. Répète jusqu'à convergence (|x| < 0.01 et |y| < 0.01)

Usage:
    python3 calibrate_robot.py
"""

import os
import sys
import cv2
import json
import numpy as np
import subprocess
import shutil
import time
from datetime import datetime

# Ajouter les chemins des autres modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "mouvement_robot"))
sys.path.insert(0, os.path.join(PROJECT_DIR, "test_extraction_plateau_image_cam_rasp"))

# ============================================================================
#                         CONFIGURATION
# ============================================================================

ROBOT_IP = "192.168.0.11"
VITESSE = 0.05  # Plus lent pour la calibration
ACCELERATION = 0.2

# ArUco du robot
ROBOT_ARUCO_ID = 36

# Dictionnaire ArUco (même que chess_detector.py)
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# IDs des marqueurs de calibration du plateau (32-35)
CALIBRATION_IDS = {
    32: 'CAL_TL',  # Top-Left
    33: 'CAL_TR',  # Top-Right
    34: 'CAL_BL',  # Bottom-Left
    35: 'CAL_BR',  # Bottom-Right
}

# Offsets de calibration (mêmes que chess_detector.py)
OFFSETS = {
    "CAL_TL": {"offset_x": 0, "offset_y": 0},
    "CAL_TR": {"offset_x": 54, "offset_y": -86},
    "CAL_BL": {"offset_x": -90, "offset_y": 112},
    "CAL_BR": {"offset_x": 53, "offset_y": 86}
}

# Taille du plateau extrait
BOARD_SIZE = 800

# Tolérance pour considérer la calibration réussie
TOLERANCE = 0.1  # Dans le repère -10/+10

# Facteur de conversion : repère -10/+10 vers mètres robot
# À AJUSTER après premiers tests !
# Si le plateau fait 40cm et le repère va de -10 à +10 :
# 1 unité repère = 40cm / 20 = 2cm = 0.02m
SCALE_FACTOR = 0.02  # mètres par unité du repère

# Fichier pour sauvegarder la calibration
CALIBRATION_FILE = os.path.join(SCRIPT_DIR, "robot_calibration.json")


# ============================================================================
#                         FONCTIONS DE DÉTECTION
#                 (Reprises de chess_detector.py pour cohérence)
# ============================================================================

def create_aruco_detector():
    """Crée un détecteur ArUco avec les paramètres optimisés."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
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
    """Détecte les marqueurs ArUco de calibration (IDs 32-35)."""
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    corners, ids, _ = detector.detectMarkers(gray)
    calibration_markers = {}
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            marker_id = int(marker_id)
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


def calculate_board_corners(calibration_markers):
    """Calcule les coins du plateau en appliquant les offsets."""
    board_corners = {}
    for marker_id, marker_data in calibration_markers.items():
        code = marker_data['code']
        center = marker_data['center']
        offset = OFFSETS[code]
        board_corners[code] = (
            center[0] + offset['offset_x'],
            center[1] + offset['offset_y']
        )
    return board_corners


def estimate_missing_corners(board_corners):
    """Estime les coins manquants si seulement 2 ou 3 ArUcos détectés."""
    codes = ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']
    detected = list(board_corners.keys())
    missing = [c for c in codes if c not in detected]
    
    if len(missing) == 0:
        return board_corners, []
    
    estimated_corners = board_corners.copy()
    estimated_codes = []
    
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
    
    return estimated_corners, estimated_codes


def extract_board(img, board_corners):
    """Extrait et redresse le plateau d'échecs."""
    src_pts = np.float32([
        board_corners['CAL_TL'],
        board_corners['CAL_TR'],
        board_corners['CAL_BL'],
        board_corners['CAL_BR']
    ])
    dst_pts = np.float32([
        [0, 0],
        [BOARD_SIZE, 0],
        [0, BOARD_SIZE],
        [BOARD_SIZE, BOARD_SIZE]
    ])
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(img, matrix, (BOARD_SIZE, BOARD_SIZE))


def detect_robot_aruco(board_img, detector):
    """
    Détecte l'ArUco du robot (ID 36) sur le plateau extrait.
    
    Returns:
        tuple: (x, y) dans le repère -10/+10, ou None si non détecté
    """
    # Vérifier que l'image est valide
    if board_img is None or board_img.size == 0:
        return None
    
    if len(board_img.shape) == 3:
        gray = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = board_img
    
    # Vérifier que l'image convertie est valide
    if gray is None or gray.size == 0 or gray.shape[0] < 10 or gray.shape[1] < 10:
        return None
    
    try:
        corners, ids, _ = detector.detectMarkers(gray)
    except cv2.error as e:
        print(f"⚠️ Erreur OpenCV lors de la détection: {e}")
        return None
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if int(marker_id) == ROBOT_ARUCO_ID:
                marker_corners = corners[i][0]
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                
                # Convertir en coordonnées -10/+10
                x = -10 + (center_x / BOARD_SIZE) * 20
                y = 10 - (center_y / BOARD_SIZE) * 20
                
                return (round(x, 2), round(y, 2))
    
    return None


# ============================================================================
#                         FONCTIONS CAMÉRA
# ============================================================================

def take_photo(filepath="/tmp/calibration_photo.jpg"):
    """Prend une photo avec rpicam-still."""
    if shutil.which('rpicam-still'):
        cmd = 'rpicam-still'
    elif shutil.which('libcamera-still'):
        cmd = 'libcamera-still'
    else:
        print("❌ Aucune commande caméra disponible")
        return None
    
    args = [cmd, '-n', '-o', filepath, '--timeout', '2000']
    
    try:
        subprocess.run(args, capture_output=True, timeout=30)
        if os.path.exists(filepath):
            return filepath
    except Exception as e:
        print(f"❌ Erreur capture: {e}")
    
    return None


# ============================================================================
#                         CLASSE PRINCIPALE
# ============================================================================

class RobotCalibrator:
    """Classe pour calibrer le robot via ArUco."""
    
    def __init__(self, simulate=False):
        self.simulate = simulate
        self.rtde_c = None
        self.rtde_r = None
        self.detector = create_aruco_detector()
        self.debug_dir = None  # Dossier de debug pour cette session
        
        if not simulate:
            self._connect_robot()
    
    def _connect_robot(self):
        """Connexion au robot."""
        try:
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface
            
            print(f"🤖 Connexion au robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)
            print("✅ Robot connecté!")
            
        except Exception as e:
            print(f"❌ Erreur connexion robot: {e}")
            print("   Mode simulation activé")
            self.simulate = True
    
    def get_robot_position(self):
        """Récupère la position actuelle du robot."""
        if self.simulate:
            return [0.3, 0.1, 0.2, 0, 3.14, 0]  # Position fictive
        return list(self.rtde_r.getActualTCPPose())
    
    def move_robot(self, position):
        """Déplace le robot vers une position."""
        if self.simulate:
            print(f"   [SIMULATION] moveL vers {position[:3]}")
            time.sleep(0.5)  # Simuler le délai
            return True
        
        try:
            self.rtde_c.moveL(position, VITESSE, ACCELERATION)
            # Attendre que le mouvement soit terminé
            time.sleep(0.3)  # Petit délai initial
            while not self.rtde_c.isSteady():
                time.sleep(0.1)
            time.sleep(0.1)  # Stabilisation rapide (caméra fixe)
            return True
        except Exception as e:
            print(f"❌ Erreur déplacement: {e}")
            return False
    
    def move_robot_delta(self, delta_x, delta_y):
        """Déplace le robot d'un delta en X et Y (mètres)."""
        current_pos = self.get_robot_position()
        new_pos = list(current_pos)
        new_pos[0] += delta_x
        new_pos[1] += delta_y
        return self.move_robot(new_pos)
    
    def _move_toward_center(self):
        """
        Déplace le robot vers le centre estimé du plateau quand l'ArUco n'est pas visible.
        Fait un petit pas vers le centre (supposé à la position actuelle + offset).
        """
        # Faire un petit déplacement aléatoire vers une zone centrale
        # On suppose que le robot est trop loin du champ de vision
        import random
        
        # Petits déplacements aléatoires (±2cm) pour retrouver l'ArUco
        delta_x = random.uniform(-0.02, 0.02)
        delta_y = random.uniform(-0.02, 0.02)
        
        print(f"   🔄 Déplacement exploratoire: Δx={delta_x*1000:.1f}mm, Δy={delta_y*1000:.1f}mm")
        self.move_robot_delta(delta_x, delta_y)
        time.sleep(0.1)
    
    def _save_debug_image(self, img, iteration, board_img=None, robot_pos=None, calibration_markers=None):
        """Sauvegarde l'image avec annotations pour debug."""
        if self.debug_dir is None:
            return
        
        # Image complète avec coins du plateau
        debug_img = img.copy()
        
        # Annoter les marqueurs de calibration détectés
        if calibration_markers:
            for marker_id, info in calibration_markers.items():
                corners = info['corners']
                center = info['center']
                
                # Dessiner le contour
                pts = corners.reshape((-1, 1, 2)).astype(np.int32)
                cv2.polylines(debug_img, [pts], True, (0, 255, 0), 2)
                
                # Annoter l'ID
                cv2.putText(debug_img, f"ID{marker_id}", 
                           (int(center[0]), int(center[1])), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Sauvegarder l'image complète
        cv2.imwrite(os.path.join(self.debug_dir, f"iter_{iteration:03d}_full.jpg"), debug_img)
        
        # Sauvegarder le plateau extrait avec ArUco robot si disponible
        if board_img is not None:
            board_debug = board_img.copy()
            
            # Détecter et annoter l'ArUco robot sur le plateau
            gray = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.detector.detectMarkers(gray)
            
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(board_debug, corners, ids)
                
                # Annoter la position si connue
                if robot_pos:
                    x, y = robot_pos
                    text = f"Robot: ({x:.2f}, {y:.2f})"
                    cv2.putText(board_debug, text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imwrite(os.path.join(self.debug_dir, f"iter_{iteration:03d}_board.jpg"), board_debug)

    def detect_robot_on_board(self, image_path=None, iteration=0):
        """
        Détecte la position du robot sur le plateau.
        
        Returns:
            tuple: (x, y) dans le repère -10/+10, ou None
        """
        # Prendre une photo si pas d'image fournie
        if image_path is None:
            image_path = take_photo()
            if image_path is None:
                return None
        
        # Charger l'image
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Impossible de charger: {image_path}")
            return None
        
        # Détecter les marqueurs de calibration
        calibration_markers = detect_calibration_markers(img, self.detector)
        
        if len(calibration_markers) < 2:
            print(f"❌ Pas assez de marqueurs de calibration ({len(calibration_markers)}/4)")
            return None
        
        # Calculer les coins du plateau
        board_corners = calculate_board_corners(calibration_markers)
        
        # Estimer les coins manquants si nécessaire
        if len(board_corners) < 4:
            board_corners, _ = estimate_missing_corners(board_corners)
        
        if len(board_corners) < 4:
            print("❌ Impossible de déterminer les 4 coins du plateau")
            return None
        
        # Extraire le plateau
        board_img = extract_board(img, board_corners)
        
        # Détecter l'ArUco du robot
        robot_pos = detect_robot_aruco(board_img, self.detector)
        
        # Sauvegarder les images de debug
        self._save_debug_image(img, iteration, board_img, robot_pos, calibration_markers)
        
        return robot_pos
    
    def calibrate(self, max_iterations=50):
        """
        Boucle de calibration principale.
        Déplace le robot vers le centre (0, 0) du repère.
        """
        # Créer le dossier de debug pour cette session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.debug_dir = os.path.join(SCRIPT_DIR, "debug_calibration", f"session_{timestamp}")
        os.makedirs(self.debug_dir, exist_ok=True)
        print(f"📁 Dossier de debug: {self.debug_dir}")
        
        print("\n" + "=" * 60)
        print("🎯 CALIBRATION DU ROBOT - CENTRAGE SUR (0, 0)")
        print("=" * 60)
        print(f"   ArUco robot: ID {ROBOT_ARUCO_ID}")
        print(f"   Tolérance: ±{TOLERANCE}")
        print(f"   Facteur d'échelle: {SCALE_FACTOR} m/unité")
        print("=" * 60)
        
        for iteration in range(max_iterations):
            print(f"\n📸 Itération {iteration + 1}/{max_iterations}")
            
            # Petite pause pour stabiliser
            time.sleep(0.1)
            
            # Détecter la position du robot
            robot_pos = self.detect_robot_on_board(iteration=iteration + 1)
            
            if robot_pos is None:
                print(f"   ⚠️  ArUco robot non détecté")
                print("   🔄 Déplacement pour retrouver l'ArUco...")
                # Bouger le robot immédiatement pour essayer de voir l'ArUco
                self._move_toward_center()
                continue
            
            x, y = robot_pos
            print(f"   📍 Position robot: x={x:.2f}, y={y:.2f}")
            
            # Calculer l'erreur
            error_x = 0 - x
            error_y = 0 - y
            
            print(f"   📏 Erreur: Δx={error_x:.2f}, Δy={error_y:.2f}")
            
            # Vérifier si on est dans la tolérance
            if abs(x) < TOLERANCE and abs(y) < TOLERANCE:
                print("\n" + "=" * 60)
                print("✅ CALIBRATION RÉUSSIE!")
                print(f"   Position finale: x={x:.2f}, y={y:.2f}")
                print("=" * 60)
                
                # Sauvegarder la calibration
                self._save_calibration()
                return True
            
            # Calculer le déplacement en mètres
            # Axes inversés: +X robot → X- plateau, +Y robot → Y- plateau
            # Donc on inverse les signes
            delta_x_robot = -error_x * SCALE_FACTOR
            delta_y_robot = -error_y * SCALE_FACTOR
            
            print(f"   🤖 Déplacement: Δx={delta_x_robot*1000:.1f}mm, Δy={delta_y_robot*1000:.1f}mm")
            
            # Déplacer le robot
            if not self.move_robot_delta(delta_x_robot, delta_y_robot):
                print("   ❌ Échec du déplacement")
                continue
            
            print("   ✅ Déplacement effectué")
        
        print(f"\n❌ Calibration non terminée après {max_iterations} itérations")
        return False
    
    def _save_calibration(self):
        """Sauvegarde les données de calibration."""
        robot_pos = self.get_robot_position()
        
        data = {
            "robot_position_at_center": robot_pos,
            "scale_factor": SCALE_FACTOR,
            "robot_aruco_id": ROBOT_ARUCO_ID,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Position TCP du robot quand l'ArUco est au centre (0,0) du plateau"
        }
        
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Calibration sauvegardée: {CALIBRATION_FILE}")
    
    def test_detection(self, image_path=None):
        """Test de détection sans déplacement."""
        print("\n🔍 TEST DE DÉTECTION")
        print("-" * 40)
        
        robot_pos = self.detect_robot_on_board(image_path)
        
        if robot_pos:
            x, y = robot_pos
            print(f"✅ ArUco {ROBOT_ARUCO_ID} détecté!")
            print(f"   Position: x={x:.2f}, y={y:.2f}")
            print(f"   Distance au centre: {(x**2 + y**2)**0.5:.2f}")
        else:
            print(f"❌ ArUco {ROBOT_ARUCO_ID} non détecté")
        
        return robot_pos


# ============================================================================
#                         POINT D'ENTRÉE
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Calibration robot via ArUco")
    parser.add_argument("--simulate", "-s", action="store_true", 
                        help="Mode simulation (sans robot)")
    parser.add_argument("--test", "-t", action="store_true",
                        help="Juste tester la détection, sans déplacer le robot")
    parser.add_argument("--image", "-i", type=str, default=None,
                        help="Image à utiliser (au lieu de prendre une photo)")
    parser.add_argument("--iterations", "-n", type=int, default=50,
                        help="Nombre max d'itérations (défaut: 50)")
    
    args = parser.parse_args()
    
    calibrator = RobotCalibrator(simulate=args.simulate)
    
    if args.test:
        calibrator.test_detection(args.image)
    else:
        calibrator.calibrate(max_iterations=args.iterations)


if __name__ == "__main__":
    main()
