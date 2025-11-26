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
result = ocr.predict(f"/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_sale.png")

img = Image.open('/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_sale.png')
draw = ImageDraw.Draw(img)

# Charger la font
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except:
    font = ImageFont.load_default()

nombres_avec_pos = []

# Le nouveau format PaddleOCR retourne un OCRResult object
if result and len(result) > 0:
    ocr_result = result[0]
    
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
            
            # Position en haut à gauche
            min_x = min(p[0] for p in bbox)
            min_y = min(p[1] for p in bbox)
            
            # Afficher le texte détecté
            label = f"{texte} ({confiance:.2f})"
            draw.text((int(min_x), int(min_y) - 25), label, fill='red', font=font)

# Sauvegarder l'image annotée
img.save('/home/loan/Documents/Junia/AP5/projet_chess/chess-project/detection_remastered/image_sale_detecte_paddle.png')

print("Nombres détectés:")
for item in nombres_avec_pos:
    print(f"{item['valeur']} - Confiance: {item['confiance']:.2f}")