#!/usr/bin/env python3
"""
Outil de calibration du plateau par clic sur les 4 coins.

Usage:
    python -m chess_vision.calibrate_board                    # Capture photo en direct (par défaut)
    python -m chess_vision.calibrate_board --no-capture       # Sélectionner une image existante
    python -m chess_vision.calibrate_board --image photo.jpg  # Utiliser une image spécifique

Instructions:
    1. Cliquer sur les 4 coins du plateau dans l'ordre:
       TL (haut-gauche) → TR (haut-droite) → BR (bas-droite) → BL (bas-gauche)
    2. Appuyer sur 'r' pour recommencer
    3. Appuyer sur 'v' pour valider et sauvegarder
    4. Appuyer sur 'q' pour quitter sans sauvegarder

Le fichier board_calibration.json est sauvegardé dans chess_vision/
et sera automatiquement chargé par le pipeline.
"""

import cv2
import json
import os
import sys
import argparse
import glob
import numpy as np
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_vision.config import (
    EXTRACTED_BOARD_SIZE,
    OUTPUT_DIR,
    IMAGES_DIR,
    SCRIPT_DIR,
    CALIBRATION_FILE,
)


# ============================================================
# CONSTANTES
# ============================================================
CORNER_NAMES = ['TL', 'TR', 'BR', 'BL']
CORNER_LABELS = {
    'TL': 'Top-Left (Haut-Gauche)',
    'TR': 'Top-Right (Haut-Droite)',
    'BR': 'Bottom-Right (Bas-Droite)',
    'BL': 'Bottom-Left (Bas-Gauche)',
}
CORNER_COLORS = {
    'TL': (0, 0, 255),    # Rouge
    'TR': (0, 255, 0),    # Vert
    'BR': (255, 0, 0),    # Bleu
    'BL': (0, 255, 255),  # Jaune
}


