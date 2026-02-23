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


class ReplaceBoardResponse(BaseModel):
    """Reponse de l'endpoint POST /game/replace-board"""
    success: bool
    message: str = ""
    moves_executed: int = 0
    total_planned: int = 0
    error: str = ""


# ============================================================================
#                         CLASSE PIÈCE ÉLIMINÉE
# ============================================================================

class PieceEliminee:
    """Représente une pièce éliminée et sa position de stockage"""

    def __init__(self, piece_symbol: str, color: bool, case_origine: str,
                 position_elimination: List[float], index: int):
        self.piece_symbol = piece_symbol  # 'P', 'N', 'B', 'R', 'Q', 'K' (majuscule)
        self.color = color  # chess.WHITE ou chess.BLACK
        self.case_origine = case_origine  # Case d'où la pièce a été capturée
        self.position_elimination = position_elimination  # Position TCP de stockage
        self.index = index  # Index dans la zone d'élimination

    def to_dict(self):
        return {
            "piece": self.piece_symbol,
            "color": "white" if self.color == chess.WHITE else "black",
            "case_origine": self.case_origine,
            "position": self.position_elimination,
            "index": self.index
        }
