#!/usr/bin/env python3
"""
Module de détection des marqueurs ArUco.
Gère la détection des marqueurs de calibration (coins du plateau) et des pièces.

Classes:
    - ArucoDetector: Détecteur ArUco configuré avec paramètres optimisés

Fonctions:
    - detect_all_markers(): Détecte tous les marqueurs dans une image
    - detect_calibration_markers(): Détecte uniquement les marqueurs de calibration
    - detect_piece_markers(): Détecte uniquement les marqueurs des pièces
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Any

from .config import (
    ARUCO_DICT_TYPE,
    ARUCO_PARAMS,
    USE_DEFAULT_ARUCO_PARAMS,
    CALIBRATION_IDS,
    PIECE_IDS,
    is_calibration_marker,
    is_piece_marker,
    get_piece_info,
    get_calibration_code,
)


class ArucoDetector:
    """
    Détecteur ArUco avec paramètres configurables.
    
    Attributes:
        aruco_dict: Dictionnaire ArUco utilisé
        detector: Détecteur OpenCV ArUco
        
    Usage:
        detector = ArucoDetector()
        markers = detector.detect(image)
    """
    
    def __init__(self, use_default_params=None):
        """
        Initialise le détecteur ArUco.
        
        Args:
            use_default_params: Si True, utilise les params par défaut OpenCV.
                               Si None, utilise la config globale.
        """
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
        self.parameters = self._create_parameters(use_default_params)
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)
    
    def _create_parameters(self, use_default=None) -> cv2.aruco.DetectorParameters:
        """Crée les paramètres de détection."""
        params = cv2.aruco.DetectorParameters()
        
        use_defaults = use_default if use_default is not None else USE_DEFAULT_ARUCO_PARAMS
        
        if not use_defaults:
            params.adaptiveThreshWinSizeMin = ARUCO_PARAMS['adaptiveThreshWinSizeMin']
            params.adaptiveThreshWinSizeMax = ARUCO_PARAMS['adaptiveThreshWinSizeMax']
            params.adaptiveThreshWinSizeStep = ARUCO_PARAMS['adaptiveThreshWinSizeStep']
            params.adaptiveThreshConstant = ARUCO_PARAMS['adaptiveThreshConstant']
            params.minMarkerPerimeterRate = ARUCO_PARAMS['minMarkerPerimeterRate']
            params.maxMarkerPerimeterRate = ARUCO_PARAMS['maxMarkerPerimeterRate']
            params.polygonalApproxAccuracyRate = ARUCO_PARAMS['polygonalApproxAccuracyRate']
            params.minCornerDistanceRate = ARUCO_PARAMS['minCornerDistanceRate']
            params.minDistanceToBorder = ARUCO_PARAMS['minDistanceToBorder']
            params.minMarkerDistanceRate = ARUCO_PARAMS['minMarkerDistanceRate']
            params.cornerRefinementMethod = ARUCO_PARAMS['cornerRefinementMethod']
            params.cornerRefinementWinSize = ARUCO_PARAMS['cornerRefinementWinSize']
            params.cornerRefinementMaxIterations = ARUCO_PARAMS['cornerRefinementMaxIterations']
            params.cornerRefinementMinAccuracy = ARUCO_PARAMS['cornerRefinementMinAccuracy']
        
        return params
    
    def detect(self, image: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """
        Détecte tous les marqueurs ArUco dans une image.
        
        Args:
            image: Image numpy (BGR ou grayscale)
            
        Returns:
            Dict {marker_id: {'center': (x, y), 'corners': array, 'size': float}}
        """
        # Conversion en niveaux de gris si nécessaire
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Détection
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        results = {}
        
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                marker_id = int(marker_id)
                marker_corners = corners[i][0]
                
                # Calculer le centre
                center_x = marker_corners[:, 0].mean()
                center_y = marker_corners[:, 1].mean()
                
                # Calculer la taille approximative (diagonal moyenne)
                diag1 = np.linalg.norm(marker_corners[0] - marker_corners[2])
                diag2 = np.linalg.norm(marker_corners[1] - marker_corners[3])
                size = (diag1 + diag2) / 2
                
                results[marker_id] = {
                    'center': (center_x, center_y),
                    'corners': marker_corners,
                    'size': size,
                }
        
        return results
    
    def detect_with_rejected(self, image: np.ndarray) -> Tuple[Dict[int, Dict], List]:
        """
        Détecte les marqueurs et retourne aussi les candidats rejetés.
        
        Args:
            image: Image numpy (BGR ou grayscale)
            
        Returns:
            Tuple (markers_dict, rejected_corners)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        results = {}
        
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                marker_id = int(marker_id)
                marker_corners = corners[i][0]
                
                center_x = marker_corners[:, 0].mean()
                center_y = marker_corners[:, 1].mean()
                
                results[marker_id] = {
                    'center': (center_x, center_y),
                    'corners': marker_corners,
                }
        
        return results, rejected


