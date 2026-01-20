#!/usr/bin/env python3
"""
Script pour déterminer la correspondance entre les axes du robot et du repère vision.

Procédure:
1. Détecte la position initiale de l'ArUco dans le repère vision
2. Bouge le robot de +5cm en X robot
3. Détecte la nouvelle position de l'ArUco
4. Compare pour voir comment X robot influence (x,y) vision
5. Répète pour Y robot
"""

import sys
import time
import cv2
import numpy as np

# Import des fonctions de chess_detector
sys.path.append('../test_extraction_plateau_image_cam_rasp')
from chess_detector import (
    create_aruco_detector,
    detect_calibration_markers,
    calculate_board_corners,
    estimate_missing_corners,
    extract_board
)

try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    print("❌ rtde_control non installé")
    sys.exit(1)

# Configuration
ROBOT_IP = "192.168.0.11"
ROBOT_ARUCO_ID = 36
BOARD_SIZE = 800
VITESSE = 0.05
ACCELERATION = 0.2

def detect_robot_position():
    """Détecte la position de l'ArUco 36 dans le repère -10/+10."""
    # Prendre une photo
    import subprocess
    subprocess.run([
        "rpicam-still",
        "-n",
        "-o", "/tmp/test_axes.jpg",
        "--timeout", "2000"
    ])
    
    # Charger l'image
    img = cv2.imread("/tmp/test_axes.jpg")
    if img is None:
        return None
    
    # Détecter le plateau
    detector = create_aruco_detector()
    markers = detect_calibration_markers(img, detector)
    
    if len(markers) < 2:
        return None
    
    board_corners = calculate_board_corners(markers)
    if len(board_corners) < 4:
        board_corners, _ = estimate_missing_corners(board_corners)
    
    if len(board_corners) < 4:
        return None
    
    # Extraire le plateau
    board_img = extract_board(img, board_corners)
    
    # Détecter l'ArUco robot
    gray = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if int(marker_id) == ROBOT_ARUCO_ID:
                marker_corners = corners[i][0]
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                
                # Convertir en -10/+10
                x = -10 + (center_x / BOARD_SIZE) * 20
                y = -10 + (center_y / BOARD_SIZE) * 20
                return (x, y)
    
    return None

