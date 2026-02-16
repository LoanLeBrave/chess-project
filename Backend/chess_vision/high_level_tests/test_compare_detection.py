#!/usr/bin/env python3
"""
Test comparatif : détection ArUco sur image originale vs plateau extrait.
Diagnostic : pourquoi warpPerspective casse la détection ArUco ?
Utilise exactement les mêmes modules que le code final chess_vision.

Usage:
    python -m chess_vision.tests.test_compare_detection
    python3 test_compare_detection.py
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.aruco_detector import ArucoDetector, detect_piece_markers, detect_calibration_markers
from chess_vision.board_extractor import BoardExtractor
from chess_vision.config import EXTRACTED_BOARD_SIZE


def detect_and_print(label, image, detector):
    """Détecte les ArUcos et affiche les résultats."""
    all_markers = detector.detect(image)
    pieces = {k: v for k, v in all_markers.items() if k < 32}
    calib = {k: v for k, v in all_markers.items() if k >= 32}
    
    print(f"  Total: {len(all_markers)} | Pièces: {len(pieces)} | Calibration: {len(calib)}")
    for mid in sorted(all_markers.keys()):
        sz = all_markers[mid]['size']
        print(f"    ID {mid:2d} : size={sz:.1f}px")
    
    _, rejected = detector.detect_with_rejected(image)
    n_rejected = len(rejected) if rejected is not None else 0
    print(f"  Candidats rejetés: {n_rejected}")
    
    return all_markers


def run():
    # Trouver le dernier run piece_analysis avec les images
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    
    run_dir = None
    for d in sorted(os.listdir(output_dir), reverse=True):
        if d.startswith("piece_analysis_"):
            candidate = os.path.join(output_dir, d)
            if os.path.exists(os.path.join(candidate, "02_02_extracted_board.jpg")):
                run_dir = candidate
                break
    
    if not run_dir:
        print("❌ Aucun dossier piece_analysis avec images trouvé")
        return
    
    print(f"📁 Dossier: {run_dir}\n")
    
    original = cv2.imread(os.path.join(run_dir, "01_01_original_input.jpg"))
    extracted = cv2.imread(os.path.join(run_dir, "02_02_extracted_board.jpg"))
    
    if original is None or extracted is None:
        print("❌ Impossible de charger les images")
        return
    
    print(f"Image originale : {original.shape[1]}x{original.shape[0]}")
    print(f"Plateau extrait : {extracted.shape[1]}x{extracted.shape[0]}")
    
    detector = ArucoDetector()
    
    # ============================================================
    # TEST 1 : Image originale
    # ============================================================
    print("\n" + "=" * 55)
    print("TEST 1 : IMAGE ORIGINALE")
    print("=" * 55)
    orig_markers = detect_and_print("original", original, detector)
    
    # ============================================================
    # TEST 2 : Plateau extrait (ce qui échoue)
    # ============================================================
    print("\n" + "=" * 55)
    print("TEST 2 : PLATEAU EXTRAIT 800x800 (warp INTER_LINEAR)")
    print("=" * 55)
    detect_and_print("extrait", extracted, detector)
    
    # ============================================================
    # TEST 3 : Re-extraire avec INTER_NEAREST
    # ============================================================
    print("\n" + "=" * 55)
    print("TEST 3 : RE-EXTRACTION avec INTER_NEAREST")
    print("=" * 55)
    
    # Refaire l'extraction depuis l'image originale
    extractor = BoardExtractor()
    calib_markers = detect_calibration_markers(original, detector)
    
    if len(calib_markers) >= 3:
        corners, _ = extractor.calculate_corners(calib_markers)
        
        # Même extraction mais avec INTER_NEAREST
        required = ['TL', 'TR', 'BL', 'BR']
        if all(c in corners for c in required):
            src_pts = np.array([
                corners['TL'], corners['TR'], corners['BR'], corners['BL']
            ], dtype=np.float32)
            
            size = EXTRACTED_BOARD_SIZE
            dst_pts = np.array([
                [0, 0], [size-1, 0], [size-1, size-1], [0, size-1]
            ], dtype=np.float32)
            
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            
            board_nearest = cv2.warpPerspective(original, M, (size, size),
                                                 flags=cv2.INTER_NEAREST)
            detect_and_print("INTER_NEAREST", board_nearest, detector)
            
            # ============================================================
            # TEST 4 : INTER_NEAREST + taille plus grande
            # ============================================================
            print("\n" + "=" * 55)
            print("TEST 4 : RE-EXTRACTION INTER_NEAREST + 2000x2000")
            print("=" * 55)
            
            size2 = 2000
            dst_pts2 = np.array([
                [0, 0], [size2-1, 0], [size2-1, size2-1], [0, size2-1]
            ], dtype=np.float32)
            
            M2 = cv2.getPerspectiveTransform(src_pts, dst_pts2)
            board_big = cv2.warpPerspective(original, M2, (size2, size2),
                                             flags=cv2.INTER_NEAREST)
            detect_and_print("NEAREST 2000x2000", board_big, detector)
            
            # ============================================================
            # TEST 5 : INTER_LINEAR + taille plus grande (plus de pixels)
            # ============================================================
            print("\n" + "=" * 55)
            print("TEST 5 : RE-EXTRACTION INTER_LINEAR + 2000x2000")
            print("=" * 55)
            
            board_big_linear = cv2.warpPerspective(original, M2, (size2, size2),
                                                    flags=cv2.INTER_LINEAR)
            detect_and_print("LINEAR 2000x2000", board_big_linear, detector)
            
            # ============================================================
            # TEST 6 : Pas de warp, détecter sur original + transformer coords
            # ============================================================
            print("\n" + "=" * 55)
            print("TEST 6 : DÉTECTION SUR ORIGINAL + PROJECTION COORDONNÉES")
            print("=" * 55)
            
            piece_markers = detect_piece_markers(original, detector)
            print(f"  Pièces détectées sur original: {len(piece_markers)}")
            
            if piece_markers:
                # Transformer les centres vers l'espace du plateau extrait
                for mid, data in sorted(piece_markers.items()):
                    cx, cy = data['center']
                    # Projeter le point via la matrice de transformation
                    pt = np.array([[[cx, cy]]], dtype=np.float32)
                    projected = cv2.perspectiveTransform(pt, M)
                    px, py = projected[0][0]
                    print(f"    ID {mid:2d} : original({cx:.0f},{cy:.0f}) → board({px:.0f},{py:.0f})")
    else:
        print("  ❌ Pas assez de marqueurs de calibration")
    
    # ============================================================
    # CONCLUSION
    # ============================================================
    print("\n" + "=" * 55)
    print("CONCLUSION")
    print("=" * 55)
    print("Si TEST 3/4/5 ne marchent pas → warpPerspective dégrade les ArUcos")
    print("Si TEST 3 marche → INTER_NEAREST est la solution")
    print("Si TEST 4/5 marchent → il faut augmenter EXTRACTED_BOARD_SIZE")
    print("TEST 6 = solution de secours : détecter sur l'original, projeter les coordonnées")


if __name__ == "__main__":
    run()