class BoardCalibrator:
    """Calibrateur interactif du plateau."""

    def __init__(self, image_path: str):
        self.image_path = image_path
        self.original = cv2.imread(image_path)
        if self.original is None:
            raise ValueError(f"Impossible de charger: {image_path}")

        self.corners = []  # Liste de (x, y) dans l'ordre TL, TR, BR, BL
        self.current_corner_idx = 0
        self.window_name = "Calibration du plateau - Cliquer les 4 coins"
        self.zoom_size = 200  # Taille de la fenêtre de zoom
        self.mouse_pos = (0, 0)
        self.display_scale = 1.0  # Scale entre image originale et affichage

    def _mouse_callback(self, event, x, y, flags, param):
        """Callback souris."""
        self.mouse_pos = (x, y)

        if event == cv2.EVENT_LBUTTONDOWN:
            if self.current_corner_idx < 4:
                # Convertir les coordonnées display → coordonnées image originale
                orig_x = int(x / self.display_scale)
                orig_y = int(y / self.display_scale)
                self.corners.append((orig_x, orig_y))
                name = CORNER_NAMES[self.current_corner_idx]
                print(f"   ✅ {name} ({CORNER_LABELS[name]}): ({orig_x}, {orig_y}) [pixels originaux]")
                self.current_corner_idx += 1

                if self.current_corner_idx == 4:
                    print("\n   ✅ 4 coins sélectionnés!")
                    print("   Appuyer sur 'v' pour valider, 'r' pour recommencer")
                else:
                    next_name = CORNER_NAMES[self.current_corner_idx]
                    print(f"   → Cliquer sur {next_name} ({CORNER_LABELS[next_name]})")

    def _draw_ui(self):
        """Dessine l'interface utilisateur."""
        display = self.original.copy()
        h, w = display.shape[:2]

        # Redimensionner pour l'affichage si trop grande
        max_display = 1200
        scale = 1.0
        if max(h, w) > max_display:
            scale = max_display / max(h, w)
            display = cv2.resize(display, (int(w * scale), int(h * scale)))

        # Stocker le scale pour la conversion souris → image originale
        self.display_scale = scale

        # Dessiner les coins déjà placés
        for i, (cx, cy) in enumerate(self.corners):
            name = CORNER_NAMES[i]
            color = CORNER_COLORS[name]
            sx, sy = int(cx * scale), int(cy * scale)

            # Croix
            size = 20
            cv2.line(display, (sx - size, sy), (sx + size, sy), color, 2)
            cv2.line(display, (sx, sy - size), (sx, sy + size), color, 2)
            cv2.circle(display, (sx, sy), 6, color, -1)

            # Label
            cv2.putText(display, f"{name} ({cx},{cy})", (sx + 12, sy - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
            cv2.putText(display, f"{name} ({cx},{cy})", (sx + 12, sy - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Dessiner les lignes entre les coins
        if len(self.corners) >= 2:
            for i in range(len(self.corners)):
                j = (i + 1) % len(self.corners)
                if j < len(self.corners):
                    p1 = (int(self.corners[i][0] * scale), int(self.corners[i][1] * scale))
                    p2 = (int(self.corners[j][0] * scale), int(self.corners[j][1] * scale))
                    cv2.line(display, p1, p2, (255, 165, 0), 2, cv2.LINE_AA)

        # Fermer le quadrilatère si 4 coins
        if len(self.corners) == 4:
            p1 = (int(self.corners[3][0] * scale), int(self.corners[3][1] * scale))
            p2 = (int(self.corners[0][0] * scale), int(self.corners[0][1] * scale))
            cv2.line(display, p1, p2, (255, 165, 0), 2, cv2.LINE_AA)

            # Overlay semi-transparent
            pts = np.array([(int(c[0] * scale), int(c[1] * scale)) for c in self.corners], np.int32)
            overlay = display.copy()
            cv2.fillPoly(overlay, [pts.reshape(-1, 1, 2)], (255, 200, 100))
            cv2.addWeighted(overlay, 0.15, display, 0.85, 0, display)

        # Bandeau d'instructions en haut
        bar_h = 50
        cv2.rectangle(display, (0, 0), (display.shape[1], bar_h), (40, 40, 40), -1)

        if self.current_corner_idx < 4:
            name = CORNER_NAMES[self.current_corner_idx]
            color = CORNER_COLORS[name]
            text = f"Cliquer sur {name} ({CORNER_LABELS[name]})  |  'r' = reset  'q' = quitter"
            cv2.putText(display, text, (10, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        else:
            text = "'v' = VALIDER et sauvegarder  |  'r' = recommencer  |  'q' = quitter"
            cv2.putText(display, text, (10, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Compteur coins
        counter = f"{self.current_corner_idx}/4"
        cv2.putText(display, counter, (display.shape[1] - 70, 33),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return display, scale

    def _preview_extraction(self):
        """Affiche un aperçu de l'extraction avec les coins actuels."""
        if len(self.corners) != 4:
            return

        corners_dict = {}
        for i, name in enumerate(CORNER_NAMES):
            corners_dict[name] = self.corners[i]

        # Transformation perspective
        src = np.array([
            corners_dict['TL'],
            corners_dict['TR'],
            corners_dict['BR'],
            corners_dict['BL'],
        ], dtype=np.float32)

        size = EXTRACTED_BOARD_SIZE
        dst = np.array([
            [0, 0],
            [size - 1, 0],
            [size - 1, size - 1],
            [0, size - 1],
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(src, dst)
        board_img = cv2.warpPerspective(self.original, matrix, (size, size))

        # Dessiner la grille 10x10
        for i in range(11):
            x = int(i * size / 10)
            y = int(i * size / 10)
            cv2.line(board_img, (x, 0), (x, size), (0, 255, 0), 1)
            cv2.line(board_img, (0, y), (size, y), (0, 255, 0), 1)
        
        # Bordure du plateau central 8x8
        inner = int(size / 10)
        cv2.rectangle(board_img, (inner, inner), (size - inner, size - inner), (0, 200, 255), 2)

        # Afficher aperçu
        preview_size = 500
        preview = cv2.resize(board_img, (preview_size, preview_size))
        cv2.imshow("Apercu du plateau extrait", preview)

    def _reset(self):
        """Réinitialise les coins."""
        self.corners = []
        self.current_corner_idx = 0
        print("\n   🔄 Réinitialisation - Cliquer sur TL (Haut-Gauche)")

    def save(self) -> str:
        """Sauvegarde la calibration en JSON."""
        if len(self.corners) != 4:
            raise ValueError("4 coins requis pour sauvegarder")

        calibration_data = {
            'corners': {
                'TL': {'x': self.corners[0][0], 'y': self.corners[0][1]},
                'TR': {'x': self.corners[1][0], 'y': self.corners[1][1]},
                'BR': {'x': self.corners[2][0], 'y': self.corners[2][1]},
                'BL': {'x': self.corners[3][0], 'y': self.corners[3][1]},
            },
            'source_image': os.path.abspath(self.image_path),
            'board_size': EXTRACTED_BOARD_SIZE,
            'calibrated_at': datetime.now().isoformat(),
            'note': 'Coins du plateau en coordonnees pixels dans l\'image originale. Ne pas deplacer la camera apres calibration.',
        }

        # Sauvegarder
        with open(CALIBRATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(calibration_data, f, indent=2, ensure_ascii=False)

        print(f"\n   💾 Calibration sauvegardée: {CALIBRATION_FILE}")
        return CALIBRATION_FILE

    def run(self) -> bool:
        """Lance l'interface de calibration. Retourne True si sauvegardé."""
        print("\n🎯 CALIBRATION DU PLATEAU")
        print("-" * 50)
        print(f"   Image: {self.image_path}")
        print(f"   Résolution: {self.original.shape[1]}x{self.original.shape[0]}")
        print(f"\n   → Cliquer sur TL ({CORNER_LABELS['TL']})")

        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        saved = False

        while True:
            display, scale = self._draw_ui()
            cv2.imshow(self.window_name, display)

            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                print("\n   ❌ Calibration annulée")
                break
            elif key == ord('r'):
                self._reset()
                cv2.destroyWindow("Apercu du plateau extrait")
            elif key == ord('v'):
                if len(self.corners) == 4:
                    self.save()
                    saved = True
                    break
                else:
                    print("   ⚠️ Sélectionnez les 4 coins avant de valider")
            elif key == ord('p') and len(self.corners) == 4:
                self._preview_extraction()

            # Auto-preview quand 4 coins sélectionnés
            if len(self.corners) == 4:
                self._preview_extraction()

        cv2.destroyAllWindows()
        return saved


def select_image():
    """Sélection interactive d'une image."""
    search_dirs = [
        IMAGES_DIR,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analyse", "images"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_extraction_plateau_image_cam_rasp", "images"),
    ]

    images = []
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                images.extend(glob.glob(os.path.join(search_dir, ext)))

    images = sorted(set(images))

    if not images:
        print("❌ Aucune image trouvée.")
        return None

    print("\n📷 Images disponibles:")
    print("-" * 50)
    for i, img_path in enumerate(images, 1):
        print(f"   {i}. {os.path.basename(img_path)}")
        print(f"      {os.path.dirname(img_path)}")
    print("-" * 50)

    while True:
        try:
            choice = input("\nNuméro de l'image (ou 'q' pour quitter): ").strip()
            if choice.lower() == 'q':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(images):
                return images[idx]
            print("   ⚠️ Numéro invalide")
        except ValueError:
            print("   ⚠️ Entrez un numéro valide")


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Calibration du plateau d'échecs par clic sur les 4 coins",
    )
    parser.add_argument('--image', '-i', type=str, help='Utiliser une image existante (au lieu de capturer)')
    parser.add_argument('--no-capture', action='store_true', help='Ne pas capturer de photo (mode sélection fichier)')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🎯 CHESS VISION - Calibration du plateau")
    print("=" * 60)

    # Vérifier si calibration existante
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, 'r') as f:
            existing = json.load(f)
        print(f"\n   ⚠️ Calibration existante trouvée:")
        print(f"      Date: {existing.get('calibrated_at', '?')}")
        print(f"      Image: {os.path.basename(existing.get('source_image', '?'))}")
        resp = input("\n   Écraser? (o/n): ").strip().lower()
        if resp != 'o':
            print("   Calibration annulée.")
            return

    # Obtenir l'image
    image_path = None
    
    # Mode 1: Image spécifique fournie en argument
    if args.image:
        image_path = args.image
        print(f"\n📷 Image fournie: {image_path}")
    
    # Mode 2: Sélection manuelle d'image (--no-capture)
    elif args.no_capture:
        image_path = select_image()
    
    # Mode 3 (par défaut): Capture photo en direct
    else:
        from chess_vision.camera import take_photo
        print("\n📸 Capture d'une photo en direct...")
        print("   (Assurez-vous que le plateau est bien visible)")
        input("   Appuyez sur ENTRÉE pour capturer...")
        image_path = take_photo()
        print(f"   ✅ Photo capturée: {image_path}")

    if not image_path or not os.path.exists(image_path):
        print("❌ Pas d'image disponible.")
        return

    # Lancer la calibration
    calibrator = BoardCalibrator(image_path)
    saved = calibrator.run()

    if saved:
        print("\n" + "=" * 60)
        print("✅ CALIBRATION TERMINÉE")
        print(f"   Fichier: {CALIBRATION_FILE}")
        print("   ⚠️ Ne pas déplacer la caméra après calibration!")
        print("=" * 60)


if __name__ == "__main__":
    main()
