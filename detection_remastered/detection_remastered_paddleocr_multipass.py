from paddleocr import PaddleOCR
import re
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import numpy as np
import cv2
import gc
import os
import glob

# ============================================================
# CONFIGURATION
# ============================================================
MAX_DIMENSION = 1200  # Taille max (largeur ou hauteur)
CONTRAST_FACTOR = 1.5  # Facteur de contraste (1.0 = original)
SATURATION_FACTOR = 2.0  # Facteur de saturation ÉLEVÉ pour faire ressortir les rouges
BRIGHTNESS_FACTOR = 1.1  # Légère augmentation de luminosité

# Seuils pour la détection du rouge (en HSV) - équilibrés
RED_HUE_LOW1, RED_HUE_HIGH1 = 0, 12  # Rouge bas
RED_HUE_LOW2, RED_HUE_HIGH2 = 155, 180  # Rouge haut
RED_SAT_MIN = 40  # Saturation minimale (modéré)
RED_VAL_MIN = 40  # Valeur minimale (modéré)

# ============================================================
# SÉLECTION DE L'IMAGE
# ============================================================
def select_image():
    """Liste les images disponibles et demande à l'utilisateur de choisir"""
    # Répertoire du script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Chercher toutes les images dans le répertoire
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(script_dir, ext)))
    
    if not images:
        print("❌ Aucune image trouvée dans le répertoire.")
        return None
    
    # Trier par nom
    images = sorted(images)
    
    # Afficher la liste
    print("\n📂 Images disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 40)
    
    # Demander le choix
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
# FONCTIONS DE PRÉTRAITEMENT
# ============================================================
def create_output_dir(base_path):
    """Crée le dossier de traitement s'il n'existe pas"""
    output_dir = os.path.join(os.path.dirname(base_path), "traitement")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_step(img, output_dir, step_name, base_name):
    """Sauvegarde une étape de traitement"""
    filename = f"{base_name}_{step_name}.png"
    filepath = os.path.join(output_dir, filename)
    
    if isinstance(img, np.ndarray):
        # Convertir numpy array en PIL Image
        if len(img.shape) == 2:  # Grayscale
            Image.fromarray(img).save(filepath)
        else:
            Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(filepath)
    else:
        img.save(filepath)
    
    print(f"  💾 Sauvegardé: {filename}")
    return filepath

def extract_red_channel(img_np):
    """Extrait uniquement les pixels rouges de l'image"""
    # Convertir en HSV
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    
    # Masque pour le rouge (deux plages car le rouge est aux extrémités du spectre HSV)
    mask1 = cv2.inRange(hsv, (RED_HUE_LOW1, RED_SAT_MIN, RED_VAL_MIN), (RED_HUE_HIGH1, 255, 255))
    mask2 = cv2.inRange(hsv, (RED_HUE_LOW2, RED_SAT_MIN, RED_VAL_MIN), (RED_HUE_HIGH2, 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Appliquer le masque
    red_only = cv2.bitwise_and(img_np, img_np, mask=mask)
    
    # Convertir en niveaux de gris pour améliorer la détection OCR
    red_gray = cv2.cvtColor(red_only, cv2.COLOR_RGB2GRAY)
    
    # Inverser (texte noir sur fond blanc pour OCR)
    red_inverted = cv2.bitwise_not(red_gray)
    
    return red_only, red_inverted, mask

def preprocess_image(img, output_dir, base_name):
    """Applique tous les prétraitements et sauvegarde chaque étape"""
    print("\n📸 Prétraitement de l'image...")
    
    # Étape 0: Image originale
    save_step(img, output_dir, "00_original", base_name)
    
    # Étape 1: Augmenter la luminosité (aide à voir les rouges sombres)
    enhancer = ImageEnhance.Brightness(img)
    img_bright = enhancer.enhance(BRIGHTNESS_FACTOR)
    save_step(img_bright, output_dir, "01_luminosite", base_name)
    
    # Étape 2: Augmenter la saturation FORTEMENT (fait ressortir les couleurs)
    enhancer = ImageEnhance.Color(img_bright)
    img_saturated = enhancer.enhance(SATURATION_FACTOR)
    save_step(img_saturated, output_dir, "02_saturation", base_name)
    
    # Étape 3: Augmenter le contraste
    enhancer = ImageEnhance.Contrast(img_saturated)
    img_contrast = enhancer.enhance(CONTRAST_FACTOR)
    save_step(img_contrast, output_dir, "03_contraste", base_name)
    
    # Étape 4: Extraction du rouge
    img_np = np.array(img_contrast)
    red_only, red_inverted, mask = extract_red_channel(img_np)
    save_step(red_only, output_dir, "04_rouge_extrait", base_name)
    save_step(mask, output_dir, "05_masque_rouge", base_name)
    
    # Étape 5: Inverser le masque rouge (chiffres noirs sur fond blanc)
    mask_inverted = cv2.bitwise_not(mask)
    save_step(mask_inverted, output_dir, "06_masque_inverse", base_name)
    
    # Convertir en RGB (PaddleOCR attend une image 3 canaux)
    final_rgb = cv2.cvtColor(mask_inverted, cv2.COLOR_GRAY2RGB)
    save_step(final_rgb, output_dir, "07_final_rgb", base_name)
    
    # Retourner l'image traitée
    return Image.fromarray(final_rgb)

# ============================================================
# FONCTIONS DE DÉTECTION
# ============================================================
def transform_bbox_back(bbox, rotation, rotated_size, original_size):
    """Transforme les coordonnées du bbox vers l'image originale"""
    w_rot, h_rot = rotated_size
    w_orig, h_orig = original_size
    
    new_bbox = []
    for point in bbox:
        x, y = point[0], point[1]
        
        if rotation == 0:
            new_x, new_y = x, y
        elif rotation == 90:
            new_x = y
            new_y = w_rot - x
        elif rotation == 180:
            new_x = w_rot - x
            new_y = h_rot - y
        elif rotation == 270:
            new_x = h_rot - y
            new_y = x
        else:
            new_x, new_y = x, y
            
        new_bbox.append([int(new_x), int(new_y)])
    
    return new_bbox

def bbox_to_rect(bbox):
    """Convertit un polygone (4 points) en rectangle (x_min, y_min, x_max, y_max)"""
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return min(xs), min(ys), max(xs), max(ys)

def compute_iou(bbox1, bbox2):
    """Calcule l'Intersection over Union (IoU) entre deux bounding boxes"""
    # Convertir les polygones en rectangles
    x1_min, y1_min, x1_max, y1_max = bbox_to_rect(bbox1)
    x2_min, y2_min, x2_max, y2_max = bbox_to_rect(bbox2)
    
    # Calculer l'intersection
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    # Si pas d'intersection
    if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
        return 0.0
    
    # Aire de l'intersection
    inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    
    # Aires des deux rectangles
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    
    # Union = somme des aires - intersection
    union_area = area1 + area2 - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area

def boxes_overlap(bbox1, bbox2, threshold=0.1):
    """Vérifie si deux boxes se chevauchent (IoU > threshold)"""
    return compute_iou(bbox1, bbox2) > threshold

def deduplicate_detections(detections, iou_threshold=0.1):
    """Élimine les doublons basés sur le chevauchement des bounding boxes.
    Si deux boxes se chevauchent (IoU > threshold), on garde celui avec la meilleure confiance."""
    if not detections:
        return []
    
    # Trier par confiance décroissante
    sorted_dets = sorted(detections, key=lambda x: x['confiance'], reverse=True)
    
    kept = []
    for det in sorted_dets:
        is_duplicate = False
        
        for kept_det in kept:
            # Vérifier si les boxes se chevauchent
            if boxes_overlap(det['position'], kept_det['position'], iou_threshold):
                is_duplicate = True
                break
        
        if not is_duplicate:
            kept.append(det)
    
    return kept

# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================
def main():
    print("=" * 60)
    print("🔍 DÉTECTION OCR MULTI-PASSES AVEC PRÉTRAITEMENT")
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
    original_img_full = Image.open(image_path)
    
    # Redimensionnement intelligent
    width, height = original_img_full.size
    if max(width, height) > MAX_DIMENSION:
        scale_factor = MAX_DIMENSION / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        original_img = original_img_full.resize((new_width, new_height), Image.LANCZOS)
        print(f"📐 Image redimensionnée: {width}x{height} → {new_width}x{new_height}")
    else:
        original_img = original_img_full
        print(f"📐 Image conservée: {width}x{height}")
    
    # Prétraitement
    processed_img = preprocess_image(original_img, output_dir, base_name)
    
    # Initialiser PaddleOCR
    print("\n🤖 Initialisation de PaddleOCR...")
    ocr = PaddleOCR(
        use_textline_orientation=True,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        lang='en'
    )
    
    # Charger la font
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    except:
        font_small = ImageFont.load_default()
    
    # Multi-passes avec rotations
    rotations = [0, 90, 180, 270]
    all_detections = []
    
    print("\n🔄 Détection multi-passes avec rotations...")
    
    for rotation in rotations:
        print(f"\n--- Pass {rotation}° ---")
        
        if rotation == 0:
            rotated_img = processed_img.copy()
        else:
            rotated_img = processed_img.rotate(-rotation, expand=True)
        
        rotated_np = np.array(rotated_img)
        result = ocr.predict(rotated_np)
        
        if result and len(result) > 0:
            ocr_result = result[0]
            
            texts = ocr_result['rec_texts']
            scores = ocr_result['rec_scores']
            polys = ocr_result['rec_polys']
            
            print(f"  Trouvé {len(texts)} éléments")
            
            for texte, confiance, bbox in zip(texts, scores, polys):
                matches = re.findall(r'\d+(?:\.\d+)?', texte)
                
                if matches:
                    for match in matches:
                        transformed_bbox = transform_bbox_back(bbox, rotation, rotated_img.size, processed_img.size)
                        
                        all_detections.append({
                            'valeur': match,
                            'texte_complet': texte,
                            'confiance': confiance,
                            'position': transformed_bbox,
                            'rotation_source': rotation
                        })
                        print(f"    {match} (confiance: {confiance:.2f})")
        
        del rotated_img, rotated_np, result
        gc.collect()
    
    # Déduplication
    unique_detections = deduplicate_detections(all_detections)
    
    print(f"\n📊 Résultats:")
    print(f"  Détections totales: {len(all_detections)}")
    print(f"  Détections uniques: {len(unique_detections)}")
    
    # Dessiner les annotations sur l'image originale (non prétraitée)
    img_annotated = original_img.copy()
    draw = ImageDraw.Draw(img_annotated)
    
    for det in unique_detections:
        bbox = det['position']
        texte = det['valeur']
        confiance = det['confiance']
        
        points = [(int(p[0]), int(p[1])) for p in bbox]
        draw.polygon(points, outline='green', width=2)
        
        center_x = sum(p[0] for p in bbox) / len(bbox)
        top_y = min(p[1] for p in bbox)
        
        label = f"{texte} ({confiance:.2f})"
        bbox_text = draw.textbbox((0, 0), label, font=font_small)
        text_width = bbox_text[2] - bbox_text[0]
        
        draw.text((int(center_x - text_width/2), int(top_y) - 20), label, fill='green', font=font_small)
    
    # Sauvegarder le résultat final
    save_step(img_annotated, output_dir, "99_resultat_final", base_name)
    
    # Afficher les résultats
    print("\n" + "=" * 60)
    print("📋 NOMBRES DÉTECTÉS (triés)")
    print("=" * 60)
    for det in sorted(unique_detections, key=lambda x: int(x['valeur']) if x['valeur'].isdigit() else 0):
        print(f"  {det['valeur']:>3} - Confiance: {det['confiance']:.2f} (rotation: {det['rotation_source']}°)")
    
    print(f"\n✅ Total: {len(unique_detections)} nombres uniques détectés")
    print(f"📁 Résultats sauvegardés dans: {output_dir}")

if __name__ == "__main__":
    main()
