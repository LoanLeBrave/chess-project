#!/usr/bin/env python3
"""
API FastAPI pour le robot d'échecs
Routes et WebSocket - Version complète
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
import json
import chess
from datetime import datetime

import math
import time

from models import MoveRequest, GameConfig
from robot_controller import RobotController
from chess_manager import ChessManager
from leaderboard_manager import LeaderboardManager
from config import FICHIER_CALIBRATION
from calibration import TwoPointCalibration


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
        self.leaderboard = LeaderboardManager()
        self.status = "idle"
        self.websocket_clients: List[WebSocket] = []

        # Etat de calibration (points enregistres pendant la session)
        self.calib_points: dict = {}  # 'a1', 'h8', 'z' -> [x, y, z, rx, ry, rz]

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


# ============================================================================
#                         ROUTES CALIBRATION
# ============================================================================

@app.post("/robot/calibrate/freedrive")
async def calibrate_freedrive(data: dict):
    """Active ou desactive le mode freedrive (XY uniquement)"""
    if not manager.robot.connected or not manager.robot.rtde_c:
        return {"success": False, "error": "Robot non connecte"}

    enable = data.get("enable", True)
    try:
        if enable:
            # Freedrive contraint sur X et Y uniquement
            manager.robot.rtde_c.freedriveMode([1, 1, 0, 0, 0, 0])
            await manager.log("info", "Mode FreeDrive active (X/Y)")
        else:
            manager.robot.rtde_c.endFreedriveMode()
            time.sleep(0.1)
            manager.robot.rtde_c.reuploadScript()
            time.sleep(0.1)
            await manager.log("info", "Mode FreeDrive desactive")
        return {"success": True, "freedrive": enable}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/robot/calibrate/close-gripper")
async def calibrate_close_gripper():
    """Ferme le gripper pour la calibration (pointe fine dans le trou)"""
    if not manager.robot.connected or not manager.robot.gripper:
        return {"success": False, "error": "Robot ou gripper non connecte"}

    try:
        manager.robot.gripper.close()
        await manager.log("info", "Gripper ferme pour calibration")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/robot/calibrate/auto-level")
async def calibrate_auto_level():
    """Remet la pince parfaitement verticale [pi, 0, 0]"""
    if not manager.robot.connected or not manager.robot.rtde_c:
        return {"success": False, "error": "Robot non connecte"}

    try:
        # Desactiver freedrive si actif
        try:
            manager.robot.rtde_c.endFreedriveMode()
            time.sleep(0.1)
            manager.robot.rtde_c.reuploadScript()
            time.sleep(0.1)
        except:
            pass

        current = manager.robot.rtde_r.getActualTCPPose()
        vertical_pose = [current[0], current[1], current[2], 3.1415, 0.0, 0.0]
        manager.robot.rtde_c.moveL(vertical_pose, 0.2, 0.2)
        await manager.log("info", "Pince remise droite (auto-level)")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/robot/calibrate/move-z")
async def calibrate_move_z(data: dict):
    """Deplace le robot en Z (monter/descendre) pour la calibration"""
    if not manager.robot.connected or not manager.robot.rtde_c:
        return {"success": False, "error": "Robot non connecte"}

    direction = data.get("direction", "down")
    velocity = 0.01  # 1 cm/s - vitesse lente pour precision
    duration = 0.3   # Mouvement de 0.3 seconde par clic

    try:
        vel_z = velocity if direction == "up" else -velocity
        manager.robot.rtde_c.speedL([0, 0, vel_z, 0, 0, 0], 0.5, duration)
        # Attendre la fin du mouvement
        time.sleep(duration + 0.1)
        manager.robot.rtde_c.speedStop()

        pose = manager.robot.rtde_r.getActualTCPPose()
        return {
            "success": True,
            "z": round(pose[2], 4),
            "direction": direction
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/robot/calibrate/point")
async def calibrate_point(data: dict):
    """Enregistre la position actuelle du robot comme point de calibration"""
    if not manager.robot.connected or not manager.robot.rtde_r:
        return {"success": False, "error": "Robot non connecte"}

    point = data.get("point")  # 'a1', 'h8', ou 'z'
    if point not in ('a1', 'h8', 'z'):
        return {"success": False, "error": f"Point invalide: {point}"}

    try:
        pose = manager.robot.rtde_r.getActualTCPPose()
        manager.calib_points[point] = list(pose)
        await manager.log("info", f"Point {point.upper()} enregistre: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")

        # Remontee de securite apres A1 ou H8
        if point in ('a1', 'h8'):
            safe_pose = list(pose)
            safe_pose[2] += 0.1  # +10cm en Z
            manager.robot.rtde_c.moveL(safe_pose, 0.5, 0.3)
            await manager.log("info", "Remontee de securite effectuee")

        return {
            "success": True,
            "point": point,
            "position": {"x": pose[0], "y": pose[1], "z": pose[2]}
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/robot/calibrate/save")
async def calibrate_save():
    """Calcule la geometrie du plateau et sauvegarde la calibration"""
    required = ['a1', 'h8', 'z']
    missing = [p for p in required if p not in manager.calib_points]
    if missing:
        return {"success": False, "error": f"Points manquants: {missing}"}

    try:
        p1 = manager.calib_points['a1']   # Trou A8/A1
        p2 = manager.calib_points['h8']   # Trou H1/H8
        p_z = manager.calib_points['z']   # Surface Z

        # Utiliser les fonctions de calibration.py
        calib = TwoPointCalibration()
        calib_data = calib.calculate_geometry(p1, p2, p_z)
        calib.save(calib_data)

        # Recharger la calibration dans le robot controller
        manager.robot.calib_origin = calib_data["origin"]
        manager.robot.calib_rotation = calib_data["rotation"]
        manager.robot.calib_scale = calib_data["camera_scale"]
        manager.robot.is_calibrated = True

        # Remontee finale de securite
        pose = manager.robot.rtde_r.getActualTCPPose()
        safe_pose = list(pose)
        safe_pose[2] += 0.1
        manager.robot.rtde_c.moveL(safe_pose, 0.5, 0.3)

        await manager.log("info", f"Calibration sauvegardee (rotation={math.degrees(calib_data['rotation']):.2f}deg)")

        # Reinitialiser les points de calibration
        manager.calib_points.clear()

        return {
            "success": True,
            "board_size_mm": round(calib_data["board_size"] * 1000, 1),
            "rotation_deg": round(math.degrees(calib_data["rotation"]), 2)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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


# ============================================================================
#                         ROUTES LEADERBOARD
# ============================================================================

@app.get("/leaderboard")
async def get_leaderboard(limit: Optional[int] = None):
    """
    Récupère le classement des joueurs
    Query params:
      - limit: nombre maximum de joueurs à retourner
    """
    rankings = manager.leaderboard.get_leaderboard(limit=limit)
    return {
        "leaderboard": rankings,
        "count": len(rankings)
    }


@app.get("/leaderboard/player/{player_name}")
async def get_player_stats(player_name: str):
    """Récupère les statistiques détaillées d'un joueur"""
    stats = manager.leaderboard.get_player_stats(player_name)
    
    if stats is None:
        return {"error": "Joueur non trouvé", "found": False}
    
    return {
        "found": True,
        "stats": stats.to_dict()
    }


