import sys
from unittest.mock import MagicMock

# On définit les modules à mocker globalement
MOCK_MODULES = [
    "rtde_control",
    "rtde_receive",
    "dashboard_client",
    "robotiq_gripper_control"
]

def pytest_sessionstart(session):
    """S'exécute avant le lancement des tests"""
    mock_obj = MagicMock()
    for mod_name in MOCK_MODULES:
        sys.modules[mod_name] = mock_obj