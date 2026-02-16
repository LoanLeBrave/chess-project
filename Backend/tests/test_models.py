import pytest
import chess
from models import PieceEliminee, GameConfig


def test_piece_eliminee_to_dict():
    """Vérifie que la conversion en dictionnaire pour le Front-end est correcte"""
    pos_test = [0.1, 0.2, 0.3, 3.14, 0, 0]
    piece = PieceEliminee(
        piece_symbol="Q",
        color=chess.WHITE,
        case_origine="d1",
        position_elimination=pos_test,
        index=0
    )

    data = piece.to_dict()

    assert data["piece"] == "Q"
    assert data["color"] == "white"
    assert data["case_origine"] == "d1"
    assert data["position"] == pos_test
    assert data["index"] == 0


def test_game_config_default():
    """Vérifie que la difficulté par défaut est bien appliquée"""
    config = GameConfig()
    assert config.difficulty == "intermediate"