#!/usr/bin/env python3
"""
Module d'analyse des pièces d'échecs.
Gère la conversion des coordonnées et l'analyse des positions.

Classes:
    - PieceAnalyzer: Analyseur de pièces avec conversion de coordonnées

Systèmes de coordonnées:
    - Pixels: (0,0) = TL, (size,size) = BR (image 1000x1000)
    - Extended (-12.5/+12.5): repère complet 10x10 (plateau + cimetière)
    - Board (-10/+10): repère du plateau central 8x8 (sous-ensemble de extended)
    - Grid notation: 0-9 x A-H (ex: A1, 08, H9...)
    - Chess notation: a1-h8 (plateau uniquement)
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from .config import (
    EXTRACTED_BOARD_SIZE,
    BOARD_COORD_MIN,
    BOARD_COORD_MAX,
    BOARD_COORD_RANGE,
    EXTENDED_COORD_MIN,
    EXTENDED_COORD_MAX,
    EXTENDED_COORD_RANGE,
    GRID_SIZE,
    CHESS_GRID_SIZE,
    GRID_COLUMNS,
    GRID_ROWS,
    COLORS,
    get_piece_info,
    is_piece_marker,
)
from .aruco_detector import ArucoDetector, detect_piece_markers


class PieceAnalyzer:
    """
    Analyseur de pièces d'échecs.
    Convertit les coordonnées et analyse les positions.
    
    Attributes:
        board_size: Taille de l'image extraite (pixels, 1000x1000)
        
    Systèmes de coordonnées:
        - Pixel: (0,0) haut-gauche, (board_size, board_size) bas-droite
        - Extended: (-12.5,-12.5) bas-gauche, (+12.5,+12.5) haut-droite
        - Board: (-10,-10) à (+10,+10) = sous-zone centrale du plateau
        - Grid: notation 10x10 (A1-H8 plateau, 08/A0/etc. cimetière)
        - Chess: a1-h8 (plateau uniquement)
    """
    
    def __init__(self, board_size=None):
        """
        Initialise l'analyseur.
        
        Args:
            board_size: Taille de l'image extraite (par défaut EXTRACTED_BOARD_SIZE)
        """
        self.board_size = board_size if board_size is not None else EXTRACTED_BOARD_SIZE
        self.detector = ArucoDetector()
    
    # ================================================================
    # CONVERSIONS DE COORDONNEES
    # ================================================================
    
    def pixel_to_extended_coords(self, px: float, py: float) -> Tuple[float, float]:
        """
        Convertit des coordonnées pixels en coordonnées du repère étendu (-12.5/+12.5).
        
        Convention:
            - Pixel (0, 0) = Top-Left = (-12.5, +12.5)
            - Pixel (size, 0) = Top-Right = (+12.5, +12.5)
            - Pixel (0, size) = Bottom-Left = (-12.5, -12.5)
            - Pixel (size, size) = Bottom-Right = (+12.5, -12.5)
        
        Args:
            px, py: Coordonnées en pixels
            
        Returns:
            Tuple (x, y) en coordonnées étendues (-12.5 à +12.5)
        """
        norm_x = px / self.board_size
        norm_y = py / self.board_size
        
        coord_x = EXTENDED_COORD_MIN + norm_x * EXTENDED_COORD_RANGE
        coord_y = EXTENDED_COORD_MAX - norm_y * EXTENDED_COORD_RANGE  # Y inversé
        
        return (round(coord_x, 2), round(coord_y, 2))
    
    def extended_coords_to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convertit des coordonnées étendues (-12.5/+12.5) en pixels.
        
        Args:
            x, y: Coordonnées étendues
            
        Returns:
            Tuple (px, py) en pixels
        """
        norm_x = (x - EXTENDED_COORD_MIN) / EXTENDED_COORD_RANGE
        norm_y = (EXTENDED_COORD_MAX - y) / EXTENDED_COORD_RANGE
        
        return (norm_x * self.board_size, norm_y * self.board_size)
    
    def pixel_to_board_coords(self, px: float, py: float) -> Tuple[float, float]:
        """
        Convertit des coordonnées pixels en coordonnées du repère plateau (-10/+10).
        
        Note : utilise le repère étendu en interne. Les valeurs hors [-10, +10]
        indiquent que la pièce est en zone cimetière.
        
        Args:
            px, py: Coordonnées en pixels
            
        Returns:
            Tuple (x, y) en coordonnées étendues (-12.5 à +12.5)
        """
        return self.pixel_to_extended_coords(px, py)
    
    def board_coords_to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convertit des coordonnées étendues en pixels.
        
        Args:
            x, y: Coordonnées étendues
            
        Returns:
            Tuple (px, py) en pixels
        """
        return self.extended_coords_to_pixel(x, y)
    
    def is_on_board(self, x: float, y: float) -> bool:
        """
        Vérifie si des coordonnées étendues sont dans le plateau central (8x8).
        
        Args:
            x, y: Coordonnées étendues
            
        Returns:
            True si la pièce est sur le plateau (A1-H8)
        """
        return (BOARD_COORD_MIN <= x <= BOARD_COORD_MAX and 
                BOARD_COORD_MIN <= y <= BOARD_COORD_MAX)
    
    def pixel_to_grid_square(self, px: float, py: float) -> Optional[str]:
        """
        Convertit des coordonnées pixels en notation de case (grille 10x10).
        
        Retourne la case au format étendu :
            - Plateau : A1-H8
            - Cimetière : cases avec 0 ou 9 (ex: 08, A0, 99)
        
        Args:
            px, py: Coordonnées en pixels
            
        Returns:
            Notation de case (ex: 'A4', '08', 'H9') ou None si hors image
        """
        if px < 0 or px >= self.board_size or py < 0 or py >= self.board_size:
            return None
        
        cell_px = self.board_size / GRID_SIZE
        
        col_idx = int(px / cell_px)
        row_idx = int(py / cell_px)
        
        col_idx = max(0, min(GRID_SIZE - 1, col_idx))
        row_idx = max(0, min(GRID_SIZE - 1, row_idx))
        
        return f"{GRID_COLUMNS[col_idx]}{GRID_ROWS[row_idx]}"
    
    def pixel_to_chess_square(self, px: float, py: float) -> Optional[str]:
        """
        Convertit des coordonnées pixels en notation d'échecs standard.
        
        Args:
            px, py: Coordonnées en pixels
            
        Returns:
            Case d'échecs en minuscule (ex: 'e4') si sur le plateau,
            None si en zone cimetière ou hors image
        """
        grid_square = self.pixel_to_grid_square(px, py)
        if grid_square is None:
            return None
        
        # Vérifier que c'est une case du plateau (colonne A-H, ligne 1-8)
        col = grid_square[0]
        row = grid_square[1]
        if col in ('0', '9') or row in ('0', '9'):
            return None  # Zone cimetière
        
        return grid_square.lower()
    
    def grid_square_to_extended_coords(self, square: str) -> Tuple[float, float]:
        """
        Convertit une case de la grille 10x10 en coordonnées étendues (centre).
        
        Args:
            square: Notation case (ex: 'A4', '08', 'H9')
            
        Returns:
            Tuple (x, y) en coordonnées étendues (-12.5 à +12.5)
        """
        col = square[0].upper()
        row = square[1]
        
        col_idx = GRID_COLUMNS.index(col)
        row_label_idx = GRID_ROWS.index(row)
        
        # Centre de la case en coordonnées étendues
        from .config import CELL_COORD_SIZE
        x = EXTENDED_COORD_MIN + (col_idx + 0.5) * CELL_COORD_SIZE
        y = EXTENDED_COORD_MAX - (row_label_idx + 0.5) * CELL_COORD_SIZE
        
        return (round(x, 2), round(y, 2))
    
    def chess_square_to_board_coords(self, square: str) -> Tuple[float, float]:
        """
        Convertit une case d'échecs (a1-h8) en coordonnées board (centre de la case).
        Compatible avec l'ancien système -10/+10.
        
        Args:
            square: Notation échecs (ex: 'e4')
            
        Returns:
            Tuple (x, y) en coordonnées board (-10 à +10)
        """
        return self.grid_square_to_extended_coords(square.upper())
    
    def board_coords_to_chess_square(self, x: float, y: float) -> Optional[str]:
        """
        Convertit des coordonnées étendues en notation d'échecs.
        
        Args:
            x, y: Coordonnées étendues
            
        Returns:
            Case d'échecs (ex: 'e4') ou None si hors plateau
        """
        px, py = self.extended_coords_to_pixel(x, y)
        return self.pixel_to_chess_square(px, py)
    
    def chess_square_to_pixel(self, square: str) -> Tuple[float, float]:
        """
        Convertit une case d'échecs en pixels (centre de la case).
        
        Args:
            square: Notation échecs (ex: 'e4')
            
        Returns:
            Tuple (px, py) en pixels
        """
        x, y = self.chess_square_to_board_coords(square)
        return self.extended_coords_to_pixel(x, y)
    
    def analyze_pieces(
        self, 
        board_img: np.ndarray,
        transform_matrix: np.ndarray = None,
        original_img: np.ndarray = None
    ) -> List[Dict[str, Any]]:
        """
        Analyse les pièces d'échecs sur la zone complète (plateau + cimetière).
        
        Stratégie de détection :
            - Si original_img + transform_matrix fournis : détecte sur l'image
              originale (haute résolution, ArUcos nets) puis projette les
              coordonnées vers le repère du plateau extrait.
            - Sinon : détecte directement sur board_img (fallback).
        
        Args:
            board_img: Image du plateau extrait et redressé (1000x1000)
            transform_matrix: Matrice de transformation perspective (optionnel)
            original_img: Image originale haute résolution (optionnel)
            
        Returns:
            Liste des pièces avec coordonnées complètes et zone (board/cemetery)
        """
        if original_img is not None and transform_matrix is not None:
            return self.analyze_from_original(original_img, transform_matrix)
        
        # Fallback : détection sur le plateau extrait
        piece_markers = detect_piece_markers(board_img, self.detector)
        
        pieces_list = []
        
        for marker_id, data in piece_markers.items():
            px, py = data['center']
            piece_info = data['piece_info']
            
            piece_data = self._build_piece_data(
                marker_id, piece_info, px, py, data['corners']
            )
            pieces_list.append(piece_data)
        
        return pieces_list
    
    def analyze_from_original(
        self,
        original_img: np.ndarray,
        transform_matrix: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Analyse les pièces depuis l'image originale (haute résolution).
        Transforme ensuite les coordonnées vers le plateau.
        
        Args:
            original_img: Image originale (BGR)
            transform_matrix: Matrice de transformation perspective
            
        Returns:
            Liste des pièces avec coordonnées complètes
        """
        piece_markers = detect_piece_markers(original_img, self.detector)
        
        pieces_list = []
        
        for marker_id, data in piece_markers.items():
            cx_orig, cy_orig = data['center']
            piece_info = data['piece_info']
            
            # Transformer vers le plateau
            point_orig = np.array([[[cx_orig, cy_orig]]], dtype=np.float32)
            point_board = cv2.perspectiveTransform(point_orig, transform_matrix)[0][0]
            px, py = float(point_board[0]), float(point_board[1])
            
            # Vérifier que le point est dans les limites de l'image
            if not (0 <= px < self.board_size and 0 <= py < self.board_size):
                continue
            
            piece_data = self._build_piece_data(
                marker_id, piece_info, px, py, data['corners'],
                original_coords=(cx_orig, cy_orig)
            )
            pieces_list.append(piece_data)
        
        return pieces_list
    
    def _build_piece_data(
        self,
        marker_id: int,
        piece_info: dict,
        px: float,
        py: float,
        corners,
        original_coords: Tuple[float, float] = None
    ) -> Dict[str, Any]:
        """
        Construit le dictionnaire de données d'une pièce détectée.
        
        Args:
            marker_id: ID du marqueur ArUco
            piece_info: Infos de la pièce (code, color, type...)
            px, py: Coordonnées en pixels dans l'image extraite
            corners: Coins du marqueur ArUco
            original_coords: Coordonnées dans l'image originale (optionnel)
            
        Returns:
            Dict complet de la pièce
        """
        # Coordonnées étendues (-12.5 à +12.5)
        ext_x, ext_y = self.pixel_to_extended_coords(px, py)
        
        # Case de la grille 10x10 (A4, 08, H9...)
        grid_square = self.pixel_to_grid_square(px, py)
        
        # Case d'échecs standard (a4, None si cimetière)
        chess_square = self.pixel_to_chess_square(px, py)
        
        # Zone : plateau ou cimetière
        zone = 'board' if chess_square is not None else 'cemetery'
        
        piece_data = {
            'id': int(marker_id),
            'code': piece_info['code'],
            'color': piece_info['color'],
            'type': piece_info['type'],
            'initial': piece_info['initial'],
            'zone': zone,
            'position': {
                'pixel': {'x': float(px), 'y': float(py)},
                'board': {'x': ext_x, 'y': ext_y},
                'grid': grid_square,
                'chess': chess_square,
            },
            'corners': corners.tolist() if isinstance(corners, np.ndarray) else corners,
        }
        
        if original_coords is not None:
            piece_data['position']['original'] = {
                'x': original_coords[0], 'y': original_coords[1]
            }
        
        return piece_data


