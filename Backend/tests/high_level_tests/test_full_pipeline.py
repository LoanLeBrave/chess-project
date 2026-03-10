#!/usr/bin/env python3
"""
TEST: Pipeline complet
======================

Ce test vérifie le pipeline complet de vision:
- Chargement de l'image
- Détection de tous les ArUcos
- Calibration du plateau
- Extraction du plateau
- Analyse des pièces
- Génération du JSON final

Ce test est le plus complet et permet de valider tout le workflow.

Usage:
    python -m chess_vision.tests.test_full_pipeline --image photo.jpg
    python -m chess_vision.tests.test_full_pipeline --image photo.jpg --verbose
"""

import sys
import os
import argparse
import cv2
import numpy as np
import json
import time

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.tests.test_utils import (
    TestLogger, DebugImageSaver, Colors,
    validate_image, load_test_image, find_test_images
)
from chess_vision import ChessVisionPipeline
from chess_vision.config import Config, EXTRACTED_BOARD_SIZE


def draw_full_debug_image(
    original: np.ndarray,
    board_image: np.ndarray,
    pieces: list,
    config: Config,
    logger: TestLogger
) -> np.ndarray:
    """
    Crée une image de debug complète montrant tout le processus.
    
    Args:
        original: Image originale
        board_image: Plateau extrait
        pieces: Pièces analysées
        config: Configuration
        logger: Logger
        
    Returns:
        Image de debug composite
    """
    # Redimensionner l'original pour correspondre au plateau
    board_size = config.BOARD_OUTPUT_SIZE
    h, w = original.shape[:2]
    scale = board_size / max(h, w)
    original_resized = cv2.resize(original, (int(w * scale), int(h * scale)))
    
    # Créer le canvas
    canvas_h = board_size + 100
    canvas_w = board_size * 2 + 50
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:] = (40, 40, 40)
    
    # Placer l'image originale
    y_off = 50
    x_off = 10
    oh, ow = original_resized.shape[:2]
    canvas[y_off:y_off+oh, x_off:x_off+ow] = original_resized
    
    # Placer le plateau extrait avec pièces
    board_annotated = board_image.copy()
    cell_size = board_size / 8
    
    # Dessiner la grille
    for i in range(9):
        x = int(i * cell_size)
        y = int(i * cell_size)
        cv2.line(board_annotated, (x, 0), (x, board_size), (100, 100, 100), 1)
        cv2.line(board_annotated, (0, y), (board_size, y), (100, 100, 100), 1)
    
    # Dessiner les pièces
    for piece in pieces:
        center = piece.get('pixel_position', piece.get('center'))
        if not center:
            continue
        
        pt = (int(center[0]), int(center[1]))
        color = piece.get('color', 'white')
        piece_type = piece.get('piece_type', 'pawn')
        
        marker_color = (255, 255, 255) if color == 'white' else (100, 100, 100)
        border_color = (0, 0, 0) if color == 'white' else (255, 255, 255)
        
        cv2.circle(board_annotated, pt, 15, marker_color, -1)
        cv2.circle(board_annotated, pt, 17, border_color, 2)
        
        # Lettre
        letters = {'king': 'K', 'queen': 'Q', 'rook': 'R', 
                   'bishop': 'B', 'knight': 'N', 'pawn': 'P'}
        letter = letters.get(piece_type, '?')
        cv2.putText(board_annotated, letter, (pt[0] - 7, pt[1] + 6),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, border_color, 2)
    
    x_off2 = board_size + 40
    canvas[y_off:y_off+board_size, x_off2:x_off2+board_size] = board_annotated
    
    # Titres
    cv2.putText(canvas, "Image Originale", (10, 35), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(canvas, "Plateau Extrait + Pieces", (board_size + 40, 35),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Stats en bas
    white_count = len([p for p in pieces if p.get('color') == 'white'])
    black_count = len([p for p in pieces if p.get('color') == 'black'])
    
    stats_y = canvas_h - 15
    cv2.putText(canvas, f"Total: {len(pieces)} pieces | Blancs: {white_count} | Noirs: {black_count}",
               (10, stats_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    
    return canvas


def run_full_pipeline_test(
    image_path: str,
    verbose: bool = True
) -> bool:
    """
    Exécute le test complet du pipeline.
    
    Args:
        image_path: Chemin de l'image
        verbose: Mode verbeux
        
    Returns:
        True si succès
    """
    # Initialisation
    logger = TestLogger("Test Pipeline Complet", verbose=verbose)
    logger.header("TEST DU PIPELINE COMPLET")
    
    saver = DebugImageSaver("full_pipeline", logger=logger)
    
    # =========================================================
    # ÉTAPE 1: Initialisation du pipeline
    # =========================================================
    logger.step("Initialisation du ChessVisionPipeline")
    
    start_time = time.time()
    pipeline = ChessVisionPipeline()
    init_time = time.time() - start_time
    
    logger.success(f"Pipeline initialisé en {init_time*1000:.1f}ms")
    
    # =========================================================
    # ÉTAPE 2: Chargement de l'image
    # =========================================================
    logger.step("Chargement de l'image")
    
    image = load_test_image(image_path, logger)
    if image is None:
        return False
    
    saver.save(image, "01_input_image",
              metadata={'path': image_path, 'shape': list(image.shape)})
    
    # =========================================================
    # ÉTAPE 3: Analyse avec le pipeline
    # =========================================================
    logger.step("Exécution du pipeline d'analyse")
    
    start_time = time.time()
    result = pipeline.analyze_image(image_path)
    analysis_time = time.time() - start_time
    
    logger.success(f"Analyse complétée en {analysis_time*1000:.1f}ms")
    
    # Vérifier le résultat
    if result is None:
        logger.error("Le pipeline a retourné None")
        return logger.summary()
    
    # =========================================================
    # ÉTAPE 4: Extraction des résultats
    # =========================================================
    logger.step("Extraction et vérification des résultats")
    
    # Vérifier la structure du résultat
    expected_keys = ['image', 'board_image', 'calibration_markers', 'pieces', 
                     'game_state', 'timestamp', 'metadata']
    
    for key in expected_keys:
        if key in result:
            logger.success(f"Clé '{key}' présente")
        else:
            logger.warning(f"Clé '{key}' manquante")
    
    # Images
    board_image = result.get('board_image')
    if board_image is not None:
        saver.save(board_image, "02_board_extracted")
        logger.success(f"Plateau extrait: {board_image.shape}")
    else:
        logger.error("Plateau non extrait")
    
    # Marqueurs de calibration
    cal_markers = result.get('calibration_markers', {})
    logger.info(f"Marqueurs de calibration: {len(cal_markers)}/4")
    
    # Pièces
    pieces = result.get('pieces', [])
    logger.info(f"Pièces détectées: {len(pieces)}")
    
    # =========================================================
    # ÉTAPE 5: Analyse détaillée des pièces
    # =========================================================
    logger.step("Analyse détaillée des pièces")
    
    white_pieces = [p for p in pieces if p.get('color') == 'white']
    black_pieces = [p for p in pieces if p.get('color') == 'black']
    
    logger.subheader("Pièces blanches")
    for piece in white_pieces:
        pos = piece.get('position', {})
        board = pos.get('board', {})
        chess = pos.get('chess', '??')
        logger.debug(f"{piece.get('symbol', '?')}: {chess} "
                    f"[board: ({board.get('x', 0.0):.2f}, {board.get('y', 0.0):.2f})]")
    
    logger.subheader("Pièces noires")
    for piece in black_pieces:
        pos = piece.get('position', {})
        board = pos.get('board', {})
        chess = pos.get('chess', '??')
        logger.debug(f"{piece.get('symbol', '?')}: {chess} "
                    f"[board: ({board.get('x', 0.0):.2f}, {board.get('y', 0.0):.2f})]")
    
    # Image avec pièces annotées
    if board_image is not None:
        cell_size = Config.BOARD_OUTPUT_SIZE / 8
        board_annotated = board_image.copy()
        
        # Grille
        for i in range(9):
            x = int(i * cell_size)
            y = int(i * cell_size)
            cv2.line(board_annotated, (x, 0), (x, board_annotated.shape[0]), (0, 255, 0), 1)
            cv2.line(board_annotated, (0, y), (board_annotated.shape[1], y), (0, 255, 0), 1)
        
        # Pièces
        for piece in pieces:
            pos = piece.get('position', {})
            pixel = pos.get('pixel', {})
            chess = pos.get('chess', '??')
            px, py = pixel.get('x', 0), pixel.get('y', 0)
            
            if px > 0 and py > 0:
                pt = (int(px), int(py))
                color = (255, 255, 255) if piece.get('color') == 'white' else (50, 50, 50)
                cv2.circle(board_annotated, pt, 15, color, -1)
                cv2.circle(board_annotated, pt, 17, (0, 255, 0), 2)
                
                # Label
                cv2.putText(board_annotated, chess, (pt[0] - 12, pt[1] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        saver.save(board_annotated, "03_board_with_pieces_annotated")
    
    # =========================================================
    # ÉTAPE 6: Vérification du game_state
    # =========================================================
    logger.step("Vérification du game_state JSON")
    
    game_state = result.get('game_state', {})
    
    if game_state:
        logger.success("game_state généré avec succès")
        
        # Afficher quelques infos
        if 'board_state' in game_state:
            occupied = sum(1 for v in game_state['board_state'].values() if v is not None)
            logger.info(f"Cases occupées: {occupied}")
        
        if 'robot_coordinates' in game_state:
            logger.info(f"Coordonnées robot: {len(game_state['robot_coordinates'])} pièces")
        
        # Sauvegarder le JSON
        json_path = os.path.join(saver.get_output_dir(), "game_state_full.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(game_state, f, indent=2, ensure_ascii=False)
        logger.success(f"JSON sauvegardé: game_state_full.json")
    else:
        logger.warning("game_state vide ou non généré")
    
    # =========================================================
    # ÉTAPE 7: Image de debug complète
    # =========================================================
    logger.step("Génération de l'image de debug complète")
    
    if board_image is not None:
        debug_image = draw_full_debug_image(image, board_image, pieces, 
                                            Config, logger)
        saver.save(debug_image, "04_full_debug_composite")
    
    # =========================================================
    # ÉTAPE 8: Comparaison des méthodes
    # =========================================================
    logger.step("Comparaison des visualisations")
    
    images_to_compare = [image]
    labels = ["Original"]
    
    if board_image is not None:
        images_to_compare.append(board_image)
        labels.append("Plateau")
        
        if len(pieces) > 0:
            images_to_compare.append(board_annotated)
            labels.append("Annoté")
    
    if len(images_to_compare) > 1:
        saver.save_comparison(images_to_compare, labels, "05_comparison", cols=3)
    
    # =========================================================
    # ÉTAPE 9: Métriques de performance
    # =========================================================
    logger.step("Métriques de performance")
    
    metadata = result.get('metadata', {})
    
    logger.subheader("Temps d'exécution")
    logger.result("Initialisation", f"{init_time*1000:.1f}ms")
    logger.result("Analyse complète", f"{analysis_time*1000:.1f}ms")
    
    if 'timings' in metadata:
        for step_name, step_time in metadata['timings'].items():
            logger.result(f"  - {step_name}", f"{step_time*1000:.1f}ms")
    
    # =========================================================
    # RÉSUMÉ FINAL
    # =========================================================
    logger.subheader("Résumé du test")
    
    summary = {
        'success': True,
        'calibration_markers': len(cal_markers),
        'calibration_complete': len(cal_markers) == 4,
        'total_pieces': len(pieces),
        'white_pieces': len(white_pieces),
        'black_pieces': len(black_pieces),
        'board_extracted': board_image is not None,
        'game_state_generated': bool(game_state),
        'init_time_ms': round(init_time * 1000, 1),
        'analysis_time_ms': round(analysis_time * 1000, 1),
    }
    
    for key, value in summary.items():
        logger.result(key, value)
    
    saver.add_custom_metadata('summary', summary)
    saver.add_custom_metadata('game_state', game_state)
    
    # Vérifications finales
    if len(cal_markers) < 3:
        logger.error("Calibration insuffisante")
        summary['success'] = False
    
    if board_image is None:
        logger.error("Plateau non extrait")
        summary['success'] = False
    
    logger.info(f"\n📁 Images de debug sauvegardées dans: {saver.get_output_dir()}")
    
    return logger.summary()


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Test du pipeline complet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python -m chess_vision.tests.test_full_pipeline --image photo.jpg
  python -m chess_vision.tests.test_full_pipeline --photo
  python -m chess_vision.tests.test_full_pipeline --image photo.jpg --verbose
        """
    )
    
    parser.add_argument('--image', '-i', type=str, help='Chemin vers l\'image')
    parser.add_argument('--photo', '-p', action='store_true', help='Prendre une photo en direct avec la caméra')
    parser.add_argument('--verbose', '-v', action='store_true', default=True)
    parser.add_argument('--quiet', '-q', action='store_true')
    
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
            success = run_full_pipeline_test(photo_path, verbose=verbose)
            sys.exit(0 if success else 1)
        else:
            logger.error("Échec de la capture photo")
            sys.exit(1)
    
    if not args.image:
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
        return
    
    success = run_full_pipeline_test(args.image, verbose=verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
