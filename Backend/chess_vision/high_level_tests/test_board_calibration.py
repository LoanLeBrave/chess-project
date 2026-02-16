#!/usr/bin/env python3
"""
TEST: Calibration du plateau et extraction
==========================================

Ce test vérifie le processus complet de calibration:
- Détection des ArUcos de calibration (32, 33, 34, 35)
- Application des offsets personnalisés
- Calcul des coins du plateau avec offsets
- Transformation de perspective
- Extraction du plateau en image carrée
- Dessin du grillage 8x8

Sauvegarde de nombreuses images de debug à chaque étape.

Usage:
    python -m chess_vision.tests.test_board_calibration --image photo.jpg
    python -m chess_vision.tests.test_board_calibration --image photo.jpg --verbose
"""

import sys
import os
import argparse
import cv2
import numpy as np
import json

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.tests.test_utils import (
    TestLogger, DebugImageSaver, Colors,
    validate_image, validate_markers, load_test_image, find_test_images,
    draw_debug_info
)
from chess_vision.config import Config, OFFSETS, CALIBRATION_IDS, EXTRACTED_BOARD_SIZE
from chess_vision.aruco_detector import (
    ArucoDetector,
    draw_detected_markers,
    detect_calibration_markers
)
from chess_vision.board_extractor import BoardExtractor, draw_chess_grid


