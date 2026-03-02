#!/usr/bin/env python3
"""
API FastAPI pour le robot d'échecs
Version 2.1.0 - Fusion complète et Documentée
"""

import os
import sys
import json
import math
import time
import asyncio
import base64
import chess
from datetime import datetime
from collections import deque
from enum import Enum
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Query, Path, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Imports locaux ---
from models import MoveRequest, GameConfig
from robot_controller import RobotController
from chess_manager import ChessManager
from leaderboard_manager import LeaderboardManager
from feedback_manager import FeedbackManager
from board_reset_manager import BoardResetManager
from config import FICHIER_CALIBRATION, FICHIER_POSITION_DEPART
from calibration import TwoPointCalibration
from hybrid_board_manager import HybridBoardManager

# Ajouter le chemin chess_vision au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ============================================================================
#                          SCHÉMAS DE DONNÉES (PYDANTIC V2)
# ============================================================================

class ResultEnum(str, Enum):
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"
    ABANDONED = "abandoned"

class VisionModeRequest(BaseModel):
    active: bool = Field(True, description="True pour capture caméra, False pour lecture JSON")

class VisionFlipRequest(BaseModel):
    flip: bool = Field(True, description="Active la rotation 180° des coordonnées caméra")

class VisionGameRequest(BaseModel):
    enabled: bool = Field(True, description="Active la détection automatique des coups")

class ConfirmPlacementRequest(BaseModel):
    use_camera: bool = Field(True, description="Utilise la vision comme référence logique")

class CalibrationPointRequest(BaseModel):
    point: str = Field(..., pattern="^(a1|h8|z)$", description="Identifiant du point de calibration")

class CalibrationZRequest(BaseModel):
    direction: str = Field(..., pattern="^(up|down)$", description="Direction du mouvement Z")

class LeaderboardAddRequest(BaseModel):
    player_name: str = Field(..., examples=["Alice"])
    acpl: float = Field(..., description="Average Centipawn Loss")
    result: ResultEnum = Field(..., description="Résultat de la partie")
    difficulty: str = Field(..., examples=["intermediate"])
    moves_played: int = Field(..., gt=0)
    game_duration: Optional[float] = Field(None, description="Durée en secondes")

class FeedbackSubmitRequest(BaseModel):
    player_name: str = Field(..., examples=["Alice"])
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field("", description="Commentaire optionnel")
    difficulty: str = Field(...)
    result: ResultEnum = Field(...)
    acpl_score: float = Field(...)
    timestamp: Optional[str] = Field(None)

