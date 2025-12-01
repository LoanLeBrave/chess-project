"""
Détection OCR BRUTE - Sans filtres d'image
PaddleOCR sur l'image originale redimensionnée uniquement.
"""

from paddleocr import PaddleOCR
import re
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import gc
import os
import glob

# ============================================================
# CONFIGURATION
# ============================================================
MAX_DIMENSION = 1200  # Taille max (largeur ou hauteur)

print("🔧 Mode: IMAGE BRUTE (sans filtres)")

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
    output_dir = os.path.join(os.path.dirname(base_path), "traitement_brut")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_step(img, output_dir, step_name, base_name):
    """Sauvegarde une étape de traitement"""
    filename = f"{base_name}_{step_name}.png"
    filepath = os.path.join(output_dir, filename)
    
    if isinstance(img, np.ndarray):
        Image.fromarray(img).save(filepath)
    else:
        img.save(filepath)
    
    print(f"  💾 Sauvegardé: {filename}")
    return filepath

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
    """Convertit un polygone en rectangle"""
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return min(xs), min(ys), max(xs), max(ys)

def compute_iou(bbox1, bbox2):
    """Calcule l'IoU entre deux bounding boxes"""
    x1_min, y1_min, x1_max, y1_max = bbox_to_rect(bbox1)
    x2_min, y2_min, x2_max, y2_max = bbox_to_rect(bbox2)
    
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
        return 0.0
    
    inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = area1 + area2 - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area

def boxes_overlap(bbox1, bbox2, threshold=0.1):
    """Vérifie si deux boxes se chevauchent"""
    return compute_iou(bbox1, bbox2) > threshold

def deduplicate_detections(detections, iou_threshold=0.1):
    """Élimine les doublons basés sur le chevauchement des bounding boxes."""
    if not detections:
        return []
    
    sorted_dets = sorted(detections, key=lambda x: x['confiance'], reverse=True)
    
    kept = []
    for det in sorted_dets:
        is_duplicate = False
        for kept_det in kept:
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
    print("🔍 DÉTECTION OCR BRUTE (sans filtres)")
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
    
    # Redimensionnement intelligent (seul traitement)
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
    
    # Sauvegarder l'image d'entrée
    save_step(original_img, output_dir, "00_input", base_name)
    
    # Convertir en numpy pour PaddleOCR
    img_np = np.array(original_img)
    
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
            rotated_img = original_img.copy()
        else:
            rotated_img = original_img.rotate(-rotation, expand=True)
        
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
                        transformed_bbox = transform_bbox_back(bbox, rotation, rotated_img.size, original_img.size)
                        
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
    
    # Dessiner les annotations
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
