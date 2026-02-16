import pytest
from chess_vision.generate_aruco_pieces import mm_to_pixels, DPI

def test_mm_to_pixels():
    # Test simple : 25.4 mm = 1 inch, donc à 300 DPI, 25.4 mm -> 300 pixels
    assert mm_to_pixels(25.4) == 300
    # Test zéro
    assert mm_to_pixels(0) == 0
    # Test valeur négative
    assert mm_to_pixels(-25.4) == -300
    # Test valeur décimale
    assert mm_to_pixels(12.7) == 150