#!/usr/bin/env python3
"""
TEST: Détection des ArUcos
==========================

Ce test vérifie la détection des marqueurs ArUco:
- Détection des marqueurs de calibration (IDs 32-35)
- Détection des marqueurs de pièces (IDs 0-31)
- Paramètres de détection
- Robustesse de la détection

Sauvegarde de nombreuses images de debug à chaque étape.

Usage:
    python -m chess_vision.tests.test_aruco_detection --image photo.jpg
    python -m chess_vision.tests.test_aruco_detection --image photo.jpg --verbose
"""

import sys
import os
import argparse
import cv2
import numpy as np

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.tests.test_utils import (
    TestLogger, DebugImageSaver, Colors,
    validate_image, validate_markers, load_test_image, find_test_images,
    draw_debug_info, timed
)
from chess_vision.config import Config, ARUCO_PARAMS, CALIBRATION_IDS, PIECE_IDS
from chess_vision.aruco_detector import (
    ArucoDetector,
    draw_detected_markers,
    detect_calibration_markers,
    detect_piece_markers
)


def draw_all_markers_debug(
    image: np.ndarray,
    all_markers: dict,
    calibration_markers: dict,
    piece_markers: dict,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine tous les marqueurs détectés avec des couleurs différentes.
    
    Args:
        image: Image originale
        all_markers: Tous les marqueurs
        calibration_markers: Marqueurs de calibration
        piece_markers: Marqueurs de pièces
        logger: Logger
        
    Returns:
        Image annotée
    """
    img = image.copy()
    
    # Couleurs
    COLOR_CALIBRATION = (0, 255, 255)  # Jaune pour calibration
    COLOR_WHITE_PIECE = (255, 255, 255)  # Blanc pour pièces blanches
    COLOR_BLACK_PIECE = (128, 0, 128)  # Violet pour pièces noires
    COLOR_UNKNOWN = (0, 165, 255)  # Orange pour inconnu
    
    for marker_id, marker_data in all_markers.items():
        corners = marker_data['corners']
        center = marker_data['center']
        
        # Déterminer la couleur et le type
        if marker_id in calibration_markers:
            color = COLOR_CALIBRATION
            marker_type = "CAL"
        elif marker_id in piece_markers:
            piece_info = piece_markers[marker_id]
            if piece_info.get('color') == 'white':
                color = COLOR_WHITE_PIECE
            else:
                color = COLOR_BLACK_PIECE
            marker_type = piece_info.get('name', 'PIECE')[:3].upper()
        else:
            color = COLOR_UNKNOWN
            marker_type = "???"
        
        # Dessiner le contour
        pts = corners.reshape((-1, 1, 2)).astype(np.int32)
        cv2.polylines(img, [pts], True, color, 3)
        
        # Dessiner le centre
        center_int = (int(center[0]), int(center[1]))
        cv2.circle(img, center_int, 8, color, -1)
        cv2.circle(img, center_int, 10, (0, 0, 0), 2)
        
        # Texte avec ID et type
        text = f"ID:{marker_id} ({marker_type})"
        text_pos = (int(center[0]) - 40, int(center[1]) - 20)
        
        # Fond pour le texte
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(img, (text_pos[0] - 2, text_pos[1] - h - 2),
                     (text_pos[0] + w + 2, text_pos[1] + 2), (0, 0, 0), -1)
        cv2.putText(img, text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, color, 2)
    
    return img


def draw_calibration_details(
    image: np.ndarray,
    calibration_markers: dict,
    config: Config,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine les détails des marqueurs de calibration.
    
    Args:
        image: Image
        calibration_markers: Marqueurs de calibration
        config: Configuration
        logger: Logger
        
    Returns:
        Image annotée
    """
    img = image.copy()
    
    # Mapping des coins
    corner_names = {
        config.CALIBRATION_IDS["TL"]: ("TL", "Top-Left", (0, 255, 0)),
        config.CALIBRATION_IDS["TR"]: ("TR", "Top-Right", (255, 0, 0)),
        config.CALIBRATION_IDS["BL"]: ("BL", "Bottom-Left", (0, 0, 255)),
        config.CALIBRATION_IDS["BR"]: ("BR", "Bottom-Right", (255, 255, 0)),
    }
    
    for marker_id, marker_data in calibration_markers.items():
        if marker_id in corner_names:
            short, full, color = corner_names[marker_id]
            center = marker_data['center']
            corners = marker_data['corners']
            
            # Contour épais
            pts = corners.reshape((-1, 1, 2)).astype(np.int32)
            cv2.polylines(img, [pts], True, color, 4)
            
            # Centre avec croix
            center_int = (int(center[0]), int(center[1]))
            cv2.drawMarker(img, center_int, color, cv2.MARKER_CROSS, 30, 3)
            
            # Label détaillé
            offset = config.OFFSETS.get(short, {"x": 0, "y": 0})
            text1 = f"{full}"
            text2 = f"ID: {marker_id}"
            text3 = f"Offset: ({offset['x']}, {offset['y']})"
            
            y_base = int(center[1]) + 30
            for i, text in enumerate([text1, text2, text3]):
                y = y_base + i * 20
                (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(img, (int(center[0]) - 2, y - h - 2),
                             (int(center[0]) + w + 2, y + 2), (0, 0, 0), -1)
                cv2.putText(img, text, (int(center[0]), y), cv2.FONT_HERSHEY_SIMPLEX,
                           0.5, color, 1)
    
    # Légende
    legend_y = 30
    for marker_id, (short, full, color) in corner_names.items():
        status = "✓" if marker_id in calibration_markers else "✗"
        text = f"{status} {short}: ID {marker_id}"
        cv2.putText(img, text, (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX,
                   0.6, color, 2)
        legend_y += 25
    
    return img


def draw_detection_parameters(
    image: np.ndarray,
    config: Config
) -> np.ndarray:
    """
    Affiche les paramètres de détection sur l'image.
    """
    img = image.copy()
    
    params_text = [
        f"Dictionary: DICT_4X4_50",
        f"adaptiveThreshWinSizeMin: {config.ARUCO_PARAMS.get('adaptiveThreshWinSizeMin', 'N/A')}",
        f"adaptiveThreshWinSizeMax: {config.ARUCO_PARAMS.get('adaptiveThreshWinSizeMax', 'N/A')}",
        f"adaptiveThreshWinSizeStep: {config.ARUCO_PARAMS.get('adaptiveThreshWinSizeStep', 'N/A')}",
        f"adaptiveThreshConstant: {config.ARUCO_PARAMS.get('adaptiveThreshConstant', 'N/A')}",
        f"minMarkerPerimeterRate: {config.ARUCO_PARAMS.get('minMarkerPerimeterRate', 'N/A')}",
        f"maxMarkerPerimeterRate: {config.ARUCO_PARAMS.get('maxMarkerPerimeterRate', 'N/A')}",
        f"polygonalApproxAccuracyRate: {config.ARUCO_PARAMS.get('polygonalApproxAccuracyRate', 'N/A')}",
        f"minCornerDistanceRate: {config.ARUCO_PARAMS.get('minCornerDistanceRate', 'N/A')}",
        f"minDistanceToBorder: {config.ARUCO_PARAMS.get('minDistanceToBorder', 'N/A')}",
    ]
    
    y = img.shape[0] - len(params_text) * 20 - 10
    
    # Fond semi-transparent
    overlay = img.copy()
    cv2.rectangle(overlay, (5, y - 25), (400, img.shape[0] - 5), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
    
    cv2.putText(img, "Parametres de detection:", (10, y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    y += 22
    
    for text in params_text:
        cv2.putText(img, text, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.45, (255, 255, 255), 1)
        y += 18
    
    return img


def test_detection_quality(
    detector: ArucoDetector,
    image: np.ndarray,
    logger: TestLogger,
    saver: DebugImageSaver
) -> dict:
    """
    Teste la qualité de détection avec différents prétraitements.
    
    Args:
        detector: Détecteur ArUco
        image: Image originale
        logger: Logger
        saver: Saver d'images
        
    Returns:
        Résultats des tests
    """
    logger.step("Test de qualité de détection avec différents prétraitements")
    
    results = {}
    images_to_compare = []
    labels = []
    
    # Test 1: Image originale
    logger.subheader("Test 1: Image originale (BGR)")
    markers_original = detector.detect(image)
    results['original'] = len(markers_original)
    logger.info(f"Marqueurs détectés: {len(markers_original)}")
    
    img_original = draw_all_markers_debug(
        image, markers_original, 
        detect_calibration_markers(image, detector),
        detect_piece_markers(image, detector),
        logger
    )
    saver.save(img_original, "quality_1_original", 
              metadata={'count': len(markers_original)})
    images_to_compare.append(img_original)
    labels.append(f"Original: {len(markers_original)}")
    
    # Test 2: Niveaux de gris
    logger.subheader("Test 2: Niveaux de gris")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    markers_gray = detector.detect(gray_bgr)
    results['grayscale'] = len(markers_gray)
    logger.info(f"Marqueurs détectés: {len(markers_gray)}")
    
    img_gray = draw_all_markers_debug(
        gray_bgr, markers_gray,
        {k: v for k, v in markers_gray.items() if k in CALIBRATION_IDS.values()},
        {k: v for k, v in markers_gray.items() if k in PIECE_IDS},
        logger
    )
    saver.save(img_gray, "quality_2_grayscale",
              metadata={'count': len(markers_gray)})
    images_to_compare.append(img_gray)
    labels.append(f"Grayscale: {len(markers_gray)}")
    
    # Test 3: Égalisation d'histogramme
    logger.subheader("Test 3: Égalisation d'histogramme")
    equalized = cv2.equalizeHist(gray)
    equalized_bgr = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)
    markers_equalized = detector.detect(equalized_bgr)
    results['equalized'] = len(markers_equalized)
    logger.info(f"Marqueurs détectés: {len(markers_equalized)}")
    
    img_eq = draw_all_markers_debug(
        equalized_bgr, markers_equalized,
        {k: v for k, v in markers_equalized.items() if k in CALIBRATION_IDS.values()},
        {k: v for k, v in markers_equalized.items() if k in PIECE_IDS},
        logger
    )
    saver.save(img_eq, "quality_3_equalized",
              metadata={'count': len(markers_equalized)})
    images_to_compare.append(img_eq)
    labels.append(f"Equalized: {len(markers_equalized)}")
    
    # Test 4: CLAHE (Contrast Limited Adaptive Histogram Equalization)
    logger.subheader("Test 4: CLAHE")
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)
    clahe_bgr = cv2.cvtColor(clahe_img, cv2.COLOR_GRAY2BGR)
    markers_clahe = detector.detect(clahe_bgr)
    results['clahe'] = len(markers_clahe)
    logger.info(f"Marqueurs détectés: {len(markers_clahe)}")
    
    img_clahe = draw_all_markers_debug(
        clahe_bgr, markers_clahe,
        {k: v for k, v in markers_clahe.items() if k in CALIBRATION_IDS.values()},
        {k: v for k, v in markers_clahe.items() if k in PIECE_IDS},
        logger
    )
    saver.save(img_clahe, "quality_4_clahe",
              metadata={'count': len(markers_clahe)})
    images_to_compare.append(img_clahe)
    labels.append(f"CLAHE: {len(markers_clahe)}")
    
    # Test 5: Flou gaussien puis détection
    logger.subheader("Test 5: Flou gaussien (réduction du bruit)")
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    markers_blurred = detector.detect(blurred)
    results['blurred'] = len(markers_blurred)
    logger.info(f"Marqueurs détectés: {len(markers_blurred)}")
    
    img_blur = draw_all_markers_debug(
        blurred, markers_blurred,
        {k: v for k, v in markers_blurred.items() if k in CALIBRATION_IDS.values()},
        {k: v for k, v in markers_blurred.items() if k in PIECE_IDS},
        logger
    )
    saver.save(img_blur, "quality_5_blurred",
              metadata={'count': len(markers_blurred)})
    images_to_compare.append(img_blur)
    labels.append(f"Blurred: {len(markers_blurred)}")
    
    # Test 6: Netteté augmentée
    logger.subheader("Test 6: Netteté augmentée")
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(image, -1, kernel)
    markers_sharp = detector.detect(sharpened)
    results['sharpened'] = len(markers_sharp)
    logger.info(f"Marqueurs détectés: {len(markers_sharp)}")
    
    img_sharp = draw_all_markers_debug(
        sharpened, markers_sharp,
        {k: v for k, v in markers_sharp.items() if k in CALIBRATION_IDS.values()},
        {k: v for k, v in markers_sharp.items() if k in PIECE_IDS},
        logger
    )
    saver.save(img_sharp, "quality_6_sharpened",
              metadata={'count': len(markers_sharp)})
    images_to_compare.append(img_sharp)
    labels.append(f"Sharpened: {len(markers_sharp)}")
    
    # Comparaison
    saver.save_comparison(images_to_compare[:4], labels[:4], "quality_comparison_1")
    saver.save_comparison(images_to_compare[4:], labels[4:], "quality_comparison_2")
    
    # Meilleur résultat
    best_method = max(results, key=results.get)
    logger.success(f"Meilleure méthode: {best_method} ({results[best_method]} marqueurs)")
    
    return results


def run_aruco_detection_test(
    image_path: str,
    verbose: bool = True
) -> bool:
    """
    Exécute le test complet de détection ArUco.
    
    Args:
        image_path: Chemin de l'image
        verbose: Mode verbeux
        
    Returns:
        True si succès
    """
    # Initialisation
    logger = TestLogger("Test Détection ArUco", verbose=verbose)
    logger.header("TEST DE DÉTECTION DES ARUCOS")
    
    saver = DebugImageSaver("aruco_detection", logger=logger)
    config = Config()
    # Utiliser les paramètres optimisés de config.py (USE_DEFAULT_ARUCO_PARAMS = False)
    detector = ArucoDetector()
    
    # =========================================================
    # ÉTAPE 1: Chargement de l'image
    # =========================================================
    logger.step("Chargement de l'image source")
    
    image = load_test_image(image_path, logger)
    if image is None:
        return False
    
    saver.save(image, "01_original_input",
              metadata={'path': image_path, 'shape': list(image.shape)})
    
    # Ajouter les infos de l'image
    info_image = draw_debug_info(image, {
        'Fichier': os.path.basename(image_path),
        'Dimensions': f"{image.shape[1]}x{image.shape[0]}",
        'Canaux': image.shape[2] if len(image.shape) > 2 else 1
    })
    saver.save(info_image, "01_original_with_info")
    
    # =========================================================
    # ÉTAPE 2: Détection de tous les marqueurs
    # =========================================================
    logger.step("Détection de tous les marqueurs ArUco")
    
    all_markers = detector.detect(image)
    
    logger.info(f"Total marqueurs détectés: {len(all_markers)}")
    
    if all_markers:
        logger.subheader("Liste des marqueurs détectés")
        for marker_id, data in sorted(all_markers.items()):
            center = data['center']
            logger.debug(f"ID {marker_id}: centre=({center[0]}, {center[1]})")
    
    # Image avec tous les marqueurs
    img_all_markers = draw_detected_markers(image, all_markers)
    saver.save(img_all_markers, "02_all_markers_detected",
              metadata={'count': len(all_markers), 'ids': list(all_markers.keys())})
    
    # =========================================================
    # ÉTAPE 3: Détection des marqueurs de calibration
    # =========================================================
    logger.step("Détection des marqueurs de calibration (IDs 32-35)")
    
    calibration_markers = detect_calibration_markers(image, detector)
    
    expected_ids = list(config.CALIBRATION_IDS.values())
    logger.info(f"IDs attendus: {expected_ids}")
    logger.info(f"IDs détectés: {list(calibration_markers.keys())}")
    
    # Vérifier chaque coin
    for corner_name, corner_id in config.CALIBRATION_IDS.items():
        if corner_id in calibration_markers:
            marker = calibration_markers[corner_id]
            offset = config.OFFSETS.get(corner_name, {"x": 0, "y": 0})
            logger.success(f"{corner_name} (ID {corner_id}): "
                         f"centre=({marker['center'][0]}, {marker['center'][1]}), "
                         f"offset=({offset['x']}, {offset['y']})")
        else:
            logger.error(f"{corner_name} (ID {corner_id}): NON DÉTECTÉ")
    
    # Image avec marqueurs de calibration détaillés
    img_calibration = draw_calibration_details(image, calibration_markers, config, logger)
    saver.save(img_calibration, "03_calibration_markers_detail",
              metadata={
                  'detected': list(calibration_markers.keys()),
                  'expected': expected_ids,
                  'complete': len(calibration_markers) == 4
              })
    
    # =========================================================
    # ÉTAPE 4: Détection des marqueurs de pièces
    # =========================================================
    logger.step("Détection des marqueurs de pièces (IDs 0-31)")
    
    piece_markers = detect_piece_markers(image, detector)
    
    white_pieces = {k: v for k, v in piece_markers.items() if v.get('color') == 'white'}
    black_pieces = {k: v for k, v in piece_markers.items() if v.get('color') == 'black'}
    
    logger.info(f"Pièces blanches détectées: {len(white_pieces)}")
    logger.info(f"Pièces noires détectées: {len(black_pieces)}")
    
    logger.subheader("Pièces blanches")
    for marker_id, data in sorted(white_pieces.items()):
        logger.debug(f"ID {marker_id}: {data.get('name', '?')} @ ({data['center'][0]}, {data['center'][1]})")
    
    logger.subheader("Pièces noires")
    for marker_id, data in sorted(black_pieces.items()):
        logger.debug(f"ID {marker_id}: {data.get('name', '?')} @ ({data['center'][0]}, {data['center'][1]})")
    
    # Image avec pièces annotées
    img_pieces = draw_all_markers_debug(image, all_markers, calibration_markers, piece_markers, logger)
    saver.save(img_pieces, "04_piece_markers_annotated",
              metadata={
                  'total_pieces': len(piece_markers),
                  'white': len(white_pieces),
                  'black': len(black_pieces)
              })
    
    # =========================================================
    # ÉTAPE 5: Affichage des paramètres de détection
    # =========================================================
    logger.step("Vérification des paramètres de détection")
    
    logger.subheader("Paramètres ArUco configurés")
    for param_name, param_value in config.ARUCO_PARAMS.items():
        logger.debug(f"{param_name}: {param_value}")
    
    img_params = draw_detection_parameters(image, config)
    saver.save(img_params, "05_detection_parameters")
    
    # =========================================================
    # ÉTAPE 6: Tests de qualité de détection
    # =========================================================
    quality_results = test_detection_quality(detector, image, logger, saver)
    saver.add_custom_metadata('quality_tests', quality_results)
    
    # =========================================================
    # ÉTAPE 7: Analyse des corners de chaque marqueur
    # =========================================================
    logger.step("Analyse détaillée des corners des marqueurs")
    
    if calibration_markers:
        logger.subheader("Corners des marqueurs de calibration")
        
        for marker_id, marker_data in calibration_markers.items():
            corners = marker_data['corners']
            logger.info(f"Marqueur ID {marker_id}:")
            for i, corner in enumerate(corners):
                logger.debug(f"  Corner {i}: ({corner[0]:.1f}, {corner[1]:.1f})", indent=2)
        
        # Image avec tous les corners annotés
        img_corners = image.copy()
        for marker_id, marker_data in calibration_markers.items():
            corners = marker_data['corners']
            for i, corner in enumerate(corners):
                pt = (int(corner[0]), int(corner[1]))
                cv2.circle(img_corners, pt, 5, (0, 255, 0), -1)
                cv2.putText(img_corners, f"{i}", (pt[0] + 5, pt[1] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        saver.save(img_corners, "07_marker_corners_analysis")
    
    # =========================================================
    # RÉSUMÉ
    # =========================================================
    logger.subheader("Résumé de la détection")
    
    summary = {
        'total_markers': len(all_markers),
        'calibration_markers': len(calibration_markers),
        'piece_markers': len(piece_markers),
        'calibration_complete': len(calibration_markers) == 4,
        'white_pieces': len(white_pieces),
        'black_pieces': len(black_pieces),
    }
    
    for key, value in summary.items():
        logger.result(key, value)
    
    saver.add_custom_metadata('summary', summary)
    
    # Validation finale
    if len(calibration_markers) < 4:
        logger.warning(f"Calibration incomplète: {len(calibration_markers)}/4 marqueurs")
    
    logger.info(f"\n📁 Images de debug sauvegardées dans: {saver.get_output_dir()}")
    
    return logger.summary()


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Test de détection des ArUcos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python -m chess_vision.tests.test_aruco_detection --image photo.jpg
  python -m chess_vision.tests.test_aruco_detection --photo
  python -m chess_vision.tests.test_aruco_detection --image photo.jpg --verbose
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
    
    # Déterminer le mode verbeux
    verbose = not args.quiet
    
    # Capture photo si demandé
    if args.photo:
        from chess_vision.camera import take_photo
        logger = TestLogger("Capture photo", verbose=verbose)
        logger.info("Capture d'une photo avec la caméra...")
        
        photo_path = take_photo()
        if photo_path:
            logger.success(f"Photo capturée: {photo_path}")
            success = run_aruco_detection_test(photo_path, verbose=verbose)
            sys.exit(0 if success else 1)
        else:
            logger.error("Échec de la capture photo")
            sys.exit(1)
    
    # Trouver une image si non spécifiée
    if not args.image:
        # Chercher dans les dossiers courants
        search_dirs = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'images_tmp'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'test_extraction_plateau_image_cam_rasp', 'images'),
            os.path.join(os.path.dirname(__file__), '..', 'images'),
            os.path.join(os.path.dirname(__file__), 'images'),
        ]
        
        logger = TestLogger("Recherche d'images", verbose=verbose)
        images = find_test_images(search_dirs, logger)
        
        if images:
            print(f"\n{Colors.CYAN}Images disponibles:{Colors.RESET}")
            for i, img_path in enumerate(images[:10]):
                print(f"  {i+1}. {img_path}")
            
            print(f"\n{Colors.YELLOW}Utilisez --image pour spécifier une image{Colors.RESET}")
            print(f"Exemple: python -m chess_vision.tests.test_aruco_detection --image {images[0]}")
        else:
            print(f"{Colors.RED}Aucune image trouvée. Utilisez --image pour spécifier le chemin.{Colors.RESET}")
        
        return
    
    # Exécuter le test
    success = run_aruco_detection_test(args.image, verbose=verbose)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
