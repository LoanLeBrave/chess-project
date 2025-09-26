import cv2, numpy as np, pytesseract, os

# ===== Chemins =====
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # adapte si besoin
IMAGE_PATH = r"C:\Users\loanb\OneDrive\Documents\Junia\AP5\Projet CHESS\code\chess-project\test\image.jpg"
assert os.path.exists(IMAGE_PATH), f"Fichier introuvable : {IMAGE_PATH}"
print("Tesseract ->", pytesseract.get_tesseract_version())

# ===== Détection simple du rouge + OCR =====
img = cv2.imread(IMAGE_PATH)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
low1, high1 = np.array([0,100,50]),  np.array([10,255,255])
low2, high2 = np.array([170,100,50]), np.array([180,255,255])
mask = cv2.inRange(hsv, low1, high1) | cv2.inRange(hsv, low2, high2)

cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
boxes = [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c) >= 80]
boxes.sort(key=lambda b: (b[1], b[0]))  # haut->bas, gauche->droite

res = []
for x,y,w,h in boxes:
    roi = img[y:y+h, x:x+w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    roi_mask = mask[y:y+h, x:x+w]
    gray = cv2.bitwise_and(gray, gray, mask=roi_mask)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    if np.mean(bw) > 127: bw = 255 - bw
    if bw.shape[0] < 40: bw = cv2.resize(bw, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    txt = pytesseract.image_to_string(bw, config="--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789")
    txt = "".join(ch for ch in txt if ch.isdigit())
    if txt:
        res.append((txt, x, y, w, h))

if res:
    print("Chiffres détectés :", " ".join(t for t, *_ in res))
    print("\nDétails :")
    for i, (t, x, y, w, h) in enumerate(res, 1):
        cx, cy = x + w//2, y + h//2
        print(f"{i:02d}. '{t}' | top-left=({x},{y}) | size=({w}x{h}) | center=({cx},{cy})")
else:
    print("Aucun chiffre détecté.")
