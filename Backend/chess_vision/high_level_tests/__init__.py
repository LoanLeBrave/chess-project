#!/usr/bin/env python3
"""
Package de tests pour chess_vision.

Ce package contient des tests unitaires et de debug pour chaque module:
- test_aruco_detection: Test de détection des ArUcos
- test_board_calibration: Test de calibration et extraction du plateau
- test_piece_analysis: Test d'analyse des pièces
- test_full_pipeline: Test du pipeline complet

Usage:
    python -m chess_vision.tests.run_all_tests --image photo.jpg
    python -m chess_vision.tests.test_aruco_detection --image photo.jpg
    python -m chess_vision.tests.test_board_calibration --image photo.jpg
"""

from .test_utils import (
    TestLogger,
    DebugImageSaver,
    Colors,
    timed,
    catch_errors,
    validate_image,
    validate_markers,
    load_test_image,
    find_test_images,
    draw_debug_info
)

__all__ = [
    'TestLogger',
    'DebugImageSaver',
    'Colors',
    'timed',
    'catch_errors',
    'validate_image',
    'validate_markers',
    'load_test_image',
    'find_test_images',
    'draw_debug_info'
]
