#!/usr/bin/env python3
"""
API FastAPI pour le robot d'échecs
Routes et WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio
import json
import chess
from datetime import datetime

from models import MoveRequest, GameConfig
from robot_controller import RobotController
from chess_manager import ChessManager


# ============================================================================
#                         APPLICATION FASTAPI
# ============================================================================

app = FastAPI(title="Chess Robot API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
#                         GESTIONNAIRE GLOBAL
# ============================================================================

class ApplicationManager:
    """Gestionnaire global de l'application"""

    def __init__(self):
        self.robot = RobotController()
        self.chess = ChessManager(self.robot)
        self.status = "idle"
        self.websocket_clients: List[WebSocket] = []

        # Connecter les callbacks
        self.robot.set_log_callback(self.log)
        self.chess.set_broadcast_callback(self.broadcast)
        self.chess.set_log_callback(self.log)
        self.chess.set_status_callback(self.set_status)

    async def broadcast(self, message: dict):
        """Envoie un message à tous les clients WebSocket"""
        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except:
                pass

    def set_status(self, status: str, message: str = ""):
        """Met à jour le statut et notifie les clients"""
        self.status = status
        asyncio.create_task(self.broadcast({
            "type": "status",
            "status": status,
            "message": message
        }))

    async def log(self, log_type: str, message: str):
        """Envoie un log aux clients"""
        await self.broadcast({
            "type": "log",
            "logType": log_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })


# Instance globale
manager = ApplicationManager()


# ============================================================================
#                         ROUTES API
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialisation au démarrage"""
    manager.chess.init_stockfish()
    manager.robot.init_robot()


@app.on_event("shutdown")
async def shutdown():
    """Nettoyage à l'arrêt"""
    manager.chess.close()
    manager.robot.close()


@app.get("/")
async def root():
    return {"message": "Chess Robot API", "version": "2.0.0"}


@app.get("/status")
async def get_status():
    """Retourne le statut du robot"""
    return {
        "connected": manager.robot.connected,
        "status": manager.status,
        "difficulty": manager.chess.difficulty,
        "fen": manager.chess.board.fen(),
        "turn": "white" if manager.chess.board.turn == chess.WHITE else "black",
        "is_game_over": manager.chess.board.is_game_over(),
        "pieces_eliminees": manager.robot.get_pieces_eliminees()
    }


@app.post("/game/new")
async def new_game(config: GameConfig):
    """Démarre une nouvelle partie"""
    result = manager.chess.new_game(config.difficulty)
    await manager.log("info", f"Nouvelle partie - Difficulté: {config.difficulty}")
    return result


@app.get("/game/fen")
async def get_fen():
    """Retourne la position FEN actuelle"""
    return {"fen": manager.chess.board.fen()}


@app.get("/game/legal-moves/{square}")
async def get_legal_moves(square: str):
    """Retourne les coups légaux pour une case"""
    moves = manager.chess.get_legal_moves(square)
    return {"square": square, "moves": moves}


@app.get("/game/best-move")
async def get_best_move():
    """Retourne le meilleur coup pour le joueur actuel"""
    return manager.chess.get_best_move()


@app.post("/game/move/human")
async def human_move(move: MoveRequest):
    """Joue le coup du joueur humain"""
    result = await manager.chess.play_human_move(move.from_square, move.to_square)
    return result


@app.post("/game/move/robot")
async def robot_move():
    """Demande au robot de jouer son coup"""
    result = await manager.chess.play_robot_move()
    return result


@app.get("/game/pieces-eliminees")
async def get_pieces_eliminees():
    """Retourne la liste des pièces éliminées"""
    return manager.robot.get_pieces_eliminees()


@app.post("/game/reset-plateau")
async def reset_plateau():
    """Remet toutes les pièces à leur position initiale"""
    await manager.log("info", "Demande de reset du plateau")
    result = await manager.chess.reset_plateau_with_board()
    return result


@app.post("/game/stop")
async def stop_game():
    """Arrête la partie et remet le plateau en place"""
    await manager.log("info", "Arrêt de la partie demandé")

    result = await manager.chess.reset_plateau_with_board()

    if result.get("success"):
        await manager.broadcast({"type": "game_stopped", "message": "Partie arrêtée, plateau remis en place"})

    return result


@app.get("/robot/position")
async def get_robot_position():
    """Retourne la position actuelle du robot"""
    position = manager.robot.get_position()
    if position is None:
        return {"error": "Robot non connecté"}
    return position


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les mises à jour en temps réel"""
    await websocket.accept()
    manager.websocket_clients.append(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "status": manager.status,
            "fen": manager.chess.board.fen(),
            "robot_connected": manager.robot.connected,
            "pieces_eliminees": manager.robot.get_pieces_eliminees()
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.websocket_clients.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in manager.websocket_clients:
            manager.websocket_clients.remove(websocket)