def draw_offset_visualization(
    image: np.ndarray,
    calibration_markers: dict,
    config: Config,
    logger: TestLogger
) -> np.ndarray:
    """
    Visualise les offsets appliqués sur chaque marqueur de calibration.
    
    Args:
        image: Image source
        calibration_markers: Marqueurs détectés
        config: Configuration avec offsets
        logger: Logger
        
    Returns:
        Image annotée
    """
    img = image.copy()
    
    # Couleurs pour chaque coin
    colors = {
        "TL": (0, 255, 0),      # Vert
        "TR": (255, 0, 0),      # Bleu
        "BL": (0, 0, 255),      # Rouge
        "BR": (255, 255, 0),    # Cyan
    }
    
    for marker_id, corner_code in CALIBRATION_IDS.items():
        if marker_id not in calibration_markers:
            logger.warning(f"Marqueur {corner_code} (ID {marker_id}) non trouvé")
            continue
        
        marker_data = calibration_markers[marker_id]
        center = marker_data['center']
        offset = config.OFFSETS.get(corner_code, {"x": 0, "y": 0})
        color = colors.get(corner_code, (255, 255, 255))
        
        # Convert to integers for drawing
        center_int = (int(center[0]), int(center[1]))
        offset_point_int = (int(center[0] + offset['x']), int(center[1] + offset['y']))
        
        # Point du centre du marqueur (cercle plein)
        cv2.circle(img, center_int, 10, color, -1)
        cv2.circle(img, center_int, 12, (0, 0, 0), 2)
        
        # Point avec offset appliqué (cercle vide + croix)
        cv2.drawMarker(img, offset_point_int, color, cv2.MARKER_CROSS, 25, 3)
        cv2.circle(img, offset_point_int, 15, color, 2)
        
        # Ligne entre centre et point offset
        cv2.line(img, center_int, offset_point_int, color, 2, cv2.LINE_AA)
        
        # Annotations
        # Label du coin
        cv2.putText(img, f"{corner_code}", (int(center[0]) - 30, int(center[1]) - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Valeur de l'offset
        offset_text = f"Offset: ({offset['x']}, {offset['y']})"
        cv2.putText(img, offset_text, (int(center[0]) - 50, int(center[1]) + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # Légende
    legend_y = 30
    cv2.putText(img, "Legende:", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    legend_y += 25
    cv2.putText(img, "● = Centre ArUco", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    legend_y += 20
    cv2.putText(img, "+ = Position avec offset", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return img


def draw_corner_calculation(
    image: np.ndarray,
    calibration_markers: dict,
    corners: dict,
    config: Config,
    logger: TestLogger
) -> np.ndarray:
    """
    Visualise le calcul des coins du plateau.
    
    Args:
        image: Image source
        calibration_markers: Marqueurs détectés
        corners: Coins calculés (avec offsets)
        config: Configuration
        logger: Logger
        
    Returns:
        Image annotée
    """
    img = image.copy()
    
    colors = {
        "TL": (0, 255, 0),
        "TR": (255, 0, 0),
        "BL": (0, 0, 255),
        "BR": (255, 255, 0),
    }
    
    # Dessiner le quadrilatère formé par les coins
    if len(corners) == 4:
        pts = np.array([
            corners["TL"],
            corners["TR"],
            corners["BR"],
            corners["BL"]
        ], dtype=np.int32)
        
        # Quadrilatère semi-transparent
        overlay = img.copy()
        cv2.fillPoly(overlay, [pts], (100, 255, 100))
        cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
        
        # Contour
        cv2.polylines(img, [pts], True, (0, 255, 0), 3)
    
    # Dessiner chaque coin
    for corner_name, corner_pos in corners.items():
        color = colors.get(corner_name, (255, 255, 255))
        
        # Point du coin calculé
        pt = (int(corner_pos[0]), int(corner_pos[1]))
        cv2.circle(img, pt, 12, color, -1)
        cv2.circle(img, pt, 14, (0, 0, 0), 2)
        
        # Label
        cv2.putText(img, corner_name, (pt[0] + 15, pt[1] + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    # Afficher les dimensions
    if "TL" in corners and "TR" in corners:
        tl = np.array(corners["TL"])
        tr = np.array(corners["TR"])
        bl = np.array(corners["BL"])
        
        width_top = np.linalg.norm(tr - tl)
        height_left = np.linalg.norm(bl - tl)
        
        # Texte des dimensions
        mid_top = (int((tl[0] + tr[0]) // 2), int((tl[1] + tr[1]) // 2 - 20))
        mid_left = (int((tl[0] + bl[0]) // 2 - 80), int((tl[1] + bl[1]) // 2))
        
        cv2.putText(img, f"W={width_top:.0f}px", mid_top,
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"H={height_left:.0f}px", mid_left,
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return img


def draw_perspective_transform_debug(
    original: np.ndarray,
    corners: dict,
    output_size: int,
    logger: TestLogger
) -> tuple:
    """
    Montre la transformation de perspective étape par étape.
    
    Args:
        original: Image originale
        corners: Coins du plateau
        output_size: Taille de sortie
        logger: Logger
        
    Returns:
        Tuple (image_avec_points_source, matrice_transformation, image_destination)
    """
    img = original.copy()
    
    # Points source (dans l'ordre: TL, TR, BR, BL)
    src_pts = np.float32([
        corners["TL"],
        corners["TR"],
        corners["BR"],
        corners["BL"]
    ])
    
    # Points destination
    dst_pts = np.float32([
        [0, 0],
        [output_size - 1, 0],
        [output_size - 1, output_size - 1],
        [0, output_size - 1]
    ])
    
    # Dessiner les points source avec numéros
    for i, (pt, name) in enumerate(zip(src_pts, ["TL", "TR", "BR", "BL"])):
        pt_int = (int(pt[0]), int(pt[1]))
        cv2.circle(img, pt_int, 15, (0, 255, 0), -1)
        cv2.putText(img, str(i), (pt_int[0] - 5, pt_int[1] + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(img, name, (pt_int[0] + 20, pt_int[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Calculer la matrice de transformation
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    
    # Appliquer la transformation
    warped = cv2.warpPerspective(original, matrix, (output_size, output_size))
    
    return img, matrix, warped


def draw_chess_grid_with_labels(
    board_image: np.ndarray,
    cell_size: float,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine un grillage d'échecs avec labels (A1, B2, etc.).
    
    Args:
        board_image: Image du plateau extrait
        cell_size: Taille d'une case
        logger: Logger
        
    Returns:
        Image avec grillage
    """
    img = board_image.copy()
    h, w = img.shape[:2]
    
    # Couleurs alternées pour les cases
    color_light = (200, 200, 220, 50)  # Semi-transparent clair
    color_dark = (100, 100, 120, 50)   # Semi-transparent foncé
    
    # Overlay pour les cases colorées
    overlay = img.copy()
    
    # Dessiner les cases colorées
    for row in range(8):
        for col in range(8):
            x1 = int(col * cell_size)
            y1 = int(row * cell_size)
            x2 = int((col + 1) * cell_size)
            y2 = int((row + 1) * cell_size)
            
            # Damier
            if (row + col) % 2 == 0:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (220, 220, 200), -1)
            else:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (120, 120, 100), -1)
    
    # Appliquer l'overlay avec transparence
    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
    
    # Dessiner la grille
    for i in range(9):
        # Lignes verticales
        x = int(i * cell_size)
        thickness = 3 if i == 0 or i == 8 else 1
        cv2.line(img, (x, 0), (x, h), (0, 255, 0), thickness)
        
        # Lignes horizontales
        y = int(i * cell_size)
        cv2.line(img, (0, y), (w, y), (0, 255, 0), thickness)
    
    # Labels des colonnes (A-H) en haut
    columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    for i, col in enumerate(columns):
        x = int((i + 0.5) * cell_size) - 10
        cv2.putText(img, col, (x, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(img, col, (x, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    # Labels des rangées (1-8) à gauche
    rows = ['8', '7', '6', '5', '4', '3', '2', '1']  # Du haut vers le bas
    for i, row in enumerate(rows):
        y = int((i + 0.5) * cell_size) + 5
        cv2.putText(img, row, (5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(img, row, (w - 20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    return img


def draw_coordinate_system(
    board_image: np.ndarray,
    cell_size: float,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine le système de coordonnées (-10 à +10).
    
    Args:
        board_image: Image du plateau
        cell_size: Taille d'une case
        logger: Logger
        
    Returns:
        Image avec coordonnées
    """
    img = board_image.copy()
    h, w = img.shape[:2]
    
    # Axes
    center = (w // 2, h // 2)
    
    # Axe X (horizontal)
    cv2.arrowedLine(img, (50, center[1]), (w - 30, center[1]), (0, 0, 255), 2)
    cv2.putText(img, "X (+10)", (w - 70, center[1] - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv2.putText(img, "(-10)", (10, center[1] - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    # Axe Y (vertical)
    cv2.arrowedLine(img, (center[0], h - 30), (center[0], 50), (0, 255, 0), 2)
    cv2.putText(img, "Y (+10)", (center[0] + 10, 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(img, "(-10)", (center[0] + 10, h - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Graduations
    for i in range(-4, 5):
        if i == 0:
            continue
        # X
        x = int(center[0] + i * (w / 10))
        cv2.line(img, (x, center[1] - 5), (x, center[1] + 5), (0, 0, 255), 1)
        # Y
        y = int(center[1] - i * (h / 10))
        cv2.line(img, (center[0] - 5, y), (center[0] + 5, y), (0, 255, 0), 1)
    
    # Centre (0, 0)
    cv2.circle(img, center, 5, (255, 255, 255), -1)
    cv2.putText(img, "(0,0)", (center[0] + 10, center[1] + 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return img


def test_corner_estimation(
    extractor: BoardExtractor,
    calibration_markers: dict,
    image: np.ndarray,
    logger: TestLogger,
    saver: DebugImageSaver
) -> bool:
    """
    Teste l'estimation des coins manquants.
    
    Args:
        extractor: Extracteur de plateau
        calibration_markers: Marqueurs de calibration
        image: Image source
        logger: Logger
        saver: Saver d'images
        
    Returns:
        True si succès
    """
    logger.step("Test d'estimation des coins manquants")
    
    if len(calibration_markers) < 3:
        logger.warning("Pas assez de marqueurs pour tester l'estimation")
        return False
    
    # Tester avec chaque coin manquant
    corner_names = list(CALIBRATION_IDS.values())  # ['TL', 'TR', 'BL', 'BR']
    
    for missing_corner in corner_names:
        logger.subheader(f"Test avec {missing_corner} manquant")
        
        # Créer un sous-ensemble sans ce coin
        test_markers = {}
        for marker_id, corner_code in CALIBRATION_IDS.items():
            if corner_code != missing_corner and marker_id in calibration_markers:
                test_markers[marker_id] = calibration_markers[marker_id]
        
        if len(test_markers) < 3:
            logger.debug(f"Pas assez de marqueurs restants (besoin de 3, a {len(test_markers)})")
            continue
        
        # Calculer les coins (seulement ceux détectés)
        corners, offset_lines = extractor.calculate_corners(test_markers)
        
        # Estimer les coins manquants
        if len(corners) < 4:
            corners, estimated_codes = extractor.estimate_missing_corners(corners)
        else:
            estimated_codes = []
        
        if corners and len(corners) == 4:
            logger.success(f"Estimation réussie avec {missing_corner} manquant (estimé: {estimated_codes})")
            
            # Visualiser
            config = Config()
            img_est = draw_corner_calculation(image, test_markers, corners, config, logger)
            saver.save(img_est, f"estimation_{missing_corner}_missing",
                      metadata={'missing': missing_corner, 'estimated': estimated_codes})
        else:
            logger.warning(f"Échec de l'estimation avec {missing_corner} manquant")
    
    return True


def run_board_calibration_test(
    image_path: str,
    verbose: bool = True
) -> bool:
    """
    Exécute le test complet de calibration du plateau.
    
    Args:
        image_path: Chemin de l'image
        verbose: Mode verbeux
        
    Returns:
        True si succès
    """
    # Initialisation
    logger = TestLogger("Test Calibration Plateau", verbose=verbose)
    logger.header("TEST DE CALIBRATION DU PLATEAU")
    
    saver = DebugImageSaver("board_calibration", logger=logger)
    config = Config()
    detector = ArucoDetector()
    extractor = BoardExtractor()
    
    # =========================================================
    # ÉTAPE 1: Chargement de l'image
    # =========================================================
    logger.step("Chargement de l'image source")
    
    image = load_test_image(image_path, logger)
    if image is None:
        return False
    
    saver.save(image, "01_original_input")
    
    # =========================================================
    # ÉTAPE 2: Détection des marqueurs de calibration
    # =========================================================
    logger.step("Détection des marqueurs de calibration")
    
    calibration_markers = detect_calibration_markers(image, detector)
    
    logger.info(f"Marqueurs de calibration détectés: {len(calibration_markers)}/4")
    
    for corner_name, corner_id in config.CALIBRATION_IDS.items():
        if corner_id in calibration_markers:
            marker = calibration_markers[corner_id]
            logger.success(f"{corner_name} (ID {corner_id}): détecté à ({marker['center'][0]}, {marker['center'][1]})")
        else:
            logger.error(f"{corner_name} (ID {corner_id}): NON DÉTECTÉ")
    
    # Image avec marqueurs détectés
    img_markers = draw_detected_markers(image, 
        {k: v for k, v in detector.detect(image).items() 
         if k in config.CALIBRATION_IDS.values()})
    saver.save(img_markers, "02_calibration_markers_detected",
              metadata={'count': len(calibration_markers)})
    
    if len(calibration_markers) < 3:
        logger.error("Pas assez de marqueurs de calibration détectés (minimum 3 requis)")
        return logger.summary()
    
    # =========================================================
    # ÉTAPE 3: Visualisation des offsets
    # =========================================================
    logger.step("Visualisation des offsets personnalisés")
    
    logger.subheader("Offsets configurés")
    for corner_name, offset in config.OFFSETS.items():
        logger.info(f"{corner_name}: dx={offset['x']}, dy={offset['y']}")
    
    img_offsets = draw_offset_visualization(image, calibration_markers, config, logger)
    saver.save(img_offsets, "03_offsets_visualization",
              metadata={'offsets': config.OFFSETS})
    
    # =========================================================
    # ÉTAPE 4: Calcul des coins du plateau
    # =========================================================
    logger.step("Calcul des coins du plateau avec offsets")
    
    corners, offset_lines = extractor.calculate_corners(calibration_markers)
    
    if not corners:
        logger.error("Impossible de calculer les coins du plateau")
        return logger.summary()
    
    logger.subheader("Coins calculés (avec offsets)")
    for corner_name, corner_pos in corners.items():
        logger.info(f"{corner_name}: ({corner_pos[0]:.1f}, {corner_pos[1]:.1f})")
    
    # Image avec coins calculés
    img_corners = draw_corner_calculation(image, calibration_markers, corners, config, logger)
    saver.save(img_corners, "04_calculated_corners",
              metadata={'corners': {k: [float(v[0]), float(v[1])] for k, v in corners.items()}})
    
    # =========================================================
    # ÉTAPE 5: Transformation de perspective
    # =========================================================
    logger.step("Transformation de perspective")
    
    output_size = config.BOARD_OUTPUT_SIZE
    logger.info(f"Taille de sortie: {output_size}x{output_size} pixels")
    
    img_src_pts, transform_matrix, board_warped = draw_perspective_transform_debug(
        image, corners, output_size, logger
    )
    
    # Sauvegarder les images de debug
    saver.save(img_src_pts, "05_source_points_for_transform")
    
    # Matrice de transformation
    logger.subheader("Matrice de transformation")
    logger.debug(f"Matrix shape: {transform_matrix.shape}")
    for i, row in enumerate(transform_matrix):
        logger.debug(f"  Row {i}: [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}]")
    
    saver.save(board_warped, "06_warped_result",
              metadata={
                  'output_size': output_size,
                  'matrix': transform_matrix.tolist()
              })
    
    # =========================================================
    # ÉTAPE 6: Extraction via l'extracteur
    # =========================================================
    logger.step("Extraction du plateau via BoardExtractor")
    
    extracted_board, extraction_matrix = extractor.extract(image, corners)
    
    if extracted_board is None:
        logger.error("Échec de l'extraction du plateau")
        return logger.summary()
    
    logger.success(f"Plateau extrait: {extracted_board.shape[1]}x{extracted_board.shape[0]}")
    saver.save(extracted_board, "07_extracted_board")
    
    # =========================================================
    # ÉTAPE 7: Dessin du grillage
    # =========================================================
    logger.step("Dessin du grillage 8x8")
    
    cell_size = output_size / 8
    logger.info(f"Taille d'une case: {cell_size:.1f} pixels")
    
    # Grillage simple
    board_with_grid = draw_chess_grid(extracted_board)
    saver.save(board_with_grid, "08_board_with_simple_grid")
    
    # Grillage avec labels
    board_with_labels = draw_chess_grid_with_labels(extracted_board, cell_size, logger)
    saver.save(board_with_labels, "09_board_with_labeled_grid")
    
    # =========================================================
    # ÉTAPE 8: Système de coordonnées
    # =========================================================
    logger.step("Visualisation du système de coordonnées (-10/+10)")
    
    board_with_coords = draw_coordinate_system(extracted_board.copy(), cell_size, logger)
    saver.save(board_with_coords, "10_coordinate_system")
    
    # Combiner grille + coordonnées
    board_complete = draw_coordinate_system(board_with_labels.copy(), cell_size, logger)
    saver.save(board_complete, "11_complete_board_visualization")
    
    # =========================================================
    # ÉTAPE 9: Test d'estimation des coins
    # =========================================================
    test_corner_estimation(extractor, calibration_markers, image, logger, saver)
    
    # =========================================================
    # ÉTAPE 10: Comparaison avant/après
    # =========================================================
    logger.step("Comparaison avant/après")
    
    # Redimensionner l'original pour la comparaison
    h, w = image.shape[:2]
    scale = output_size / max(h, w)
    original_resized = cv2.resize(image, (int(w * scale), int(h * scale)))
    
    # Créer une image de comparaison
    saver.save_comparison(
        [original_resized, extracted_board, board_with_labels],
        ["Original", "Extrait", "Avec grille"],
        "12_comparison_before_after",
        cols=3
    )
    
    # =========================================================
    # RÉSUMÉ
    # =========================================================
    logger.subheader("Résumé de la calibration")
    
    # Calculer les métriques
    src_pts = np.float32([corners["TL"], corners["TR"], corners["BR"], corners["BL"]])
    
    # Aire du quadrilatère source
    def quad_area(pts):
        n = len(pts)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += pts[i][0] * pts[j][1]
            area -= pts[j][0] * pts[i][1]
        return abs(area) / 2.0
    
    source_area = quad_area(src_pts)
    target_area = output_size * output_size
    
    summary = {
        'calibration_markers_detected': len(calibration_markers),
        'calibration_complete': len(calibration_markers) == 4,
        'source_quad_area': f"{source_area:.0f} px²",
        'target_area': f"{target_area} px²",
        'output_size': f"{output_size}x{output_size}",
        'cell_size': f"{cell_size:.1f} px",
    }
    
    for key, value in summary.items():
        logger.result(key, value)
    
    saver.add_custom_metadata('summary', summary)
    saver.add_custom_metadata('corners', {k: [float(v[0]), float(v[1])] for k, v in corners.items()})
    saver.add_custom_metadata('transform_matrix', transform_matrix.tolist())
    
    logger.info(f"\n📁 Images de debug sauvegardées dans: {saver.get_output_dir()}")
    
    return logger.summary()


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Test de calibration du plateau",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python -m chess_vision.tests.test_board_calibration --image photo.jpg
  python -m chess_vision.tests.test_board_calibration --photo
  python -m chess_vision.tests.test_board_calibration --image photo.jpg --verbose
        """
    )
    
    parser.add_argument(
        '--image', '-i',
        type=str,
        help='Chemin vers l\'image à tester'
    )
    
    parser.add_argument(
        '--photo', '-p',
        action='store_true',
        help='Prendre une photo en direct avec la caméra'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=True,
        help='Mode verbeux (par défaut: True)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Mode silencieux (désactive verbose)'
    )
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    # Capture photo si demandé
    if args.photo:
        from chess_vision.camera import take_photo
        logger = TestLogger("Capture photo", verbose=verbose)
        logger.info("Capture d'une photo avec la caméra...")
        
        photo_path = take_photo()
        if photo_path:
            logger.success(f"Photo capturée: {photo_path}")
            success = run_board_calibration_test(photo_path, verbose=verbose)
            sys.exit(0 if success else 1)
        else:
            logger.error("Échec de la capture photo")
            sys.exit(1)
    
    if not args.image:
        # Chercher des images
        search_dirs = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'images_tmp'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'test_extraction_plateau_image_cam_rasp', 'images'),
        ]
        
        logger = TestLogger("Recherche d'images", verbose=verbose)
        images = find_test_images(search_dirs, logger)
        
        if images:
            print(f"\n{Colors.CYAN}Images disponibles:{Colors.RESET}")
            for i, img_path in enumerate(images[:10]):
                print(f"  {i+1}. {img_path}")
            print(f"\n{Colors.YELLOW}Utilisez --image pour spécifier une image{Colors.RESET}")
        else:
            print(f"{Colors.RED}Aucune image trouvée.{Colors.RESET}")
        return
    
    success = run_board_calibration_test(args.image, verbose=verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
