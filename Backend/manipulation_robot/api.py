#!/usr/bin/env python3
"""
API FastAPI pour le robot d'échecs
Version 2.0.0 - Intégration complète avec documentation optimisée
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
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

# --- Imports locaux ---
from models import MoveRequest, GameConfig
from robot_controller import RobotController
from chess_manager import ChessManager
from leaderboard_manager import LeaderboardManager
from config import FICHIER_CALIBRATION
from calibration import TwoPointCalibration

# Ajouter le chemin chess_vision au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ============================================================================
#                          SCHÉMAS DE DONNÉES (DOCS)
# ============================================================================

class VisionModeRequest(BaseModel):
    active: bool = Field(True, description="Active le mode capture caméra ou lecture JSON")

class VisionFlipRequest(BaseModel):
    flip: bool = Field(True, description="Active la rotation 180° des coordonnées")

class VisionGameRequest(BaseModel):
    enabled: bool = Field(True, description="Active la détection automatique des coups")

class ConfirmPlacementRequest(BaseModel):
    use_camera: bool = Field(True, description="Utilise la caméra comme référence initiale")

class CalibrationPointRequest(BaseModel):
    point: str = Field(..., pattern="^(a1|h8|z)$", description="Identifiant du point")


class CalibrationZRequest(BaseModel):
    # Idem ici
    direction: str = Field(..., pattern="^(up|down)$", description="Sens du mouvement")

class LeaderboardAddRequest(BaseModel):
    player_name: str
    acpl: float
    # Et ici aussi
    result: str = Field(..., pattern="^(win|lose|draw|abandoned)$")
    difficulty: str
    moves_played: int
    game_duration: Optional[float] = None
# ============================================================================
#                          CONFIGURATION API
# ============================================================================

tags_metadata = [
    {"name": "System", "description": "Statut général et endpoints de base."},
    {"name": "Game", "description": "Gestion de la partie, Stockfish et coups."},
    {"name": "Vision", "description": "Analyse d'image et détection de mouvements (Delta-based)."},
    {"name": "Robot", "description": "Contrôle direct du bras UR et du gripper."},
    {"name": "Calibration", "description": "Procédures de calibration Robot et Caméra."},
    {"name": "Leaderboard", "description": "Statistiques, scores et classements."},
]

app = FastAPI(
    title="♔ Chess Robot API",
    description="Interface de contrôle pour robot d'échecs industriel avec Vision par ordinateur.",
    version="2.0.0",
    openapi_tags=tags_metadata
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_STATE_PATH = os.path.join(_BACKEND_DIR, "chess_vision", "output", "latest", "game_state.json")

# ============================================================================
#                          SERVICES & LOGIQUE MÉTIER
# ============================================================================

class VisionService:
    BUFFER_SIZE = 3
    STABLE_THRESHOLD = 2
    DISAPPEAR_THRESHOLD = 3

    def __init__(self):
        self._buffers: dict[str, deque] = {}
        self.raw_board: dict[str, str] = {}
        self.stable_board: dict[str, str] = {}
        self.confidence: dict[str, float] = {}
        self.last_game_state: Optional[dict] = None
        self.last_timestamp: Optional[str] = None
        self.pieces_count: int = 0
        self.running: bool = False
        self._pipeline = None
        self.active_mode: bool = True
        self.last_error: Optional[str] = None
        self.vision_game_enabled: bool = True
        self.flip_board: bool = False
        self.reference_board: Optional[dict[str, str]] = None
        self.camera_baseline: Optional[dict[str, str]] = None
        self.game_started: bool = False

    def _get_pipeline(self):
        if self._pipeline is None:
            try:
                from chess_vision import ChessVisionPipeline
                self._pipeline = ChessVisionPipeline(save_visualization_images=False)
                if not self._pipeline.extractor.is_calibrated:
                    self.last_error = "Camera non calibree"
                    self._pipeline = None
            except Exception as e:
                self.last_error = str(e)
                self._pipeline = None
        return self._pipeline

    def _capture_and_analyze(self) -> Optional[dict]:
        pipeline = self._get_pipeline()
        if pipeline is None: return None
        try:
            result = pipeline.capture_and_analyze(save_outputs=True)
            return result.get("game_state") if result.get("success") else None
        except: return None

    def _read_game_state(self) -> Optional[dict]:
        if not os.path.exists(GAME_STATE_PATH): return None
        try:
            with open(GAME_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None

    @staticmethod
    def _flip_square(square: str) -> str:
        if len(square) != 2: return square
        return f"{square[0]}{9 - int(square[1])}"

    def _get_board_map(self, game_state: dict) -> dict[str, str]:
        board = {}
        for piece in game_state.get("pieces", []):
            if piece.get("zone") != "board": continue
            chess_pos = piece.get("position", {}).get("chess")
            if not chess_pos: continue
            color_char = "W" if piece.get("color") == "white" else "B"
            type_char = "N" if piece.get("type") == "Knight" else piece.get("type", "Pawn")[0]
            sq = chess_pos.lower()
            if self.flip_board:
                sq = self._flip_square(sq)
                color_char = "B" if color_char == "W" else "W"
            board[sq] = f"{color_char}{type_char}"
        return board

    def confirm_placement(self, use_camera: bool = True) -> dict:
        if use_camera and self.stable_board:
            self.reference_board = dict(self.stable_board)
            source = "camera"
        else:
            self.reference_board = {
                "a1": "WR", "b1": "WN", "c1": "WB", "d1": "WQ", "e1": "WK", "f1": "WB", "g1": "WN", "h1": "WR",
                "a2": "WP", "b2": "WP", "c2": "WP", "d2": "WP", "e2": "WP", "f2": "WP", "g2": "WP", "h2": "WP",
                "a7": "BP", "b7": "BP", "c7": "BP", "d7": "BP", "e7": "BP", "f7": "BP", "g7": "BP", "h7": "BP",
                "a8": "BR", "b8": "BN", "c8": "BB", "d8": "BQ", "e8": "BK", "f8": "BB", "g8": "BN", "h8": "BR",
            }
            source = "simulated"
        self.camera_baseline = dict(self.stable_board) if self.stable_board else {}
        self.game_started = True
        self._buffers.clear()
        return {"reference_board": self.reference_board, "source": source}

    def update_reference_after_move(self, from_sq: str, to_sq: str, is_capture: bool = False):
        for board_dict in [self.reference_board, self.camera_baseline]:
            if board_dict is not None:
                piece = board_dict.pop(from_sq, None)
                if piece:
                    if is_capture: board_dict.pop(to_sq, None)
                    board_dict[to_sq] = piece

    def detect_delta(self) -> Optional[dict]:
        if self.camera_baseline is None or not self.stable_board: return None
        baseline, cam = self.camera_baseline, self.stable_board
        disappeared, appeared, changed = {}, {}, {}
        all_sq = set(list(baseline.keys()) + list(cam.keys()))
        for sq in all_sq:
            b, c = baseline.get(sq), cam.get(sq)
            if b and not c: disappeared[sq] = b
            elif c and not b: appeared[sq] = c
            elif b and c and b != c: changed[sq] = (b, c)
        if not disappeared and not appeared and not changed: return None
        for sq_f, col_f in disappeared.items():
            if not col_f.startswith("W"): continue
            for sq_t, col_t in appeared.items():
                if col_f == col_t: return {"from": sq_f, "to": sq_t, "type": "move"}
            for sq_t, (b_c, c_c) in changed.items():
                if b_c.startswith("B") and c_c == col_f: return {"from": sq_f, "to": sq_t, "type": "capture"}
        return {"from": None, "to": None, "type": "unclear", "dis": disappeared, "app": appeared}

    def update(self) -> bool:
        game_state = self._capture_and_analyze() if self.active_mode else self._read_game_state()
        if game_state is None: return False
        ts = game_state.get("metadata", {}).get("timestamp")
        if ts == self.last_timestamp: return False
        self.last_timestamp, self.last_game_state = ts, game_state
        self.raw_board = self._get_board_map(game_state)
        self.pieces_count = len(self.raw_board)
        all_sq = [f"{c}{r}" for c in "abcdefgh" for r in "12345678"]
        for sq in all_sq:
            if sq not in self._buffers: self._buffers[sq] = deque(maxlen=self.BUFFER_SIZE)
            self._buffers[sq].append(self.raw_board.get(sq))
        new_stable, new_conf = {}, {}
        for sq in all_sq:
            buf = self._buffers[sq]
            if not buf: continue
            counts = {}
            for v in buf: counts[v] = counts.get(v, 0) + 1
            best_p = max(counts, key=counts.get)
            best_c = counts[best_p]
            if best_p is not None and best_c >= self.STABLE_THRESHOLD:
                new_stable[sq], new_conf[sq] = best_p, best_c / len(buf)
            elif best_p is None and best_c >= self.DISAPPEAR_THRESHOLD:
                new_conf[sq] = 0.0
            elif sq in self.stable_board:
                new_stable[sq], new_conf[sq] = self.stable_board[sq], 1.0 - (counts.get(None, 0) / len(buf))
        self.stable_board, self.confidence = new_stable, new_conf
        return True

    def get_state_message(self) -> dict:
        return {
            "type": "vision_state", "board": self.stable_board, "raw_board": self.raw_board,
            "confidence": self.confidence, "timestamp": self.last_timestamp or datetime.now().isoformat(),
            "pieces_count": self.pieces_count, "game_started": self.game_started,
            "reference_set": self.reference_board is not None,
        }

class ApplicationManager:
    def __init__(self):
        self.robot = RobotController()
        self.chess = ChessManager(self.robot)
        self.leaderboard = LeaderboardManager()
        self.vision = VisionService()
        self.chess.vision_service = self.vision
        self.status = "idle"
        self.websocket_clients: List[WebSocket] = []
        self.calib_points: dict = {}
        self.robot.set_log_callback(self.log)
        self.chess.set_broadcast_callback(self.broadcast)
        self.chess.set_log_callback(self.log)
        self.chess.set_status_callback(self.set_status)

    async def broadcast(self, message: dict):
        for client in self.websocket_clients[:]:
            try: await client.send_json(message)
            except: self.websocket_clients.remove(client)

    def set_status(self, status: str, message: str = ""):
        self.status = status
        asyncio.create_task(self.broadcast({"type": "status", "status": status, "message": message}))

    async def log(self, log_type: str, message: str):
        await self.broadcast({"type": "log", "logType": log_type, "message": message, "timestamp": datetime.now().isoformat()})

manager = ApplicationManager()

# ============================================================================
#                          BOUCLES DE FOND
# ============================================================================

async def vision_loop():
    manager.vision.running = True
    while manager.vision.running:
        try:
            updated = manager.vision.update()
            if updated and manager.websocket_clients:
                await manager.broadcast(manager.vision.get_state_message())
            if updated and manager.vision.vision_game_enabled and manager.vision.game_started:
                if manager.status == "idle": await _check_vision_move()
        except Exception as e: print(f"Vision Error: {e}")
        await asyncio.sleep(0.3 if manager.vision.active_mode else 0.5)

_vision_move_lock = False

async def _check_vision_move():
    global _vision_move_lock
    if _vision_move_lock or manager.chess.board.turn != chess.WHITE: return
    delta = manager.vision.detect_delta()
    if not delta or delta["type"] == "unclear": return
    from_sq, to_sq = delta.get("from"), delta.get("to")
    if delta["type"] == "appeared_only" and to_sq and not from_sq:
        for m in manager.chess.board.legal_moves:
            if chess.square_name(m.to_square) == to_sq:
                from_sq = chess.square_name(m.from_square)
                break
    if not from_sq or not to_sq: return
    legal = any(chess.Move.from_uci(f"{from_sq}{to_sq}{s}") in manager.chess.board.legal_moves for s in ["", "q", "r", "b", "n"])
    if legal:
        _vision_move_lock = True
        try:
            res = await manager.chess.play_vision_move(from_sq, to_sq)
            if res.get("success"):
                manager.vision.update_reference_after_move(from_sq, to_sq, delta["type"] == "capture")
                r_resp = res.get("robot_response", {})
                if r_resp.get("success"):
                    manager.vision.update_reference_after_move(r_resp.get("from"), r_resp.get("to"), False)
                await asyncio.sleep(1.0)
                manager.vision.update()
                if manager.vision.stable_board: manager.vision.camera_baseline = dict(manager.vision.stable_board)
        finally: _vision_move_lock = False
    else:
        await manager.broadcast({"type": "vision_anomaly", "message": f"Illegal: {from_sq}->{to_sq}"})

# ============================================================================
#                          ROUTES API
# ============================================================================

# --- SYSTEM ---
@app.get("/", tags=["System"])
async def root():
    return {"message": "Chess Robot API", "version": "2.0.0", "status": "operational"}

@app.get("/status", tags=["System"])
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
    }

# --- VISION ---
@app.get("/vision/status", tags=["Vision"])
async def get_vision_status():
    return {
        "running": manager.vision.running,
        "active_mode": manager.vision.active_mode,
        "vision_game_enabled": manager.vision.vision_game_enabled,
        "last_error": manager.vision.last_error,
        "pieces_count": manager.vision.pieces_count,
    }

@app.post("/vision/mode", tags=["Vision"])
async def set_vision_mode(data: VisionModeRequest):
    manager.vision.active_mode = data.active
    manager.vision._pipeline = None
    await manager.log("info", f"Vision mode: {'actif' if data.active else 'passif'}")
    return {"success": True, "active_mode": data.active}

@app.post("/vision/flip", tags=["Vision"])
async def set_vision_flip(data: VisionFlipRequest):
    manager.vision.flip_board = data.flip
    return {"success": True, "flip_board": data.flip}

@app.post("/vision/game", tags=["Vision"])
async def set_vision_game(data: VisionGameRequest):
    manager.vision.vision_game_enabled = data.enabled
    return {"success": True, "vision_game_enabled": data.enabled}

@app.post("/vision/confirm-placement", tags=["Vision"])
async def confirm_placement(data: ConfirmPlacementRequest = None):
    use_cam = data.use_camera if data else True
    result = manager.vision.confirm_placement(use_camera=use_cam)
    await manager.broadcast({"type": "vision_game_started", "source": result["source"]})
    return {"success": True, **result}

@app.get("/vision/sync", tags=["Vision"])
async def get_vision_sync():
    return manager.chess.sync_with_vision(manager.vision.stable_board)

@app.get("/vision/state", tags=["Vision"])
async def get_vision_state():
    return manager.vision.get_state_message()

# --- GAME ---
@app.post("/game/new", tags=["Game"])
async def new_game(config: GameConfig):
    result = manager.chess.new_game(config.difficulty)
    await manager.broadcast({"type": "game_started", "difficulty": config.difficulty, "fen": manager.chess.board.fen()})
    return result

@app.get("/game/fen", tags=["Game"])
async def get_fen():
    return {"fen": manager.chess.board.fen(), "turn": "white" if manager.chess.board.turn == chess.WHITE else "black"}

@app.post("/game/pause", tags=["Game"])
async def toggle_pause():
    result = await manager.chess.toggle_pause()
    await manager.broadcast({"type": "pause_toggled", "paused": result.get("paused")})
    return result

@app.post("/game/stop", tags=["Game"])
async def stop_game():
    result = await manager.chess.reset_plateau_with_board()
    await manager.broadcast({"type": "game_stopped"})
    return result

@app.get("/game/legal-moves/{square}", tags=["Game"])
async def get_legal_moves(square: str):
    moves = manager.chess.get_legal_moves(square)
    return {"square": square, "moves": moves, "count": len(moves)}

@app.get("/game/best-move", tags=["Game"])
async def get_best_move():
    return manager.chess.get_best_move()

@app.post("/game/move/human", tags=["Game"])
async def human_move(move: MoveRequest):
    return await manager.chess.play_human_move(move.from_square, move.to_square)

@app.post("/game/move/robot", tags=["Game"])
async def robot_move():
    return await manager.chess.play_robot_move()

@app.get("/game/history", tags=["Game"])
async def get_game_history():
    moves = []
    board_copy = chess.Board()
    for m in manager.chess.board.move_stack:
        moves.append({"from": chess.square_name(m.from_square), "to": chess.square_name(m.to_square), "san": board_copy.san(m)})
        board_copy.push(m)
    return {"moves": moves, "current_fen": manager.chess.board.fen()}

# --- ROBOT & CALIBRATION ---
@app.get("/robot/position", tags=["Robot"])
async def get_robot_position():
    return manager.robot.get_position() or {"error": "Robot non connecté"}

@app.post("/robot/calibrate/freedrive", tags=["Calibration"])
async def calibrate_freedrive(enable: bool = Body(True, embed=True)):
    if not manager.robot.connected: return {"success": False, "error": "Non connecté"}
    if enable: manager.robot.rtde_c.freedriveMode([1, 1, 0, 0, 0, 0])
    else: manager.robot.rtde_c.endFreedriveMode()
    return {"success": True, "freedrive": enable}

@app.post("/robot/calibrate/point", tags=["Calibration"])
async def calibrate_point(data: CalibrationPointRequest):
    pose = manager.robot.rtde_r.getActualTCPPose()
    manager.calib_points[data.point] = list(pose)
    return {"success": True, "point": data.point, "position": pose}

@app.post("/robot/calibrate/save", tags=["Calibration"])
async def calibrate_save():
    calib = TwoPointCalibration()
    data = calib.calculate_geometry(manager.calib_points['a1'], manager.calib_points['h8'], manager.calib_points['z'])
    calib.save(data)
    manager.robot.is_calibrated = True
    return {"success": True, "board_size": data["board_size"]}

@app.post("/camera/capture", tags=["Calibration"])
async def camera_capture():
    from chess_vision.modules.camera import take_photo
    path = take_photo()
    with open(path, 'rb') as f: img_b64 = base64.b64encode(f.read()).decode()
    return {"success": True, "image_base64": img_b64}

# --- LEADERBOARD ---
@app.get("/leaderboard", tags=["Leaderboard"])
async def get_leaderboard(limit: Optional[int] = None):
    return {"leaderboard": manager.leaderboard.get_leaderboard(limit=limit)}

@app.post("/leaderboard/add-game", tags=["Leaderboard"])
async def add_game_to_leaderboard(data: LeaderboardAddRequest):
    success = manager.leaderboard.add_game(**data.dict())
    return {"success": success}

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.websocket_clients.append(websocket)
    try:
        await websocket.send_json({"type": "connected", "fen": manager.chess.board.fen()})
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "ping": await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect: manager.websocket_clients.remove(websocket)

# --- LIFECYCLE ---
@app.on_event("startup")
async def startup():
    manager.chess.init_stockfish()
    manager.robot.init_robot()
    asyncio.create_task(vision_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)