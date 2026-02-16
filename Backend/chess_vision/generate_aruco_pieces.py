#!/usr/bin/env python3
"""
Génère une planche A4 avec tous les marqueurs ArUco des pièces d'échecs.
Chaque marqueur fait exactement 2cm x 2cm pour l'impression.

Usage:
    python -m chess_vision.generate_aruco_pieces
"""

import cv2
import numpy as np
from config import ARUCO_DICT_TYPE, PIECES

# Paramètres A4 et impression
DPI = 300  # Résolution d'impression standard
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
MARKER_SIZE_MM = 14  # 1.4cm = 14mm

# Conversion mm → pixels à 300 DPI
def mm_to_pixels(mm):
    return int(mm * DPI / 25.4)

# Dimensions en pixels
A4_WIDTH_PX = mm_to_pixels(A4_WIDTH_MM)
A4_HEIGHT_PX = mm_to_pixels(A4_HEIGHT_MM)
MARKER_SIZE_PX = mm_to_pixels(MARKER_SIZE_MM)

# Marges et espacement
MARGIN_PX = mm_to_pixels(10)  # 1cm de marge
SPACING_PX = mm_to_pixels(5)  # 5mm entre marqueurs
LABEL_HEIGHT_PX = mm_to_pixels(5)  # Hauteur pour le label

# Calculer le nombre de colonnes et lignes
CELL_WIDTH = MARKER_SIZE_PX + SPACING_PX
CELL_HEIGHT = MARKER_SIZE_PX + LABEL_HEIGHT_PX + SPACING_PX

USABLE_WIDTH = A4_WIDTH_PX - 2 * MARGIN_PX
USABLE_HEIGHT = A4_HEIGHT_PX - 2 * MARGIN_PX

COLS = USABLE_WIDTH // CELL_WIDTH
ROWS = USABLE_HEIGHT // CELL_HEIGHT

print(f"📄 Génération planche ArUco A4")
print(f"   Format: {A4_WIDTH_MM}x{A4_HEIGHT_MM}mm à {DPI} DPI")
print(f"   Résolution: {A4_WIDTH_PX}x{A4_HEIGHT_PX} pixels")
print(f"   Taille marqueur: {MARKER_SIZE_MM}mm = {MARKER_SIZE_PX}px")
print(f"   Disposition: {COLS} colonnes × {ROWS} lignes")
print(f"   Capacité: {COLS * ROWS} marqueurs")

# Créer la page blanche
page = np.ones((A4_HEIGHT_PX, A4_WIDTH_PX), dtype=np.uint8) * 255

# Dictionnaire ArUco
aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)

# Générer les 32 marqueurs (IDs 0-31)
piece_ids = sorted([id for id in PIECES.keys() if id < 32])

print(f"\n🎯 Génération de {len(piece_ids)} marqueurs...")

for idx, marker_id in enumerate(piece_ids):
    piece_info = PIECES[marker_id]
    
    # Calculer position sur la grille
    col = idx % COLS
    row = idx // COLS
    
    if row >= ROWS:
        print(f"⚠️  Pas assez d'espace pour le marqueur {marker_id}")
        break
    
    # Position du coin supérieur gauche
    x = MARGIN_PX + col * CELL_WIDTH
    y = MARGIN_PX + row * CELL_HEIGHT
    
    # Générer le marqueur ArUco
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, MARKER_SIZE_PX)
    
    # Placer le marqueur sur la page
    page[y:y+MARKER_SIZE_PX, x:x+MARKER_SIZE_PX] = marker_img
    
    # Ajouter le label sous le marqueur
    label = f"{marker_id}: {piece_info['code']}"
    label_y = y + MARKER_SIZE_PX + mm_to_pixels(3)
    
    # Calculer la taille du texte pour le centrer
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    thickness = 1
    (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, thickness)
    
    label_x = x + (MARKER_SIZE_PX - text_width) // 2
    
    cv2.putText(page, label, (label_x, label_y), font, font_scale, 0, thickness, cv2.LINE_AA)
    
    print(f"   ✅ ID {marker_id:2d}: {piece_info['code']} - {piece_info['symbol']} {piece_info['type']}")

# Ajouter un titre en haut
title = "ARUCO MARKERS - CHESS PIECES (1.4cm each)"
title_font = cv2.FONT_HERSHEY_SIMPLEX
title_scale = 0.8
title_thickness = 2
(title_width, title_height), _ = cv2.getTextSize(title, title_font, title_scale, title_thickness)
title_x = (A4_WIDTH_PX - title_width) // 2
title_y = mm_to_pixels(7)
cv2.putText(page, title, (title_x, title_y), title_font, title_scale, 0, title_thickness, cv2.LINE_AA)

# Ajouter instructions en bas
instructions = [
    f"Print at {DPI} DPI - Each marker = {MARKER_SIZE_MM}mm x {MARKER_SIZE_MM}mm",
    "Use DICT_4X4_50 - IDs 0-31 (Pieces) - Verify size after printing!"
]
inst_y = A4_HEIGHT_PX - mm_to_pixels(5)
for inst in reversed(instructions):
    (inst_width, inst_height), _ = cv2.getTextSize(inst, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    inst_x = (A4_WIDTH_PX - inst_width) // 2
    cv2.putText(page, inst, (inst_x, inst_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1, cv2.LINE_AA)
    inst_y -= mm_to_pixels(4)

# Sauvegarder avec métadonnées DPI
output_path = "aruco_pieces_1.4cm_A4.png"

# Encoder avec DPI metadata
import os
from PIL import Image

# Convertir OpenCV → PIL pour sauvegarder avec DPI
pil_img = Image.fromarray(page)
pil_img.save(output_path, dpi=(DPI, DPI))

print(f"\n💾 Fichier sauvegardé: {output_path}")
print(f"   Taille: {os.path.getsize(output_path) / 1024:.1f} KB")

# Vérification
file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
print(f"\n✅ TERMINÉ")
print(f"   📄 Ouvrez: {output_path}")
print(f"   🖨️  Imprimez à 100% (pas de mise à l'échelle)")
print(f"   📏 Vérifiez avec une règle: chaque marqueur doit faire 1.4cm")
print(f"   ⚠️  IMPORTANT: Dans les paramètres d'impression, sélectionnez 'Taille réelle' ou '100%'")
