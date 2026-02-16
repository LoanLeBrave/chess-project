#!/usr/bin/env python3
"""
TEST: Analyse des pièces
========================

Ce test vérifie l'analyse des pièces sur le plateau:
- Détection des marqueurs de pièces après extraction
- Conversion pixel -> coordonnées plateau (-10/+10)
- Conversion pixel -> notation échecs (A1-H8)
- Identification des pièces (nom, couleur)
- Génération du mapping complet

Sauvegarde de nombreuses images de debug à chaque étape.

Usage:
    python -m chess_vision.tests.test_piece_analysis --image photo.jpg
    python -m chess_vision.tests.test_piece_analysis --image photo.jpg --verbose
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
    validate_image, load_test_image, find_test_images
)
from chess_vision.config import Config, EXTRACTED_BOARD_SIZE
from chess_vision.aruco_detector import (
    ArucoDetector,
    draw_detected_markers,
    detect_calibration_markers,
    detect_piece_markers
)
from chess_vision.board_extractor import BoardExtractor, draw_chess_grid
from chess_vision.piece_analyzer import PieceAnalyzer


def draw_piece_positions_detailed(
    board_image: np.ndarray,
    pieces: list,
    cell_size: float,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine les positions des pièces avec toutes les informations.
    
    Args:
        board_image: Image du plateau extrait
        pieces: Liste des pièces analysées
        cell_size: Taille d'une case
        logger: Logger
        
    Returns:
        Image annotée
    """
    img = board_image.copy()
    
    # D'abord dessiner la grille
    h, w = img.shape[:2]
    for i in range(9):
        x = int(i * cell_size)
        y = int(i * cell_size)
        cv2.line(img, (x, 0), (x, h), (100, 100, 100), 1)
        cv2.line(img, (0, y), (w, y), (100, 100, 100), 1)
    
    # Couleurs par type de pièce
    piece_colors = {
        'king': (0, 0, 255),      # Rouge
        'queen': (255, 0, 255),   # Magenta
        'rook': (0, 255, 0),      # Vert
        'bishop': (255, 165, 0),  # Orange
        'knight': (0, 255, 255),  # Cyan
        'pawn': (128, 128, 128),  # Gris
    }
    
    for piece in pieces:
        # Extraire position pixel
        pixel_pos = piece.get('position', {}).get('pixel', {})
        px = pixel_pos.get('x')
        py = pixel_pos.get('y')
        
        if px is None or py is None:
            continue
        
        pt = (int(px), int(py))
        color = piece.get('color', 'white')
        piece_type = piece.get('type', 'unknown')
        chess_square = piece.get('position', {}).get('chess', '??')
        board_pos = piece.get('position', {}).get('board', {})
        board_x = board_pos.get('x', 0)
        board_y = board_pos.get('y', 0)
        
        # Couleur du marqueur selon le type de pièce
        marker_color = piece_colors.get(piece_type, (200, 200, 200))
        
        # Contour selon la couleur (blanc ou noir)
        if color == 'white':
            border_color = (255, 255, 255)
            text_color = (255, 255, 255)
        else:
            border_color = (50, 50, 50)
            text_color = (180, 180, 180)
        
        # Convert to integer coordinates
        pt_int = (int(pt[0]), int(pt[1]))
        
        # Cercle principal
        cv2.circle(img, pt_int, 18, marker_color, -1)
        cv2.circle(img, pt_int, 20, border_color, 3)
        
        # Centre exact
        cv2.circle(img, pt_int, 3, (0, 0, 0), -1)
        
        # Texte: nom court de la pièce
        piece_short = {
            'king': 'K', 'queen': 'Q', 'rook': 'R',
            'bishop': 'B', 'knight': 'N', 'pawn': 'P'
        }.get(piece_type, '?')
        
        cv2.putText(img, piece_short, (pt_int[0] - 8, pt_int[1] + 6),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Case d'échecs
        cv2.putText(img, chess_square, (pt_int[0] - 12, pt_int[1] + 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        
        # Coordonnées board
        coord_text = f"({board_x:.1f},{board_y:.1f})"
        cv2.putText(img, coord_text, (pt_int[0] - 30, pt_int[1] - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, text_color, 1)
    
    return img


def draw_coordinate_conversion_demo(
    board_image: np.ndarray,
    analyzer: PieceAnalyzer,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine une démonstration de la conversion de coordonnées.
    
    Args:
        board_image: Image du plateau
        analyzer: Analyseur de pièces
        logger: Logger
        
    Returns:
        Image avec démo
    """
    img = board_image.copy()
    h, w = img.shape[:2]
    cell_size = w / 8
    
    # Dessiner des points de référence avec leurs coordonnées
    test_points = [
        (0, 0),           # Coin TL
        (w-1, 0),         # Coin TR
        (0, h-1),         # Coin BL
        (w-1, h-1),       # Coin BR
        (w//2, h//2),     # Centre
        (int(cell_size * 0.5), int(cell_size * 7.5)),   # A1
        (int(cell_size * 7.5), int(cell_size * 0.5)),   # H8
    ]
    
    colors = [
        (0, 255, 0), (0, 255, 0), (0, 255, 0), (0, 255, 0),
        (255, 255, 255), (255, 0, 0), (0, 0, 255)
    ]
    
    for pt, color in zip(test_points, colors):
        # Conversion
        board_coords = analyzer.pixel_to_board_coords(pt[0], pt[1])
        chess_square = analyzer.pixel_to_chess_square(pt[0], pt[1])
        
        # Convert to integer coordinates
        pt_int = (int(pt[0]), int(pt[1]))
        
        # Dessiner le point
        cv2.circle(img, pt_int, 8, color, -1)
        cv2.circle(img, pt_int, 10, (0, 0, 0), 2)
        
        # Annotations
        text1 = f"px:({pt[0]},{pt[1]})"
        text2 = f"board:({board_coords[0]:.1f},{board_coords[1]:.1f})"
        text3 = f"chess:{chess_square}"
        
        y_offset = -40 if pt[1] > h // 2 else 20
        
        for i, text in enumerate([text1, text2, text3]):
            y = pt_int[1] + y_offset + i * 15
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(img, (pt_int[0] - 2, y - th - 2), (pt_int[0] + tw + 2, y + 2), (0, 0, 0), -1)
            cv2.putText(img, text, (pt_int[0], y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    return img


def draw_pieces_by_color(
    board_image: np.ndarray,
    white_pieces: list,
    black_pieces: list,
    cell_size: float,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine les pièces séparées par couleur.
    
    Args:
        board_image: Image du plateau
        white_pieces: Pièces blanches
        black_pieces: Pièces noires
        cell_size: Taille d'une case
        logger: Logger
        
    Returns:
        Image annotée
    """
    img = board_image.copy()
    
    # Pièces blanches
    for piece in white_pieces:
        pixel_pos = piece.get('position', {}).get('pixel', {})
        px, py = pixel_pos.get('x'), pixel_pos.get('y')
        if px is not None and py is not None:
            pt = (int(px), int(py))
            cv2.circle(img, pt, 20, (255, 255, 255), -1)
            cv2.circle(img, pt, 22, (0, 0, 0), 2)
            
            piece_type = piece.get('type', 'W?')[:3]
            cv2.putText(img, piece_type, (pt[0] - 15, pt[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    
    # Pièces noires
    for piece in black_pieces:
        pixel_pos = piece.get('position', {}).get('pixel', {})
        px, py = pixel_pos.get('x'), pixel_pos.get('y')
        if px is not None and py is not None:
            pt = (int(px), int(py))
            cv2.circle(img, pt, 20, (50, 50, 50), -1)
            cv2.circle(img, pt, 22, (255, 255, 255), 2)
            
            piece_type = piece.get('type', 'B?')[:3]
            cv2.putText(img, piece_type, (pt[0] - 15, pt[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    # Légende
    cv2.rectangle(img, (5, 5), (150, 55), (0, 0, 0), -1)
    cv2.putText(img, f"Blancs: {len(white_pieces)}", (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(img, f"Noirs: {len(black_pieces)}", (10, 48),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    return img


def draw_chess_board_state(
    board_image: np.ndarray,
    pieces: list,
    cell_size: float,
    logger: TestLogger
) -> np.ndarray:
    """
    Dessine l'état du plateau en notation d'échecs standard.
    
    Args:
        board_image: Image du plateau
        pieces: Liste des pièces
        cell_size: Taille d'une case
        logger: Logger
        
    Returns:
        Image avec état
    """
    img = board_image.copy()
    h, w = img.shape[:2]
    
    # Créer un damier de fond
    for row in range(8):
        for col in range(8):
            x1 = int(col * cell_size)
            y1 = int(row * cell_size)
            x2 = int((col + 1) * cell_size)
            y2 = int((row + 1) * cell_size)
            
            if (row + col) % 2 == 0:
                cv2.rectangle(img, (x1, y1), (x2, y2), (210, 210, 190), -1)
            else:
                cv2.rectangle(img, (x1, y1), (x2, y2), (140, 140, 120), -1)
    
    # Dessiner les pièces
    unicode_pieces = {
        ('white', 'king'): '♔', ('white', 'queen'): '♕',
        ('white', 'rook'): '♖', ('white', 'bishop'): '♗',
        ('white', 'knight'): '♘', ('white', 'pawn'): '♙',
        ('black', 'king'): '♚', ('black', 'queen'): '♛',
        ('black', 'rook'): '♜', ('black', 'bishop'): '♝',
        ('black', 'knight'): '♞', ('black', 'pawn'): '♟',
    }
    
    # Comme OpenCV ne supporte pas bien Unicode, on utilise des lettres
    letter_pieces = {
        ('white', 'king'): 'K', ('white', 'queen'): 'Q',
        ('white', 'rook'): 'R', ('white', 'bishop'): 'B',
        ('white', 'knight'): 'N', ('white', 'pawn'): 'P',
        ('black', 'king'): 'k', ('black', 'queen'): 'q',
        ('black', 'rook'): 'r', ('black', 'bishop'): 'b',
        ('black', 'knight'): 'n', ('black', 'pawn'): 'p',
    }
    
    for piece in pieces:
        pixel_pos = piece.get('position', {}).get('pixel', {})
        px, py = pixel_pos.get('x'), pixel_pos.get('y')
        if px is None or py is None:
            continue
        
        pt = (int(px), int(py))
        color = piece.get('color', 'white')
        piece_type = piece.get('type', 'pawn')
        
        letter = letter_pieces.get((color, piece_type), '?')
        
        text_color = (255, 255, 255) if color == 'white' else (30, 30, 30)
        bg_color = (0, 0, 0) if color == 'white' else (200, 200, 200)
        
        # Fond pour la pièce
        cv2.circle(img, pt, int(cell_size * 0.35), bg_color, -1)
        
        # Lettre de la pièce
        cv2.putText(img, letter, (pt[0] - 12, pt[1] + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, text_color, 2)
    
    # Labels de colonnes
    columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    for i, col in enumerate(columns):
        x = int((i + 0.5) * cell_size)
        cv2.putText(img, col, (x - 5, h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Labels de rangées
    for i in range(8):
        y = int((i + 0.5) * cell_size) + 5
        cv2.putText(img, str(8 - i), (5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    return img


def run_piece_analysis_test(
    image_path: str,
    verbose: bool = True
) -> bool:
    """
    Exécute le test complet d'analyse des pièces.
    
    Args:
        image_path: Chemin de l'image
        verbose: Mode verbeux
        
    Returns:
        True si succès
    """
    # Initialisation
    logger = TestLogger("Test Analyse Pièces", verbose=verbose)
    logger.header("TEST D'ANALYSE DES PIÈCES")
    
    saver = DebugImageSaver("piece_analysis", logger=logger)
    config = Config()
    detector = ArucoDetector()
    extractor = BoardExtractor()
    analyzer = PieceAnalyzer()
    
    # =========================================================
    # ÉTAPE 1: Chargement et préparation
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
    logger.info(f"Marqueurs de calibration: {len(calibration_markers)}/4")
    
    if len(calibration_markers) < 3:
        logger.error("Pas assez de marqueurs de calibration")
        return logger.summary()
    
    # =========================================================
    # ÉTAPE 3: Extraction du plateau
    # =========================================================
    logger.step("Extraction du plateau")
    
    # Calculate board corners from calibration markers
    corners, offset_lines = extractor.calculate_corners(calibration_markers)
    if not corners:
        logger.error("Impossible de calculer les coins du plateau")
        return logger.summary()
    
    logger.info(f"Coins calculés: {list(corners.keys())}")
    for corner_name, corner_pos in corners.items():
        logger.debug(f"{corner_name}: ({corner_pos[0]:.1f}, {corner_pos[1]:.1f})")
    
    # Extract board using calculated corners
    board_image, transform_matrix = extractor.extract(image, corners)
    
    if board_image is None:
        logger.error("Échec de l'extraction du plateau")
        logger.error(f"Corners disponibles: {list(corners.keys())}")
        return logger.summary()
    
    saver.save(board_image, "02_extracted_board")
    
    # Avec grille
    board_with_grid = draw_chess_grid(board_image)
    saver.save(board_with_grid, "03_board_with_grid")
    
    # =========================================================
    # ÉTAPE 4: Détection des pièces sur le plateau extrait
    # =========================================================
    logger.step("Détection des marqueurs de pièces (sur image originale)")
    
    # Détecter sur l'image ORIGINALE (ArUcos nets, pas dégradés par warpPerspective)
    piece_markers = detect_piece_markers(image, detector)
    logger.info(f"Pièces détectées sur image originale: {len(piece_markers)}")
    
    # Projeter les positions vers le plateau extrait pour visualisation
    projected_markers = {}
    for mid, data in piece_markers.items():
        cx, cy = data['center']
        pt = np.array([[[cx, cy]]], dtype=np.float32)
        proj = cv2.perspectiveTransform(pt, transform_matrix)
        px, py = float(proj[0][0][0]), float(proj[0][0][1])
        projected_markers[mid] = {
            'center': (px, py),
            'corners': data['corners'],  # corners originaux
            'piece_info': data.get('piece_info'),
        }
    
    # Dessiner les pièces projetées sur le plateau extrait
    img_pieces_raw = board_image.copy()
    for mid, pdata in projected_markers.items():
        cx, cy = int(pdata['center'][0]), int(pdata['center'][1])
        if 0 <= cx < board_image.shape[1] and 0 <= cy < board_image.shape[0]:
            cv2.circle(img_pieces_raw, (cx, cy), 8, (0, 255, 0), -1)
            cv2.putText(img_pieces_raw, str(mid), (cx - 10, cy - 12),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    saver.save(img_pieces_raw, "04_piece_markers_raw",
              metadata={'count': len(piece_markers)})
    
    if not piece_markers:
        logger.warning("Aucune pièce détectée")
    
    # =========================================================
    # ÉTAPE 5: Analyse des pièces
    # =========================================================
    logger.step("Analyse des pièces (coordonnées, identification)")
    
    cell_size = config.BOARD_OUTPUT_SIZE / 8
    analyzed_pieces = analyzer.analyze_pieces(
        board_image,
        transform_matrix=transform_matrix,
        original_img=image
    )
    
    logger.subheader("Pièces analysées")
    for piece in analyzed_pieces:
        marker_id = piece.get('id', '?')
        piece_type = piece.get('type', '?')
        color = piece.get('color', '?')
        chess_square = piece.get('position', {}).get('chess', '??')
        board_x = piece.get('position', {}).get('board', {}).get('x', 0)
        board_y = piece.get('position', {}).get('board', {}).get('y', 0)
        
        logger.info(f"ID {marker_id}: {piece_type} ({color}) -> {chess_square} "
                   f"[board: ({board_x:.2f}, {board_y:.2f})]")
    
    # Image avec pièces annotées
    img_pieces_detailed = draw_piece_positions_detailed(
        board_image, analyzed_pieces, cell_size, logger
    )
    saver.save(img_pieces_detailed, "05_pieces_analyzed_detailed",
              metadata={'pieces': [p.get('name', '?') for p in analyzed_pieces]})
    
    # =========================================================
    # ÉTAPE 6: Démonstration conversion coordonnées
    # =========================================================
    logger.step("Démonstration de la conversion de coordonnées")
    
    img_coord_demo = draw_coordinate_conversion_demo(board_image, analyzer, logger)
    saver.save(img_coord_demo, "06_coordinate_conversion_demo")
    
    # Test manuel de quelques conversions
    logger.subheader("Tests de conversion de coordonnées")
    
    test_cases = [
        (0, 0, "TL -> A8 area"),
        (799, 0, "TR -> H8 area"),
        (0, 799, "BL -> A1 area"),
        (799, 799, "BR -> H1 area"),
        (400, 400, "Center"),
        (50, 750, "Near A1"),
        (750, 50, "Near H8"),
    ]
    
    for x, y, desc in test_cases:
        board_coords = analyzer.pixel_to_board_coords(x, y)
        chess_square = analyzer.pixel_to_chess_square(x, y)
        logger.debug(f"{desc}: pixel({x},{y}) -> board({board_coords[0]:.2f},{board_coords[1]:.2f}) -> {chess_square}")
    
    # =========================================================
    # ÉTAPE 7: Séparation par couleur
    # =========================================================
    logger.step("Séparation des pièces par couleur")
    
    white_pieces = [p for p in analyzed_pieces if p.get('color') == 'white']
    black_pieces = [p for p in analyzed_pieces if p.get('color') == 'black']
    
    logger.info(f"Pièces blanches: {len(white_pieces)}")
    logger.info(f"Pièces noires: {len(black_pieces)}")
    
    img_by_color = draw_pieces_by_color(board_image, white_pieces, black_pieces, cell_size, logger)
    saver.save(img_by_color, "07_pieces_by_color")
    
    # =========================================================
    # ÉTAPE 8: État du plateau style échecs
    # =========================================================
    logger.step("Visualisation style échiquier")
    
    img_chess_board = draw_chess_board_state(board_image, analyzed_pieces, cell_size, logger)
    saver.save(img_chess_board, "08_chess_board_state")
    
    # =========================================================
    # ÉTAPE 9: Génération du mapping JSON
    # =========================================================
    logger.step("Génération du mapping des positions")
    
    # Mapping par case d'échecs
    chess_mapping = {}
    for piece in analyzed_pieces:
        square = piece.get('position', {}).get('chess', '??')
        if square != '??':
            chess_mapping[square] = {
                'piece': piece.get('type', '?'),
                'color': piece.get('color', '?'),
                'marker_id': piece.get('id', -1)
            }
    
    logger.subheader("Mapping cases d'échecs")
    for square in sorted(chess_mapping.keys()):
        info = chess_mapping[square]
        logger.debug(f"{square}: {info['piece']} ({info['color']})")
    
    # Mapping par coordonnées plateau
    board_mapping = {}
    for piece in analyzed_pieces:
        board_pos = piece.get('position', {}).get('board', {})
        bx, by = board_pos.get('x', 0), board_pos.get('y', 0)
        board_mapping[f"({bx:.2f}, {by:.2f})"] = {
            'piece': piece.get('type', '?'),
            'color': piece.get('color', '?'),
            'chess_square': piece.get('position', {}).get('chess', '??')
        }
    
    # Sauvegarder le JSON
    mapping_data = {
        'chess_notation': chess_mapping,
        'board_coordinates': board_mapping,
        'summary': {
            'total_pieces': len(analyzed_pieces),
            'white_pieces': len(white_pieces),
            'black_pieces': len(black_pieces)
        }
    }
    
    json_path = os.path.join(saver.get_output_dir(), "piece_mapping.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)
    
    logger.success(f"Mapping sauvegardé: piece_mapping.json")
    
    # =========================================================
    # ÉTAPE 10: Comparaison
    # =========================================================
    logger.step("Comparaison des résultats")
    
    saver.save_comparison(
        [board_with_grid, img_pieces_detailed, img_chess_board],
        ["Plateau + Grille", "Pieces Analysées", "État Échiquier"],
        "09_comparison",
        cols=3
    )
    
    # =========================================================
    # RÉSUMÉ
    # =========================================================
    logger.subheader("Résumé de l'analyse")
    
    summary = {
        'total_pieces_detected': len(analyzed_pieces),
        'white_pieces': len(white_pieces),
        'black_pieces': len(black_pieces),
        'unique_squares': len(chess_mapping),
        'board_size': f"{config.BOARD_OUTPUT_SIZE}x{config.BOARD_OUTPUT_SIZE}",
        'cell_size': f"{cell_size:.1f}px",
    }
    
    for key, value in summary.items():
        logger.result(key, value)
    
    saver.add_custom_metadata('summary', summary)
    saver.add_custom_metadata('pieces', [
        {
            'id': p.get('id'),
            'name': p.get('type'),
            'color': p.get('color'),
            'square': p.get('position', {}).get('chess'),
            'board_coords': (p.get('position', {}).get('board', {}).get('x'), p.get('position', {}).get('board', {}).get('y'))
        }
        for p in analyzed_pieces
    ])
    
    logger.info(f"\n📁 Images de debug sauvegardées dans: {saver.get_output_dir()}")
    
    return logger.summary()


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Test d'analyse des pièces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python -m chess_vision.tests.test_piece_analysis --image photo.jpg
  python -m chess_vision.tests.test_piece_analysis --photo
  python -m chess_vision.tests.test_piece_analysis --image photo.jpg --verbose
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
            success = run_piece_analysis_test(photo_path, verbose=verbose)
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
    
    success = run_piece_analysis_test(args.image, verbose=verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
