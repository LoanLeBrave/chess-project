#!/usr/bin/env python3
"""
Prétraitement d'image avant la détection ArUco.

Chaque étape est une fonction indépendante activable/désactivable
depuis PREPROCESSING dans config.py.

Les étapes sont appliquées dans l'ordre défini par PREPROCESSING_PIPELINE.

Ajouter une nouvelle étape :
    1. Écrire une fonction step_xxx(image) → image ci-dessous
    2. L'ajouter dans PREPROCESSING_PIPELINE de config.py avec enabled=True/False

Usage (automatique via ArucoDetector) :
    from chess_vision.modules.preprocessing import preprocess
    processed = preprocess(image)
"""

import cv2
import numpy as np


# ─── Étapes disponibles ───────────────────────────────────────────────────────

def step_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8) -> np.ndarray:
    """
    Égalisation adaptative de l'histogramme (CLAHE).
    Améliore le contraste local, très efficace pour lumière non uniforme.

    Paramètres dans config.py :
        clip_limit  : limite de rognage (2.0 = modéré, 4.0 = fort)
        tile_size   : taille de la grille en pixels (8 = fin, 16 = large)
    """
    gray = _to_gray(image)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    return clahe.apply(gray)


def step_denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """
    Débruitage (filtre Non-Local Means).
    Réduit le bruit de capteur sans trop flouter les bords.

    Paramètres :
        strength : intensité du débruitage (5=léger, 10=normal, 20=fort)
    """
    gray = _to_gray(image)
    return cv2.fastNlMeansDenoising(gray, h=strength)


def step_sharpen(image: np.ndarray, strength: float = 1.5) -> np.ndarray:
    """
    Accentuation des contours (unsharp masking).
    Renforce les bords des marqueurs ArUco.

    Paramètres :
        strength : intensité (1.0 = neutral, 1.5 = modéré, 2.5 = fort)
    """
    gray = _to_gray(image)
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    return cv2.addWeighted(gray, strength, blurred, -(strength - 1), 0)


def step_gamma(image: np.ndarray, gamma: float = 1.2) -> np.ndarray:
    """
    Correction gamma.
    < 1.0 = éclaircit, > 1.0 = assombrit.

    Paramètres :
        gamma : valeur gamma (0.8 = éclaircit, 1.2 = assombrit légèrement)
    """
    gray = _to_gray(image)
    lut = np.array([
        np.clip(((i / 255.0) ** (1.0 / gamma)) * 255, 0, 255)
        for i in range(256)
    ], dtype=np.uint8)
    return cv2.LUT(gray, lut)


def step_bilateral(image: np.ndarray, d: int = 9, sigma: float = 75) -> np.ndarray:
    """
    Filtre bilatéral : lisse les zones homogènes en préservant les bords.
    Alternative plus douce que step_denoise.

    Paramètres :
        d     : diamètre de filtre (5=rapide, 9=normal, 15=lent)
        sigma : force du lissage (50=léger, 75=normal, 150=fort)
    """
    gray = _to_gray(image)
    return cv2.bilateralFilter(gray, d, sigma, sigma)


# ─── Registre des fonctions ───────────────────────────────────────────────────

# Liaison nom → fonction (utilisé par preprocess() pour dispatcher les steps)
_STEP_REGISTRY = {
    'clahe':     step_clahe,
    'denoise':   step_denoise,
    'sharpen':   step_sharpen,
    'gamma':     step_gamma,
    'bilateral': step_bilateral,
}


# ─── Fonction principale ──────────────────────────────────────────────────────

def preprocess(image: np.ndarray) -> np.ndarray:
    """
    Applique le pipeline de prétraitement défini dans config.py.

    Les steps désactivées (enabled=False) sont ignorées.
    L'ordre d'application suit PREPROCESSING_PIPELINE.

    Args:
        image: image BGR ou grayscale

    Returns:
        image prétraitée en niveaux de gris (uint8)
    """
    from ..config import PREPROCESSING_PIPELINE

    result = _to_gray(image)

    for step in PREPROCESSING_PIPELINE:
        if not step.get('enabled', False):
            continue

        name = step['name']
        params = step.get('params', {})

        fn = _STEP_REGISTRY.get(name)
        if fn is None:
            print(f"⚠️  Preprocessing: step inconnue '{name}' — ignorée")
            continue

        result = fn(result, **params)

    return result


# ─── Utilitaire interne ───────────────────────────────────────────────────────

def _to_gray(image: np.ndarray) -> np.ndarray:
    """Convertit en niveaux de gris si l'image est en couleur."""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image
