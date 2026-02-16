#!/usr/bin/env python3
"""
Module de capture photo.
Gère la prise de photo avec différentes caméras (Raspberry Pi, webcam).

Fonctions:
    - take_photo(): Prend une photo et la sauvegarde
    - capture_with_rpicam(): Capture avec rpicam-still
    - capture_with_opencv(): Capture avec OpenCV
"""

import os
import subprocess
import shutil
from datetime import datetime
from typing import Optional

from ..config import (
    CAMERA_CONFIG,
    USE_DEFAULT_CAMERA_PARAMS,
    IMAGES_DIR,
)


def _check_rpicam_available() -> bool:
    """Vérifie si rpicam-still ou libcamera-still est disponible."""
    return (shutil.which('rpicam-still') is not None or 
            shutil.which('libcamera-still') is not None)


def _check_picamera2_available() -> bool:
    """Vérifie si Picamera2 est disponible."""
    try:
        from picamera2 import Picamera2
        return True
    except ImportError:
        return False


def get_camera_mode() -> str:
    """
    Détecte le mode caméra disponible.
    
    Returns:
        'rpicam', 'picamera2', ou 'opencv'
    """
    if _check_rpicam_available():
        return 'rpicam'
    elif _check_picamera2_available():
        return 'picamera2'
    return 'opencv'


def take_photo(
    output_path=None,
    output_dir=None,
    filename=None
) -> str:
    """
    Prend une photo et la sauvegarde.
    
    Args:
        output_path: Chemin complet du fichier (prioritaire)
        output_dir: Dossier de sortie (si output_path non spécifié)
        filename: Nom du fichier (si output_path non spécifié)
        
    Returns:
        Chemin du fichier créé
        
    Raises:
        RuntimeError: Si la capture échoue
    """
    # Déterminer le chemin de sortie
    if output_path is None:
        if output_dir is None:
            output_dir = IMAGES_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
        
        output_path = os.path.join(output_dir, filename)
    else:
        # Créer le dossier parent si nécessaire
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
    
    print(f"📷 Capture photo...")
    print(f"   📄 Destination: {output_path}")
    
    # Déterminer le mode caméra
    camera_mode = get_camera_mode()
    print(f"   🎥 Mode: {camera_mode}")
    
    # Capture selon le mode
    if camera_mode == 'rpicam':
        _capture_with_rpicam(output_path)
    elif camera_mode == 'picamera2':
        _capture_with_picamera2(output_path)
    else:
        _capture_with_opencv(output_path)
    
    # Vérifier la création du fichier
    if not os.path.exists(output_path):
        raise RuntimeError(f"Échec de la capture: {output_path} n'a pas été créé")
    
    file_size = os.path.getsize(output_path)
    print(f"   ✅ Photo créée: {file_size} bytes")
    
    return output_path


def _capture_with_rpicam(filepath: str):
    """Capture avec rpicam-still ou libcamera-still."""
    # Déterminer la commande
    if shutil.which('rpicam-still'):
        cmd = 'rpicam-still'
    else:
        cmd = 'libcamera-still'
    
    # Construire les arguments
    args = [cmd, '-n', '-o', filepath]
    
    # Timeout
    timeout_ms = CAMERA_CONFIG.get('timeout', 2000)
    args.extend(['--timeout', str(timeout_ms)])
    
    # Paramètres personnalisés
    if not USE_DEFAULT_CAMERA_PARAMS:
        if CAMERA_CONFIG.get('width') and CAMERA_CONFIG.get('height'):
            args.extend(['--width', str(CAMERA_CONFIG['width'])])
            args.extend(['--height', str(CAMERA_CONFIG['height'])])
        
        if CAMERA_CONFIG.get('shutter'):
            args.extend(['--shutter', str(CAMERA_CONFIG['shutter'])])
        
        if CAMERA_CONFIG.get('gain'):
            args.extend(['--gain', str(CAMERA_CONFIG['gain'])])
        
        if CAMERA_CONFIG.get('awb'):
            args.extend(['--awb', str(CAMERA_CONFIG['awb'])])
        
        if CAMERA_CONFIG.get('brightness'):
            args.extend(['--brightness', str(CAMERA_CONFIG['brightness'])])
        
        if CAMERA_CONFIG.get('contrast'):
            args.extend(['--contrast', str(CAMERA_CONFIG['contrast'])])
        
        if CAMERA_CONFIG.get('saturation'):
            args.extend(['--saturation', str(CAMERA_CONFIG['saturation'])])
        
        if CAMERA_CONFIG.get('sharpness'):
            args.extend(['--sharpness', str(CAMERA_CONFIG['sharpness'])])
        
        if CAMERA_CONFIG.get('autofocus_mode'):
            args.extend(['--autofocus-mode', str(CAMERA_CONFIG['autofocus_mode'])])
        
        if CAMERA_CONFIG.get('lens_position') is not None:
            args.extend(['--lens-position', str(CAMERA_CONFIG['lens_position'])])
        
        if CAMERA_CONFIG.get('autofocus_on_capture'):
            args.extend(['--autofocus-on-capture'])
        
        if CAMERA_CONFIG.get('denoise'):
            args.extend(['--denoise', str(CAMERA_CONFIG['denoise'])])
    
    print(f"   🔄 Commande: {' '.join(args)}")
    
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"{cmd} a échoué: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{cmd} timeout après 30 secondes")
    except FileNotFoundError:
        raise RuntimeError(f"{cmd} non trouvé")


def _capture_with_picamera2(filepath: str):
    """Capture avec Picamera2."""
    from picamera2 import Picamera2
    import time
    
    try:
        print("   🔄 Initialisation Picamera2...")
        picam2 = Picamera2()
        config = picam2.create_still_configuration()
        picam2.configure(config)
        
        print("   🔄 Démarrage caméra...")
        picam2.start()
        
        # Appliquer les contrôles de focus depuis CAMERA_CONFIG
        controls = {}
        
        # Focus manuel si configuré
        if CAMERA_CONFIG.get('autofocus_mode') == 'manual':
            controls['AfMode'] = 0  # 0 = Manual focus
            if CAMERA_CONFIG.get('lens_position') is not None:
                controls['LensPosition'] = float(CAMERA_CONFIG['lens_position'])
                print(f"   🔍 Focus manuel: position {CAMERA_CONFIG['lens_position']}")
        
        # Appliquer tous les contrôles
        if controls:
            picam2.set_controls(controls)
        
        # Délai de stabilisation optimisé (configurable)
        stabilization_delay = CAMERA_CONFIG.get('stabilization_delay', 2.0)
        print(f"   ⏳ Stabilisation ({stabilization_delay}s)...")
        time.sleep(stabilization_delay)
        
        print("   📸 Capture...")
        picam2.capture_file(filepath)
        
        print("   🛑 Arrêt caméra...")
        picam2.stop()
        picam2.close()
        
    except Exception as e:
        raise RuntimeError(f"Erreur Picamera2: {e}")


def _capture_with_opencv(filepath: str):
    """Capture avec OpenCV (webcam)."""
    import cv2
    
    print("   🔄 Ouverture webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        raise RuntimeError("Impossible d'ouvrir la caméra")
    
    print("   📸 Capture frame...")
    ret, frame = cap.read()
    
    if not ret:
        cap.release()
        raise RuntimeError("Échec de lecture de la frame")
    
    cv2.imwrite(filepath, frame)
    cap.release()
