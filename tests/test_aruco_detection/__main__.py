#!/usr/bin/env python3
"""
Test de détection des marqueurs ArUco sur les pièces d'échecs.

Prend une photo (ou charge une image existante) et identifie
tous les marqueurs ArUco présents avec leur pièce correspondante.

Sauvegarde deux images dans output/ :
  - original_annotated_<ts>.jpg  : image brute avec marqueurs
  - preprocessed_annotated_<ts>.jpg : image après prétraitement avec marqueurs

Usage:
    python -m tests.test_aruco_detection
    python -m tests.test_aruco_detection --image path/to/image.jpg
    python -m tests.test_aruco_detection --image path/to/image.jpg --show
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

from chess_vision.config import CALIBRATION_IDS, PIECES
from chess_vision.modules.aruco_detector import ArucoDetector
from chess_vision.modules.preprocessing import preprocess

# ─── Constantes ──────────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')

# Couleurs BGR
COLOR_CALIBRATION = (0,   255, 255)   # Jaune  – marqueurs coins du plateau
COLOR_WHITE_PIECE = (255, 255, 255)   # Blanc  – pièces blanches
COLOR_BLACK_PIECE = (180,  50, 230)   # Violet – pièces noires
COLOR_UNKNOWN     = (0,   165, 255)   # Orange – ID inconnu


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def capture_photo(output_path: str) -> str:
    """Prend une photo via chess_vision (Raspberry Pi ou webcam)."""
    from chess_vision.modules.camera import take_photo
    print("📷  Prise de photo…")
    path = take_photo(output_path=output_path)
    print(f"    → sauvegardée : {path}")
    return path


def annotate_image(image: np.ndarray, markers: dict) -> np.ndarray:
    """
    Dessine les marqueurs détectés sur l'image avec leur pièce.
    Fonctionne sur image BGR ou grayscale (convertie en BGR si besoin).
    """
    # Toujours annoter en couleur
    img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if len(image.shape) == 2 else image.copy()

    for marker_id, data in markers.items():
        pts = data['corners'].astype(int)
        center = pts.mean(axis=0).astype(int)

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

        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=2)

        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        tx, ty = center[0] - tw // 2, center[1] - 10
        cv2.rectangle(img, (tx - 2, ty - th - 4), (tx + tw + 2, ty + 4), (0, 0, 0), cv2.FILLED)
        cv2.putText(img, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

    return img


def make_comparison(original_annotated: np.ndarray, preprocessed_annotated: np.ndarray) -> np.ndarray:
    """Assemble les deux images côte à côte avec un titre chacune."""
    h = max(original_annotated.shape[0], preprocessed_annotated.shape[0])
    HEADER = 30
    BORDER = 4

    def pad(img, target_h):
        pad_h = target_h - img.shape[0]
        return np.pad(img, ((0, pad_h), (0, 0), (0, 0)), mode='constant') if pad_h > 0 else img

    left  = pad(original_annotated,     h)
    right = pad(preprocessed_annotated, h)

    # Ajouter une bande de titre
    def with_title(img, title):
        banner = np.zeros((HEADER, img.shape[1], 3), dtype=np.uint8)
        cv2.putText(banner, title, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        return np.vstack([banner, img])

    left  = with_title(left,  "Original")
    right = with_title(right, "Après prétraitement")

    separator = np.full((left.shape[0], BORDER, 3), 80, dtype=np.uint8)
    return np.hstack([left, separator, right])


def print_results(markers: dict):
    """Affiche un résumé des marqueurs détectés dans le terminal."""
    if not markers:
        print("\n❌  Aucun marqueur ArUco détecté.")
        return

    ids = sorted(markers.keys())
    calibration_found = [m for m in ids if m in CALIBRATION_IDS]
    pieces_found      = [m for m in ids if m in PIECES]
    unknown_found     = [m for m in ids if m not in CALIBRATION_IDS and m not in PIECES]

    print(f"\n{'─'*55}")
    print(f"  Total détectés : {len(ids)} marqueur(s)")
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
                        help="Afficher la comparaison dans une fenêtre")
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

    # ── Prétraitement ─────────────────────────────────────────────────────────
    print("\n🎨  Prétraitement…")
    preprocessed = preprocess(image)   # image grayscale après pipeline config.py
    print(f"    → image prétraitée : {preprocessed.shape[1]}×{preprocessed.shape[0]} px (grayscale)")

    # ── Détection (via ArucoDetector qui appelle preprocess en interne) ───────
    print("\n🔍  Détection ArUco…")
    detector = ArucoDetector()
    markers, rejected = detector.detect_with_rejected(image)
    print(f"    {len(markers)} marqueur(s) détecté(s), {len(rejected)} candidat(s) rejeté(s)")

    # ── Résumé terminal ───────────────────────────────────────────────────────
    print_results(markers)

    # ── Annotation des deux images ────────────────────────────────────────────
    original_annotated     = annotate_image(image,        markers)
    preprocessed_annotated = annotate_image(preprocessed, markers)

    # ── Sauvegarde individuelle ───────────────────────────────────────────────
    path_orig = os.path.join(OUTPUT_DIR, f"original_annotated_{timestamp}.jpg")
    path_pre  = os.path.join(OUTPUT_DIR, f"preprocessed_annotated_{timestamp}.jpg")
    cv2.imwrite(path_orig, original_annotated)
    cv2.imwrite(path_pre,  preprocessed_annotated)
    print(f"💾  Original annoté      → {path_orig}")
    print(f"💾  Prétraité annoté     → {path_pre}")

    # ── Comparaison côte à côte ───────────────────────────────────────────────
    comparison = make_comparison(original_annotated, preprocessed_annotated)
    path_cmp = os.path.join(OUTPUT_DIR, f"comparison_{timestamp}.jpg")
    cv2.imwrite(path_cmp, comparison)
    print(f"💾  Comparaison          → {path_cmp}")

    # ── Affichage optionnel ───────────────────────────────────────────────────
    if args.show:
        cv2.imshow("ArUco Detection — Original vs Prétraité", comparison)
        print("    (appuyer sur une touche pour fermer)")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
