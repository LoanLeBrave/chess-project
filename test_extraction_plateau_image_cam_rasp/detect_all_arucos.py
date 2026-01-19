#!/usr/bin/env python3
"""
Script simple pour détecter TOUS les ArUcos dans une image.
Utile pour identifier l'ID de marqueurs inconnus.

Usage:
    python3 detect_all_arucos.py              # Prendre une photo et scanner
    python3 detect_all_arucos.py image.jpg    # Scanner une image existante
"""

import cv2
import sys
import os
import subprocess
import shutil

# Dictionnaire ArUco (même que chess_detector.py)
ARUCO_DICT = cv2.aruco.DICT_4X4_50

def take_photo(filepath="temp_scan.jpg"):
    """Prend une photo rapide avec rpicam-still"""
    if shutil.which('rpicam-still'):
        cmd = 'rpicam-still'
    else:
        cmd = 'libcamera-still'
    
    print(f"📷 Capture avec {cmd}...")
    args = [cmd, '-n', '-o', filepath, '--timeout', '2000']
    
    try:
        subprocess.run(args, capture_output=True, timeout=30)
        print(f"✅ Photo enregistrée: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def detect_all_arucos(image_path):
    """Détecte TOUS les ArUcos dans l'image"""
    # Charger l'image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Impossible de charger: {image_path}")
        return
    
    print(f"📷 Image: {image_path} ({img.shape[1]}x{img.shape[0]})")
    
    # Convertir en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Créer le détecteur ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Détecter
    print("\n🔍 Détection des ArUcos...")
    corners, ids, rejected = detector.detectMarkers(gray)
    
    if ids is not None and len(ids) > 0:
        print(f"\n✅ {len(ids)} ArUco(s) détecté(s):\n")
        
        # Trier par ID
        sorted_ids = sorted([(int(marker_id), i) for i, marker_id in enumerate(ids.flatten())])
        
        for marker_id, idx in sorted_ids:
            marker_corners = corners[idx][0]
            center_x = sum(c[0] for c in marker_corners) / 4
            center_y = sum(c[1] for c in marker_corners) / 4
            
            # Déterminer la catégorie
            if 0 <= marker_id <= 15:
                category = "🟦 PIÈCE BLANCHE"
            elif 16 <= marker_id <= 31:
                category = "🟥 PIÈCE NOIRE"
            elif 32 <= marker_id <= 35:
                category = "📐 CALIBRATION PLATEAU"
            else:
                category = "❓ AUTRE (peut-être le robot?)"
            
            print(f"   ID {marker_id:2d} - {category}")
            print(f"          Centre: ({center_x:.1f}, {center_y:.1f})")
            print()
        
        # Dessiner sur l'image
        img_annotated = img.copy()
        cv2.aruco.drawDetectedMarkers(img_annotated, corners, ids)
        
        # Sauvegarder
        output_path = "detected_arucos.jpg"
        cv2.imwrite(output_path, img_annotated)
        print(f"💾 Image annotée sauvegardée: {output_path}")
        
    else:
        print("\n❌ Aucun ArUco détecté")
        print("   Vérifiez:")
        print("   - La qualité de l'image (netteté, éclairage)")
        print("   - La taille des marqueurs (pas trop petits)")
        print("   - Le dictionnaire utilisé (DICT_4X4_50)")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 DÉTECTION DE TOUS LES ARUCOS")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n❌ Veuillez fournir une image en argument")
        print("Usage: python3 detect_all_arucos.py <image.jpg>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"\n❌ Fichier introuvable: {image_path}")
        sys.exit(1)
    
    detect_all_arucos(image_path)
    
    print("\n" + "=" * 60)
