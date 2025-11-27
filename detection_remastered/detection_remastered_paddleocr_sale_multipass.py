from paddleocr import PaddleOCR
import re
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Initialiser PaddleOCR avec des paramètres optimisés pour la détection
ocr = PaddleOCR(
    use_textline_orientation=True,  # Gère les rotations des lignes de texte
    use_doc_orientation_classify=False,  # Désactive la rotation automatique du document
    use_doc_unwarping=False,  # Désactive la correction de perspective
    lang='en'
)

# Lecture de l'image
image_path = "/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/photo_noirblanc.jpg"

# Charger l'image originale
original_img = Image.open(image_path)

# Charger la font
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
except:
    font = ImageFont.load_default()
    font_small = font


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


def deduplicate_detections(detections, distance_threshold=50):
    """Élimine les doublons basés uniquement sur la position (ignore la valeur).
    Garde la détection avec la meilleure confiance pour chaque zone."""
    if not detections:
        return []
    
    # Trier par confiance décroissante
    sorted_dets = sorted(detections, key=lambda x: x['confiance'], reverse=True)
    
    kept = []
    for det in sorted_dets:
        center1 = np.mean(det['position'], axis=0)
        is_duplicate = False
        
        for kept_det in kept:
            # Calculer la distance entre les centres (sans vérifier la valeur)
            center2 = np.mean(kept_det['position'], axis=0)
            distance = np.linalg.norm(center1 - center2)
            
            # Si les centres sont proches, c'est un doublon
            if distance < distance_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            kept.append(det)
    
    return kept


# Stratégie: faire plusieurs passes avec différentes rotations de l'image
# puis fusionner les résultats
rotations = [0, 90, 180, 270]  # Degrés de rotation à tester

all_detections = []

print("=== Détection multi-passes avec rotations ===\n")

for rotation in rotations:
    print(f"--- Pass avec rotation de {rotation}° ---")
    
    # Tourner l'image
    if rotation == 0:
        rotated_img = original_img.copy()
    else:
        rotated_img = original_img.rotate(-rotation, expand=True)  # -rotation car PIL tourne dans le sens anti-horaire
    
    # Convertir en numpy pour PaddleOCR
    rotated_np = np.array(rotated_img)
    
    # Faire la détection
    result = ocr.predict(rotated_np)
    
    if result and len(result) > 0:
        ocr_result = result[0]
        
        texts = ocr_result['rec_texts']
        scores = ocr_result['rec_scores']
        polys = ocr_result['rec_polys']
        
        print(f"  Trouvé {len(texts)} éléments")
        
        for texte, confiance, bbox in zip(texts, scores, polys):
            # Extraire les nombres
            matches = re.findall(r'\d+(?:\.\d+)?', texte)
            
            if matches:
                for match in matches:
                    # Transformer les coordonnées vers l'image originale
                    transformed_bbox = transform_bbox_back(bbox, rotation, rotated_img.size, original_img.size)
                    
                    all_detections.append({
                        'valeur': match,
                        'texte_complet': texte,
                        'confiance': confiance,
                        'position': transformed_bbox,
                        'rotation_source': rotation
                    })
                    print(f"    {match} (confiance: {confiance:.2f})")

# Dédupliquer les résultats
unique_detections = deduplicate_detections(all_detections)

print(f"\n=== Résultats après fusion ===")
print(f"Détections totales: {len(all_detections)}")
print(f"Détections uniques: {len(unique_detections)}")

# Dessiner sur l'image originale
img_annotated = original_img.copy()
draw = ImageDraw.Draw(img_annotated)

for det in unique_detections:
    bbox = det['position']
    texte = det['valeur']
    confiance = det['confiance']
    
    # Dessiner le box rouge
    points = [(int(p[0]), int(p[1])) for p in bbox]
    draw.polygon(points, outline='red', width=2)
    
    # Calculer le centre
    center_x = sum(p[0] for p in bbox) / len(bbox)
    top_y = min(p[1] for p in bbox)
    
    # Label
    label = f"{texte} ({confiance:.2f})"
    bbox_text = draw.textbbox((0, 0), label, font=font_small)
    text_width = bbox_text[2] - bbox_text[0]
    
    draw.text((int(center_x - text_width/2), int(top_y) - 20), label, fill='red', font=font_small)

# Sauvegarder
img_annotated.save('/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_sale_detecte_multipass.png')

print("\n=== Nombres détectés (uniques) ===")
for det in sorted(unique_detections, key=lambda x: int(x['valeur']) if x['valeur'].isdigit() else 0):
    print(f"{det['valeur']} - Confiance: {det['confiance']:.2f} (rotation source: {det['rotation_source']}°)")

print(f"\nTotal: {len(unique_detections)} nombres uniques détectés")
