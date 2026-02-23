#!/usr/bin/env python3
"""
Modèles de données pour l'API du robot d'échecs
"""

from pydantic import BaseModel
from typing import List
import chess


# ============================================================================
#                         MODÈLES PYDANTIC
# ============================================================================

class MoveRequest(BaseModel):
    from_square: str
    to_square: str


class GameConfig(BaseModel):
    difficulty: str = "intermediate"


class RobotPosition(BaseModel):
    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float


# ============================================================================
#                         CLASSE PIÈCE ÉLIMINÉE
# ============================================================================

class PieceEliminee:
    """Représente une pièce éliminée et sa case de cimetière dans la grille 10x10"""

    def __init__(self, piece_symbol: str, color: bool, case_origine: str,
                 case_cimetiere: str, index: int):
        self.piece_symbol = piece_symbol  # 'P', 'N', 'B', 'R', 'Q', 'K' (majuscule)
        self.color = color  # chess.WHITE ou chess.BLACK
        self.case_origine = case_origine  # Case d'où la pièce a été capturée
        self.case_cimetiere = case_cimetiere  # Case de la grille 10x10, ex: "a0", "b9"
        self.index = index  # Index dans la liste du cimetière

    def to_dict(self):
        return {
            "piece": self.piece_symbol,
            "color": "white" if self.color == chess.WHITE else "black",
            "case_origine": self.case_origine,
            "case_cimetiere": self.case_cimetiere,
            "index": self.index
        }
