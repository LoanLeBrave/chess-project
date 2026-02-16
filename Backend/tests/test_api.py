import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

# Maintenant on peut importer api sans crash
from api import app, manager

client = TestClient(app)


# ============================================================================
#                                FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def mock_dependencies():
    """
    Cette fixture mock les composants internes du manager.
    'create=True' permet de mocker des méthodes même si elles ne sont pas encore définies.
    """
    with patch.object(manager.robot, 'init_robot', create=True), \
         patch.object(manager.robot, 'get_pieces_eliminees', return_value=[], create=True), \
         patch.object(manager.robot, 'get_position', return_value={"x": 0, "y": 0, "z": 0}, create=True), \
         patch.object(manager.chess, 'init_stockfish', create=True), \
         patch.object(manager.chess, 'new_game', return_value={"success": True}, create=True):
        yield

# ============================================================================
#                            TESTS DES ROUTES API
# ============================================================================

def test_read_root():
    """Vérifie que la racine répond correctement"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Chess Robot API", "version": "2.0.0"}


def test_get_status():
    """Vérifie le format du statut"""
    # On force manuellement une FEN pour le test
    manager.chess.board.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "fen" in data
    assert data["turn"] == "white"


def test_post_new_game():
    """Vérifie la création d'une nouvelle partie avec le bon type de donnée"""
    # On envoie une string pour correspondre au type de GameConfig
    payload = {"difficulty": "hard"}
    response = client.post("/game/new", json=payload)

    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_human_move():
    """Test de l'envoi d'un coup humain"""
    # On mock la méthode asynchrone play_human_move
    with patch.object(manager.chess, 'play_human_move', new_callable=AsyncMock) as mock_move:
        mock_move.return_value = {"success": True, "move": "e2e4"}

        payload = {"from_square": "e2", "to_square": "e4"}
        response = client.post("/game/move/human", json=payload)

        assert response.status_code == 200
        assert response.json()["move"] == "e2e4"


# ============================================================================
#                          TESTS DES WEBSOCKETS
# ============================================================================

def test_websocket_connection():
    """Vérifie la connexion WebSocket et le système de Ping/Pong"""
    with client.websocket_connect("/ws") as websocket:
        # Au début, on doit recevoir le message de bienvenue
        data = websocket.receive_json()
        assert data["type"] == "connected"

        # Test du Ping
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"


# ============================================================================
#                         TESTS LOGIQUE MANAGER
# ============================================================================

@pytest.mark.asyncio
async def test_manager_broadcast():
    """Vérifie que le broadcast envoie bien aux clients connectés"""
    with client.websocket_connect("/ws") as websocket:
        # On force un broadcast via le manager
        test_message = {"type": "test", "content": "hello"}
        await manager.broadcast(test_message)

        # Le premier message est 'connected', le second sera notre broadcast
        _ = websocket.receive_json()
        data = websocket.receive_json()
        assert data == test_message