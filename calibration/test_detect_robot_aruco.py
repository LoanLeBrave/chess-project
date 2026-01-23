#!/usr/bin/env python3
"""
Script de test simple pour détecter l'ArUco robot (ID 36).
Prend une image, détecte TOUS les ArUcos, affiche lesquels sont visibles.
"""

import sys
import cv2
import os
import subprocess
import shutil

# Configuration
ROBOT_ARUCO_ID = 36
ARUCO_DICT = cv2.aruco.DICT_4X4_50

def create_aruco_detector():
    """Crée un détecteur ArUco."""
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    detector_params = cv2.aruco.DetectorParameters()
    return cv2.aruco.ArucoDetector(dictionary, detector_params)

def take_photo(filepath="/tmp/test_aruco.jpg"):
    """Prend une photo avec rpicam-still."""
    print(f"📸 Capture photo...")
    
    cmd = [
        "rpicam-still" if shutil.which("rpicam-still") else "libcamera-still",
        "-n", "-o", filepath,
        "--timeout", "2000",
        "--autofocus-mode", "manual",
        "--lens-position", "7.0"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Photo prise: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Erreur capture: {e}")
        return None

def main():
    print("=" * 70)
    print("🔍 TEST DÉTECTION ArUco ROBOT (ID 36)")
    print("=" * 70)
    
    # Créer dossier tmp_test à côté du script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_dir = os.path.join(script_dir, "tmp_test")
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Prendre une photo
    image_path = os.path.join(tmp_dir, "test_aruco.jpg")
    image_path = take_photo(image_path)
    if image_path is None:
        return
    
    # Charger l'image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Impossible de charger: {image_path}")
        return
    
    print(f"\n📊 Image: {img.shape}")
    
    # Créer le détecteur
    detector = create_aruco_detector()
    
    # ===== TEST 1: Détection sur image complète =====
    print("\n" + "=" * 70)
    print("TEST 1: Détection sur IMAGE COMPLÈTE")
    print("=" * 70)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    print(f"✅ ArUcos détectés: {ids.flatten() if ids is not None else 'AUCUN'}")
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            marker_id = int(marker_id)
            if marker_id == ROBOT_ARUCO_ID:
                print(f"   🎯 ArUco ROBOT (ID 36) TROUVÉ! ✅")
            else:
                print(f"   • ID {marker_id}")
    else:
        print("   ❌ Aucun ArUco détecté sur l'image complète!")
    
    # ===== TEST 2: Détection sans conversion gris =====
    print("\n" + "=" * 70)
    print("TEST 2: Détection directement en COULEUR (BGR)")
    print("=" * 70)
    
    corners_bgr, ids_bgr, _ = detector.detectMarkers(img)
    print(f"✅ ArUcos détectés: {ids_bgr.flatten() if ids_bgr is not None else 'AUCUN'}")
    
    if ids_bgr is not None:
        for i, marker_id in enumerate(ids_bgr.flatten()):
            marker_id = int(marker_id)
            if marker_id == ROBOT_ARUCO_ID:
                print(f"   🎯 ArUco ROBOT (ID 36) TROUVÉ! ✅")
    
    # ===== TEST 3: Histogramme de contraste =====
    print("\n" + "=" * 70)
    print("TEST 3: ANALYSE CONTRASTE")
    print("=" * 70)
    
    min_val = gray.min()
    max_val = gray.max()
    mean_val = gray.mean()
    
    print(f"   Min: {min_val}, Max: {max_val}, Moyenne: {mean_val:.1f}")
    
    if max_val - min_val < 50:
        print("   ⚠️  CONTRASTE TRÈS FAIBLE - Les ArUcos peuvent pas être vus!")
    
    # ===== Créer une image annotée avec ce qu'on trouve =====
    print("\n" + "=" * 70)
    print("TEST 4: VISUALISATION")
    print("=" * 70)
    
    result_img = img.copy()
    
    # Annoter avec la meilleure détection (celle qui a trouvé le plus)
    best_corners = corners if ids is not None and len(ids) > 0 else corners_bgr
    best_ids = ids if ids is not None and len(ids) > 0 else ids_bgr
    
    if best_ids is not None:
        # Dessiner tous les ArUcos détectés
        cv2.aruco.drawDetectedMarkers(result_img, best_corners, best_ids, (0, 255, 0))
        
        # Marquer en rouge l'ArUco robot s'il est présent
        for i, marker_id in enumerate(best_ids.flatten()):
            if int(marker_id) == ROBOT_ARUCO_ID:
                # Redessiner en rouge
                pts = best_corners[i][0].reshape((-1, 1, 2)).astype(int)
                cv2.polylines(result_img, [pts], True, (0, 0, 255), 3)
                center = best_corners[i][0].mean(axis=0).astype(int)
                cv2.circle(result_img, tuple(center), 10, (0, 0, 255), 2)
                cv2.putText(result_img, "ROBOT!", tuple(center + [20, 0]),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    else:
        cv2.putText(result_img, "AUCUN ArUco DETECTE!", (50, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
    
    # Sauvegarder l'image annotée
    output_path = os.path.join(tmp_dir, "test_aruco_result.jpg")
    cv2.imwrite(output_path, result_img)
    print(f"✅ Image annotée sauvegardée: {output_path}")
    
    # ===== Résumé =====
    print("\n" + "=" * 70)
    print("📝 RÉSUMÉ")
    print("=" * 70)
    
    robot_found = (ids is not None and ROBOT_ARUCO_ID in ids.flatten()) or \
                  (ids_bgr is not None and ROBOT_ARUCO_ID in ids_bgr.flatten())
    
    if robot_found:
        print("✅ L'ArUco ROBOT (ID 36) a été détecté!")
    else:
        print("❌ L'ArUco ROBOT (ID 36) N'a PAS été détecté!")
        print("\nPossibles causes:")
        print("  • ArUco pas assez visible/net dans l'image")
        print("  • Mauvaise position de focus")
        print("  • Mauvais éclairage")
        print("  • ArUco endommagé ou mal imprimé")
        print("  • Caméra pas alignée correctement")

if __name__ == "__main__":
    main()
