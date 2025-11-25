from paddleocr import PaddleOCR
import re

ocr = PaddleOCR(use_textline_orientation=True, lang='en')
result = ocr.ocr('image_2.jpg')

print("=== DEBUG: Structure complète du résultat ===")
print(f"Type de result: {type(result)}")
print(f"Longueur: {len(result)}")

if result and len(result) > 0:
    page_result = result[0]
    print(f"\n--- Page 0 ---")
    print(f"Type: {type(page_result)}")
    print(f"\nAttributs disponibles: {dir(page_result)}")
    
    # Afficher tous les attributs qui ne commencent pas par _
    print("\n=== Contenu des attributs ===")
    for attr in dir(page_result):
        if not attr.startswith('_'):
            try:
                value = getattr(page_result, attr)
                if not callable(value):
                    print(f"{attr}: {value}")
            except:
                pass
    
    # Essayer d'accéder aux textes reconnus
    if hasattr(page_result, 'rec_texts'):
        print("\n=== TEXTES DÉTECTÉS ===")
        for i, (texte, score) in enumerate(zip(page_result.rec_texts, page_result.rec_scores)):
            print(f"{i}: '{texte}' (confiance: {score:.4f})")
            matches = re.findall(r'\d+(?:\.\d+)?', texte)
            if matches:
                print(f"   ✓ Chiffres: {matches}")

print("\n=== Fin du debug ===")
