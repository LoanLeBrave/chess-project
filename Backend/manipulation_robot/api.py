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
import base64
import os
import sys

from collections import deque

from models import MoveRequest, GameConfig
from robot_controller import RobotController
from chess_manager import ChessManager
from leaderboard_manager import LeaderboardManager
from config import FICHIER_CALIBRATION
from calibration import TwoPointCalibration

# Ajouter le chemin chess_vision au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


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
#                         CHEMIN GAME_STATE
# ============================================================================

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_STATE_PATH = os.path.join(_BACKEND_DIR, "chess_vision", "output", "latest", "game_state.json")


# ============================================================================
#                         VISION SERVICE
# ============================================================================

class VisionService:
    """
    Appelle chess_vision() en continu et maintient un etat stabilise
    avec buffer temporel anti-hallucination.

    Deux modes de fonctionnement :
    - Mode actif : appelle chess_vision() directement (capture + analyse)
    - Mode passif : lit game_state.json si deja produit par un script externe
    """

    BUFFER_SIZE = 5          # Nombre de frames dans le buffer
    STABLE_THRESHOLD = 3     # Minimum de detections pour considerer stable
    DISAPPEAR_THRESHOLD = 5  # Toutes les frames sans piece = disparue

    def __init__(self):
        # Buffer par case : deque de N derniers etats (piece_code ou None)
        self._buffers: dict[str, deque] = {}
        # Dernier etat brut
        self.raw_board: dict[str, str] = {}
        # Etat stabilise
        self.stable_board: dict[str, str] = {}
        # Confiance par case (0.0 - 1.0)
        self.confidence: dict[str, float] = {}
        # Dernier game_state complet (pour coords precises)
        self.last_game_state: Optional[dict] = None
        # Timestamp derniere lecture
        self.last_timestamp: Optional[str] = None
        # Nombre de pieces detectees
        self.pieces_count: int = 0
        # Flag actif
        self.running: bool = False
        # Pipeline chess_vision (initialise au premier appel)
        self._pipeline = None
        # Mode actif (appelle chess_vision) vs passif (lit JSON)
        self.active_mode: bool = True
        # Erreur courante (pour debug)
        self.last_error: Optional[str] = None

    def _get_pipeline(self):
        """Initialise le pipeline chess_vision a la demande."""
        if self._pipeline is None:
            try:
                from chess_vision import ChessVisionPipeline
                self._pipeline = ChessVisionPipeline(save_visualization_images=False)
                if not self._pipeline.extractor.is_calibrated:
                    self.last_error = "Camera non calibree (board_calibration.json manquant)"
                    self._pipeline = None
                    return None
                self.last_error = None
            except Exception as e:
                self.last_error = f"Impossible d'initialiser chess_vision: {e}"
                self._pipeline = None
        return self._pipeline

    def _capture_and_analyze(self) -> Optional[dict]:
        """Appelle chess_vision pour capturer et analyser."""
        pipeline = self._get_pipeline()
        if pipeline is None:
            return None
        try:
            result = pipeline.capture_and_analyze(save_outputs=True)
            if result.get("success"):
                self.last_error = None
                return result.get("game_state")
            else:
                self.last_error = result.get("error", "Erreur inconnue")
                return None
        except Exception as e:
            self.last_error = f"Erreur capture: {e}"
            return None

    def _read_game_state(self) -> Optional[dict]:
        """Lit game_state.json de maniere safe (mode passif)."""
        if not os.path.exists(GAME_STATE_PATH):
            return None
        try:
            with open(GAME_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _get_board_map(self, game_state: dict) -> dict[str, str]:
        """Construit {case: code_piece} a partir du game_state."""
        board = {}
        for piece in game_state.get("pieces", []):
            if piece.get("zone") != "board":
                continue
            chess_pos = piece.get("position", {}).get("chess")
            if not chess_pos:
                continue
            color_char = "W" if piece.get("color") == "white" else "B"
            type_char = piece.get("type", "Pawn")[0]
            if piece.get("type") == "Knight":
                type_char = "N"
            board[chess_pos.lower()] = f"{color_char}{type_char}"
        return board

    def find_piece_at(self, square: str) -> Optional[dict]:
        """Retourne les donnees completes de la piece sur une case."""
        if not self.last_game_state:
            return None
        for piece in self.last_game_state.get("pieces", []):
            if piece.get("zone") != "board":
                continue
            chess_pos = piece.get("position", {}).get("chess")
            if chess_pos and chess_pos.lower() == square.lower():
                return piece
        return None

    def update(self) -> bool:
        """
        Capture + analyse (mode actif) ou lit le JSON (mode passif).
        Met a jour le buffer et calcule l'etat stabilise.
        Retourne True si une mise a jour a eu lieu.
        """
        # Mode actif : appeler chess_vision directement
        if self.active_mode:
            game_state = self._capture_and_analyze()
        else:
            game_state = self._read_game_state()

        if game_state is None:
            return False

        ts = game_state.get("metadata", {}).get("timestamp")
        if ts == self.last_timestamp:
            return False  # Pas de nouvelle donnee

        self.last_timestamp = ts
        self.last_game_state = game_state
        self.raw_board = self._get_board_map(game_state)
        self.pieces_count = len(self.raw_board)

        # Toutes les cases possibles
        all_squares = [f"{c}{r}" for c in "abcdefgh" for r in "12345678"]

        # Mettre a jour les buffers
        for sq in all_squares:
            if sq not in self._buffers:
                self._buffers[sq] = deque(maxlen=self.BUFFER_SIZE)
            self._buffers[sq].append(self.raw_board.get(sq))

        # Calculer l'etat stabilise et la confiance
        new_stable = {}
        new_confidence = {}
        for sq in all_squares:
            buf = self._buffers[sq]
            if len(buf) == 0:
                continue

            # Compter les occurrences de chaque piece sur cette case
            counts: dict[Optional[str], int] = {}
            for val in buf:
                counts[val] = counts.get(val, 0) + 1

            # Piece la plus frequente
            best_piece = max(counts, key=counts.get)
            best_count = counts[best_piece]

            if best_piece is not None and best_count >= self.STABLE_THRESHOLD:
                new_stable[sq] = best_piece
                new_confidence[sq] = best_count / len(buf)
            elif best_piece is None and best_count >= self.DISAPPEAR_THRESHOLD:
                # La piece a vraiment disparu
                new_confidence[sq] = 0.0
            else:
                # Pas assez stable — garder l'ancien etat stabilise si existant
                if sq in self.stable_board:
                    new_stable[sq] = self.stable_board[sq]
                    # Confiance degradee
                    none_count = counts.get(None, 0)
                    new_confidence[sq] = 1.0 - (none_count / len(buf))

        self.stable_board = new_stable
        self.confidence = new_confidence
        return True

    def get_state_message(self) -> dict:
        """Retourne le message WebSocket vision_state."""
        return {
            "type": "vision_state",
            "board": self.stable_board,
            "raw_board": self.raw_board,
            "confidence": self.confidence,
            "timestamp": self.last_timestamp or datetime.now().isoformat(),
            "pieces_count": self.pieces_count,
        }


# ============================================================================
#                         GESTIONNAIRE GLOBAL
# ============================================================================

class ApplicationManager:
    """Gestionnaire global de l'application"""

    def __init__(self):
        self.robot = RobotController()
        self.chess = ChessManager(self.robot)
        self.leaderboard = LeaderboardManager()
        self.vision = VisionService()

        # Injecter le VisionService dans le ChessManager
        self.chess.vision_service = self.vision
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

async def vision_loop():
    """Tache de fond : capture + analyse chess_vision et broadcast l'etat vision."""
    manager.vision.running = True
    mode = "actif (capture camera)" if manager.vision.active_mode else "passif (lecture JSON)"
    print(f"👁️ VisionService demarre en mode {mode}")
    while manager.vision.running:
        try:
            updated = manager.vision.update()
            if updated and manager.websocket_clients:
                await manager.broadcast(manager.vision.get_state_message())
        except Exception as e:
            print(f"[VisionService] Erreur: {e}")
        # En mode actif, chess_vision() prend ~2s, donc pas besoin de sleep long
        await asyncio.sleep(0.5 if manager.vision.active_mode else 1.0)


@app.get("/vision/status")
async def get_vision_status():
    """Retourne le statut du VisionService (debug)."""
    return {
        "running": manager.vision.running,
        "active_mode": manager.vision.active_mode,
        "last_error": manager.vision.last_error,
        "last_timestamp": manager.vision.last_timestamp,
        "pieces_count": manager.vision.pieces_count,
        "buffer_size": manager.vision.BUFFER_SIZE,
        "has_pipeline": manager.vision._pipeline is not None,
    }


@app.post("/vision/mode")
async def set_vision_mode(data: dict):
    """Change le mode du VisionService (actif/passif)."""
    active = data.get("active", True)
    manager.vision.active_mode = active
    manager.vision._pipeline = None  # Reset le pipeline
    mode = "actif" if active else "passif"
    await manager.log("info", f"VisionService passe en mode {mode}")
    return {"success": True, "active_mode": active}


@app.get("/vision/sync")
async def get_vision_sync():
    """Compare l'etat camera stabilise avec l'etat Stockfish."""
    sync_result = manager.chess.sync_with_vision(manager.vision.stable_board)
    return sync_result


@app.on_event("startup")
async def startup():
    """Initialisation au démarrage"""
    print("🚀 Démarrage de l'API Chess Robot...")
    manager.chess.init_stockfish()
    manager.robot.init_robot()
    asyncio.create_task(vision_loop())
    print("✅ API prête!")


@app.on_event("shutdown")
async def shutdown():
    """Nettoyage à l'arrêt"""
    print("🛑 Arrêt de l'API...")
    manager.vision.running = False
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


@app.post("/robot/calibrate/move-z/start")
async def calibrate_move_z_start(data: dict):
    """Demarre un mouvement continu en Z (appel au keydown)"""
    if not manager.robot.connected or not manager.robot.rtde_c:
        return {"success": False, "error": "Robot non connecte"}

    direction = data.get("direction", "down")
    velocity = 0.01  # 1 cm/s - vitesse lente pour precision

    try:
        vel_z = velocity if direction == "up" else -velocity
        # Duree longue (10s) - sera interrompu par stop
        manager.robot.rtde_c.speedL([0, 0, vel_z, 0, 0, 0], 0.5, 10.0)
        return {"success": True, "direction": direction}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/robot/calibrate/move-z/stop")
async def calibrate_move_z_stop():
    """Arrete immediatement le mouvement Z (appel au keyup)"""
    if not manager.robot.connected or not manager.robot.rtde_c:
        return {"success": False, "error": "Robot non connecte"}

    try:
        manager.robot.rtde_c.speedStop()
        pose = manager.robot.rtde_r.getActualTCPPose()
        return {"success": True, "z": round(pose[2], 4)}
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


# ============================================================================
#                         ROUTES CAMERA
# ============================================================================

@app.post("/camera/capture")
async def camera_capture():
    """Prend une photo et la renvoie en base64"""
    try:
        from chess_vision.modules.camera import take_photo
        from PIL import Image

        photo_path = take_photo()

        # Lire les dimensions
        with Image.open(photo_path) as img:
            width, height = img.size

        # Encoder en base64
        with open(photo_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()

        await manager.log("info", f"Photo capturee: {width}x{height}")
        return {
            "success": True,
            "image_base64": image_data,
            "image_path": photo_path,
            "width": width,
            "height": height
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/camera/calibrate/save")
async def camera_calibrate_save(data: dict):
    """Sauvegarde la calibration camera (4 coins du plateau)"""
    try:
        from chess_vision.config import CALIBRATION_FILE, EXTRACTED_BOARD_SIZE

        corners = data.get("corners")
        source_image = data.get("source_image", "")

        if not corners:
            return {"success": False, "error": "Coins manquants"}

        required_corners = ['TL', 'TR', 'BR', 'BL']
        for c in required_corners:
            if c not in corners or 'x' not in corners[c] or 'y' not in corners[c]:
                return {"success": False, "error": f"Coin {c} invalide"}

        calibration_data = {
            "corners": {
                "TL": {"x": corners["TL"]["x"], "y": corners["TL"]["y"]},
                "TR": {"x": corners["TR"]["x"], "y": corners["TR"]["y"]},
                "BR": {"x": corners["BR"]["x"], "y": corners["BR"]["y"]},
                "BL": {"x": corners["BL"]["x"], "y": corners["BL"]["y"]},
            },
            "source_image": source_image,
            "board_size": EXTRACTED_BOARD_SIZE,
            "calibrated_at": datetime.now().isoformat(),
            "note": "Coins du plateau en coordonnees pixels dans l'image originale. Ne pas deplacer la camera apres calibration.",
        }

        with open(CALIBRATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(calibration_data, f, indent=2, ensure_ascii=False)

        await manager.log("info", f"Calibration camera sauvegardee: {CALIBRATION_FILE}")
        return {"success": True, "file": CALIBRATION_FILE}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
#                         VISION CAMERA
# ============================================================================

@app.get("/vision/state")
async def get_vision_state():
    """Retourne l'etat courant de la vision camera (stabilise)."""
    return manager.vision.get_state_message()


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
