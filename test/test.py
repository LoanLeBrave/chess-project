# detect_digits_relative.py
import cv2, numpy as np, pytesseract, os
from pathlib import Path

# --- Chemins relatifs ---
HERE = Path(__file__).resolve().parent
IMAGE_PATH = HERE / "image.jpg"          # <- place image.jpg à côté du script

# Option : si Tesseract n'est pas dans ton PATH, tu peux définir la variable d'env TESSERACT_CMD
# setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.environ.get("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]

assert IMAGE_PATH.exists(), f"Fichier introuvable : {IMAGE_PATH}"
print("Tesseract ->", pytesseract.get_tesseract_version())

# --- Params simples ---
MIN_AREA = 80
HSV_LOW1, HSV_HIGH1 = np.array([0,100,50]),  np.array([10,255,255])
HSV_LOW2, HSV_HIGH2 = np.array([170,100,50]), np.array([180,255,255])
CFG_PSM7  = r"--oem 1 --psm 7  -c tessedit_char_whitelist=0123456789"
CFG_PSM10 = r"--oem 1 --psm 10 -c tessedit_char_whitelist=0123456789"

def mask_red(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, HSV_LOW1, HSV_HIGH1) | cv2.inRange(hsv, HSV_LOW2, HSV_HIGH2)
    k = np.ones((3,3), np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k, 1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, 1)
    return m

def ocr_roi(img, mask, x, y, w, h):
    roi_mask = mask[y:y+h, x:x+w]
    if cv2.countNonZero(roi_mask) < 30:
        return ""
    gray = cv2.cvtColor(img[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_and(gray, gray, mask=roi_mask)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    if np.mean(bw) > 127:  # texte noir sur blanc
        bw = 255 - bw
    if bw.shape[0] < 40:   # agrandir si petit
        bw = cv2.resize(bw, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    bw = cv2.copyMakeBorder(bw, 10,10,10,10, cv2.BORDER_CONSTANT, value=255)

    txt = pytesseract.image_to_string(bw, config=CFG_PSM7)
    txt = "".join(ch for ch in txt if ch.isdigit())
    if not txt:  # secours "un seul chiffre"
        txt = pytesseract.image_to_string(bw, config=CFG_PSM10)
        txt = "".join(ch for ch in txt if ch.isdigit())
    return txt

def main():
    img = cv2.imread(str(IMAGE_PATH))
    if img is None:
        raise SystemExit(f"Impossible de lire l'image : {IMAGE_PATH}")

    mask = mask_red(img)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c) >= MIN_AREA]
    boxes.sort(key=lambda b: (b[1], b[0]))  # haut->bas, gauche->droite

    res = []
    for (x,y,w,h) in boxes:
        t = ocr_roi(img, mask, x, y, w, h)
        if t:
            res.append((t, x, y, w, h))

    if res:
        print("Chiffres détectés :", " ".join(t for t, *_ in res))
        print("\nDétails :")
        for i, (t,x,y,w,h) in enumerate(res, 1):
            cx, cy = x + w//2, y + h//2
            print(f"{i:02d}. '{t}' | top-left=({x},{y}) | size=({w}x{h}) | center=({cx},{cy})")
    else:
        print("Aucun chiffre rouge détecté.")

if __name__ == "__main__":
    main()