def main():
    print("=" * 70)
    print("🧪 TEST DE CORRESPONDANCE DES AXES ROBOT ↔ VISION")
    print("=" * 70)
    
    # Connexion robot
    print(f"\n🤖 Connexion au robot {ROBOT_IP}...")
    try:
        rtde_c = RTDEControlInterface(ROBOT_IP)
        rtde_r = RTDEReceiveInterface(ROBOT_IP)
        print("✅ Connecté!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    # Position initiale
    print("\n" + "=" * 70)
    print("ÉTAPE 1: POSITION INITIALE")
    print("=" * 70)
    
    print("📸 Détection position initiale...")
    pos_vision_1 = detect_robot_position()
    
    if pos_vision_1 is None:
        print("❌ ArUco non détecté - positionnez le robot sur le plateau")
        rtde_c.disconnect()
        rtde_r.disconnect()
        return
    
    pos_robot_1 = list(rtde_r.getActualTCPPose())
    
    print(f"✅ Position vision: x={pos_vision_1[0]:.2f}, y={pos_vision_1[1]:.2f}")
    print(f"✅ Position robot:  X={pos_robot_1[0]*1000:.1f}mm, Y={pos_robot_1[1]*1000:.1f}mm")
    
    # Test 1: Mouvement en X robot
    print("\n" + "=" * 70)
    print("ÉTAPE 2: MOUVEMENT +50mm EN X ROBOT")
    print("=" * 70)
    
    pos_robot_2 = list(pos_robot_1)
    pos_robot_2[0] += 0.050  # +5cm en X
    
    print("🚀 Déplacement...")
    rtde_c.moveL(pos_robot_2, VITESSE, ACCELERATION)
    time.sleep(0.3)
    while not rtde_c.isSteady():
        time.sleep(0.1)
    time.sleep(1.0)
    
    print("📸 Détection nouvelle position...")
    pos_vision_2 = detect_robot_position()
    
    if pos_vision_2 is None:
        print("❌ ArUco non détecté après déplacement")
        rtde_c.disconnect()
        rtde_r.disconnect()
        return
    
    print(f"✅ Nouvelle position vision: x={pos_vision_2[0]:.2f}, y={pos_vision_2[1]:.2f}")
    
    delta_x_vision = pos_vision_2[0] - pos_vision_1[0]
    delta_y_vision = pos_vision_2[1] - pos_vision_1[1]
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Robot: +50mm en X robot")
    print(f"   Vision: Δx={delta_x_vision:.2f}, Δy={delta_y_vision:.2f}")
    
    if abs(delta_x_vision) > abs(delta_y_vision):
        print(f"   → X robot correspond à X vision (facteur: {delta_x_vision/0.05:.3f})")
    else:
        print(f"   → X robot correspond à Y vision (facteur: {delta_y_vision/0.05:.3f})")
    
    # Test 2: Mouvement en Y robot
    print("\n" + "=" * 70)
    print("ÉTAPE 3: MOUVEMENT +50mm EN Y ROBOT")
    print("=" * 70)
    
    pos_robot_3 = list(pos_robot_1)
    pos_robot_3[1] += 0.050  # +5cm en Y
    
    print("🚀 Retour position initiale puis déplacement...")
    rtde_c.moveL(pos_robot_1, VITESSE, ACCELERATION)
    time.sleep(0.3)
    while not rtde_c.isSteady():
        time.sleep(0.1)
    time.sleep(1.0)
    
    rtde_c.moveL(pos_robot_3, VITESSE, ACCELERATION)
    time.sleep(0.3)
    while not rtde_c.isSteady():
        time.sleep(0.1)
    time.sleep(1.0)
    
    print("📸 Détection nouvelle position...")
    pos_vision_3 = detect_robot_position()
    
    if pos_vision_3 is None:
        print("❌ ArUco non détecté")
        rtde_c.disconnect()
        rtde_r.disconnect()
        return
    
    print(f"✅ Nouvelle position vision: x={pos_vision_3[0]:.2f}, y={pos_vision_3[1]:.2f}")
    
    delta_x_vision2 = pos_vision_3[0] - pos_vision_1[0]
    delta_y_vision2 = pos_vision_3[1] - pos_vision_1[1]
    
    print(f"\n📊 RÉSULTAT:")
    print(f"   Robot: +50mm en Y robot")
    print(f"   Vision: Δx={delta_x_vision2:.2f}, Δy={delta_y_vision2:.2f}")
    
    if abs(delta_x_vision2) > abs(delta_y_vision2):
        print(f"   → Y robot correspond à X vision (facteur: {delta_x_vision2/0.05:.3f})")
    else:
        print(f"   → Y robot correspond à Y vision (facteur: {delta_y_vision2/0.05:.3f})")
    
    # Retour position initiale
    print("\n🔙 Retour position initiale...")
    rtde_c.moveL(pos_robot_1, VITESSE, ACCELERATION)
    time.sleep(0.3)
    while not rtde_c.isSteady():
        time.sleep(0.1)
    
    # Déconnexion
    rtde_c.disconnect()
    rtde_r.disconnect()
    
    print("\n" + "=" * 70)
    print("📝 RÉSUMÉ DE LA CALIBRATION")
    print("=" * 70)
    print(f"X robot (+50mm) → Vision: Δx={delta_x_vision:.2f}, Δy={delta_y_vision:.2f}")
    print(f"Y robot (+50mm) → Vision: Δx={delta_x_vision2:.2f}, Δy={delta_y_vision2:.2f}")
    print("\nUtilise ces valeurs pour calculer la matrice de transformation!")
    print("=" * 70)

if __name__ == "__main__":
    main()
