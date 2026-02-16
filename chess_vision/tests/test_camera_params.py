#!/usr/bin/env python3
"""
TEST: Optimisation des paramètres de détection pour marqueurs flous
===================================================================

Ce script teste différentes combinaisons de paramètres de traitement d'image
pour améliorer la détection de marqueurs ArUco flous ou petits.

Usage:
    python -m chess_vision.tests.test_camera_params --image board_extracted.jpg
    python -m chess_vision.tests.test_camera_params --image board_extracted.jpg --best 5
"""

import sys
import os
import argparse
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.tests.test_utils import TestLogger, DebugImageSaver
from chess_vision.aruco_detector import ArucoDetector, detect_piece_markers
from chess_vision.config import ARUCO_DICT_TYPE


class PreprocessConfig:
    """Configuration de prétraitement d'image."""
    def __init__(self, name: str, **params):
        self.name = name
        self.sharpen = params.get('sharpen', 0)  # 0=off, 1=light, 2=medium, 3=strong
        self.denoise = params.get('denoise', 0)  # 0=off, 1-10=strength
        self.clahe = params.get('clahe', False)  # True/False
        self.clahe_clip = params.get('clahe_clip', 2.0)  # 1.0-4.0
        self.upscale = params.get('upscale', 1.0)  # 1.0=original, 2.0=double, etc.
        self.bilateral = params.get('bilateral', False)  # True/False
        self.blur = params.get('blur', 0)  # 0=off, 1-5=kernel size
        self.gamma = params.get('gamma', 1.0)  # 0.5-2.0 (1.0=no change)
        self.morphology = params.get('morphology', None)  # None, 'open', 'close'
        
        # Paramètres ArUco
        self.aruco_adaptive_thresh_win_size_min = params.get('win_size_min', 3)
        self.aruco_adaptive_thresh_win_size_max = params.get('win_size_max', 23)
        self.aruco_adaptive_thresh_constant = params.get('thresh_constant', 7)
        self.aruco_min_marker_perimeter_rate = params.get('min_perimeter', 0.03)
        self.aruco_polygonal_approx_accuracy_rate = params.get('poly_accuracy', 0.03)
        
    def __str__(self):
        return self.name


def apply_sharpening(image: np.ndarray, strength: int) -> np.ndarray:
    """Applique un filtre de netteté."""
    if strength == 0:
        return image
    
    kernels = {
        1: np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]),  # Light
        2: np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]),  # Medium
        3: np.array([[-1, -2, -1], [-2, 13, -2], [-1, -2, -1]]) / 4,  # Strong
    }
    
    kernel = kernels.get(strength, kernels[1])
    return cv2.filter2D(image, -1, kernel)


def apply_denoising(image: np.ndarray, strength: int) -> np.ndarray:
    """Applique un débruitage."""
    if strength == 0:
        return image
    
    h = strength * 3  # 3-30
    return cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)


