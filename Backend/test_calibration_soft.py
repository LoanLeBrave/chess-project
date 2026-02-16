import sys
from unittest.mock import MagicMock, patch
from unittest.mock import MagicMock, patch, ANY, mock_open

# --- MOCK DES MODULES MATÉRIELS ET SYSTÈME ---
mock_hardware = MagicMock()
sys.modules["rtde_control"] = mock_hardware
sys.modules["rtde_receive"] = mock_hardware
sys.modules["robotiq_gripper_control"] = mock_hardware
# On mock termios et tty pour éviter de casser le terminal pendant les tests
sys.modules["termios"] = MagicMock()
sys.modules["tty"] = MagicMock()

import pytest
import math
from calibration import TwoPointCalibration


@pytest.fixture
def calib():
    """Initialise une instance de calibration avec des mocks"""
    c = TwoPointCalibration()
    c.rtde_c = MagicMock()
    c.rtde_r = MagicMock()
    return c


# ============================================================================
#                          TESTS GÉOMÉTRIQUES (MATHS)
# ============================================================================

def test_calculate_geometry_logic(calib):
    """
    Vérifie les calculs de rotation, taille et échelle.
    On simule deux points formant une diagonale parfaite à 45°.
    """
    # Point 1 (A8) : [0, 0, 0]
    # Point 2 (H1) : [0.1, 0.1, 0]
    # La distance entre trous sera sqrt(0.1^2 + 0.1^2) = 0.1414...
    p1 = [0.0, 0.0, 0.0, 0, 0, 0]
    p2 = [0.1, 0.1, 0.0, 0, 0, 0]

    # On patche OFFSET_TROU_M pour le test (ex: 2cm = 0.02)
    with patch('calibration.OFFSET_TROU_M', 0.02):
        data = calib.calculate_geometry(p1, p2)

        # 1. Distance et Taille
        # dist_trous = 0.1414...
        # side_inner = dist_trous / sqrt(2) = 0.1
        # board_size = 0.1 + (2 * 0.02) = 0.14
        assert pytest.approx(data["board_size"]) == 0.14

        # 2. Rotation
        # atan2(0.1, 0.1) = 45° (pi/4)
        # rotation = angle_diag + 45° = 90° (pi/2)
        assert pytest.approx(data["rotation"]) == math.pi / 2

        # 3. Centre (Origin)
        assert data["origin"] == [0.05, 0.05, 0.0]


# ============================================================================
#                         TESTS DES FLUX (MOCKS)
# ============================================================================

def test_init_robot_failure(calib):
    """Vérifie que l'échec de connexion est géré"""
    with patch('calibration.RTDEControlInterface', side_effect=Exception("Timeout")):
        success = calib.init_robot()
        assert success is False
        assert calib.connected is False


@patch('calibration.TwoPointCalibration.get_key_non_blocking')
def test_interactive_positioning_validation(mock_key, calib):
    """Simule un utilisateur qui appuie sur 'q' pour valider immédiatement"""
    # On configure le mock pour renvoyer 'q' au premier appel
    mock_key.return_value = 'q'

    # On simule une position TCP actuelle du robot
    fake_pose = [0.1, 0.2, 0.3, 3.14, 0, 0]
    calib.rtde_r.getActualTCPPose.return_value = fake_pose

    result = calib.interactive_positioning("Test Step")

    assert result == fake_pose
    calib.rtde_c.speedStop.assert_called()


def test_save_calibration_file(calib):
    """Vérifie la création du fichier JSON sans encombre"""
    test_data = {"origin": [0, 0, 0], "rotation": 1.5}

    # mock_open simule parfaitement le comportement d'un fichier (le 'with open...')
    m = mock_open()
    with patch("builtins.open", m):
        with patch("json.dump") as mock_json:
            calib.save(test_data)

            # On vérifie que json.dump a été appelé avec :
            # 1. Nos données
            # 2. Le handle du fichier (n'importe lequel, d'où le ANY)
            # 3. L'indentation à 4
            mock_json.assert_called_once_with(test_data, ANY, indent=4)

    # Bonus : on vérifie que le bon fichier a été ouvert en écriture ('w')
    m.assert_called_once_with("robot_calibration.json", 'w')
    # Ou plus simple si tu connais le chemin :
    # m.assert_called_once_with("votre_chemin/calibration.json", 'w')