# ============================================================================
#                          VISION SERVICE
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
        self._stability_counter: int = 0

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
            if result.get("success"):
                self.last_error = None
                return result.get("game_state")
            self.last_error = result.get("error", "Erreur inconnue")
            return None
        except Exception as e:
            self.last_error = f"Erreur capture: {e}"
            return None

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

    def find_piece_at(self, square: str) -> Optional[dict]:
        if not self.last_game_state: return None
        target = self._flip_square(square.lower()) if self.flip_board else square.lower()
        for piece in self.last_game_state.get("pieces", []):
            if piece.get("zone") != "board": continue
            chess_pos = piece.get("position", {}).get("chess")
            if chess_pos and chess_pos.lower() == target:
                return piece
        return None

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

    def detect_delta(self, chess_board=None, stockfish_board: Optional[dict] = None) -> Optional[dict]:
        if self.camera_baseline is None or not self.stable_board: return None
        baseline, cam = self.camera_baseline, self.stable_board
        dis, app, chg = {}, {}, {}
        all_sq = set(list(baseline.keys()) + list(cam.keys()))
        for sq in all_sq:
            b, c = baseline.get(sq), cam.get(sq)
            if b and not c: dis[sq] = b
            elif c and not b: app[sq] = c
            elif b and c and b != c: chg[sq] = (b, c)
        if not dis and not app and not chg: return None

        # ── Approche principale : Stockfish-first ─────────────────────────────
        # On cherche un coup légal dont la case d'arrivée est visible dans la
        # caméra ET dont la case de départ est maintenant vide. Le "from" est
        # déduit de Stockfish, jamais des disparitions caméra (trop instables).
        if chess_board is not None:
            candidate_to_squares = list(app.keys()) + list(chg.keys())
            for sq_t in candidate_to_squares:
                for move in chess_board.legal_moves:
                    if chess.square_name(move.to_square) != sq_t:
                        continue
                    sq_f = chess.square_name(move.from_square)
                    # La case de départ doit être vide dans la caméra actuelle
                    if cam.get(sq_f):
                        continue
                    move_type = "capture" if chess_board.is_capture(move) else "move"
                    return {"from": sq_f, "to": sq_t, "type": move_type}

        # ── Fallback : approche originale avec filtre stockfish_board ─────────
        def _is_valid_from(sq_f: str, col_f: str) -> bool:
            if not col_f.startswith("W"):
                return False
            if stockfish_board is not None:
                return stockfish_board.get(sq_f, "").startswith("W")
            return True
        for sq_f, col_f in dis.items():
            if not _is_valid_from(sq_f, col_f): continue
            for sq_t, col_t in app.items():
                if col_f == col_t: return {"from": sq_f, "to": sq_t, "type": "move"}
            for sq_t, (b_c, c_c) in chg.items():
                if b_c.startswith("B") and c_c == col_f: return {"from": sq_f, "to": sq_t, "type": "capture"}
        return {"from": None, "to": None, "type": "unclear", "dis": dis, "app": app}

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
            # Solution 2 : seuil plus élevé pour les cases absentes du baseline.
            # Une pièce apparaissant sur une case qui était vide (non connue du
            # baseline) doit être vue dans TOUTES les frames du buffer avant
            # d'être stabilisée. Cela empêche les détections transitoires
            # (ArUco en transit pendant un déplacement) de polluer le stable_board.
            sq_in_baseline = (self.camera_baseline is None or sq in self.camera_baseline)
            appearance_threshold = self.STABLE_THRESHOLD if sq_in_baseline else len(buf)
            if best_p is not None and best_c >= appearance_threshold:
                new_stable[sq], new_conf[sq] = best_p, best_c / len(buf)
            elif best_p is None and best_c >= self.DISAPPEAR_THRESHOLD:
                new_conf[sq] = 0.0
            elif sq in self.stable_board:
                new_stable[sq], new_conf[sq] = self.stable_board[sq], 1.0 - (counts.get(None, 0) / len(buf))
        # Compteur de stabilité : incrémenté si le plateau n'a pas changé,
        # remis à zéro dès qu'une case change (pièce en mouvement).
        if new_stable == self.stable_board:
            self._stability_counter += 1
        else:
            self._stability_counter = 0
        self.stable_board, self.confidence = new_stable, new_conf
        return True

    def get_state_message(self) -> dict:
        return {
            "type": "vision_state", "board": self.stable_board, "raw_board": self.raw_board,
            "confidence": self.confidence, "timestamp": self.last_timestamp or datetime.now().isoformat(),
            "pieces_count": self.pieces_count, "game_started": self.game_started,
            "reference_set": self.reference_board is not None,
        }

    def get_occupied_cimetiere_cells(self) -> set:
        """
        Retourne les cases du cimetière actuellement occupées d'après la vision
        (pièces avec zone='cemetery', placées par le robot OU manuellement par un joueur).

        La notation vision (ex: 'A0') est normalisée en minuscules ('a0') pour
        correspondre à la notation utilisée par RobotController.
        """
        if not self.last_game_state:
            return set()
        occupied = set()
        for piece in self.last_game_state.get("pieces", []):
            if piece.get("zone") == "cemetery":
                grid = piece.get("position", {}).get("grid")
                if grid:
                    occupied.add(grid.lower())
        return occupied

# ============================================================================
#                          APPLICATION MANAGER
# ============================================================================

class ApplicationManager:
    def __init__(self):
        self.robot = RobotController()
        self.chess = ChessManager(self.robot)
        self.leaderboard = LeaderboardManager()
        self.feedback = FeedbackManager()
        self.board_reset = BoardResetManager(self.robot)
        self.vision = VisionService()
        self.chess.vision_service = self.vision
        self.status = "idle"
        self.websocket_clients: List[WebSocket] = []
        self.calib_points: dict = {}
        self.robot.set_log_callback(self.log)
        self.robot.set_cimetiere_vision_callback(self.vision.get_occupied_cimetiere_cells)
        self.chess.set_broadcast_callback(self.broadcast)
        self.chess.set_log_callback(self.log)
        self.chess.set_status_callback(self.set_status)
        self.board_reset.set_log_callback(self.log)
        self.board_reset.set_broadcast_callback(self.broadcast)

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
hybrid_manager = HybridBoardManager()

