#!/usr/bin/env python3
"""
Script simple pour prendre une photo avec la caméra Raspberry Pi
Utilise Picamera2 (sur Raspberry Pi) ou OpenCV (sur PC)
"""


from datetime import datetime
import os

# Dossier de sortie pour les images
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "images")

# Détection automatique de l'environnement
try:
    from picamera2 import Picamera2
    USE_PICAMERA = True
except ImportError:
    import cv2
    USE_PICAMERA = False


def take_photo(filename=None):
    """
    Prend une photo et l'enregistre dans le dossier images/
    
    Args:
        filename: Nom du fichier (optionnel). Si non spécifié, utilise un timestamp.
    
    Returns:
        str: Chemin complet du fichier enregistré
    """
    # Créer le dossier images s'il n'existe pas
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Générer un nom de fichier si non spécifié
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if USE_PICAMERA:
        # Raspberry Pi avec Picamera2
        picam2 = Picamera2()
        config = picam2.create_still_configuration()
        picam2.configure(config)
        picam2.start()
        picam2.capture_file(filepath)
        picam2.stop()
        picam2.close()
    else:
        # PC avec OpenCV (webcam USB)
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Impossible d'ouvrir la caméra")
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filepath, frame)
        cap.release()
    
    print(f"Photo enregistrée: {filepath}")
    return filepath


if __name__ == "__main__":
    take_photo()