def detect_calibration_markers(image: np.ndarray, detector=None) -> Dict[int, Dict]:
    """
    Détecte uniquement les marqueurs de calibration (IDs 32-35).
    
    Args:
        image: Image numpy (BGR)
        detector: Détecteur ArUco (optionnel, créé automatiquement si None)
        
    Returns:
        Dict {marker_id: {'center': (x, y), 'corners': array, 'code': 'TL/TR/BL/BR'}}
    """
    if detector is None:
        detector = ArucoDetector()
    
    all_markers = detector.detect(image)
    
    calibration_markers = {}
    
    for marker_id, data in all_markers.items():
        if is_calibration_marker(marker_id):
            calibration_markers[marker_id] = {
                **data,
                'code': get_calibration_code(marker_id),
            }
    
    return calibration_markers


def detect_piece_markers(image: np.ndarray, detector=None) -> Dict[int, Dict]:
    """
    Détecte uniquement les marqueurs des pièces d'échecs (IDs 0-31).
    
    Args:
        image: Image numpy (BGR)
        detector: Détecteur ArUco (optionnel)
        
    Returns:
        Dict {marker_id: {'center': (x, y), 'corners': array, 'piece_info': {...}}}
    """
    if detector is None:
        detector = ArucoDetector()
    
    all_markers = detector.detect(image)
    
    piece_markers = {}
    
    for marker_id, data in all_markers.items():
        if is_piece_marker(marker_id):
            piece_markers[marker_id] = {
                **data,
                'piece_info': get_piece_info(marker_id),
            }
    
    return piece_markers


def draw_detected_markers(
    image: np.ndarray,
    markers: Dict[int, Dict],
    draw_ids: bool = True,
    draw_centers: bool = True,
    color: Tuple[int, int, int] = (0, 255, 0)
) -> np.ndarray:
    """
    Dessine les marqueurs détectés sur une image.
    
    Args:
        image: Image numpy (BGR)
        markers: Dict des marqueurs détectés
        draw_ids: Dessiner les IDs
        draw_centers: Dessiner les centres
        color: Couleur des annotations (BGR)
        
    Returns:
        Image annotée
    """
    img_annotated = image.copy()
    
    for marker_id, data in markers.items():
        corners = data['corners'].astype(np.int32)
        center = data['center']
        
        # Dessiner le contour
        pts = corners.reshape((-1, 1, 2))
        cv2.polylines(img_annotated, [pts], True, color, 2)
        
        # Dessiner le centre
        if draw_centers:
            cx, cy = int(center[0]), int(center[1])
            cv2.circle(img_annotated, (cx, cy), 5, (0, 0, 255), -1)
        
        # Dessiner l'ID
        if draw_ids:
            cx, cy = int(center[0]), int(center[1])
            label = str(marker_id)
            cv2.putText(img_annotated, label, (cx - 10, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(img_annotated, label, (cx - 10, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
    
    return img_annotated


def get_detection_summary(markers: Dict[int, Dict]) -> Dict[str, Any]:
    """
    Génère un résumé des marqueurs détectés.
    
    Args:
        markers: Dict des marqueurs détectés
        
    Returns:
        Dict avec statistiques de détection
    """
    calibration_count = sum(1 for mid in markers if is_calibration_marker(mid))
    piece_count = sum(1 for mid in markers if is_piece_marker(mid))
    
    white_pieces = [mid for mid in markers if is_piece_marker(mid) and mid < 16]
    black_pieces = [mid for mid in markers if is_piece_marker(mid) and mid >= 16]
    
    calibration_status = {
        32: 32 in markers,
        33: 33 in markers,
        34: 34 in markers,
        35: 35 in markers,
    }
    
    return {
        'total': len(markers),
        'calibration_count': calibration_count,
        'calibration_complete': calibration_count == 4,
        'calibration_status': calibration_status,
        'piece_count': piece_count,
        'white_count': len(white_pieces),
        'black_count': len(black_pieces),
        'white_ids': sorted(white_pieces),
        'black_ids': sorted(black_pieces),
    }
