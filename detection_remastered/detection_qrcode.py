"""
Détection de QR Codes pour pièces d'échecs
Version QR Code du script de détection (remplace PaddleOCR)
Beaucoup plus rapide et fiable que l'OCR

Utilise cv2.QRCodeDetector (intégré à OpenCV, pas de dépendance externe)
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import os
import glob
import time

# ============================================================
# CONFIGURATION
# ============================================================
MAX_DIMENSION = 1500  # Taille max (peut être plus grand car QR est plus rapide)

# Dictionnaire des pièces pour affichage
PIECES = {
    # Pièces blanches
    'WK': {'nom': 'Roi', 'couleur': 'Blanc', 'symbole': '♔'},
    'WQ': {'nom': 'Dame', 'couleur': 'Blanc', 'symbole': '♕'},
    'WR1': {'nom': 'Tour 1', 'couleur': 'Blanc', 'symbole': '♖'},
    'WR2': {'nom': 'Tour 2', 'couleur': 'Blanc', 'symbole': '♖'},
    'WB1': {'nom': 'Fou 1', 'couleur': 'Blanc', 'symbole': '♗'},
    'WB2': {'nom': 'Fou 2', 'couleur': 'Blanc', 'symbole': '♗'},
    'WN1': {'nom': 'Cavalier 1', 'couleur': 'Blanc', 'symbole': '♘'},
    'WN2': {'nom': 'Cavalier 2', 'couleur': 'Blanc', 'symbole': '♘'},
    'WP1': {'nom': 'Pion 1', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP2': {'nom': 'Pion 2', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP3': {'nom': 'Pion 3', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP4': {'nom': 'Pion 4', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP5': {'nom': 'Pion 5', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP6': {'nom': 'Pion 6', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP7': {'nom': 'Pion 7', 'couleur': 'Blanc', 'symbole': '♙'},
    'WP8': {'nom': 'Pion 8', 'couleur': 'Blanc', 'symbole': '♙'},
    # Pièces noires
    'BK': {'nom': 'Roi', 'couleur': 'Noir', 'symbole': '♚'},
    'BQ': {'nom': 'Dame', 'couleur': 'Noir', 'symbole': '♛'},
    'BR1': {'nom': 'Tour 1', 'couleur': 'Noir', 'symbole': '♜'},
    'BR2': {'nom': 'Tour 2', 'couleur': 'Noir', 'symbole': '♜'},
    'BB1': {'nom': 'Fou 1', 'couleur': 'Noir', 'symbole': '♝'},
    'BB2': {'nom': 'Fou 2', 'couleur': 'Noir', 'symbole': '♝'},
    'BN1': {'nom': 'Cavalier 1', 'couleur': 'Noir', 'symbole': '♞'},
    'BN2': {'nom': 'Cavalier 2', 'couleur': 'Noir', 'symbole': '♞'},
    'BP1': {'nom': 'Pion 1', 'couleur': 'Noir', 'symbole': '♟'},
    'BP2': {'nom': 'Pion 2', 'couleur': 'Noir', 'symbole': '♟'},
    'BP3': {'nom': 'Pion 3', 'couleur': 'Noir', 'symbole': '♟'},
    'BP4': {'nom': 'Pion 4', 'couleur': 'Noir', 'symbole': '♟'},
    'BP5': {'nom': 'Pion 5', 'couleur': 'Noir', 'symbole': '♟'},
    'BP6': {'nom': 'Pion 6', 'couleur': 'Noir', 'symbole': '♟'},
    'BP7': {'nom': 'Pion 7', 'couleur': 'Noir', 'symbole': '♟'},
    'BP8': {'nom': 'Pion 8', 'couleur': 'Noir', 'symbole': '♟'},
}

# ============================================================
# SÉLECTION DE L'IMAGE
# ============================================================
def select_image():
    """Liste les images disponibles et demande à l'utilisateur de choisir"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(script_dir, ext)))
    
    if not images:
        print("❌ Aucune image trouvée dans le répertoire.")
        return None
    
    images = sorted(images)
    
    print("\n📂 Images disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("\n🔢 Entrez le numéro de l'image (ou 'q' pour quitter): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(images):
                return images[choice_num - 1]
            else:
                print(f"⚠️  Veuillez entrer un numéro entre 1 et {len(images)}")
        except ValueError:
            print("⚠️  Veuillez entrer un numéro valide")

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def create_output_dir(base_path):
    """Crée le dossier de traitement s'il n'existe pas"""
    output_dir = os.path.join(os.path.dirname(base_path), "traitement_qr")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_step(img, output_dir, step_name, base_name):
    """Sauvegarde une étape de traitement"""
    filename = f"{base_name}_{step_name}.png"
    filepath = os.path.join(output_dir, filename)
    
    if isinstance(img, np.ndarray):
        if len(img.shape) == 2:
            Image.fromarray(img).save(filepath)
        else:
            Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(filepath)
    else:
        img.save(filepath)
    
    print(f"  💾 Sauvegardé: {filename}")
    return filepath

def get_piece_info(code):
    """Retourne les informations d'une pièce à partir de son code"""
    if code in PIECES:
        return PIECES[code]
    return {'nom': 'Inconnu', 'couleur': '?', 'symbole': '?'}

# ============================================================
# DÉTECTION QR CODES
# ============================================================
def detect_qr_codes(img_np):
    """
    Détecte tous les QR codes dans une image en utilisant OpenCV.
    Retourne une liste de détections avec valeur, position, etc.
    """
    detections = []
    
    # Conversion en niveaux de gris pour améliorer la détection
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    # Créer le détecteur QR d'OpenCV
    qr_detector = cv2.QRCodeDetector()
    
    # Détecter et décoder tous les QR codes
    # detectAndDecodeMulti retourne: (retval, decoded_info, points, straight_qrcode)
    retval, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(gray)
    
    if retval and points is not None:
        for i, (value, polygon) in enumerate(zip(decoded_info, points)):
            if not value:  # Skip si pas décodé
                continue
            
            # Convertir le polygone en liste de points
            position = [[int(p[0]), int(p[1])] for p in polygon]
            
            # Calculer le rectangle englobant
            xs = [p[0] for p in position]
            ys = [p[1] for p in position]
            rect = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            
            # Centre du QR code
            center = (sum(xs) / len(xs), sum(ys) / len(ys))
            
            # Informations de la pièce
            piece_info = get_piece_info(value)
            
            detections.append({
                'code': value,
                'piece': piece_info,
                'position': position,
                'rect': rect,
                'center': center,
                'type': 'QRCODE'
            })
    
    return detections

def detect_with_preprocessing(img_np):
    """
    Tente la détection avec différents prétraitements si nécessaire.
    Plus robuste pour les images difficiles.
    """
    all_detections = []
    seen_codes = set()
    
    # Pass 1: Image originale
    print("  🔍 Pass 1: Image originale...")
    detections = detect_qr_codes(img_np)
    for det in detections:
        if det['code'] not in seen_codes:
            det['pass'] = 'original'
            all_detections.append(det)
            seen_codes.add(det['code'])
    print(f"     Trouvé: {len(detections)} QR codes")
    
    # Pass 2: Contraste amélioré (si pas tous trouvés)
    if len(all_detections) < 32:
        print("  🔍 Pass 2: Contraste amélioré...")
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY) if len(img_np.shape) == 3 else img_np
        enhanced = cv2.equalizeHist(gray)
        enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        
        detections = detect_qr_codes(enhanced_rgb)
        new_count = 0
        for det in detections:
            if det['code'] not in seen_codes:
                det['pass'] = 'enhanced'
                all_detections.append(det)
                seen_codes.add(det['code'])
                new_count += 1
        print(f"     Nouveaux: {new_count} QR codes")
    
    # Pass 3: Binarisation adaptative (si toujours pas tous trouvés)
    if len(all_detections) < 32:
        print("  🔍 Pass 3: Binarisation adaptative...")
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY) if len(img_np.shape) == 3 else img_np
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        binary_rgb = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
        
        detections = detect_qr_codes(binary_rgb)
        new_count = 0
        for det in detections:
            if det['code'] not in seen_codes:
                det['pass'] = 'binary'
                all_detections.append(det)
                seen_codes.add(det['code'])
                new_count += 1
        print(f"     Nouveaux: {new_count} QR codes")
    
    return all_detections

# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================
def main():
    print("=" * 60)
    print("🔍 DÉTECTION QR CODES - PIÈCES D'ÉCHECS")
    print("   (Alternative rapide à PaddleOCR)")
    print("=" * 60)
    
    # Sélection de l'image
    print("\n📂 Sélectionnez une image...")
    image_path = select_image()
    
    if not image_path:
        print("❌ Aucune image sélectionnée. Arrêt du programme.")
        return
    
    print(f"✅ Image sélectionnée: {os.path.basename(image_path)}")
    
    # Créer le dossier de sortie
    output_dir = create_output_dir(image_path)
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    print(f"📁 Dossier de sortie: {output_dir}")
    
    # Charger l'image
    original_img = Image.open(image_path)
    
    # Redimensionnement si nécessaire
    width, height = original_img.size
    if max(width, height) > MAX_DIMENSION:
        scale_factor = MAX_DIMENSION / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        original_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f"📐 Image redimensionnée: {width}x{height} → {new_width}x{new_height}")
    else:
        print(f"📐 Image conservée: {width}x{height}")
    
    # Sauvegarder l'original
    save_step(original_img, output_dir, "00_original", base_name)
    
    # Conversion en numpy array
    img_np = np.array(original_img)
    
    # Détection des QR codes
    print("\n🔄 Détection des QR codes...")
    start_time = time.time()
    
    detections = detect_with_preprocessing(img_np)
    
    detection_time = time.time() - start_time
    print(f"\n⏱️  Temps de détection: {detection_time:.3f} secondes")
    
    # Charger la font
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        font_small = ImageFont.load_default()
        font_large = ImageFont.load_default()
    
    # Dessiner les annotations
    img_annotated = original_img.copy()
    draw = ImageDraw.Draw(img_annotated)
    
    for det in detections:
        position = det['position']
        code = det['code']
        piece = det['piece']
        center = det['center']
        
        # Dessiner le contour du QR code
        points = [(int(p[0]), int(p[1])) for p in position]
        
        # Couleur selon la pièce (vert pour blanc, bleu pour noir)
        if code.startswith('W'):
            color = (0, 200, 0)  # Vert pour blancs
        elif code.startswith('B'):
            color = (0, 100, 255)  # Bleu pour noirs
        else:
            color = (255, 165, 0)  # Orange pour inconnu
        
        # Dessiner le polygone
        draw.polygon(points, outline=color, width=3)
        
        # Dessiner le centre
        cx, cy = int(center[0]), int(center[1])
        draw.ellipse([cx-5, cy-5, cx+5, cy+5], fill=color)
        
        # Label avec le code et le symbole
        label = f"{piece['symbole']} {code}"
        text_bbox = draw.textbbox((0, 0), label, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position du texte (au-dessus du QR code)
        top_y = min(p[1] for p in position)
        text_x = int(center[0] - text_width / 2)
        text_y = int(top_y) - text_height - 10
        
        # Fond pour le texte
        draw.rectangle(
            [text_x - 3, text_y - 3, text_x + text_width + 3, text_y + text_height + 3],
            fill='white',
            outline=color
        )
        draw.text((text_x, text_y), label, fill=color, font=font_large)
    
    # Sauvegarder le résultat
    save_step(img_annotated, output_dir, "99_resultat_final", base_name)
    
    # Afficher les résultats
    print("\n" + "=" * 60)
    print("📋 PIÈCES DÉTECTÉES")
    print("=" * 60)
    
    # Trier par couleur puis par type de pièce
    whites = [d for d in detections if d['code'].startswith('W')]
    blacks = [d for d in detections if d['code'].startswith('B')]
    others = [d for d in detections if not d['code'].startswith('W') and not d['code'].startswith('B')]
    
    if whites:
        print("\n🔵 PIÈCES BLANCHES:")
        for det in sorted(whites, key=lambda x: x['code']):
            piece = det['piece']
            center = det['center']
            print(f"   {det['code']:4} {piece['symbole']} {piece['nom']:12} @ ({center[0]:.0f}, {center[1]:.0f})")
    
    if blacks:
        print("\n⚫ PIÈCES NOIRES:")
        for det in sorted(blacks, key=lambda x: x['code']):
            piece = det['piece']
            center = det['center']
            print(f"   {det['code']:4} {piece['symbole']} {piece['nom']:12} @ ({center[0]:.0f}, {center[1]:.0f})")
    
    if others:
        print("\n❓ AUTRES QR CODES:")
        for det in others:
            print(f"   {det['code']} @ ({det['center'][0]:.0f}, {det['center'][1]:.0f})")
    
    # Statistiques
    print("\n" + "=" * 60)
    print("📊 STATISTIQUES")
    print("=" * 60)
    print(f"  Total détecté: {len(detections)} QR codes")
    print(f"  Pièces blanches: {len(whites)}/16")
    print(f"  Pièces noires: {len(blacks)}/16")
    print(f"  Temps de détection: {detection_time:.3f}s")
    
    # Pièces manquantes
    all_codes = set(PIECES.keys())
    detected_codes = set(d['code'] for d in detections)
    missing = all_codes - detected_codes
    
    if missing:
        print(f"\n⚠️  Pièces manquantes ({len(missing)}):")
        for code in sorted(missing):
            piece = PIECES[code]
            print(f"     {code} - {piece['symbole']} {piece['couleur']} {piece['nom']}")
    else:
        print("\n✅ Toutes les 32 pièces ont été détectées!")
    
    print(f"\n📁 Résultats sauvegardés dans: {output_dir}")


if __name__ == "__main__":
    main()
