#!/usr/bin/env python3
"""
Test de détection des marqueurs ArUco sur les pièces d'échecs.

Prend une photo (ou charge une image existante) et identifie
tous les marqueurs ArUco présents avec leur pièce correspondante.

Usage:
    python -m test.test_aruco_detection
    python -m test.test_aruco_detection --image path/to/image.jpg
    python -m test.test_aruco_detection --no-camera --image path/to/image.jpg
"""

import sys
import os
import argparse
import cv2
import numpy as np
from datetime import datetime

# Ajouter le Backend au path pour les imports chess_vision
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Backend')
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from chess_vision.config import (
    ARUCO_DICT_TYPE,
    ARUCO_PARAMS,
    USE_DEFAULT_ARUCO_PARAMS,
    CALIBRATION_IDS,
    PIECES,
)

# ─── Constantes ──────────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')

# Couleurs BGR
COLOR_CALIBRATION    = (0,   255, 255)   # Jaune  – marqueurs coins du plateau
COLOR_WHITE_PIECE    = (255, 255, 255)   # Blanc  – pièces blanches
COLOR_BLACK_PIECE    = (180,  50, 230)   # Violet – pièces noires
COLOR_UNKNOWN        = (0,   165, 255)   # Orange – ID inconnu


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def build_detector() -> cv2.aruco.ArucoDetector:
    """Construit le détecteur ArUco avec les paramètres du projet."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
    params = cv2.aruco.DetectorParameters()

    if not USE_DEFAULT_ARUCO_PARAMS:
        params.adaptiveThreshWinSizeMin     = ARUCO_PARAMS['adaptiveThreshWinSizeMin']
        params.adaptiveThreshWinSizeMax     = ARUCO_PARAMS['adaptiveThreshWinSizeMax']
        params.adaptiveThreshWinSizeStep    = ARUCO_PARAMS['adaptiveThreshWinSizeStep']
        params.adaptiveThreshConstant       = ARUCO_PARAMS['adaptiveThreshConstant']
        params.minMarkerPerimeterRate       = ARUCO_PARAMS['minMarkerPerimeterRate']
        params.maxMarkerPerimeterRate       = ARUCO_PARAMS['maxMarkerPerimeterRate']
        params.polygonalApproxAccuracyRate  = ARUCO_PARAMS['polygonalApproxAccuracyRate']
        params.minCornerDistanceRate        = ARUCO_PARAMS['minCornerDistanceRate']
        params.minDistanceToBorder          = ARUCO_PARAMS['minDistanceToBorder']
        params.minMarkerDistanceRate        = ARUCO_PARAMS['minMarkerDistanceRate']
        params.cornerRefinementMethod       = ARUCO_PARAMS['cornerRefinementMethod']
        params.cornerRefinementWinSize      = ARUCO_PARAMS['cornerRefinementWinSize']
        params.cornerRefinementMaxIterations= ARUCO_PARAMS['cornerRefinementMaxIterations']
        params.cornerRefinementMinAccuracy  = ARUCO_PARAMS['cornerRefinementMinAccuracy']

    return cv2.aruco.ArucoDetector(aruco_dict, params)


def capture_photo(output_path: str) -> str:
    """Prend une photo via chess_vision (Raspberry Pi ou webcam)."""
    from chess_vision.modules.camera import take_photo
    print("📷  Prise de photo…")
    path = take_photo(output_path=output_path)
    print(f"    → sauvegardée : {path}")
    return path


def detect_arucos(image: np.ndarray) -> tuple:
    """
    Détecte tous les marqueurs ArUco dans l'image.

    Returns:
        (corners, ids, rejected)  — même format que cv2.aruco.ArucoDetector.detectMarkers()
    """
    detector = build_detector()
    corners, ids, rejected = detector.detectMarkers(image)
    return corners, ids, rejected


def annotate_image(image: np.ndarray, corners, ids) -> np.ndarray:
    """
    Dessine les marqueurs détectés sur l'image avec leur pièce.

    Returns:
        Image annotée (copie)
    """
    img = image.copy()

    if ids is None:
        return img

    for corner, marker_id in zip(corners, ids.flatten()):
        pts = corner[0].astype(int)
        center = pts.mean(axis=0).astype(int)

        # Identifier le marqueur
        if marker_id in CALIBRATION_IDS:
            color = COLOR_CALIBRATION
            label = f"CAL-{CALIBRATION_IDS[marker_id]}"
        elif marker_id in PIECES:
            piece = PIECES[marker_id]
            color = COLOR_WHITE_PIECE if piece['color'] == 'white' else COLOR_BLACK_PIECE
            label = f"{piece['symbol']} {piece['code']} (id={marker_id})"
        else:
            color = COLOR_UNKNOWN
            label = f"ID={marker_id} (?)"

        # Contour du marqueur
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=2)

        # Fond semi-transparent pour le texte
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        tx, ty = center[0] - tw // 2, center[1] - 10
        cv2.rectangle(img, (tx - 2, ty - th - 4), (tx + tw + 2, ty + 4),
                      (0, 0, 0), cv2.FILLED)
        cv2.putText(img, label, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

    return img


def print_results(ids):
    """Affiche un résumé des marqueurs détectés dans le terminal."""
    if ids is None or len(ids) == 0:
        print("\n❌  Aucun marqueur ArUco détecté.")
        return

    flat = sorted(ids.flatten())
    calibration_found = []
    pieces_found      = []
    unknown_found     = []

    for mid in flat:
        if mid in CALIBRATION_IDS:
            calibration_found.append(mid)
        elif mid in PIECES:
            pieces_found.append(mid)
        else:
            unknown_found.append(mid)

    print(f"\n{'─'*55}")
    print(f"  Total détectés : {len(flat)} marqueur(s)")
    print(f"{'─'*55}")

    if calibration_found:
        print(f"\n  🟡  Calibration ({len(calibration_found)}) :")
        for mid in calibration_found:
            print(f"      ID {mid:>2}  →  {CALIBRATION_IDS[mid]}")

    if pieces_found:
        white = [m for m in pieces_found if PIECES[m]['color'] == 'white']
        black = [m for m in pieces_found if PIECES[m]['color'] == 'black']

        print(f"\n  ⬜  Pièces blanches ({len(white)}) :")
        for mid in white:
            p = PIECES[mid]
            print(f"      ID {mid:>2}  →  {p['symbol']}  {p['code']:<5}  ({p['type']})")

        print(f"\n  ⬛  Pièces noires ({len(black)}) :")
        for mid in black:
            p = PIECES[mid]
            print(f"      ID {mid:>2}  →  {p['symbol']}  {p['code']:<5}  ({p['type']})")

    if unknown_found:
        print(f"\n  🟠  IDs inconnus ({len(unknown_found)}) : {unknown_found}")

    print(f"{'─'*55}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Détecte les marqueurs ArUco d'échecs sur une photo."
    )
    parser.add_argument('--image', '-i', type=str, default=None,
                        help="Chemin vers une image existante (skip prise de photo)")
    parser.add_argument('--no-camera', action='store_true',
                        help="Ne pas utiliser la caméra (--image requis)")
    parser.add_argument('--show', action='store_true',
                        help="Afficher l'image annotée dans une fenêtre")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Acquisition ──────────────────────────────────────────────────────────
    if args.image:
        image_path = args.image
        print(f"📂  Chargement image : {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌  Impossible de lire : {image_path}")
            sys.exit(1)
    elif args.no_camera:
        print("❌  --no-camera spécifié mais aucune --image fournie.")
        parser.print_help()
        sys.exit(1)
    else:
        photo_path = os.path.join(OUTPUT_DIR, f"capture_{timestamp}.jpg")
        image_path = capture_photo(photo_path)
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌  Erreur lecture image capturée : {image_path}")
            sys.exit(1)

    print(f"    Taille image : {image.shape[1]}×{image.shape[0]} px")

    # ── Détection ────────────────────────────────────────────────────────────
    print("\n🔍  Détection ArUco…")
    corners, ids, rejected = detect_arucos(image)
    n_detected = len(ids) if ids is not None else 0
    n_rejected = len(rejected) if rejected is not None else 0
    print(f"    {n_detected} marqueur(s) détecté(s), {n_rejected} candidat(s) rejeté(s)")

    # ── Résumé terminal ───────────────────────────────────────────────────────
    print_results(ids)

    # ── Sauvegarde image annotée ──────────────────────────────────────────────
    annotated = annotate_image(image, corners, ids)
    out_path = os.path.join(OUTPUT_DIR, f"annotated_{timestamp}.jpg")
    cv2.imwrite(out_path, annotated)
    print(f"💾  Image annotée sauvegardée : {out_path}")

    # ── Affichage optionnel ───────────────────────────────────────────────────
    if args.show:
        cv2.imshow("ArUco Detection", annotated)
        print("    (appuyer sur une touche pour fermer)")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