# Chemin du fichier game_state (mode passif, quand active_mode=False)
GAME_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_state.json")

# ============================================================================
#                          APPLICATION FASTAPI
# ============================================================================

tags_metadata = [
    {"name": "System", "description": "Statut général et endpoints de base."},
    {"name": "Game", "description": "Gestion de la partie, Stockfish et coups."},
    {"name": "Vision", "description": "Analyse d'image et détection de mouvements."},
    {"name": "Robot", "description": "Contrôle direct du bras UR et du gripper."},
    {"name": "Calibration", "description": "Procédures de calibration Robot et Caméra."},
    {"name": "Leaderboard", "description": "Statistiques, scores et classements."},
    {"name": "Feedback", "description": "Avis et commentaires utilisateurs."},
]

app = FastAPI(title="Chess Robot API", version="2.0.0", openapi_tags=tags_metadata)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ============================================================================
#                          BOUCLES & LOGIQUE MÉTIER
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
        await asyncio.sleep(0.15 if manager.vision.active_mode else 0.3)

_vision_move_lock = False
_last_anomaly = ""
_last_anomaly_time = 0.0

# Nombre de frames consécutives stables exigées avant de tenter une détection.
# Cela garantit que la pièce est posée et le plateau figé, pas en transit.
_MIN_STABLE_FRAMES = 2

async def _check_vision_move():
    global _vision_move_lock
    if _vision_move_lock or manager.chess.board.turn != chess.WHITE: return
    # Attendre que le plateau ait été stable pendant N frames consécutives :
    # cela élimine les fausses détections pendant le déplacement physique.
    if manager.vision._stability_counter < _MIN_STABLE_FRAMES: return
    delta = manager.vision.detect_delta(
        chess_board=manager.chess.board,
        stockfish_board=manager.chess._board_to_map(),
    )
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
            is_capture = delta["type"] == "capture"
            await manager.log("info", f"Coup detecte: {from_sq} -> {to_sq}" + (" (capture)" if is_capture else ""))
            result = await manager.chess.play_vision_move(from_sq, to_sq)
            
            if result.get("success"):
                # Mettre a jour la reference apres le coup humain
                manager.vision.update_reference_after_move(from_sq, to_sq, is_capture)
                hybrid_manager.on_move_played(from_sq, to_sq, is_capture)
                
                # Verifier si le coup humain a termine la partie
                if result.get("game_over"):
                    manager.vision.game_started = False
                    await asyncio.sleep(0.3) # Petit delai pour laisser le broadcast game_over partir
                    return

                # Aussi mettre a jour apres le coup robot si il a joue
                robot_resp = result.get("robot_response", {})
                if robot_resp.get("success"):
                    r_from = robot_resp.get("from")
                    r_to = robot_resp.get("to")
                    if r_from and r_to:
                        r_capture = manager.vision.reference_board and r_to in manager.vision.reference_board
                        manager.vision.update_reference_after_move(r_from, r_to, r_capture)
                        hybrid_manager.on_move_played(r_from, r_to, bool(r_capture))
                    
                    # Verifier si le coup robot a termine la partie
                    if robot_resp.get("game_over"):
                        manager.vision.game_started = False
                        await asyncio.sleep(0.3)
                        return

                # Vider les buffers et réinitialiser la stabilité pour repartir clean
                manager.vision._buffers.clear()
                manager.vision._stability_counter = 0

                # Attendre que les pieces se stabilisent physiquement,
                # puis prendre un nouveau snapshot camera comme baseline
                await asyncio.sleep(0.5)
                manager.vision.update()  # capture fraiche
                if manager.vision.stable_board:
                    # Baseline hybride : camera + pieces encore simulees
                    manager.vision.camera_baseline = hybrid_manager.get_hybrid_baseline(
                        manager.vision.stable_board
                    )
            else:
                await manager.log("warning", f"Echec: {result.get('error')}")
        finally:
            _vision_move_lock = False
    else:
        global _last_anomaly, _last_anomaly_time
        anomaly_key = f"{from_sq}{to_sq}"
        now = time.time()
        # Cooldown 5s pour ne pas spammer la meme anomalie
        if anomaly_key != _last_anomaly or (now - _last_anomaly_time) > 5:
            _last_anomaly = anomaly_key
            _last_anomaly_time = now
            await manager.broadcast({
                "type": "vision_anomaly",
                "message": f"Coup illegal: {from_sq} -> {to_sq}",
                "suggestions": [f"Verifiez le deplacement {from_sq} -> {to_sq}"],
            })