@app.post("/leaderboard/add-game")
async def add_game_to_leaderboard(data: dict):
    """
    Ajoute une partie au leaderboard
    Body JSON:
    {
      "player_name": "Alice",
      "acpl": 25.5,
      "result": "win",  // 'win', 'lose', 'abandoned'
      "difficulty": "intermediate",
      "moves_played": 45,
      "game_duration": 1234.5  // optionnel, en secondes
    }
    """
    try:
        success = manager.leaderboard.add_game(
            player_name=data['player_name'],
            acpl=data['acpl'],
            result=data['result'],
            difficulty=data['difficulty'],
            moves_played=data['moves_played'],
            game_duration=data.get('game_duration')
        )
        
        if success:
            await manager.log("info", f"🏆 Partie enregistrée pour {data['player_name']} (ACPL: {data['acpl']})")
            
            # Broadcaster la mise à jour du leaderboard
            await manager.broadcast({
                "type": "leaderboard_updated",
                "player": data['player_name'],
                "acpl": data['acpl'],
                "result": data['result']
            })
            
            return {"success": True, "message": "Partie enregistrée"}
        else:
            return {"success": False, "error": "Erreur lors de la sauvegarde"}
            
    except KeyError as e:
        return {"success": False, "error": f"Champ manquant: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/leaderboard/games")
async def get_all_games(player_name: Optional[str] = None, limit: Optional[int] = None):
    """
    Récupère toutes les parties
    Query params:
      - player_name: filtrer par joueur (optionnel)
      - limit: nombre maximum de parties (optionnel)
    """
    if limit:
        games = manager.leaderboard.get_recent_games(limit=limit)
    else:
        games = manager.leaderboard.get_all_games(player_name=player_name)
    
    return {
        "games": games,
        "count": len(games)
    }


@app.get("/leaderboard/statistics")
async def get_leaderboard_statistics():
    """Récupère les statistiques globales du leaderboard"""
    stats = manager.leaderboard.get_statistics()
    return stats


@app.delete("/leaderboard/player/{player_name}")
async def delete_player(player_name: str):
    """Supprime toutes les parties d'un joueur"""
    success = manager.leaderboard.delete_player(player_name)
    
    if success:
        await manager.log("info", f"🗑️ Joueur {player_name} supprimé du leaderboard")
        await manager.broadcast({
            "type": "leaderboard_updated",
            "action": "player_deleted",
            "player": player_name
        })
        return {"success": True, "message": f"Joueur {player_name} supprimé"}
    else:
        return {"success": False, "error": "Joueur non trouvé ou erreur"}


@app.delete("/leaderboard/clear")
async def clear_leaderboard():
    """Efface toutes les données du leaderboard (ATTENTION!)"""
    success = manager.leaderboard.clear_all()
    
    if success:
        await manager.log("warning", "🗑️ Leaderboard effacé complètement")
        await manager.broadcast({
            "type": "leaderboard_updated",
            "action": "cleared"
        })
        return {"success": True, "message": "Leaderboard effacé"}
    else:
        return {"success": False, "error": "Erreur lors de l'effacement"}


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