def draw_pieces_on_board(
    board_img: np.ndarray,
    pieces: List[Dict],
    draw_coords: bool = True,
    draw_ids: bool = True
) -> np.ndarray:
    """
    Dessine les pièces détectées sur l'image du plateau.
    Pièces du cimetière marquées visuellement différemment.
    
    Args:
        board_img: Image du plateau (1000x1000)
        pieces: Liste des pièces analysées
        draw_coords: Afficher les coordonnées board
        draw_ids: Afficher les IDs
        
    Returns:
        Image annotée
    """
    if board_img is None:
        return None
    
    img_annotated = board_img.copy()
    
    for piece in pieces:
        px = int(piece['position']['pixel']['x'])
        py = int(piece['position']['pixel']['y'])
        is_cemetery = piece.get('zone') == 'cemetery'
        
        # Couleurs selon la pièce
        if piece['color'] == 'white':
            fill_color = COLORS['white_piece']
            outline_color = (0, 0, 0)
        else:
            fill_color = COLORS['black_piece']
            outline_color = (255, 255, 255)
        
        # Cercle (contour rouge si cimetière)
        border_color = (0, 0, 200) if is_cemetery else outline_color
        cv2.circle(img_annotated, (px, py), 25, border_color, 3)
        cv2.circle(img_annotated, (px, py), 22, fill_color, -1)
        
        # Symbole de la pièce
        text = piece['type'][0]
        if piece['type'] == 'Knight':
            text = 'N'
        cv2.putText(img_annotated, text, (px - 8, py + 8),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, outline_color, 2)
        
        # ID
        if draw_ids:
            cv2.putText(img_annotated, f"ID:{piece['id']}", (px - 20, py - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # Coordonnées + case
        if draw_coords:
            coord_text = f"({piece['position']['board']['x']:.1f},{piece['position']['board']['y']:.1f})"
            cv2.putText(img_annotated, coord_text, (px - 35, py + 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)
            grid_label = piece['position'].get('grid', '??')
            cv2.putText(img_annotated, grid_label, (px - 12, py + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 255), 1)
    
    return img_annotated


def draw_pieces_aruco(
    board_img: np.ndarray,
    pieces: List[Dict]
) -> np.ndarray:
    """
    Dessine les contours ArUco des pièces détectées.
    
    Args:
        board_img: Image du plateau
        pieces: Liste des pièces analysées
        
    Returns:
        Image annotée
    """
    if board_img is None:
        return None
    
    img_annotated = board_img.copy()
    
    # Récupérer les corners pour cv2.aruco.drawDetectedMarkers
    if pieces:
        corners_list = []
        ids_list = []
        
        for piece in pieces:
            if 'corners' in piece:
                corners_array = np.array(piece['corners'], dtype=np.float32)
                corners_list.append(corners_array.reshape(1, 4, 2))
                ids_list.append(piece['id'])
        
        if corners_list:
            corners = tuple(corners_list)
            ids = np.array(ids_list)
            cv2.aruco.drawDetectedMarkers(img_annotated, corners, ids)
    
    # Ajouter infos supplémentaires
    for piece in pieces:
        px = int(piece['position']['pixel']['x'])
        py = int(piece['position']['pixel']['y'])
        
        # Couleur selon la pièce
        if piece['color'] == 'white':
            box_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            box_color = (50, 50, 50)
            text_color = (255, 255, 255)
        
        # Info text
        info_text = f"ID:{piece['id']} {piece['type'][0]}"
        if piece['type'] == 'Knight':
            info_text = f"ID:{piece['id']} N"
        
        text_x = px - 35
        text_y = py + 40
        
        (text_w, text_h), _ = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img_annotated, (text_x - 2, text_y - text_h - 2),
                     (text_x + text_w + 2, text_y + 4), box_color, -1)
        cv2.rectangle(img_annotated, (text_x - 2, text_y - text_h - 2),
                     (text_x + text_w + 2, text_y + 4), (0, 255, 0), 1)
        cv2.putText(img_annotated, info_text, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
    
    # Titre
    board_pieces = [p for p in pieces if p.get('zone') == 'board']
    cemetery_pieces = [p for p in pieces if p.get('zone') == 'cemetery']
    cv2.putText(img_annotated, f"Pieces: {len(pieces)} (plateau:{len(board_pieces)} cem:{len(cemetery_pieces)})",
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    white_count = len([p for p in pieces if p['color'] == 'white'])
    black_count = len([p for p in pieces if p['color'] == 'black'])
    cv2.putText(img_annotated, f"Blanches: {white_count} | Noires: {black_count}", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    return img_annotated


def get_pieces_summary(pieces: List[Dict]) -> Dict[str, Any]:
    """
    Génère un résumé des pièces détectées.
    Sépare les pièces sur le plateau et au cimetière.
    
    Args:
        pieces: Liste des pièces analysées
        
    Returns:
        Dict avec statistiques
    """
    white_pieces = [p for p in pieces if p['color'] == 'white']
    black_pieces = [p for p in pieces if p['color'] == 'black']
    board_pieces = [p for p in pieces if p.get('zone') == 'board']
    cemetery_pieces = [p for p in pieces if p.get('zone') == 'cemetery']
    
    # Grouper par type
    by_type = {}
    for piece in pieces:
        ptype = piece['type']
        if ptype not in by_type:
            by_type[ptype] = {'white': [], 'black': []}
        by_type[ptype][piece['color']].append(piece)
    
    return {
        'total': len(pieces),
        'white_count': len(white_pieces),
        'black_count': len(black_pieces),
        'on_board': len(board_pieces),
        'in_cemetery': len(cemetery_pieces),
        'white_ids': sorted([p['id'] for p in white_pieces]),
        'black_ids': sorted([p['id'] for p in black_pieces]),
        'by_type': {
            ptype: {
                'white': len(data['white']),
                'black': len(data['black']),
            }
            for ptype, data in by_type.items()
        },
        'board_positions': {
            p['position']['chess']: {
                'id': p['id'],
                'code': p['code'],
                'color': p['color'],
                'type': p['type'],
            }
            for p in board_pieces if p['position']['chess']
        },
        'cemetery_positions': {
            p['position']['grid']: {
                'id': p['id'],
                'code': p['code'],
                'color': p['color'],
                'type': p['type'],
            }
            for p in cemetery_pieces if p['position'].get('grid')
        },
    }
