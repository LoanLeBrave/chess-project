#!/usr/bin/env python3
"""
Module d'extraction et transformation du plateau d'échecs.
Utilise des coins fixes définis par calibration manuelle (board_calibration.json).

La zone calibrée couvre la grille 10x10 :
    - Plateau central 8x8 (cases A1-H8)
    - Cimetière sur le pourtour (1 case de profondeur)

Classes:
    - BoardExtractor: Extracteur de plateau à partir de coins fixes

Fonctions:
    - extract_board(): Extrait et redresse le plateau
    - draw_chess_grid(): Dessine la grille 10x10 (plateau + cimetière)
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from ..config import (
    FIXED_BOARD_CORNERS,
    EXTRACTED_BOARD_SIZE,
    COLORS,
    CALIBRATION_FILE,
    GRID_SIZE,
    CHESS_GRID_SIZE,
    GRID_COLUMNS,
    GRID_ROWS,
)


class BoardExtractor:
    """
    Extracteur de plateau d'échecs à partir de coins fixes.
    
    Les coins sont chargés depuis board_calibration.json (généré par calibrate_board.py).
    
    Attributes:
        board_corners: Coins fixes du plateau {code: (x, y)}
        board_size: Taille de l'image extraite (pixels)
        
    Usage:
        extractor = BoardExtractor()
        board_img, matrix = extractor.extract(original_image)
    """
    
    def __init__(self, board_corners=None, board_size=None):
        """
        Initialise l'extracteur.
        
        Args:
            board_corners: Coins personnalisés {code: (x, y)} (sinon chargés depuis calibration)
            board_size: Taille de l'image extraite (par défaut EXTRACTED_BOARD_SIZE)
        """
        self.board_corners = board_corners if board_corners is not None else FIXED_BOARD_CORNERS
        self.board_size = board_size if board_size is not None else EXTRACTED_BOARD_SIZE
        self._transform_matrix = None
    
    @property
    def transform_matrix(self) -> Optional[np.ndarray]:
        """Retourne la dernière matrice de transformation calculée."""
        return self._transform_matrix
    
    @property
    def is_calibrated(self) -> bool:
        """Vérifie si la calibration est disponible."""
        if self.board_corners is None:
            return False
        required = ['TL', 'TR', 'BR', 'BL']
        return all(c in self.board_corners for c in required)
    
    def get_corners(self) -> Dict[str, Tuple[float, float]]:
        """
        Retourne les coins du plateau.
        
        Returns:
            Dict {code: (x, y)} pour chaque coin
            
        Raises:
            ValueError: Si pas de calibration disponible
        """
        if not self.is_calibrated:
            raise ValueError(
                "Pas de calibration disponible!\n"
                f"Lancez: python -m chess_vision.calibrate_board\n"
                f"Fichier attendu: {CALIBRATION_FILE}"
            )
        return self.board_corners.copy()
    
    def extract(
        self, 
        image: np.ndarray, 
        board_corners: Dict[str, Tuple[float, float]] = None
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Extrait et redresse le plateau par transformation perspective.
        
        Args:
            image: Image originale (BGR)
            board_corners: Coins du plateau (optionnel, utilise les coins fixes si None)
            
        Returns:
            Tuple (board_image, transform_matrix) ou (None, None) si échec
        """
        if board_corners is None:
            board_corners = self.get_corners()
        
        required_corners = ['TL', 'TR', 'BL', 'BR']
        if not all(c in board_corners for c in required_corners):
            return None, None
        
        # Points source (coins du plateau dans l'image originale)
        # Ordre: TL, TR, BR, BL (sens horaire)
        src_points = np.array([
            [board_corners['TL'][0], board_corners['TL'][1]],
            [board_corners['TR'][0], board_corners['TR'][1]],
            [board_corners['BR'][0], board_corners['BR'][1]],
            [board_corners['BL'][0], board_corners['BL'][1]],
        ], dtype=np.float32)
        
        # Points destination (image carrée)
        size = self.board_size
        dst_points = np.array([
            [0, 0],
            [size - 1, 0],
            [size - 1, size - 1],
            [0, size - 1],
        ], dtype=np.float32)
        
        # Calculer et stocker la matrice de transformation
        self._transform_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Appliquer la transformation
        board_img = cv2.warpPerspective(image, self._transform_matrix, (size, size))
        
        return board_img, self._transform_matrix
    
    def transform_point(
        self, 
        point: Tuple[float, float], 
        inverse: bool = False
    ) -> Tuple[float, float]:
        """
        Transforme un point entre l'image originale et le plateau extrait.
        
        Args:
            point: Point (x, y) à transformer
            inverse: Si True, transforme du plateau vers l'original
            
        Returns:
            Point transformé (x, y)
        """
        if self._transform_matrix is None:
            raise ValueError("Aucune transformation calculée. Appelez extract() d'abord.")
        
        matrix = self._transform_matrix
        if inverse:
            matrix = cv2.invert(matrix)[1]
        
        pt = np.array([[[point[0], point[1]]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, matrix)[0][0]
        
        return (float(transformed[0]), float(transformed[1]))


def draw_chess_grid(
    board_img: np.ndarray,
    color=None,
    thickness: int = 2,
    draw_labels: bool = True
) -> np.ndarray:
    """
    Dessine une grille 10x10 sur l'image du plateau (plateau + cimetière).
    
    La zone centrale 8x8 est le plateau d'échecs.
    La bordure de 1 case est le cimetière.
    
    Args:
        board_img: Image extraite (carré 1000x1000)
        color: Couleur des lignes (BGR)
        thickness: Épaisseur des lignes
        draw_labels: Dessiner les labels (0, A-H, 9 / 0-9)
        
    Returns:
        Image avec grille
    """
    if board_img is None:
        return None
    
    img_grid = board_img.copy()
    h, w = img_grid.shape[:2]
    
    grid_color = color if color is not None else COLORS['grid']
    cemetery_color = COLORS.get('cemetery', (100, 100, 100))
    
    cell_w = w / GRID_SIZE
    cell_h = h / GRID_SIZE
    
    # Zone cimetière : overlay semi-transparent
    overlay = img_grid.copy()
    # Bande haut
    cv2.rectangle(overlay, (0, 0), (w, int(cell_h)), (80, 80, 80), -1)
    # Bande bas
    cv2.rectangle(overlay, (0, int(9 * cell_h)), (w, h), (80, 80, 80), -1)
    # Bande gauche (entre haut et bas)
    cv2.rectangle(overlay, (0, int(cell_h)), (int(cell_w), int(9 * cell_h)), (80, 80, 80), -1)
    # Bande droite (entre haut et bas)
    cv2.rectangle(overlay, (int(9 * cell_w), int(cell_h)), (w, int(9 * cell_h)), (80, 80, 80), -1)
    cv2.addWeighted(overlay, 0.3, img_grid, 0.7, 0, img_grid)
    
    # Lignes de la grille 10x10
    for i in range(GRID_SIZE + 1):
        x = int(i * cell_w)
        cv2.line(img_grid, (x, 0), (x, h), grid_color, thickness)
    for i in range(GRID_SIZE + 1):
        y = int(i * cell_h)
        cv2.line(img_grid, (0, y), (w, y), grid_color, thickness)
    
    # Bordure du plateau central (8x8) plus épaisse
    inner_x0 = int(cell_w)
    inner_y0 = int(cell_h)
    inner_x1 = int(9 * cell_w)
    inner_y1 = int(9 * cell_h)
    cv2.rectangle(img_grid, (inner_x0, inner_y0), (inner_x1, inner_y1), (0, 200, 255), thickness + 1)
    
    if draw_labels:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = cell_w / 120
        font_thickness = max(1, int(font_scale * 2))
        
        # Labels colonnes (0, A-H, 9)
        for i, col in enumerate(GRID_COLUMNS):
            x = int((i + 0.5) * cell_w) - 6
            y = h - 5
            cv2.putText(img_grid, col, (x, y), font, font_scale, (0, 0, 0), font_thickness + 2)
            cv2.putText(img_grid, col, (x, y), font, font_scale, (255, 255, 255), font_thickness)
        
        # Labels lignes (9, 8, 7, ..., 1, 0)
        for i, row in enumerate(GRID_ROWS):
            x = 5
            y = int((i + 0.5) * cell_h) + 5
            cv2.putText(img_grid, row, (x, y), font, font_scale, (0, 0, 0), font_thickness + 2)
            cv2.putText(img_grid, row, (x, y), font, font_scale, (255, 255, 255), font_thickness)
    
    return img_grid


def draw_board_visualization(
    image: np.ndarray,
    board_corners: Dict[str, Tuple[float, float]],
) -> np.ndarray:
    """
    Dessine la visualisation des coins du plateau sur l'image originale.
    
    Args:
        image: Image originale (BGR)
        board_corners: Coins du plateau calculés
        
    Returns:
        Image annotée
    """
    img_annotated = image.copy()
    
    # 1. Coins du plateau
    for code, (bx, by) in board_corners.items():
        bx_int, by_int = int(bx), int(by)
        
        color = COLORS['board_corner']
        
        # Croix
        size = 15
        cv2.line(img_annotated, (bx_int - size, by_int), (bx_int + size, by_int), color, 3)
        cv2.line(img_annotated, (bx_int, by_int - size), (bx_int, by_int + size), color, 3)
        cv2.circle(img_annotated, (bx_int, by_int), 5, color, -1)
        
        # Label
        cv2.putText(img_annotated, f"{code} ({bx_int},{by_int})", (bx_int + 10, by_int - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text_bg'], 2)
        cv2.putText(img_annotated, f"{code} ({bx_int},{by_int})", (bx_int + 10, by_int - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # 2. Contour du plateau
    adjacencies = [('TL', 'TR'), ('TR', 'BR'), ('BR', 'BL'), ('BL', 'TL')]
    for c1, c2 in adjacencies:
        if c1 in board_corners and c2 in board_corners:
            pt1 = (int(board_corners[c1][0]), int(board_corners[c1][1]))
            pt2 = (int(board_corners[c2][0]), int(board_corners[c2][1]))
            cv2.line(img_annotated, pt1, pt2, COLORS['board_outline'], 3, cv2.LINE_AA)
    
    # 3. Overlay semi-transparent
    if len(board_corners) == 4:
        corner_order = ['TL', 'TR', 'BR', 'BL']
        pts = np.array([[int(board_corners[c][0]), int(board_corners[c][1])]
                       for c in corner_order], np.int32)
        overlay = img_annotated.copy()
        cv2.fillPoly(overlay, [pts.reshape((-1, 1, 2))], (255, 200, 100))
        cv2.addWeighted(overlay, 0.15, img_annotated, 0.85, 0, img_annotated)
    
    # 4. Label "Calibration fixe"
    cv2.putText(img_annotated, "Calibration: coins fixes", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
    cv2.putText(img_annotated, "Calibration: coins fixes", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    return img_annotated


def get_cell_bounds(board_size=None) -> Dict[str, Dict]:
    """
    Retourne les limites de chaque case de la grille 10x10.
    Inclut le plateau (A1-H8) et le cimetière (cases avec 0 ou 9).
    
    Args:
        board_size: Taille de l'image extraite (pixels)
        
    Returns:
        Dict {case: {'x': (min, max), 'y': (min, max), 'center': (cx, cy),
                      'col_idx': int, 'row_idx': int, 'zone': 'board'|'cemetery'}}
    """
    size = board_size if board_size is not None else EXTRACTED_BOARD_SIZE
    cell_px = size / GRID_SIZE
    
    cells = {}
    
    for col_idx, col in enumerate(GRID_COLUMNS):
        for row_idx, row in enumerate(GRID_ROWS):
            case = f"{col}{row}"
            x_min = col_idx * cell_px
            x_max = (col_idx + 1) * cell_px
            y_min = row_idx * cell_px
            y_max = (row_idx + 1) * cell_px
            
            is_cemetery = col in ('0', '9') or row in ('0', '9')
            
            cells[case] = {
                'x': (x_min, x_max),
                'y': (y_min, y_max),
                'center': ((x_min + x_max) / 2, (y_min + y_max) / 2),
                'col_idx': col_idx,
                'row_idx': row_idx,
                'zone': 'cemetery' if is_cemetery else 'board',
            }
    
    return cells
