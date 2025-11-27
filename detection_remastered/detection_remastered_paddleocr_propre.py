from paddleocr import PaddleOCR
import re
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Initialiser PaddleOCR avec détection d'angle
ocr = PaddleOCR(
    use_textline_orientation=True,  # Gère les rotations
    lang='en'
)

# Lecture de l'image
image_path = "/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_propre.jpg"
result = ocr.predict(image_path)

# Charger la font
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except:
    font = ImageFont.load_default()

nombres_avec_pos = []

# Le nouveau format PaddleOCR retourne un OCRResult object
if result and len(result) > 0:
    ocr_result = result[0]
    
    # IMPORTANT: Les coordonnées sont relatives à l'image prétraitée par PaddleOCR
    # Il faut utiliser l'image de sortie du preprocesseur pour dessiner les annotations
    preprocessed_img = ocr_result['doc_preprocessor_res']['output_img']
    
    # Convertir le numpy array en PIL Image
    img = Image.fromarray(preprocessed_img)
    draw = ImageDraw.Draw(img)
    
    # Extraire les données depuis l'OCRResult
    texts = ocr_result['rec_texts']
    scores = ocr_result['rec_scores']
    polys = ocr_result['rec_polys']
    
    # Traiter chaque détection
    for i, (texte, confiance, bbox) in enumerate(zip(texts, scores, polys)):
        # Extraire les nombres du texte
        matches = re.findall(r'\d+(?:\.\d+)?', texte)
        
        if matches:
            for match in matches:
                nombres_avec_pos.append({
                    'valeur': match,
                    'texte_complet': texte,
                    'confiance': confiance,
                    'position': bbox.tolist()    
                })
            
            # Dessiner le box rouge
            points = [(int(p[0]), int(p[1])) for p in bbox]
            draw.polygon(points, outline='red', width=2)
            
            # Calculer le centre du polygone pour placer le label
            center_x = sum(p[0] for p in bbox) / len(bbox)
            center_y = sum(p[1] for p in bbox) / len(bbox)
            
            # Trouver le point le plus haut du polygone pour placer le label au-dessus
            top_y = min(p[1] for p in bbox)
            
            # Afficher le texte détecté au centre horizontal, au-dessus du texte
            label = f"{texte} ({confiance:.2f})"
            # Obtenir la taille du texte pour le centrer
            bbox_text = draw.textbbox((0, 0), label, font=font)
            text_width = bbox_text[2] - bbox_text[0]
            
            draw.text((int(center_x - text_width/2), int(top_y) - 25), label, fill='red', font=font)

    # Sauvegarder l'image annotée (image prétraitée avec annotations)
    img.save('/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_propre_detecte_paddle.png')
    
    # Optionnel: sauvegarder aussi l'image prétraitée sans annotations pour comparaison
    Image.fromarray(ocr_result['doc_preprocessor_res']['output_img']).save('/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_propre_preprocessed.png')

print("Nombres détectés:")
for item in nombres_avec_pos:
    print(f"{item['valeur']} - Confiance: {item['confiance']:.2f}")