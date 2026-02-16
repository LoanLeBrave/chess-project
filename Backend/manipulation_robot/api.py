#!/usr/bin/env python3
"""
API FastAPI pour le robot d'échecs
Routes et WebSocket - Version complète
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
    allow_origins=["*"],  # En production, spécifier l'origine exacte
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
        disconnected = []
        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except:
                disconnected.append(client)
        
        # Nettoyer les clients déconnectés
        for client in disconnected:
            self.websocket_clients.remove(client)

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
    print("🚀 Démarrage de l'API Chess Robot...")
    manager.chess.init_stockfish()
    manager.robot.init_robot()
    print("✅ API prête!")


@app.on_event("shutdown")
async def shutdown():
    """Nettoyage à l'arrêt"""
    print("🛑 Arrêt de l'API...")
    manager.chess.close()
    manager.robot.close()
    print("✅ Arrêt propre effectué")


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "Chess Robot API",
        "version": "2.0.0",
        "status": "operational"
    }


@app.get("/status")
async def get_status():
    """Retourne le statut complet du système"""
    return {
        "connected": manager.robot.connected,
        "status": manager.status,
        "paused": getattr(manager.chess, 'is_paused', False),
        "difficulty": manager.chess.difficulty,
        "fen": manager.chess.board.fen(),
        "turn": "white" if manager.chess.board.turn == chess.WHITE else "black",
        "is_game_over": manager.chess.board.is_game_over(),
        "pieces_eliminees": manager.robot.get_pieces_eliminees(),
        "game_result": manager.chess.get_game_result() if manager.chess.board.is_game_over() else None
    }


@app.post("/game/new")
async def new_game(config: GameConfig):
    """Démarre une nouvelle partie"""
    result = manager.chess.new_game(config.difficulty)
    await manager.log("info", f"🎮 Nouvelle partie - Difficulté: {config.difficulty}")
    await manager.broadcast({
        "type": "game_started",
        "difficulty": config.difficulty,
        "fen": manager.chess.board.fen()
    })
    return result


@app.get("/game/fen")
async def get_fen():
    """Retourne la position FEN actuelle"""
    return {
        "fen": manager.chess.board.fen(),
        "turn": "white" if manager.chess.board.turn == chess.WHITE else "black"
    }


@app.post("/game/pause")
async def toggle_pause():
    """Bascule l'état de pause de la partie (Arrêt d'urgence)"""
    await manager.log("info", "⏸️ Demande de bascule de pause reçue")
    result = await manager.chess.toggle_pause()
    
    # Notifier tous les clients
    await manager.broadcast({
        "type": "pause_toggled",
        "paused": result.get("paused", False),
        "message": result.get("message", "")
    })
    
    return result


@app.post("/game/stop")
async def stop_game():
    """Arrête la partie et remet le plateau en place"""
    await manager.log("info", "🛑 Arrêt de la partie demandé")
    
    # Remettre le plateau en position initiale
    result = await manager.chess.reset_plateau_with_board()

    if result.get("success"):
        await manager.broadcast({
            "type": "game_stopped",
            "message": "Partie arrêtée, plateau remis en place"
        })
        await manager.log("info", "✅ Partie arrêtée et plateau réinitialisé")
    else:
        await manager.log("error", "❌ Échec de la réinitialisation du plateau")

    return result


@app.post("/game/reset-plateau")
async def reset_plateau():
    """Remet toutes les pièces à leur position initiale"""
    await manager.log("info", "🔄 Demande de reset du plateau")
    result = await manager.chess.reset_plateau_with_board()
    
    if result.get("success"):
        await manager.broadcast({
            "type": "plateau_reset",
            "fen": manager.chess.board.fen()
        })
    
    return result


@app.get("/game/legal-moves/{square}")
async def get_legal_moves(square: str):
    """Retourne les coups légaux pour une case"""
    moves = manager.chess.get_legal_moves(square)
    return {
        "square": square,
        "moves": moves,
        "count": len(moves)
    }


