import easyocr
import re
from PIL import Image, ImageDraw, ImageFont

reader = easyocr.Reader(['en'])
result = reader.readtext('image_2.jpg')

img = Image.open('image_2.jpg')
draw = ImageDraw.Draw(img)

# Essayer de charger une font, sinon utiliser la default
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except:
    font = ImageFont.load_default()

nombres_avec_pos = []
for detection in result:
    bbox, texte, confiance = detection
    matches = re.findall(r'\d+(?:\.\d+)?', texte)
    
    if matches:
        for match in matches:
            nombres_avec_pos.append({
                'valeur': match,
                'texte_complet': texte,
                'confiance': confiance,
                'position': bbox    
            })
        
        # Dessiner le box rouge
        points = [(int(p[0]), int(p[1])) for p in bbox]
        draw.polygon(points, outline='red', width=2)
        
        # Récupérer la position en haut à gauche du box
        min_x = min(p[0] for p in bbox)
        min_y = min(p[1] for p in bbox)
        
        # Afficher le texte détecté à côté
        label = f"{texte} ({confiance:.2f})"
        draw.text((int(min_x), int(min_y) - 25), label, fill='red', font=font)

img.save('image_2_detecte.jpg')

print("Nombres détectés:")
for item in nombres_avec_pos:
    print(f"{item['valeur']} - Confiance: {item['confiance']:.2f}")