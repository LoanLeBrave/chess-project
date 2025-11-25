from paddleocr import PaddleOCR
import re
from PIL import Image, ImageDraw, ImageFont

ocr = PaddleOCR(use_textline_orientation=True, lang='en')
result = ocr.ocr('image_2.jpg')

img = Image.open('image_2.jpg')
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except:
    font = ImageFont.load_default()

# Seuil de confiance
SEUIL = 0.30

nombres_avec_pos = []

# Nouveau format PaddleOCR : résultat est une liste avec un objet OCRResult
if result and len(result) > 0:
    page_result = result[0]
    
    # Accéder aux attributs rec_texts, rec_scores, rec_polys
    for texte, confiance, bbox in zip(page_result['rec_texts'], 
                                       page_result['rec_scores'], 
                                       page_result['rec_polys']):
        
        if confiance < SEUIL:
            continue
        
        matches = re.findall(r'\d+(?:\.\d+)?', texte)
        
        if matches:
            for match in matches:
                nombres_avec_pos.append({
                    'valeur': match,
                    'texte_complet': texte,
                    'confiance': confiance,
                })
            
            # Dessiner le box rouge
            points = [(int(p[0]), int(p[1])) for p in bbox]
            draw.polygon(points, outline='red', width=2)
            
            min_x = min(p[0] for p in bbox)
            min_y = min(p[1] for p in bbox)
            
            label = f"{texte} ({confiance:.2f})"
            draw.text((int(min_x), int(min_y) - 25), label, fill='red', font=font)

img.save('image_2_detecte.jpg')

print("Nombres détectés:")
for item in nombres_avec_pos:
    print(f"{item['valeur']} - Confiance: {item['confiance']:.2f}")