@app.get("/game/best-move")
async def get_best_move():
    """Retourne le meilleur coup pour le joueur actuel avec évaluation"""
    result = manager.chess.get_best_move()
    
    if result.get("success"):
        await manager.log("info", f"💡 Suggestion: {result.get('from')} → {result.get('to')} (eval: {result.get('evaluation')})")
    
    return result


@app.post("/game/move/human")
async def human_move(move: MoveRequest):
    """Joue le coup du joueur humain"""
    await manager.log("info", f"👤 Coup humain: {move.from_square} → {move.to_square}")
    result = await manager.chess.play_human_move(move.from_square, move.to_square)
    return result


@app.post("/game/move/robot")
async def robot_move():
    """Demande au robot de jouer son coup"""
    await manager.log("info", "🤖 Le robot réfléchit...")
    result = await manager.chess.play_robot_move()
    return result


@app.get("/game/pieces-eliminees")
async def get_pieces_eliminees():
    """Retourne la liste des pièces éliminées"""
    pieces = manager.robot.get_pieces_eliminees()
    return {
        "pieces_eliminees": pieces,
        "count": len(pieces)
    }


@app.get("/robot/position")
async def get_robot_position():
    """Retourne la position actuelle du robot"""
    position = manager.robot.get_position()
    if position is None:
        return {"error": "Robot non connecté"}
    return position


@app.get("/robot/gripper-state")
async def get_gripper_state():
    """Retourne l'état du gripper"""
    if not manager.robot.connected or not manager.robot.gripper:
        return {"error": "Robot ou gripper non connecté"}
    
    try:
        # Ces méthodes dépendent de votre implémentation du gripper
        return {
            "connected": True,
            "position": manager.robot.gripper.get_current_position() if hasattr(manager.robot.gripper, 'get_current_position') else None,
            "status": "operational"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/game/history")
async def get_game_history():
    """Retourne l'historique des coups de la partie"""
    moves = []
    board_copy = chess.Board()
    
    for move in manager.chess.board.move_stack:
        san = board_copy.san(move)
        moves.append({
            "from": chess.square_name(move.from_square),
            "to": chess.square_name(move.to_square),
            "san": san,
            "uci": move.uci()
        })
        board_copy.push(move)
    
    return {
        "moves": moves,
        "move_count": len(moves),
        "current_fen": manager.chess.board.fen()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les mises à jour en temps réel"""
    await websocket.accept()
    manager.websocket_clients.append(websocket)
    
    print(f"🔌 Nouveau client WebSocket connecté (total: {len(manager.websocket_clients)})")

    try:
        # Envoyer le statut initial
        await websocket.send_json({
            "type": "connected",
            "status": manager.status,
            "paused": getattr(manager.chess, 'is_paused', False),
            "fen": manager.chess.board.fen(),
            "robot_connected": manager.robot.connected,
            "pieces_eliminees": manager.robot.get_pieces_eliminees(),
            "difficulty": manager.chess.difficulty
        })

        # Boucle de réception des messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Traiter les commandes WebSocket
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            elif message.get("type") == "get_status":
                await websocket.send_json({
                    "type": "status_update",
                    "status": manager.status,
                    "paused": getattr(manager.chess, 'is_paused', False),
                    "fen": manager.chess.board.fen()
                })

    except WebSocketDisconnect:
        manager.websocket_clients.remove(websocket)
        print(f"🔌 Client WebSocket déconnecté (restants: {len(manager.websocket_clients)})")
    except Exception as e:
        print(f"❌ Erreur WebSocket: {e}")
        if websocket in manager.websocket_clients:
            manager.websocket_clients.remove(websocket)


# ============================================================================
#                         MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("     ♔ CHESS ROBOT API ♚")
    print("=" * 60)
    print("\n🚀 Démarrage du serveur...")
    print("📍 Interface: http://localhost:8000")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
