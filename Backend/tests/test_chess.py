import sys
from unittest.mock import MagicMock, AsyncMock, patch  # <--- Il manquait MagicMock ici !

# --- TRICK: On neutralise les imports matériels ---
mock_hardware = MagicMock()
sys.modules["rtde_control"] = mock_hardware
sys.modules["rtde_receive"] = mock_hardware
sys.modules["dashboard_client"] = mock_hardware
sys.modules["robotiq_gripper_control"] = mock_hardware

import pytest
import chess
from chess_manager import ChessManager


# ============================================================================
#                                FIXTURES
# ============================================================================

@pytest.fixture
def mock_robot():
    """Crée un mock du RobotController avec les méthodes nécessaires"""
    robot = MagicMock()
    # On définit explicitement les méthodes asynchrones
    robot.execute_move = AsyncMock(return_value=True)
    robot.reset_plateau = AsyncMock(return_value={"success": True})
    robot.reset_tracking = MagicMock()
    return robot


@pytest.fixture
def manager(mock_robot):
    """Initialise le ChessManager avec le robot mocké"""
    return ChessManager(mock_robot)


# ============================================================================
#                            TESTS DE LOGIQUE
# ============================================================================

def test_get_legal_moves_standard(manager):
    """Vérifie les coups légaux pour un pion en début de partie (e2)"""
    moves = manager.get_legal_moves("e2")
    assert "e3" in moves
    assert "e4" in moves
    assert len(moves) == 2


@pytest.mark.asyncio
async def test_play_human_move_success(manager):
    """Vérifie qu'un coup humain valide met à jour le plateau"""
    manager.broadcast_callback = AsyncMock()

    result = await manager.play_human_move("e2", "e4")

    assert result["success"] is True
    assert manager.board.piece_at(chess.E4) is not None
    manager.robot.execute_move.assert_called_once()


@pytest.mark.asyncio
async def test_play_robot_move_mocked_engine(manager):
    """Vérifie le coup du robot en simulant Stockfish et les presets"""
    mock_engine = MagicMock()

    # Simuler un score pour l'évaluation
    mock_score = MagicMock()
    mock_score.relative.score.return_value = 100  # +1.0

    # On simule un retour de Stockfish : il veut jouer g1 -> f3
    mock_info = {
        "pv": [chess.Move.from_uci("g1f3")],
        "score": mock_score
    }
    mock_engine.analyse.return_value = mock_info
    manager.engine = mock_engine

    # On s'assure que la difficulté existe pour éviter un crash sur les PRESETS
    manager.difficulty = "intermediate"

    result = await manager.play_robot_move()

    assert result["success"] is True
    assert result["from"] == "g1"
    assert result["to"] == "f3"
    assert result["evaluation"] == 1.0