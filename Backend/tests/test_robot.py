import pytest
import chess
import math
from robot_controller import RobotController


@pytest.fixture
def robot():
    """Fixture qui initialise un contrôleur avec une calibration fictive"""
    r = RobotController()
    # On simule une calibration réussie
    r.calib_origin = [0.2, -0.1, 0.05]  # X, Y, Z du coin A1
    r.calib_rotation = 0.0
    r.calib_scale = 0.02  # 2cm par unité
    r.is_calibrated = True
    r.connected = False  # Mode simulation par défaut

    # On définit les zones d'élimination pour éviter les erreurs None
    r._calculate_dynamic_zones()
    return r


# ============================================================================
#                         TESTS GÉOMÉTRIQUES (MATHS)
# ============================================================================

def test_get_square_center_values(robot):
    """Vérifie le calcul des coordonnées caméra pour les cases clés"""
    # Case a1 (coin inférieur gauche)
    # file_idx=0, rank_idx=0 -> (0-3.5)*2.5 = -8.75
    cx, cy = robot.get_square_center("a1")
    assert cx == -8.75
    assert cy == -8.75

    # Case h8 (coin supérieur droit)
    # file_idx=7, rank_idx=7 -> (7-3.5)*2.5 = 8.75
    cx, cy = robot.get_square_center("h8")
    assert cx == 8.75
    assert cy == 8.75


def test_cam_to_robot_translation(robot):
    """Vérifie que la transformation caméra -> robot respecte l'origine et l'échelle"""
    # Centre de la caméra (0,0) doit correspondre à l'origine décalée du centre du plateau
    # Mais ici cam_to_robot ajoute simplement x_scaled à calib_origin[0]
    res = robot.cam_to_robot(10, 0, use_piece_height=False)

    # x_scaled = 10 * 0.02 = 0.2
    # robot_x = 0.2 (origin) + 0.2 = 0.4
    assert pytest.approx(res[0]) == 0.4
    assert res[1] == -0.1  # Y origin


# ============================================================================
#                         TESTS LOGIQUE DE JEU
# ============================================================================

def test_pieces_eliminees_storage(robot):
    """Vérifie que le dictionnaire des pièces éliminées est bien structuré"""
    # Simuler une pièce déjà là
    mock_piece = MagicMock()
    mock_piece.to_dict.return_value = {"symbol": "P", "color": True}
    robot.pieces_blanches_eliminees.append(mock_piece)

    data = robot.get_pieces_eliminees()
    assert "blanches" in data
    assert len(data["blanches"]) == 1
    assert "noires" in data


@pytest.mark.asyncio
async def test_execute_move_uncalibrated(robot):
    """Vérifie que le robot refuse de bouger s'il n'est pas calibré"""
    robot.is_calibrated = False
    result = await robot.execute_move("e2", "e4", False)
    assert result is False


# ============================================================================
#                         TESTS DE SÉCURITÉ
# ============================================================================

def test_close_connection(robot):
    """Vérifie que la fermeture ne crash pas si rtde_c est None"""
    robot.rtde_c = None
    # Ne doit pas lever d'exception
    robot.close()