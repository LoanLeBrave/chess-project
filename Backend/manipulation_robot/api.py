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
from board_reset_manager import BoardResetManager
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
    Appelle chess_vision() en continu et maintient un etat stabilise.

    Systeme delta-based :
    - On confirme la position initiale (ou on la simule)
    - Ensuite on observe les CHANGEMENTS par rapport a la reference
    - Buffer reduit (3 frames) pour detection rapide (~3-4s)
    """

    BUFFER_SIZE = 3          # Frames dans le buffer (reduit pour vitesse)
    STABLE_THRESHOLD = 2     # 2/3 pour considerer stable
    DISAPPEAR_THRESHOLD = 3  # 3/3 absent = disparu

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

        # Flip 180° des coordonnees camera (si la camera voit le plateau a l'envers)
        self.flip_board: bool = False

        # --- Systeme delta-based ---
        # Board logique : position selon Stockfish (pour valider les coups)
        self.reference_board: Optional[dict[str, str]] = None
        # Baseline camera : ce que la camera voyait au dernier etat confirme
        # C'est CA qu'on compare avec stable_board pour detecter les deltas
        self.camera_baseline: Optional[dict[str, str]] = None
        # True quand le placement a ete confirme
        self.game_started: bool = False

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
        """Lit game_state.json (mode passif)."""
        if not os.path.exists(GAME_STATE_PATH):
            return None
        try:
            with open(GAME_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _flip_square(square: str) -> str:
        """Miroir horizontal : inverse les rangees, garde les colonnes. Ex: e7 -> e2, a1 -> a8."""
        if len(square) != 2:
            return square
        file_char = square[0]  # 'a'-'h' — inchange
        rank_char = square[1]  # '1'-'8'
        flipped_rank = str(9 - int(rank_char))
        return f"{file_char}{flipped_rank}"

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
            sq = chess_pos.lower()
            if self.flip_board:
                sq = self._flip_square(sq)
                # La camera voit les couleurs inversees (blanc=noir, noir=blanc)
                color_char = "B" if color_char == "W" else "W"
            board[sq] = f"{color_char}{type_char}"
        return board

    def find_piece_at(self, square: str) -> Optional[dict]:
        """Retourne les donnees completes de la piece sur une case."""
        if not self.last_game_state:
            return None
        # Si le board est flippe, on cherche la case inverse dans les donnees camera
        target = self._flip_square(square.lower()) if self.flip_board else square.lower()
        for piece in self.last_game_state.get("pieces", []):
            if piece.get("zone") != "board":
                continue
            chess_pos = piece.get("position", {}).get("chess")
            if chess_pos and chess_pos.lower() == target:
                return piece
        return None

    # ------------------------------------------------------------------
    #  Confirmation du placement
    # ------------------------------------------------------------------

    def confirm_placement(self, use_camera: bool = True) -> dict:
        """
        Confirme que les pieces sont bien placees.

        - reference_board = etat logique (pour Stockfish). Toujours 32 pieces.
        - camera_baseline = ce que la camera voit MAINTENANT. Sert de base
          pour la detection delta (on compare futur vs baseline).

        Args:
            use_camera: True = reference logique = camera, False = position standard.
        """
        # Reference logique
        if use_camera and self.stable_board:
            self.reference_board = dict(self.stable_board)
            source = "camera"
        else:
            self.reference_board = {
                "a1": "WR", "b1": "WN", "c1": "WB", "d1": "WQ",
                "e1": "WK", "f1": "WB", "g1": "WN", "h1": "WR",
                "a2": "WP", "b2": "WP", "c2": "WP", "d2": "WP",
                "e2": "WP", "f2": "WP", "g2": "WP", "h2": "WP",
                "a7": "BP", "b7": "BP", "c7": "BP", "d7": "BP",
                "e7": "BP", "f7": "BP", "g7": "BP", "h7": "BP",
                "a8": "BR", "b8": "BN", "c8": "BB", "d8": "BQ",
                "e8": "BK", "f8": "BB", "g8": "BN", "h8": "BR",
            }
            source = "simulated"

        # Baseline camera = snapshot de ce que la camera voit MAINTENANT
        # C'est toujours la camera, meme en mode simule.
        # Comme ca, detect_delta compare "camera maintenant" vs "camera au moment de confirm"
        self.camera_baseline = dict(self.stable_board) if self.stable_board else {}

        self.game_started = True
        self._buffers.clear()
        return {
            "reference_board": self.reference_board,
            "camera_baseline_count": len(self.camera_baseline),
            "source": source,
        }

    def update_reference_after_move(self, from_sq: str, to_sq: str, is_capture: bool = False):
        """Met a jour le board de reference ET la baseline camera apres un coup confirme."""
        # 1. Mettre a jour le board logique (Stockfish)
        if self.reference_board is not None:
            piece = self.reference_board.pop(from_sq, None)
            if piece:
                if is_capture:
                    self.reference_board.pop(to_sq, None)
                self.reference_board[to_sq] = piece

        # 2. Mettre a jour la baseline camera de la meme maniere
        #    Comme ca, detect_delta() ne reverra pas ce coup comme un delta
        if self.camera_baseline is not None:
            cam_piece = self.camera_baseline.pop(from_sq, None)
            if cam_piece:
                if is_capture:
                    self.camera_baseline.pop(to_sq, None)
                self.camera_baseline[to_sq] = cam_piece

    def detect_delta(self) -> Optional[dict]:
        """
        Compare l'etat camera ACTUEL avec la BASELINE camera.

        On ne compare PAS avec reference_board (logique/Stockfish) car
        la camera peut ne pas voir toutes les pieces. On compare
        "ce que la camera voit maintenant" vs "ce qu'elle voyait avant".
        """
        if self.camera_baseline is None or not self.stable_board:
            return None

        baseline = self.camera_baseline
        cam = self.stable_board

        disappeared = {}  # case: code — visible dans baseline, disparu maintenant
        appeared = {}     # case: code — absent dans baseline, visible maintenant
        changed = {}      # case: (baseline_code, cam_code)

        all_squares = set(list(baseline.keys()) + list(cam.keys()))
        for sq in all_squares:
            b = baseline.get(sq)
            c = cam.get(sq)
            if b and not c:
                disappeared[sq] = b
            elif c and not b:
                appeared[sq] = c
            elif b and c and b != c:
                changed[sq] = (b, c)

        if not disappeared and not appeared and not changed:
            return None  # Aucun changement

        # Coup simple : piece blanche disparait, meme piece apparait ailleurs
        for sq_from, code_from in disappeared.items():
            if not code_from.startswith("W"):
                continue
            for sq_to, code_to in appeared.items():
                if code_from == code_to:
                    return {"from": sq_from, "to": sq_to, "type": "move"}

        # Capture : piece blanche disparait de A, case B change de noire a blanche
        for sq_from, code_from in disappeared.items():
            if not code_from.startswith("W"):
                continue
            for sq_to, (base_code, cam_code) in changed.items():
                if base_code.startswith("B") and cam_code == code_from:
                    return {"from": sq_from, "to": sq_to, "type": "capture"}

        # Cas special : piece blanche apparait sans disparition correspondante
        # (la camera ne voyait pas le pion a l'origine dans le baseline)
        # On retourne la destination pour que _check_vision_move puisse
        # chercher dans les coups legaux de Stockfish
        white_appeared = {sq: code for sq, code in appeared.items() if code.startswith("W")}
        if len(white_appeared) == 1 and not disappeared:
            sq_to = list(white_appeared.keys())[0]
            return {"from": None, "to": sq_to, "type": "appeared_only",
                    "appeared": white_appeared}

        # Rien de clair
        return {"from": None, "to": None, "type": "unclear",
                "disappeared": disappeared, "appeared": appeared, "changed": changed}

    # ------------------------------------------------------------------
    #  Update principal
    # ------------------------------------------------------------------

    def update(self) -> bool:
        """
        Capture + analyse, met a jour le buffer et l'etat stabilise.
        Retourne True si une mise a jour a eu lieu.
        """
        if self.active_mode:
            game_state = self._capture_and_analyze()
        else:
            game_state = self._read_game_state()

        if game_state is None:
            return False

        ts = game_state.get("metadata", {}).get("timestamp")
        if ts == self.last_timestamp:
            return False

        self.last_timestamp = ts
        self.last_game_state = game_state
        self.raw_board = self._get_board_map(game_state)
        self.pieces_count = len(self.raw_board)

        all_squares = [f"{c}{r}" for c in "abcdefgh" for r in "12345678"]

        for sq in all_squares:
            if sq not in self._buffers:
                self._buffers[sq] = deque(maxlen=self.BUFFER_SIZE)
            self._buffers[sq].append(self.raw_board.get(sq))

        new_stable = {}
        new_confidence = {}
        for sq in all_squares:
            buf = self._buffers[sq]
            if len(buf) == 0:
                continue

            counts: dict[Optional[str], int] = {}
            for val in buf:
                counts[val] = counts.get(val, 0) + 1

            best_piece = max(counts, key=counts.get)
            best_count = counts[best_piece]

            if best_piece is not None and best_count >= self.STABLE_THRESHOLD:
                new_stable[sq] = best_piece
                new_confidence[sq] = best_count / len(buf)
            elif best_piece is None and best_count >= self.DISAPPEAR_THRESHOLD:
                new_confidence[sq] = 0.0
            else:
                if sq in self.stable_board:
                    new_stable[sq] = self.stable_board[sq]
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
            "game_started": self.game_started,
            "reference_set": self.reference_board is not None,
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
        self.board_reset = BoardResetManager(self.robot)
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
        self.board_reset.set_log_callback(self.log)
        self.board_reset.set_broadcast_callback(self.broadcast)

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
    """Tache de fond : capture + analyse, broadcast, detection delta des coups."""
    manager.vision.running = True
    mode = "actif (capture camera)" if manager.vision.active_mode else "passif (lecture JSON)"
    print(f"👁️ VisionService demarre en mode {mode}")

    while manager.vision.running:
        try:
            updated = manager.vision.update()
            if updated and manager.websocket_clients:
                await manager.broadcast(manager.vision.get_state_message())

            # Detection automatique des coups via delta
            if updated and manager.vision.vision_game_enabled and manager.vision.game_started:
                if manager.status != "idle":
                    pass  # Robot pas idle, on attend
                else:
                    await _check_vision_move()

        except Exception as e:
            print(f"[VisionService] Erreur: {e}")
        # Reduit pour vitesse : 0.3s en actif, 0.5s en passif
        await asyncio.sleep(0.3 if manager.vision.active_mode else 0.5)


_vision_move_lock = False
_last_anomaly: Optional[str] = None
_last_anomaly_time: float = 0


async def _check_vision_move():
    """Detecte un coup humain par delta avec le board de reference."""
    global _vision_move_lock
    if _vision_move_lock:
        return

    # Seulement quand c'est le tour des blancs (joueur humain)
    if manager.chess.board.turn != chess.WHITE:
        return

    delta = manager.vision.detect_delta()
    if delta is None:
        return  # Aucun changement

    print(f"[Vision] Delta detecte: {delta}")

    if delta["type"] == "unclear":
        print(f"[Vision] Delta unclear, on attend: {delta}")
        return

    from_sq = delta.get("from")
    to_sq = delta.get("to")

    # Cas "appeared_only" : la camera voit une piece arriver mais pas
    # le depart (baseline incomplete). On cherche dans les coups legaux
    # de Stockfish celui qui arrive sur cette case.
    if delta["type"] == "appeared_only" and to_sq and not from_sq:
        found_move = None
        for legal_move in manager.chess.board.legal_moves:
            if chess.square_name(legal_move.to_square) == to_sq:
                found_move = legal_move
                break
        if found_move:
            from_sq = chess.square_name(found_move.from_square)
            print(f"[Vision] appeared_only: deduit {from_sq} -> {to_sq} via coups legaux")
        else:
            print(f"[Vision] appeared_only: aucun coup legal vers {to_sq}")
            return

    if not from_sq or not to_sq:
        return

    # Verifier la legalite (avec promotion)
    legal = False
    for suffix in ["", "q", "r", "b", "n"]:
        try:
            move = chess.Move.from_uci(f"{from_sq}{to_sq}{suffix}")
            if move in manager.chess.board.legal_moves:
                legal = True
                break
        except ValueError:
            continue

    if legal:
        _vision_move_lock = True
        try:
            is_capture = delta["type"] == "capture"
            await manager.log("info", f"Coup detecte: {from_sq} -> {to_sq}" + (" (capture)" if is_capture else ""))
            result = await manager.chess.play_vision_move(from_sq, to_sq)
            if result.get("success"):
                # Mettre a jour la reference apres le coup humain
                manager.vision.update_reference_after_move(from_sq, to_sq, is_capture)
                # Aussi mettre a jour apres le coup robot si il a joue
                robot_resp = result.get("robot_response", {})
                if robot_resp.get("success"):
                    r_from = robot_resp.get("from")
                    r_to = robot_resp.get("to")
                    if r_from and r_to:
                        r_capture = manager.vision.reference_board and r_to in manager.vision.reference_board
                        manager.vision.update_reference_after_move(r_from, r_to, r_capture)

                # Vider les buffers pour repartir clean
                manager.vision._buffers.clear()

                # Attendre que les pieces se stabilisent physiquement,
                # puis prendre un nouveau snapshot camera comme baseline
                await asyncio.sleep(1.0)
                manager.vision.update()  # capture fraiche
                if manager.vision.stable_board:
                    manager.vision.camera_baseline = dict(manager.vision.stable_board)
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
    await manager.log("info", "Demande de reset du plateau")
    result = await manager.chess.reset_plateau_with_board()
    
    if result.get("success"):
        await manager.broadcast({
            "type": "plateau_reset",
            "fen": manager.chess.board.fen()
        })
    
    return result


@app.post("/game/replace-board")
async def replace_board():
    """
    Replace toutes les pieces a leur position initiale
    en utilisant la vision camera (game_state.json).

    Prerequis : infinite_chess_vision doit tourner en parallele.
    """
    if manager.status == "replacing":
        return {"success": False, "error": "Replacement deja en cours"}

    manager.set_status("replacing", "Replacement du plateau en cours")
    await manager.log("info", "Replacement du plateau demande")

    try:
        result = await manager.board_reset.replace_board()

        if result.get("success"):
            # Reinitialiser le plateau logique
            manager.chess.board.reset()
            manager.chess.robot.reset_tracking()
            await manager.broadcast({
                "type": "board_replaced",
                "fen": manager.chess.board.fen(),
                "moves_executed": result.get("moves_executed", 0),
            })
            await manager.log("info", "Plateau replace avec succes")
        else:
            await manager.log("warning", result.get("error", "Echec du replacement"))
    finally:
        manager.set_status("idle")

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
