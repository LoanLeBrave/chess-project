"""
Générateur de marqueurs ArUco pour pièces d'échecs
ArUco = Alternative ultra-compacte aux QR codes (6x6 modules vs 21x21)
Natif OpenCV, pas de dépendance externe !
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# ============================================================
# CONFIGURATION DES PIÈCES
# ============================================================

# ============================================================
# MARQUEURS DE CALIBRATION (Coins)
# ============================================================

# IDs réservés pour calibration (32-35)
CALIBRATION_MARKERS = {
    32: {'code': 'CAL_TL', 'nom': 'Calibration Haut-Gauche', 'position': 'top-left', 'symbole': '📍'},
    33: {'code': 'CAL_TR', 'nom': 'Calibration Haut-Droite', 'position': 'top-right', 'symbole': '📍'},
    34: {'code': 'CAL_BL', 'nom': 'Calibration Bas-Gauche', 'position': 'bottom-left', 'symbole': '📍'},
    35: {'code': 'CAL_BR', 'nom': 'Calibration Bas-Droite', 'position': 'bottom-right', 'symbole': '📍'},
}

# ============================================================
# MARQUEUR ROBOT
# ============================================================

# ID réservé pour robot (36)
ROBOT_MARKER = {
    36: {'code': 'ROBOT', 'nom': 'Centre Pince Robot', 'symbole': '🤖'},
}

# Mapping ID ArUco -> Pièce (IDs 0-31 pour 32 pièces)
PIECES = {
    # Pièces blanches (IDs 0-15)
    0: {'code': 'WK', 'nom': 'Roi', 'couleur': 'Blanc', 'symbole': '♔'},
    1: {'code': 'WQ', 'nom': 'Dame', 'couleur': 'Blanc', 'symbole': '♕'},
    2: {'code': 'WR1', 'nom': 'Tour 1', 'couleur': 'Blanc', 'symbole': '♖'},
    3: {'code': 'WR2', 'nom': 'Tour 2', 'couleur': 'Blanc', 'symbole': '♖'},
    4: {'code': 'WB1', 'nom': 'Fou 1', 'couleur': 'Blanc', 'symbole': '♗'},
    5: {'code': 'WB2', 'nom': 'Fou 2', 'couleur': 'Blanc', 'symbole': '♗'},
    6: {'code': 'WN1', 'nom': 'Cavalier 1', 'couleur': 'Blanc', 'symbole': '♘'},
    7: {'code': 'WN2', 'nom': 'Cavalier 2', 'couleur': 'Blanc', 'symbole': '♘'},
    8: {'code': 'WP1', 'nom': 'Pion 1', 'couleur': 'Blanc', 'symbole': '♙'},
    9: {'code': 'WP2', 'nom': 'Pion 2', 'couleur': 'Blanc', 'symbole': '♙'},
    10: {'code': 'WP3', 'nom': 'Pion 3', 'couleur': 'Blanc', 'symbole': '♙'},
    11: {'code': 'WP4', 'nom': 'Pion 4', 'couleur': 'Blanc', 'symbole': '♙'},
    12: {'code': 'WP5', 'nom': 'Pion 5', 'couleur': 'Blanc', 'symbole': '♙'},
    13: {'code': 'WP6', 'nom': 'Pion 6', 'couleur': 'Blanc', 'symbole': '♙'},
    14: {'code': 'WP7', 'nom': 'Pion 7', 'couleur': 'Blanc', 'symbole': '♙'},
    15: {'code': 'WP8', 'nom': 'Pion 8', 'couleur': 'Blanc', 'symbole': '♙'},
    
    # Pièces noires (IDs 16-31)
    16: {'code': 'BK', 'nom': 'Roi', 'couleur': 'Noir', 'symbole': '♚'},
    17: {'code': 'BQ', 'nom': 'Dame', 'couleur': 'Noir', 'symbole': '♛'},
    18: {'code': 'BR1', 'nom': 'Tour 1', 'couleur': 'Noir', 'symbole': '♜'},
    19: {'code': 'BR2', 'nom': 'Tour 2', 'couleur': 'Noir', 'symbole': '♜'},
    20: {'code': 'BB1', 'nom': 'Fou 1', 'couleur': 'Noir', 'symbole': '♝'},
    21: {'code': 'BB2', 'nom': 'Fou 2', 'couleur': 'Noir', 'symbole': '♝'},
    22: {'code': 'BN1', 'nom': 'Cavalier 1', 'couleur': 'Noir', 'symbole': '♞'},
    23: {'code': 'BN2', 'nom': 'Cavalier 2', 'couleur': 'Noir', 'symbole': '♞'},
    24: {'code': 'BP1', 'nom': 'Pion 1', 'couleur': 'Noir', 'symbole': '♟'},
    25: {'code': 'BP2', 'nom': 'Pion 2', 'couleur': 'Noir', 'symbole': '♟'},
    26: {'code': 'BP3', 'nom': 'Pion 3', 'couleur': 'Noir', 'symbole': '♟'},
    27: {'code': 'BP4', 'nom': 'Pion 4', 'couleur': 'Noir', 'symbole': '♟'},
    28: {'code': 'BP5', 'nom': 'Pion 5', 'couleur': 'Noir', 'symbole': '♟'},
    29: {'code': 'BP6', 'nom': 'Pion 6', 'couleur': 'Noir', 'symbole': '♟'},
    30: {'code': 'BP7', 'nom': 'Pion 7', 'couleur': 'Noir', 'symbole': '♟'},
    31: {'code': 'BP8', 'nom': 'Pion 8', 'couleur': 'Noir', 'symbole': '♟'},
}

# ============================================================
# CONFIGURATION DE LA FEUILLE
# ============================================================

# Taille A4 en pixels (300 DPI)
DPI = 300
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
A4_WIDTH_PX = int(A4_WIDTH_MM * DPI / 25.4)
A4_HEIGHT_PX = int(A4_HEIGHT_MM * DPI / 25.4)

# Grille 4x8 = 32 marqueurs
COLS = 4
ROWS = 8

# Marges
MARGIN_MM = 10
MARGIN_PX = int(MARGIN_MM * DPI / 25.4)

# Taille de chaque cellule
CELL_WIDTH = (A4_WIDTH_PX - 2 * MARGIN_PX) // COLS
CELL_HEIGHT = (A4_HEIGHT_PX - 2 * MARGIN_PX) // ROWS

# Taille du marqueur ArUco (en pixels sur la feuille)
MARKER_SIZE_PX = min(CELL_WIDTH, CELL_HEIGHT) - 80

# Dictionnaire ArUco à utiliser
# DICT_4X4_50 = 50 marqueurs de 4x4 bits (le plus compact!)
# DICT_5X5_50 = 50 marqueurs de 5x5 bits
# DICT_6X6_50 = 50 marqueurs de 6x6 bits
ARUCO_DICT = cv2.aruco.DICT_4X4_50  # 4x4 = le plus petit possible!

# ============================================================
# FONCTIONS
# ============================================================

def generate_aruco_marker(marker_id, size):
    """Génère un marqueur ArUco"""
    # Charger le dictionnaire
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    
    # Générer le marqueur
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size)
    
    # Convertir en PIL Image
    return Image.fromarray(marker_img)


def create_aruco_sheet():
    """Crée une feuille A4 avec tous les marqueurs ArUco + calibration aux 4 coins"""
    
    # Créer l'image blanche A4
    sheet = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), 'white')
    draw = ImageDraw.Draw(sheet)
    
    # Charger les polices
    try:
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_id = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font_label = ImageFont.load_default()
        font_id = ImageFont.load_default()
    
    print(f"📐 Génération de {len(PIECES)} marqueurs ArUco + 4 marqueurs de calibration + 1 marqueur robot...")
    print(f"   Format: A4 ({A4_WIDTH_MM}x{A4_HEIGHT_MM}mm) @ {DPI} DPI")
    print(f"   Grille: {COLS} colonnes x {ROWS} lignes")
    print(f"   Dictionnaire: DICT_4X4_50 (le plus compact)")
    print(f"   Taille marqueur: ~{MARKER_SIZE_PX * 25.4 / DPI:.1f}mm")
    print(f"   Calibration: 4 marqueurs aux coins (IDs 32-35)")
    print(f"   Robot: 1 marqueur au centre (ID 36)")
    
    for marker_id, piece in PIECES.items():
        # Position dans la grille
        col = marker_id % COLS
        row = marker_id // COLS
        
        # Coin supérieur gauche de la cellule
        cell_x = MARGIN_PX + col * CELL_WIDTH
        cell_y = MARGIN_PX + row * CELL_HEIGHT
        
        # Centre de la cellule
        center_x = cell_x + CELL_WIDTH // 2
        center_y = cell_y + CELL_HEIGHT // 2 - 20
        
        # Générer le marqueur
        marker_img = generate_aruco_marker(marker_id, MARKER_SIZE_PX)
        
        # Coller le marqueur centré
        marker_x = center_x - MARKER_SIZE_PX // 2
        marker_y = center_y - MARKER_SIZE_PX // 2
        sheet.paste(marker_img, (marker_x, marker_y))
        
        # Lignes de découpe pointillées
        for i in range(0, CELL_WIDTH, 10):
            if i % 20 < 10:
                draw.line([(cell_x + i, cell_y), (cell_x + i + 5, cell_y)], fill='lightgray', width=1)
                draw.line([(cell_x + i, cell_y + CELL_HEIGHT), (cell_x + i + 5, cell_y + CELL_HEIGHT)], fill='lightgray', width=1)
        for i in range(0, CELL_HEIGHT, 10):
            if i % 20 < 10:
                draw.line([(cell_x, cell_y + i), (cell_x, cell_y + i + 5)], fill='lightgray', width=1)
                draw.line([(cell_x + CELL_WIDTH, cell_y + i), (cell_x + CELL_WIDTH, cell_y + i + 5)], fill='lightgray', width=1)
        
        # Texte : symbole + code
        label = f"{piece['symbole']} {piece['code']}"
        text_bbox = draw.textbbox((0, 0), label, font=font_label)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = center_x - text_width // 2
        text_y = marker_y + MARKER_SIZE_PX + 8
        draw.text((text_x, text_y), label, fill='black', font=font_label)
        
        # ID ArUco
        id_text = f"ID: {marker_id}"
        id_bbox = draw.textbbox((0, 0), id_text, font=font_id)
        id_width = id_bbox[2] - id_bbox[0]
        id_x = center_x - id_width // 2
        id_y = text_y + 32
        draw.text((id_x, id_y), id_text, fill='gray', font=font_id)
        
        print(f"  ✓ ID {marker_id:2}: {piece['symbole']} {piece['code']:4} - {piece['couleur']} {piece['nom']}")
    
    # Ajouter les marqueurs de calibration aux 4 coins
    print(f"\n  🔷 Ajout des marqueurs de calibration:")
    calibration_size = 150  # Taille des marqueurs de calibration
    
    for marker_id, calib in CALIBRATION_MARKERS.items():
        # Générer le marqueur
        marker_img = generate_aruco_marker(marker_id, calibration_size)
        
        # Positionner selon la position
        if calib['position'] == 'top-left':
            pos_x = MARGIN_PX
            pos_y = MARGIN_PX
        elif calib['position'] == 'top-right':
            pos_x = A4_WIDTH_PX - MARGIN_PX - calibration_size
            pos_y = MARGIN_PX
        elif calib['position'] == 'bottom-left':
            pos_x = MARGIN_PX
            pos_y = A4_HEIGHT_PX - MARGIN_PX - calibration_size
        else:  # bottom-right
            pos_x = A4_WIDTH_PX - MARGIN_PX - calibration_size
            pos_y = A4_HEIGHT_PX - MARGIN_PX - calibration_size
        
        # Coller le marqueur
        sheet.paste(marker_img, (pos_x, pos_y))
        
        # Ajouter un label avec l'ID
        label = f"{calib['code']} (ID: {marker_id})"
        
        # Positionner le texte intelligemment selon le coin
        if calib['position'] == 'top-left':
            text_x = pos_x
            text_y = pos_y + calibration_size + 5
        elif calib['position'] == 'top-right':
            text_bbox = draw.textbbox((0, 0), label, font=font_id)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = pos_x + calibration_size - text_width
            text_y = pos_y + calibration_size + 5
        elif calib['position'] == 'bottom-left':
            text_x = pos_x
            text_y = pos_y - 30
        else:  # bottom-right
            text_bbox = draw.textbbox((0, 0), label, font=font_id)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = pos_x + calibration_size - text_width
            text_y = pos_y - 30
        
        draw.text((text_x, text_y), label, fill='darkred', font=font_id)
        
        print(f"    ✓ ID {marker_id}: {calib['code']} ({calib['nom']})")
    
    # Ajouter le marqueur robot au centre
    print(f"\n  🤖 Ajout du marqueur robot:")
    robot_marker_id = 36
    robot_marker = ROBOT_MARKER[robot_marker_id]
    robot_size = 150
    
    # Calculer la position du centre de la feuille
    center_page_x = A4_WIDTH_PX // 2 - robot_size // 2
    center_page_y = A4_HEIGHT_PX // 2 - robot_size // 2
    
    # Générer et coller le marqueur robot
    robot_img = generate_aruco_marker(robot_marker_id, robot_size)
    sheet.paste(robot_img, (center_page_x, center_page_y))
    
    # Ajouter un label au-dessus
    robot_label = f"{robot_marker['code']} (ID: {robot_marker_id})"
    robot_label_bbox = draw.textbbox((0, 0), robot_label, font=font_label)
    robot_label_width = robot_label_bbox[2] - robot_label_bbox[0]
    robot_text_x = center_page_x + robot_size // 2 - robot_label_width // 2
    robot_text_y = center_page_y - 40
    draw.text((robot_text_x, robot_text_y), robot_label, fill='darkgreen', font=font_label)
    
    print(f"    ✓ ID {robot_marker_id}: {robot_marker['code']} ({robot_marker['nom']})")
    
    return sheet


def save_individual_markers(output_dir):
    """Sauvegarde chaque marqueur individuellement (pièces + calibration + robot)"""
    individual_dir = os.path.join(output_dir, "aruco_individuels")
    os.makedirs(individual_dir, exist_ok=True)
    
    print(f"\n💾 Sauvegarde des marqueurs individuels...")
    
    # Pièces d'échecs
    for marker_id, piece in PIECES.items():
        marker_img = generate_aruco_marker(marker_id, 200)
        filepath = os.path.join(individual_dir, f"{marker_id:02d}_{piece['code']}.png")
        marker_img.save(filepath)
    
    # Marqueurs de calibration
    for marker_id, calib in CALIBRATION_MARKERS.items():
        marker_img = generate_aruco_marker(marker_id, 200)
        filepath = os.path.join(individual_dir, f"{marker_id:02d}_{calib['code']}.png")
        marker_img.save(filepath)
    
    # Marqueur robot
    for marker_id, robot in ROBOT_MARKER.items():
        marker_img = generate_aruco_marker(marker_id, 200)
        filepath = os.path.join(individual_dir, f"{marker_id:02d}_{robot['code']}.png")
        marker_img.save(filepath)
    
    total_markers = len(PIECES) + len(CALIBRATION_MARKERS) + len(ROBOT_MARKER)
    print(f"  ✓ {total_markers} marqueurs individuels sauvegardés")


def main():
    print("=" * 60)
    print("🎯 GÉNÉRATEUR DE MARQUEURS ARUCO POUR ÉCHECS")
    print("   (Ultra-compact: 4x4 modules vs 21x21 pour QR)")
    print("=" * 60)
    
    # Répertoire de sortie
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "aruco_markers")
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer la feuille
    print("\n📄 Création de la feuille A4...")
    sheet = create_aruco_sheet()
    
    # Sauvegarder
    sheet_path = os.path.join(output_dir, "aruco_echecs_A4.png")
    sheet.save(sheet_path, dpi=(DPI, DPI))
    print(f"\n✅ Feuille sauvegardée: {sheet_path}")
    
    pdf_path = os.path.join(output_dir, "aruco_echecs_A4.pdf")
    sheet.save(pdf_path, dpi=(DPI, DPI))
    print(f"✅ PDF sauvegardé: {pdf_path}")
    
    # Marqueurs individuels
    save_individual_markers(output_dir)
    
    # Résumé
    print("\n" + "=" * 60)
    print("📋 TABLE DE CORRESPONDANCE ID → PIÈCE")
    print("=" * 60)
    
    print("\n🔵 PIÈCES BLANCHES (IDs 0-15):")
    for id, piece in PIECES.items():
        if id < 16:
            print(f"   ID {id:2} = {piece['symbole']} {piece['code']:4} ({piece['nom']})")
    
    print("\n⚫ PIÈCES NOIRES (IDs 16-31):")
    for id, piece in PIECES.items():
        if id >= 16:
            print(f"   ID {id:2} = {piece['symbole']} {piece['code']:4} ({piece['nom']})")
    
    print("\n🔷 MARQUEURS DE CALIBRATION (IDs 32-35):")
    for id, calib in CALIBRATION_MARKERS.items():
        print(f"   ID {id:2} = {calib['code']:8} ({calib['nom']})")
    
    print("\n🤖 MARQUEUR ROBOT (ID 36):")
    for id, robot in ROBOT_MARKER.items():
        print(f"   ID {id:2} = {robot['code']:8} ({robot['nom']})")
    
    print("\n" + "=" * 60)
    print("📊 COMPARAISON TAILLE")
    print("=" * 60)
    print("   QR Code v1:  21×21 = 441 modules")
    print("   ArUco 4×4:    6×6  =  36 modules  ← 12× moins!")
    print("")
    print("📁 Fichiers générés dans:", output_dir)
    print("=" * 60)


if __name__ == "__main__":
    main()