@app.get("/vision/status")
async def get_vision_status():
    """Retourne le statut du VisionService (debug)."""
    return {
        "running": manager.vision.running,
        "active_mode": manager.vision.active_mode,
        "vision_game_enabled": manager.vision.vision_game_enabled,
        "last_error": manager.vision.last_error,
        "last_timestamp": manager.vision.last_timestamp,
        "pieces_count": manager.vision.pieces_count,
        "stable_board_count": len(manager.vision.stable_board),
        "raw_board_count": len(manager.vision.raw_board),
        "buffer_size": manager.vision.BUFFER_SIZE,
        "has_pipeline": manager.vision._pipeline is not None,
    }


@app.post("/vision/debug-aruco")
async def debug_aruco_detection():
    """
    Diagnostic ArUco : capture une photo et teste TOUS les dictionnaires
    ArUco courants pour identifier lequel détecte les marqueurs physiques.

    Retourne pour chaque dictionnaire le nombre de marqueurs détectés,
    les IDs trouvés, et si des IDs de calibration (32-35) ou pièces (0-31)
    sont présents.
    """
    import cv2
    import numpy as np

    try:
        from chess_vision.modules.camera import take_photo
        photo_path = take_photo()
        image = cv2.imread(photo_path)
        if image is None:
            return {"success": False, "error": "Impossible de lire la photo"}
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    except Exception as e:
        return {"success": False, "error": f"Capture impossible: {e}"}

    # Tous les dictionnaires ArUco OpenCV courants
    dicts_to_test = {
        "DICT_4X4_50":   cv2.aruco.DICT_4X4_50,
        "DICT_4X4_100":  cv2.aruco.DICT_4X4_100,
        "DICT_4X4_250":  cv2.aruco.DICT_4X4_250,
        "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
        "DICT_5X5_50":   cv2.aruco.DICT_5X5_50,
        "DICT_5X5_100":  cv2.aruco.DICT_5X5_100,
        "DICT_5X5_250":  cv2.aruco.DICT_5X5_250,
        "DICT_6X6_50":   cv2.aruco.DICT_6X6_50,
        "DICT_6X6_100":  cv2.aruco.DICT_6X6_100,
        "DICT_6X6_250":  cv2.aruco.DICT_6X6_250,
        "DICT_7X7_50":   cv2.aruco.DICT_7X7_50,
        "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
    }

    results = {}
    best_dict = None
    best_count = 0

    for dict_name, dict_type in dicts_to_test.items():
        try:
            aruco_dict = cv2.aruco.getPredefinedDictionary(dict_type)
            detector_params = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)
            corners, ids, _ = detector.detectMarkers(gray)

            detected_ids = ids.flatten().tolist() if ids is not None else []
            piece_ids    = [i for i in detected_ids if 0 <= i <= 31]
            calib_ids    = [i for i in detected_ids if 32 <= i <= 35]

            results[dict_name] = {
                "total": len(detected_ids),
                "all_ids": sorted(detected_ids),
                "piece_ids": sorted(piece_ids),
                "calib_ids": sorted(calib_ids),
            }

            if len(detected_ids) > best_count:
                best_count = len(detected_ids)
                best_dict = dict_name

        except Exception as e:
            results[dict_name] = {"error": str(e)}

    current_dict = "DICT_4X4_50"
    return {
        "success": True,
        "photo_path": photo_path,
        "current_dict": current_dict,
        "current_dict_detects": results.get(current_dict, {}).get("total", 0),
        "best_dict": best_dict,
        "best_dict_count": best_count,
        "recommendation": (
            f"Changer ARUCO_DICT_TYPE vers {best_dict} dans config.py"
            if best_dict and best_dict != current_dict
            else "Le dictionnaire actuel est correct"
        ),
        "all_results": results,
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


@app.post("/vision/flip")
async def set_vision_flip(data: dict):
    """Active/desactive la rotation 180° des coordonnees camera."""
    flip = data.get("flip", True)
    manager.vision.flip_board = flip
    state = "active" if flip else "desactive"
    await manager.log("info", f"Rotation 180° camera {state}")
    return {"success": True, "flip_board": flip}


@app.post("/vision/game")
async def set_vision_game(data: dict):
    """Active/desactive la detection automatique des coups par la camera."""
    enabled = data.get("enabled", True)
    manager.vision.vision_game_enabled = enabled
    state = "activee" if enabled else "desactivee"
    await manager.log("info", f"Detection vision des coups {state}")
    return {"success": True, "vision_game_enabled": enabled}


@app.post("/vision/confirm-placement")
async def confirm_placement(data: dict = None):
    """
    Confirme que les pieces sont bien placees et demarre l'observation.

    Body optionnel: {"use_camera": true/false}
    - true (defaut) : utilise la camera comme reference (si elle voit les pieces)
    - false : simule la position initiale standard (32 pieces)
    """
    use_camera = True
    if data:
        use_camera = data.get("use_camera", True)

    result = manager.vision.confirm_placement(use_camera=use_camera)
    source = result.get("source", "unknown")
    piece_count = len(result.get("reference_board", {}))
    await manager.log("info", f"Placement confirme ({source}, {piece_count} pieces)")
    await manager.broadcast({
        "type": "vision_game_started",
        "source": source,
        "pieces_count": piece_count,
    })
    return {"success": True, **result}


@app.get("/vision/hybrid/missing")
async def get_hybrid_missing():
    """
    Retourne les pieces non détectées par la caméra par rapport à la position
    de départ standard.

    À appeler avant la confirmation pour informer le joueur des pièces que
    la caméra ne voit pas encore.
    """
    camera_board = manager.vision.stable_board or {}
    missing = hybrid_manager.analyze_missing_pieces(camera_board)
    return {
        "camera_pieces_count": len([v for v in camera_board.values() if v]),
        "missing_count": len(missing),
        "missing_pieces": missing,
        "ready_to_confirm": True,
    }


@app.post("/vision/hybrid/confirm")
async def confirm_hybrid_placement():
    """
    Le joueur confirme que toutes les pièces sont bien placées sur le plateau.

    - Les pièces détectées par la caméra sont utilisées telles quelles.
    - Les pièces NON détectées sont simulées à leur position de départ standard.
    - Le baseline caméra (camera_baseline) est enrichi avec ces pièces simulées
      pour que la détection delta fonctionne correctement.

    Sans cette étape, une pièce qui devient visible en cours de partie est
    vue comme une "apparition illégale" par Stockfish.
    """
    camera_board = manager.vision.stable_board or {}

    # Construire le baseline hybride (caméra + simulées) et marquer les simulées
    hybrid_baseline = hybrid_manager.build_hybrid_baseline(camera_board)

    # Confirmer le placement : reference_board = position standard complète
    result = manager.vision.confirm_placement(use_camera=False)

    # Remplacer camera_baseline par le baseline hybride enrichi
    manager.vision.camera_baseline = hybrid_baseline

    simulated_count = len(hybrid_manager.simulated_squares)
    simulated_list = sorted(hybrid_manager.simulated_squares)

    await manager.log(
        "info",
        f"Placement hybride confirme : {len(camera_board)} pieces vues, "
        f"{simulated_count} simulees ({', '.join(simulated_list) or 'aucune'})"
    )
    await manager.broadcast({
        "type": "vision_game_started",
        "source": "hybrid",
        "pieces_count": len(hybrid_baseline),
        "simulated_count": simulated_count,
        "simulated_squares": simulated_list,
    })

    return {
        "success": True,
        "camera_pieces_count": len(camera_board),
        "simulated_count": simulated_count,
        "simulated_squares": simulated_list,
        "total_baseline_count": len(hybrid_baseline),
    }


@app.get("/vision/hybrid/simulated")
async def get_hybrid_simulated():
    """
    Retourne les pieces actuellement simulées pendant la partie.

    Une pièce est simulée tant que la caméra ne l'a pas vue se déplacer.
    Dès qu'elle bouge (et est détectée), elle sort de la liste simulée.
    """
    camera_board = manager.vision.stable_board or {}

    # Mettre à jour : si une pièce simulée est maintenant visible, la retirer
    de_simulated = hybrid_manager.on_camera_update(camera_board)
    if de_simulated:
        await manager.log("info", f"Pieces de-simulees (maintenant visibles) : {de_simulated}")

    status = hybrid_manager.get_status(camera_board)
    return status


@app.post("/vision/visualization")
async def get_vision_visualization():
    """
    Capture une image, lance l'analyse chess_vision avec les visualisations
    activées et retourne l'image annotée (grille + pièces détectées).

    Utilise un pipeline one-shot indépendant du pipeline principal pour ne
    pas ralentir la boucle de détection en cours.
    """
    try:
        from chess_vision import ChessVisionPipeline
        from chess_vision.config import OUTPUT_DIR

        pipeline = ChessVisionPipeline(save_visualization_images=True)
        if not pipeline.extractor.is_calibrated:
            return {"success": False, "error": "Camera non calibree (board_calibration.json manquant)"}

        result = pipeline.capture_and_analyze(save_outputs=True)

        latest_dir = os.path.join(OUTPUT_DIR, "latest")

        # Priorité : image avec pièces > grille seule > plateau brut
        for filename in ["5_pieces.jpg", "4_board_grid.jpg", "3_board.jpg"]:
            img_path = os.path.join(latest_dir, filename)
            if os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()
                return {
                    "success": True,
                    "image_base64": image_data,
                    "source": filename,
                    "pieces_count": result.get("pieces_count", 0),
                    "error": result.get("error"),
                }

        return {"success": False, "error": "Aucune image de visualisation generee"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/vision/sync")
async def get_vision_sync():
    """Compare l'etat camera stabilise avec l'etat Stockfish."""
    sync_result = manager.chess.sync_with_vision(manager.vision.stable_board)
    return sync_result


async def _move_to_waiting_position():
    """Déplace le robot vers la position d'attente de jeu au démarrage."""
    await asyncio.sleep(0.5)  # Laisser le temps à l'initialisation de se terminer
    if manager.robot.connected and manager.robot.is_calibrated and manager.robot.position_depart:
        try:
            await manager.robot._move_tcp(manager.robot.position_depart)
            print("✓ Robot en position d'attente")
        except Exception as e:
            print(f"⚠ Erreur position d'attente: {e}")


@app.on_event("startup")
async def startup():
    """Initialisation au démarrage"""
    print(" Démarrage de l'API Chess Robot...")
    manager.chess.init_stockfish()
    manager.robot.init_robot()
    asyncio.create_task(vision_loop())
    asyncio.create_task(_move_to_waiting_position())
    print("API prête!")

# ============================================================================
#                          ROUTES API
# ============================================================================

# --- SYSTEM ---
@app.get("/", tags=["System"])
async def root(): return {"status": "operational"}

@app.get("/status", tags=["System"])
async def get_status():
    """Retourne le statut complet du système"""
    return {
        "connected": manager.robot.connected,
        "status": manager.status,
        "fen": manager.chess.board.fen(),
        "turn": "white" if manager.chess.board.turn == chess.WHITE else "black",
        "pieces_eliminees": manager.robot.get_pieces_eliminees(),
        "game_result": manager.chess.get_game_result() if manager.chess.board.is_game_over() else None
    }

# --- GAME ---
@app.post("/game/new", tags=["Game"])
async def new_game(config: GameConfig):
    """Démarre une nouvelle partie"""
    hybrid_manager.reset()
    result = manager.chess.new_game(config.difficulty)
    await manager.log("info", f"Nouvelle partie - Difficulté: {config.difficulty}")
    await manager.broadcast({
        "type": "game_started",
        "difficulty": config.difficulty,
        "fen": manager.chess.board.fen()
    })
    return result

@app.get("/game/fen", tags=["Game"])
async def get_fen():
    """Retourne la position FEN actuelle"""
    return {"fen": manager.chess.board.fen(), "turn": "white" if manager.chess.board.turn == chess.WHITE else "black"}

@app.post("/game/pause", tags=["Game"])
async def toggle_pause():
    """Bascule l'état de pause de la partie (Arrêt d'urgence)"""
    result = await manager.chess.toggle_pause()
    await manager.broadcast({
        "type": "pause_toggled",
        "paused": result.get("paused", False),
        "message": result.get("message", "")
    })
    return result

@app.post("/game/stop", tags=["Game"])
async def stop_game():
    """Arrête immédiatement tous les processus de jeu (sans déplacer les pièces physiquement)."""
    # 1. Arrêt matériel immédiat du robot
    if manager.robot.connected and manager.robot.rtde_c:
        try:
            manager.robot.rtde_c.stopScript()
        except Exception:
            pass

    # 2. Désactiver la détection vision pour éviter tout nouveau coup automatique
    manager.vision.game_started = False
    manager.vision._buffers.clear()
    manager.vision._stability_counter = 0

    # 3. Réinitialiser les flags de pause
    manager.chess.is_paused = False
    manager.robot.is_paused = False

    # 4. Relancer le script robot pour que la connexion reste opérationnelle
    if manager.robot.connected and manager.robot.rtde_c:
        try:
            await asyncio.sleep(0.15)
            manager.robot.rtde_c.reuploadScript()
            await asyncio.sleep(0.15)
        except Exception:
            pass

    # 5. Reset virtuel uniquement (aucun déplacement physique)
    manager.chess.board.reset()
    manager.robot.reset_tracking()

    manager.set_status("idle", "Partie arrêtée")
    await manager.log("info", "Partie arrêtée — tous les processus de jeu stoppés")
    await manager.broadcast({"type": "game_stopped"})
    return {"success": True}

@app.post("/game/reset-plateau", tags=["Game"])
async def reset_plateau():
    """Remet toutes les pièces à leur position initiale"""
    result = await manager.chess.reset_plateau_with_board()
    if result.get("success"):
        await manager.broadcast({"type": "plateau_reset", "fen": manager.chess.board.fen()})
    return result

@app.post("/game/replace-board", tags=["Game"])
async def replace_board():
    """Replace toutes les pièces via la vision caméra"""
    if manager.status == "replacing": return {"success": False, "error": "Déjà en cours"}
    manager.set_status("replacing", "Replacement en cours")
    try:
        result = await manager.board_reset.replace_board()
        if result.get("success"):
            manager.chess.board.reset()
            await manager.broadcast({"type": "board_replaced", "fen": manager.chess.board.fen()})
    finally: manager.set_status("idle")
    return result

@app.post("/game/confirm-promotion", tags=["Game"])
async def confirm_promotion(data: dict):
    """
    Confirme la case où le joueur a placé la pièce de promotion (dame).
    À appeler après avoir reçu l'événement WebSocket 'promotion_required'.

    Body: {"from_sq": "a0"}  — n'importe quelle case accessible (cimetière, bord, etc.)
    """
    from_sq = data.get("from_sq", "").strip().lower()
    if not from_sq:
        return {"success": False, "error": "Paramètre from_sq manquant"}
    success = manager.chess.confirm_promotion(from_sq)
    if not success:
        return {"success": False, "error": "Aucune promotion en attente"}
    await manager.log("info", f"Promotion confirmée — dame en {from_sq}")
    return {"success": True}

@app.get("/game/legal-moves/{square}", tags=["Game"])
async def get_legal_moves(square: str = Path(..., pattern="^[a-h][1-8]$")):
    return {"square": square, "moves": manager.chess.get_legal_moves(square)}

@app.get("/game/best-move", tags=["Game"])
async def get_best_move(): return manager.chess.get_best_move()

@app.post("/game/move/human", tags=["Game"])
async def human_move(move: MoveRequest):
    """Joue le coup du joueur humain"""
    await manager.log("info", f" Coup humain: {move.from_square} → {move.to_square}")
    return await manager.chess.play_human_move(move.from_square, move.to_square)

@app.post("/game/move/robot", tags=["Game"])
async def robot_move():
    """Demande au robot de jouer son coup"""
    return await manager.chess.play_robot_move()

@app.get("/game/pieces-eliminees", tags=["Game"])
async def get_pieces_eliminees():
    pieces = manager.robot.get_pieces_eliminees()
    return {
        "pieces_eliminees": pieces,
        "count": len(pieces)
    }


@app.post("/robot/reconnect", tags=["Robot"])
async def reconnect_robot():
    """Reconnecte complètement le robot (RTDE + gripper) après un blocage ou un timeout."""
    success = await manager.robot.reconnect()
    if success:
        manager.set_status("idle", "Robot reconnecté")
        await manager.broadcast({"type": "robot_reconnected", "success": True})
    else:
        manager.set_status("error", "Échec de la reconnexion")
        await manager.broadcast({"type": "robot_reconnected", "success": False})
    return {"success": success}


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
            manager.robot.rtde_c.freedriveMode([1, 1, 1, 0, 0, 0])
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


@app.post("/robot/save-home-position")
async def save_home_position():
    """Enregistre la position TCP actuelle comme position d'attente de démarrage."""
    if not manager.robot.connected or not manager.robot.rtde_r:
        return {"success": False, "error": "Robot non connecte"}
    try:
        pose = manager.robot.rtde_r.getActualTCPPose()
        data = {"position_depart": list(pose)}
        with open(FICHIER_POSITION_DEPART, 'w') as f:
            json.dump(data, f, indent=2)
        manager.robot.position_depart = list(pose)
        await manager.log("info", f"Position d'attente sauvegardee: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
        return {"success": True, "position": {"x": pose[0], "y": pose[1], "z": pose[2]}}
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


@app.get("/camera/calibration")
async def get_camera_calibration():
    """Retourne les coins de calibration du plateau depuis board_calibration.json."""
    try:
        from chess_vision.config import CALIBRATION_FILE
        if not os.path.exists(CALIBRATION_FILE):
            return {"success": False, "error": "Non calibre (board_calibration.json manquant)"}
        with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        corners = data.get("corners", {})
        if not all(k in corners for k in ("TL", "TR", "BR", "BL")):
            return {"success": False, "error": "Fichier de calibration incomplet"}
        return {"success": True, "corners": corners}
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
            "note": "Coins physiques du plateau 8x8 (angles A8/H8/H1/A1). La zone cimetiere est deduite automatiquement (1 case de bordure). Ne pas deplacer la camera apres calibration.",
        }

        with open(CALIBRATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(calibration_data, f, indent=2, ensure_ascii=False)

        await manager.log("info", f"Calibration camera sauvegardee: {CALIBRATION_FILE}")
        return {"success": True, "file": CALIBRATION_FILE}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- GAME HISTORY ---
@app.get("/game/history", tags=["Game"])
async def get_game_history():
    moves = []
    board_copy = chess.Board()
    for m in manager.chess.board.move_stack:
        moves.append({"san": board_copy.san(m), "uci": m.uci()})
        board_copy.push(m)
    return {"moves": moves}

# --- LEADERBOARD ---
@app.get("/leaderboard", tags=["Leaderboard"])
async def get_leaderboard(limit: Optional[int] = None): return manager.leaderboard.get_leaderboard(limit=limit)

@app.post("/leaderboard/add-game", tags=["Leaderboard"])
async def add_game_to_leaderboard(data: LeaderboardAddRequest):
    return {"success": manager.leaderboard.add_game(**data.model_dump())}

# --- FEEDBACK ---
@app.post("/feedback/submit", tags=["Feedback"])
async def submit_feedback(data: FeedbackSubmitRequest):
    """Soumet un nouveau feedback"""
    success = manager.feedback.add_feedback(
        player_name=data.player_name,
        rating=data.rating,
        comment=data.comment,
        difficulty=data.difficulty,
        result=data.result,
        acpl_score=data.acpl_score
    )
    if success:
        await manager.log("info", f"Nouveau feedback de {data.player_name} ({data.rating}/5)")
    return {"success": success}

@app.get("/feedback/logs", tags=["Feedback"])
async def get_feedback_logs():
    """Récupère tous les feedbacks"""
    return {"feedbacks": manager.feedback.get_feedbacks()}

@app.post("/feedback/reset", tags=["Feedback"])
async def reset_feedbacks():
    """Efface tous les feedbacks"""
    success = manager.feedback.reset_feedbacks()
    if success:
        await manager.log("warning", "Tous les feedbacks ont été effacés")
    return {"success": success}

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.websocket_clients.append(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.websocket_clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)