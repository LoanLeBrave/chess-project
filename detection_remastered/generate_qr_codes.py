"""
Générateur de QR Codes pour pièces d'échecs
Génère une feuille A4 avec 32 QR codes à imprimer et découper
"""

import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

# ============================================================
# CONFIGURATION DES PIÈCES
# ============================================================

# Définition des 32 pièces d'échecs avec leurs codes
PIECES = {
    # Pièces blanches (White)
    'WK': {'nom': 'Roi', 'nom_en': 'King', 'couleur': 'Blanc', 'symbole': '♔'},
    'WQ': {'nom': 'Dame', 'nom_en': 'Queen', 'couleur': 'Blanc', 'symbole': '♕'},
    'WR1': {'nom': 'Tour 1', 'nom_en': 'Rook 1', 'couleur': 'Blanc', 'symbole': '♖'},
    'WR2': {'nom': 'Tour 2', 'nom_en': 'Rook 2', 'couleur': 'Blanc', 'symbole': '♖'},
    'WB1': {'nom': 'Fou 1', 'nom_en': 'Bishop 1', 'couleur': 'Blanc', 'symbole': '♗'},
    'WB2': {'nom': 'Fou 2', 'nom_en': 'Bishop 2', 'couleur': 'Blanc', 'symbole': '♗'},
    'WN1': {'nom': 'Cavalier 1', 'nom_en': 'Knight 1', 'couleur': 'Blanc', 'symbole': '♘'},
    'WN2': {'nom': 'Cavalier 2', 'nom_en': 'Knight 2', 'couleur': 'Blanc', 'symbole': '♘'},
    'WP1': {'nom': 'Pion 1', 'nom_en': 'Pawn 1', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP2': {'nom': 'Pion 2', 'nom_en': 'Pawn 2', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP3': {'nom': 'Pion 3', 'nom_en': 'Pawn 3', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP4': {'nom': 'Pion 4', 'nom_en': 'Pawn 4', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP5': {'nom': 'Pion 5', 'nom_en': 'Pawn 5', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP6': {'nom': 'Pion 6', 'nom_en': 'Pawn 6', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP7': {'nom': 'Pion 7', 'nom_en': 'Pawn 7', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP8': {'nom': 'Pion 8', 'nom_en': 'Pawn 8', 'couleur': 'Blanc', 'symbole': '♙'},
    
    # Pièces noires (Black)
    'BK': {'nom': 'Roi', 'nom_en': 'King', 'couleur': 'Noir', 'symbole': '♚'},
    'BQ': {'nom': 'Dame', 'nom_en': 'Queen', 'couleur': 'Noir', 'symbole': '♛'},
    'BR1': {'nom': 'Tour 1', 'nom_en': 'Rook 1', 'couleur': 'Noir', 'symbole': '♜'},
    'BR2': {'nom': 'Tour 2', 'nom_en': 'Rook 2', 'couleur': 'Noir', 'symbole': '♜'},
    'BB1': {'nom': 'Fou 1', 'nom_en': 'Bishop 1', 'couleur': 'Noir', 'symbole': '♝'},
    'BB2': {'nom': 'Fou 2', 'nom_en': 'Bishop 2', 'couleur': 'Noir', 'symbole': '♝'},
    'BN1': {'nom': 'Cavalier 1', 'nom_en': 'Knight 1', 'couleur': 'Noir', 'symbole': '♞'},
    'BN2': {'nom': 'Cavalier 2', 'nom_en': 'Knight 2', 'couleur': 'Noir', 'symbole': '♞'},
    'BP1': {'nom': 'Pion 1', 'nom_en': 'Pawn 1', 'couleur': 'Noir', 'symbole': '♟'},
    'BP2': {'nom': 'Pion 2', 'nom_en': 'Pawn 2', 'couleur': 'Noir', 'symbole': '♟'},
    'BP3': {'nom': 'Pion 3', 'nom_en': 'Pawn 3', 'couleur': 'Noir', 'symbole': '♟'},
    'BP4': {'nom': 'Pion 4', 'nom_en': 'Pawn 4', 'couleur': 'Noir', 'symbole': '♟'},
    'BP5': {'nom': 'Pion 5', 'nom_en': 'Pawn 5', 'couleur': 'Noir', 'symbole': '♟'},
    'BP6': {'nom': 'Pion 6', 'nom_en': 'Pawn 6', 'couleur': 'Noir', 'symbole': '♟'},
    'BP7': {'nom': 'Pion 7', 'nom_en': 'Pawn 7', 'couleur': 'Noir', 'symbole': '♟'},
    'BP8': {'nom': 'Pion 8', 'nom_en': 'Pawn 8', 'couleur': 'Noir', 'symbole': '♟'},
}

# ============================================================
# CONFIGURATION DE LA FEUILLE
# ============================================================

# Taille A4 en pixels (300 DPI)
DPI = 300
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
A4_WIDTH_PX = int(A4_WIDTH_MM * DPI / 25.4)  # ~2480px
A4_HEIGHT_PX = int(A4_HEIGHT_MM * DPI / 25.4)  # ~3508px

# Configuration de la grille (4 colonnes x 8 lignes = 32 QR codes)
COLS = 4
ROWS = 8

# Marges en mm
MARGIN_MM = 10
MARGIN_PX = int(MARGIN_MM * DPI / 25.4)

# Taille de chaque cellule
CELL_WIDTH = (A4_WIDTH_PX - 2 * MARGIN_PX) // COLS
CELL_HEIGHT = (A4_HEIGHT_PX - 2 * MARGIN_PX) // ROWS

# Taille du QR code dans la cellule (en pixels)
QR_SIZE = min(CELL_WIDTH, CELL_HEIGHT) - 60  # Marge pour le texte

# ============================================================
# FONCTIONS
# ============================================================

def generate_qr_code(data, size):
    """Génère un QR code MINIMAL pour les données spécifiées"""
    qr = qrcode.QRCode(
        version=1,  # Taille minimale (21x21 modules) - FORCÉ
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Correction minimale (7%) = QR plus petit
        box_size=10,
        border=1,  # Bordure minimale (1 module au lieu de 4)
    )
    qr.add_data(data, optimize=0)  # Pas d'optimisation pour garder version 1
    qr.make(fit=False)  # Ne PAS augmenter la version automatiquement
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((size, size), Image.NEAREST)
    
    return qr_img


def create_qr_sheet():
    """Crée une feuille A4 avec tous les QR codes"""
    
    # Créer l'image blanche A4
    sheet = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), 'white')
    draw = ImageDraw.Draw(sheet)
    
    # Charger la police
    try:
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_code = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_label = ImageFont.load_default()
        font_code = ImageFont.load_default()
    
    # Liste des codes dans l'ordre
    piece_codes = list(PIECES.keys())
    
    print(f"📐 Génération de {len(piece_codes)} QR codes...")
    print(f"   Format: A4 ({A4_WIDTH_MM}x{A4_HEIGHT_MM}mm) @ {DPI} DPI")
    print(f"   Grille: {COLS} colonnes x {ROWS} lignes")
    print(f"   Taille QR: ~{QR_SIZE * 25.4 / DPI:.1f}mm")
    
    for idx, code in enumerate(piece_codes):
        piece = PIECES[code]
        
        # Calculer la position dans la grille
        col = idx % COLS
        row = idx // COLS
        
        # Position du coin supérieur gauche de la cellule
        cell_x = MARGIN_PX + col * CELL_WIDTH
        cell_y = MARGIN_PX + row * CELL_HEIGHT
        
        # Centre de la cellule
        center_x = cell_x + CELL_WIDTH // 2
        center_y = cell_y + CELL_HEIGHT // 2 - 15  # Décalé vers le haut pour le texte
        
        # Générer le QR code
        qr_img = generate_qr_code(code, QR_SIZE)
        
        # Coller le QR code centré
        qr_x = center_x - QR_SIZE // 2
        qr_y = center_y - QR_SIZE // 2
        sheet.paste(qr_img, (qr_x, qr_y))
        
        # Dessiner le cadre de découpe (pointillés)
        for i in range(0, CELL_WIDTH, 10):
            if i % 20 < 10:
                draw.line([(cell_x + i, cell_y), (cell_x + i + 5, cell_y)], fill='lightgray', width=1)
                draw.line([(cell_x + i, cell_y + CELL_HEIGHT), (cell_x + i + 5, cell_y + CELL_HEIGHT)], fill='lightgray', width=1)
        for i in range(0, CELL_HEIGHT, 10):
            if i % 20 < 10:
                draw.line([(cell_x, cell_y + i), (cell_x, cell_y + i + 5)], fill='lightgray', width=1)
                draw.line([(cell_x + CELL_WIDTH, cell_y + i), (cell_x + CELL_WIDTH, cell_y + i + 5)], fill='lightgray', width=1)
        
        # Ajouter le texte sous le QR code
        label = f"{piece['symbole']} {code}"
        text_bbox = draw.textbbox((0, 0), label, font=font_label)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = center_x - text_width // 2
        text_y = qr_y + QR_SIZE + 5
        draw.text((text_x, text_y), label, fill='black', font=font_label)
        
        # Ajouter la description
        desc = f"{piece['couleur']} - {piece['nom']}"
        desc_bbox = draw.textbbox((0, 0), desc, font=font_code)
        desc_width = desc_bbox[2] - desc_bbox[0]
        desc_x = center_x - desc_width // 2
        desc_y = text_y + 28
        draw.text((desc_x, desc_y), desc, fill='gray', font=font_code)
        
        print(f"  ✓ {code}: {piece['symbole']} {piece['couleur']} {piece['nom']}")
    
    return sheet


def save_individual_qr_codes(output_dir):
    """Sauvegarde aussi chaque QR code individuellement"""
    individual_dir = os.path.join(output_dir, "qr_individuels")
    os.makedirs(individual_dir, exist_ok=True)
    
    print(f"\n💾 Sauvegarde des QR codes individuels dans {individual_dir}...")
    
    for code, piece in PIECES.items():
        qr_img = generate_qr_code(code, 200)
        filepath = os.path.join(individual_dir, f"{code}.png")
        qr_img.save(filepath)
    
    print(f"  ✓ {len(PIECES)} QR codes individuels sauvegardés")


def main():
    print("=" * 60)
    print("♟️  GÉNÉRATEUR DE QR CODES POUR PIÈCES D'ÉCHECS")
    print("=" * 60)
    
    # Répertoire de sortie
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "qr_codes")
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer la feuille A4
    print("\n📄 Création de la feuille A4...")
    sheet = create_qr_sheet()
    
    # Sauvegarder la feuille
    sheet_path = os.path.join(output_dir, "qr_codes_echecs_A4.png")
    sheet.save(sheet_path, dpi=(DPI, DPI))
    print(f"\n✅ Feuille sauvegardée: {sheet_path}")
    
    # Sauvegarder aussi en PDF pour impression facile
    pdf_path = os.path.join(output_dir, "qr_codes_echecs_A4.pdf")
    sheet.save(pdf_path, dpi=(DPI, DPI))
    print(f"✅ PDF sauvegardé: {pdf_path}")
    
    # Sauvegarder les QR codes individuels
    save_individual_qr_codes(output_dir)
    
    # Résumé
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ DES CODES")
    print("=" * 60)
    print("\n🔵 PIÈCES BLANCHES:")
    for code, piece in PIECES.items():
        if code.startswith('W'):
            print(f"   {code:4} = {piece['symbole']} {piece['nom']}")
    
    print("\n⚫ PIÈCES NOIRES:")
    for code, piece in PIECES.items():
        if code.startswith('B'):
            print(f"   {code:4} = {piece['symbole']} {piece['nom']}")
    
    print("\n" + "=" * 60)
    print("📁 Fichiers générés dans:", output_dir)
    print("   - qr_codes_echecs_A4.png (pour visualiser)")
    print("   - qr_codes_echecs_A4.pdf (pour imprimer)")
    print("   - qr_individuels/ (QR codes séparés)")
    print("=" * 60)


if __name__ == "__main__":
    main()