def apply_clahe(image: np.ndarray, clip_limit: float) -> np.ndarray:
    """Applique CLAHE pour améliorer le contraste."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def apply_bilateral_filter(image: np.ndarray) -> np.ndarray:
    """Applique un filtre bilatéral (préserve les bords)."""
    return cv2.bilateralFilter(image, 9, 75, 75)


def apply_gaussian_blur(image: np.ndarray, kernel: int) -> np.ndarray:
    """Applique un flou gaussien léger."""
    if kernel == 0:
        return image
    k = kernel * 2 + 1  # 3, 5, 7, 9, 11
    return cv2.GaussianBlur(image, (k, k), 0)


def apply_gamma_correction(image: np.ndarray, gamma: float) -> np.ndarray:
    """Applique une correction gamma."""
    if gamma == 1.0:
        return image
    
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)


def apply_morphology(image: np.ndarray, operation: str) -> np.ndarray:
    """Applique des opérations morphologiques."""
    if operation is None:
        return image
    
    kernel = np.ones((3, 3), np.uint8)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    if operation == 'open':
        gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
    elif operation == 'close':
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def preprocess_image(image: np.ndarray, config: PreprocessConfig) -> np.ndarray:
    """Applique le prétraitement selon la configuration."""
    img = image.copy()
    
    # Upscaling
    if config.upscale != 1.0:
        new_size = (int(img.shape[1] * config.upscale), int(img.shape[0] * config.upscale))
        img = cv2.resize(img, new_size, interpolation=cv2.INTER_CUBIC)
    
    # Débruitage
    if config.denoise > 0:
        img = apply_denoising(img, config.denoise)
    
    # Filtre bilatéral
    if config.bilateral:
        img = apply_bilateral_filter(img)
    
    # Netteté
    if config.sharpen > 0:
        img = apply_sharpening(img, config.sharpen)
    
    # CLAHE
    if config.clahe:
        img = apply_clahe(img, config.clahe_clip)
    
    # Gamma
    if config.gamma != 1.0:
        img = apply_gamma_correction(img, config.gamma)
    
    # Flou
    if config.blur > 0:
        img = apply_gaussian_blur(img, config.blur)
    
    # Morphologie
    if config.morphology:
        img = apply_morphology(img, config.morphology)
    
    return img


def create_aruco_detector_with_params(config: PreprocessConfig) -> ArucoDetector:
    """Crée un détecteur ArUco avec des paramètres personnalisés."""
    detector = ArucoDetector(use_default_params=False)
    
    # Modifier les paramètres
    params = detector.parameters
    params.adaptiveThreshWinSizeMin = config.aruco_adaptive_thresh_win_size_min
    params.adaptiveThreshWinSizeMax = config.aruco_adaptive_thresh_win_size_max
    params.adaptiveThreshConstant = config.aruco_adaptive_thresh_constant
    params.minMarkerPerimeterRate = config.aruco_min_marker_perimeter_rate
    params.polygonalApproxAccuracyRate = config.aruco_polygonal_approx_accuracy_rate
    
    # Recréer le détecteur avec les nouveaux paramètres
    detector.parameters = params
    detector.detector = cv2.aruco.ArucoDetector(detector.aruco_dict, detector.parameters)
    
    return detector


def test_configuration(image: np.ndarray, config: PreprocessConfig, logger: TestLogger) -> Dict[str, Any]:
    """Teste une configuration de prétraitement."""
    # Prétraiter l'image
    processed = preprocess_image(image, config)
    
    # Créer un détecteur avec les paramètres personnalisés
    detector = create_aruco_detector_with_params(config)
    
    # Détecter les marqueurs
    markers = detect_piece_markers(processed, detector)
    
    # Dessiner les marqueurs détectés
    img_result = processed.copy()
    for marker_id, data in markers.items():
        corners = data['corners'].astype(np.int32)
        center = tuple(map(int, data['center']))
        
        # Contour
        pts = corners.reshape((-1, 1, 2))
        cv2.polylines(img_result, [pts], True, (0, 255, 0), 2)
        
        # ID
        cv2.putText(img_result, str(marker_id), (center[0] - 10, center[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return {
        'config': config,
        'processed': processed,
        'result': img_result,
        'markers': markers,
        'count': len(markers),
        'ids': sorted(markers.keys())
    }


def generate_test_configs() -> List[PreprocessConfig]:
    """Génère une liste de configurations à tester."""
    configs = []
    
    # Baseline
    configs.append(PreprocessConfig("00_baseline"))
    
    # Netteté seule
    configs.append(PreprocessConfig("01_sharpen_light", sharpen=1))
    configs.append(PreprocessConfig("02_sharpen_medium", sharpen=2))
    configs.append(PreprocessConfig("03_sharpen_strong", sharpen=3))
    
    # CLAHE seul
    configs.append(PreprocessConfig("04_clahe_2.0", clahe=True, clahe_clip=2.0))
    configs.append(PreprocessConfig("05_clahe_3.0", clahe=True, clahe_clip=3.0))
    
    # Upscaling
    configs.append(PreprocessConfig("06_upscale_1.5x", upscale=1.5))
    configs.append(PreprocessConfig("07_upscale_2.0x", upscale=2.0))
    
    # Combinaisons
    configs.append(PreprocessConfig("08_sharp+clahe", sharpen=2, clahe=True, clahe_clip=2.5))
    configs.append(PreprocessConfig("09_upscale+sharp", upscale=1.5, sharpen=2))
    configs.append(PreprocessConfig("10_upscale+clahe", upscale=1.5, clahe=True, clahe_clip=2.5))
    configs.append(PreprocessConfig("11_full_combo", upscale=1.5, sharpen=2, clahe=True, clahe_clip=2.5))
    
    # Débruitage
    configs.append(PreprocessConfig("12_denoise_light", denoise=2))
    configs.append(PreprocessConfig("13_denoise+sharp", denoise=2, sharpen=2))
    
    # Bilateral
    configs.append(PreprocessConfig("14_bilateral", bilateral=True))
    configs.append(PreprocessConfig("15_bilateral+sharp", bilateral=True, sharpen=2))
    
    # Gamma
    configs.append(PreprocessConfig("16_gamma_0.8", gamma=0.8))
    configs.append(PreprocessConfig("17_gamma_1.2", gamma=1.2))
    
    # Paramètres ArUco ajustés
    configs.append(PreprocessConfig("18_aruco_sensitive", 
                                   win_size_min=3, win_size_max=15, 
                                   thresh_constant=5, min_perimeter=0.01))
    configs.append(PreprocessConfig("19_aruco_aggressive", 
                                   win_size_min=5, win_size_max=31, 
                                   thresh_constant=10, min_perimeter=0.005))
    
    # Best combos
    configs.append(PreprocessConfig("20_best_combo_1", 
                                   upscale=1.5, sharpen=2, clahe=True, clahe_clip=2.5,
                                   win_size_min=3, win_size_max=20, thresh_constant=7))
    configs.append(PreprocessConfig("21_best_combo_2", 
                                   upscale=2.0, bilateral=True, sharpen=1, clahe=True,
                                   win_size_min=5, win_size_max=25, min_perimeter=0.01))
    
    return configs


def create_comparison_grid(results: List[Dict], cols: int = 4) -> np.ndarray:
    """Crée une grille de comparaison des résultats."""
    if not results:
        return None
    
    rows = (len(results) + cols - 1) // cols
    
    # Taille de référence
    h, w = results[0]['result'].shape[:2]
    thumb_h, thumb_w = 400, 400
    
    # Créer la grille
    grid = np.zeros((rows * thumb_h, cols * thumb_w, 3), dtype=np.uint8)
    
    for idx, result in enumerate(results):
        row = idx // cols
        col = idx % cols
        
        # Redimensionner
        img = cv2.resize(result['result'], (thumb_w, thumb_h))
        
        # Ajouter le texte
        label = f"{result['config'].name}"
        count_text = f"{result['count']} markers"
        cv2.putText(img, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(img, count_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Placer dans la grille
        y1 = row * thumb_h
        y2 = (row + 1) * thumb_h
        x1 = col * thumb_w
        x2 = (col + 1) * thumb_w
        grid[y1:y2, x1:x2] = img
    
    return grid


def main():
    parser = argparse.ArgumentParser(description="Test des paramètres de détection pour marqueurs flous")
    parser.add_argument('--image', '-i', required=True, help="Image du plateau extrait à tester")
    parser.add_argument('--best', '-b', type=int, default=None, help="Afficher seulement les N meilleurs résultats")
    parser.add_argument('--verbose', '-v', action='store_true', help="Mode verbose")
    args = parser.parse_args()
    
    logger = TestLogger("Test Paramètres Caméra", verbose=args.verbose)
    logger.header("TEST D'OPTIMISATION DES PARAMÈTRES")
    
    # Charger l'image
    if not os.path.exists(args.image):
        logger.error(f"Image non trouvée: {args.image}")
        return False
    
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"Impossible de charger l'image: {args.image}")
        return False
    
    logger.info(f"Image chargée: {os.path.basename(args.image)} ({image.shape[1]}x{image.shape[0]})")
    
    # Créer le dossier de sortie
    saver = DebugImageSaver("camera_params_test", logger=logger)
    
    # Générer les configurations à tester
    configs = generate_test_configs()
    logger.info(f"Configurations à tester: {len(configs)}")
    
    # Tester chaque configuration
    logger.step("Test des configurations")
    results = []
    
    for i, config in enumerate(configs, 1):
        logger.info(f"[{i}/{len(configs)}] Test: {config.name}")
        result = test_configuration(image, config, logger)
        results.append(result)
        
        # Sauvegarder
        saver.save(result['result'], config.name, 
                  metadata={'count': result['count'], 'ids': result['ids']})
        
        logger.success(f"  → {result['count']} marqueurs détectés: {result['ids']}")
    
    # Trier par nombre de détections
    results.sort(key=lambda x: x['count'], reverse=True)
    
    # Afficher les résultats
    logger.step("Résumé des résultats")
    logger.subheader("Top configurations par nombre de détections:")
    
    display_count = args.best if args.best else len(results)
    for i, result in enumerate(results[:display_count], 1):
        config = result['config']
        logger.info(f"{i}. {config.name}: {result['count']} marqueurs {result['ids']}")
    
    # Créer une grille de comparaison des meilleurs
    logger.step("Création de la grille de comparaison")
    top_results = results[:min(12, len(results))]
    grid = create_comparison_grid(top_results, cols=4)
    if grid is not None:
        saver.save(grid, "comparison_grid")
        logger.success("Grille de comparaison sauvegardée")
    
    # Sauvegarder le rapport
    report_path = os.path.join(saver.debug_dir, "report.txt")
    with open(report_path, 'w') as f:
        f.write("RAPPORT DE TEST DES PARAMÈTRES\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Image testée: {args.image}\n")
        f.write(f"Nombre de configurations: {len(configs)}\n\n")
        
        f.write("RÉSULTATS TRIÉS PAR NOMBRE DE DÉTECTIONS:\n")
        f.write("-" * 60 + "\n")
        for i, result in enumerate(results, 1):
            config = result['config']
            f.write(f"\n{i}. {config.name}\n")
            f.write(f"   Marqueurs détectés: {result['count']}\n")
            f.write(f"   IDs: {result['ids']}\n")
            f.write(f"   Paramètres:\n")
            f.write(f"     - Sharpen: {config.sharpen}\n")
            f.write(f"     - Denoise: {config.denoise}\n")
            f.write(f"     - CLAHE: {config.clahe} (clip={config.clahe_clip})\n")
            f.write(f"     - Upscale: {config.upscale}x\n")
            f.write(f"     - Bilateral: {config.bilateral}\n")
            f.write(f"     - Gamma: {config.gamma}\n")
            f.write(f"     - ArUco win_size: {config.aruco_adaptive_thresh_win_size_min}-{config.aruco_adaptive_thresh_win_size_max}\n")
            f.write(f"     - ArUco threshold: {config.aruco_adaptive_thresh_constant}\n")
            f.write(f"     - ArUco min_perimeter: {config.aruco_min_marker_perimeter_rate}\n")
    
    logger.success(f"Rapport sauvegardé: {report_path}")
    logger.summary()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
