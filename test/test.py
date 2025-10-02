# detect_digits_easyocr.py
from pathlib import Path
import cv2, numpy as np, easyocr

HERE = Path(__file__).resolve().parent
IMAGE_PATH = HERE / "image.jpg"   # mets image.jpg à côté du script

def main():
    img = cv2.imread(str(IMAGE_PATH))
    if img is None:
        raise SystemExit(f"Image introuvable : {IMAGE_PATH}")

    h, w = img.shape[:2]
    # Up-scale léger si l'image est petite (aide fortement l'OCR)
    scale = 1.0
    if max(h, w) < 1200:
        scale = 2.0
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    # detection + recognition en une passe
    results = reader.readtext(img, detail=1, paragraph=False)  # [(bbox, text, conf), ...]

    detections = []
    for bbox, text, conf in results:
        # garde seulement les chiffres
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits or conf < 0.30:
            continue
        xs = [p[0] for p in bbox]; ys = [p[1] for p in bbox]
        x, y = int(min(xs)), int(min(ys))
        wbox, hbox = int(max(xs) - min(xs)), int(max(ys) - min(ys))
        # reviens aux coords de l'image d'origine si on a upscalé
        if scale != 1.0:
            x = int(x / scale); y = int(y / scale)
            wbox = int(wbox / scale); hbox = int(hbox / scale)
        cx, cy = x + wbox // 2, y + hbox // 2
        detections.append((digits, conf, x, y, wbox, hbox, cx, cy))

    # tri visuel : haut→bas, puis gauche→droite
    detections.sort(key=lambda t: (t[3], t[2]))

    if detections:
        print("Chiffres détectés :", " ".join(d[0] for d in detections))
        print("\nDétails :")
        for i, (digits, conf, x, y, wbox, hbox, cx, cy) in enumerate(detections, 1):
            print(f"{i:02d}. '{digits}' conf={conf:.2f} | top-left=({x},{y}) | size=({wbox}x{hbox}) | center=({cx},{cy})")
    else:
        print("Aucun chiffre détecté.")

if __name__ == "__main__":
    main()
