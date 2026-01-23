#!/usr/bin/env python3
"""
API pour contrôler le robot d'échecs depuis une interface web
FastAPI + WebSocket pour communication temps réel
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json
import chess
import chess.engine
from pathlib import Path
from datetime import datetime
import os
import time

# ============================================================================
#                         CONFIGURATION
# ============================================================================

ROBOT_IP = "192.168.0.11"
VITESSE = 0.1
ACCELERATION = 0.3
GRIPPER_OUVERTURE = 25
DELTA_APPROCHE = 0.03
DELTA_TRANSIT = 0.08
DELTA_RELACHE_BASE = 0.004
ESPACEMENT_DEFAUSSE = 0.04

FICHIER_POSITION_DEPART = "position_depart_robot.json"
FICHIER_ZONE_DEFAUSSE = "zone_defausse_robot.json"
FICHIER_MAPPING = "chess_board_positions.json"

# Hauteur de dépose par type de pièce
HAUTEUR_PIECES = {
    chess.PAWN: 0.005,
    chess.KNIGHT: 0.010,
    chess.BISHOP: 0.012,
    chess.ROOK: 0.008,
    chess.QUEEN: 0.015,
    chess.KING: 0.018,
}

# Niveaux de difficulté
DIFFICULTY_PRESETS = {
    'beginner': {'skill_level': 3, 'depth': 8, 'time_limit': 0.5},
    'intermediate': {'skill_level': 10, 'depth': 12, 'time_limit': 1.0},
    'advanced': {'skill_level': 18, 'depth': 18, 'time_limit': 2.0},
}

# ============================================================================
#                         APPLICATION FASTAPI
# ============================================================================

app = FastAPI(title="Chess Robot API", version="1.0.0")

# CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier l'origine exacte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
#                         MODÈLES PYDANTIC
# ============================================================================

class MoveRequest(BaseModel):
    from_square: str
    to_square: str


class GameConfig(BaseModel):
    difficulty: str = "intermediate"


class RobotPosition(BaseModel):
    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float


# ============================================================================
#                         GESTIONNAIRE DE JEU
# ============================================================================

class ChessRobotManager:
    def __init__(self):
        self.board = chess.Board()
        self.engine = None
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.cases = {}
        self.connected = False
        self.difficulty = "intermediate"
        self.status = "idle"  # idle, thinking, moving, error
        self.defausse_index = 0
        self.position_depart = None
        self.zone_defausse_debut = None
        self.zone_defausse_fin = None
        self.piece_courante = None
        self.websocket_clients: List[WebSocket] = []

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

    def init_stockfish(self):
        """Initialise Stockfish"""
        for path in ['/usr/games/stockfish', '/usr/bin/stockfish', '/usr/local/bin/stockfish', 'stockfish']:
            if Path(path).exists():
                try:
                    self.engine = chess.engine.SimpleEngine.popen_uci(path)
                    print(f"✓ Stockfish: {path}")
                    return True
                except:
                    pass
        print("⚠ Stockfish non trouvé")
        return False

    def init_robot(self):
        """Initialise la connexion au robot"""
        try:
            # Charger mapping
            if not os.path.exists(FICHIER_MAPPING):
                print(f"⚠ Mapping non trouvé: {FICHIER_MAPPING}")
                return False

            with open(FICHIER_MAPPING, 'r') as f:
                data = json.load(f)
            self.cases = data.get("cases", {})
            print(f"✓ Mapping: {len(self.cases)} cases")

            # Charger positions
            if os.path.exists(FICHIER_POSITION_DEPART):
                with open(FICHIER_POSITION_DEPART, 'r') as f:
                    self.position_depart = json.load(f).get("position_depart")

            if os.path.exists(FICHIER_ZONE_DEFAUSSE):
                with open(FICHIER_ZONE_DEFAUSSE, 'r') as f:
                    data = json.load(f)
                    self.zone_defausse_debut = data.get("debut")
                    self.zone_defausse_fin = data.get("fin")

            # Connexion robot
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface
            from robotiq_gripper_control import RobotiqGripper

            print(f"Connexion robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)

            print("Activation gripper...")
            self.gripper = RobotiqGripper(self.rtde_c)
            self.gripper.activate()
            self.gripper.set_force(40)
            self.gripper.set_speed(150)
            self.gripper.move(GRIPPER_OUVERTURE)

            self.connected = True
            print("✓ Robot connecté!")
            return True

        except Exception as e:
            print(f"⚠ Erreur robot: {e}")
            self.connected = False
            return False

    def _pos_avec_z(self, tcp, delta_z):
        pos = list(tcp)
        pos[2] += delta_z
        return pos

    def _get_position_defausse(self):
        """Calcule la prochaine position de défausse"""
        if not self.zone_defausse_debut or not self.zone_defausse_fin:
            return None

        import math
        longueur_zone = math.sqrt(
            (self.zone_defausse_fin[0] - self.zone_defausse_debut[0]) ** 2 +
            (self.zone_defausse_fin[1] - self.zone_defausse_debut[1]) ** 2 +
            (self.zone_defausse_fin[2] - self.zone_defausse_debut[2]) ** 2
        )

        max_pieces = max(1, int(longueur_zone / ESPACEMENT_DEFAUSSE))

        if self.defausse_index >= max_pieces:
            self.defausse_index = 0

        distance_parcourue = self.defausse_index * ESPACEMENT_DEFAUSSE

        if longueur_zone > 0:
            dir_x = (self.zone_defausse_fin[0] - self.zone_defausse_debut[0]) / longueur_zone
            dir_y = (self.zone_defausse_fin[1] - self.zone_defausse_debut[1]) / longueur_zone
            dir_z = (self.zone_defausse_fin[2] - self.zone_defausse_debut[2]) / longueur_zone
        else:
            dir_x, dir_y, dir_z = 0, 0, 0

        position = [
            self.zone_defausse_debut[0] + distance_parcourue * dir_x,
            self.zone_defausse_debut[1] + distance_parcourue * dir_y,
            self.zone_defausse_debut[2] + distance_parcourue * dir_z,
            self.zone_defausse_debut[3],
            self.zone_defausse_debut[4],
            self.zone_defausse_debut[5],
        ]

        self.defausse_index += 1
        return position

    async def _prendre_piece(self, case: str):
        """Prend une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            await self.log("error", f"Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        # Identifier la pièce
        square = chess.parse_square(case)
        piece = self.board.piece_at(square)
        if piece:
            self.piece_courante = piece.piece_type

        await self.log("robot", f"Approche {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.2)

        await self.log("robot", f"Descente...")
        self.rtde_c.moveL(tcp, VITESSE, ACCELERATION)
        time.sleep(0.2)

        await self.log("robot", f"Fermeture gripper...")
        self.gripper.close()
        time.sleep(0.3)

        await self.log("robot", f"Remontée...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    async def _poser_piece(self, case: str):
        """Pose une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            await self.log("error", f"Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        hauteur_piece = HAUTEUR_PIECES.get(self.piece_courante, 0.005)
        delta_relache = DELTA_RELACHE_BASE + hauteur_piece

        await self.log("robot", f"Transit vers {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

        await self.log("robot", f"Dépose...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, delta_relache), VITESSE, ACCELERATION)
        time.sleep(0.2)

        self.gripper.move(GRIPPER_OUVERTURE)
        time.sleep(0.3)

        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    async def _deposer_defausse(self):
        """Dépose une pièce dans la zone de défausse"""
        pos_defausse = self._get_position_defausse()

        if pos_defausse:
            await self.log("robot", f"Dépôt en zone de défausse...")
            pos_haute = list(pos_defausse)
            pos_haute[2] += DELTA_TRANSIT
            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)

            pos_relache = list(pos_defausse)
            pos_relache[2] += DELTA_RELACHE_BASE + 0.01
            self.rtde_c.moveL(pos_relache, VITESSE, ACCELERATION)
            time.sleep(0.2)

            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)
        else:
            # Pas de zone, lâcher en l'air
            pose = self.rtde_r.getActualTCPPose()
            pose_haute = list(pose)
            pose_haute[2] += 0.05
            self.rtde_c.moveL(pose_haute, VITESSE, ACCELERATION)
            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

    async def execute_move_on_robot(self, from_sq: str, to_sq: str, is_capture: bool):
        """Exécute un mouvement sur le robot"""
        if not self.connected:
            await self.log("warning", "Robot non connecté - Simulation")
            return True

        try:
            self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")

            if is_capture:
                await self.log("robot", f"Capture: {from_sq.upper()} prend {to_sq.upper()}")

                # Retirer la pièce capturée
                await self._prendre_piece(to_sq)
                await self._deposer_defausse()

                # Déplacer la pièce qui capture
                await self._prendre_piece(from_sq)
                await self._poser_piece(to_sq)
            else:
                await self.log("robot", f"Déplacement: {from_sq.upper()} → {to_sq.upper()}")
                await self._prendre_piece(from_sq)
                await self._poser_piece(to_sq)

            # Retour position de départ
            if self.position_depart:
                self.rtde_c.moveL(self.position_depart, VITESSE, ACCELERATION)

            self.set_status("idle")
            return True

        except Exception as e:
            await self.log("error", f"Erreur robot: {e}")
            self.set_status("error", str(e))
            return False

    async def play_human_move(self, from_sq: str, to_sq: str):
        """Joue le coup du joueur humain"""
        # Vérifier que le coup est légal
        try:
            move = chess.Move.from_uci(f"{from_sq}{to_sq}")

            # Vérifier promotion
            piece = self.board.piece_at(chess.parse_square(from_sq))
            if piece and piece.piece_type == chess.PAWN:
                to_rank = to_sq[1]
                if (piece.color == chess.WHITE and to_rank == '8') or \
                        (piece.color == chess.BLACK and to_rank == '1'):
                    move = chess.Move.from_uci(f"{from_sq}{to_sq}q")  # Promotion en dame

            if move not in self.board.legal_moves:
                # Essayer avec promotion
                move = chess.Move.from_uci(f"{from_sq}{to_sq}q")
                if move not in self.board.legal_moves:
                    return {"success": False, "error": "Coup illégal"}
        except:
            return {"success": False, "error": "Format de coup invalide"}

        is_capture = self.board.is_capture(move)

        # Exécuter sur le robot
        await self.execute_move_on_robot(from_sq, to_sq, is_capture)

        # Jouer sur le plateau virtuel
        san = self.board.san(move)
        self.board.push(move)

        await self.broadcast({
            "type": "move",
            "player": "human",
            "from": from_sq,
            "to": to_sq,
            "san": san,
            "fen": self.board.fen()
        })

        # Vérifier fin de partie
        if self.board.is_game_over():
            result = self.get_game_result()
            await self.broadcast({"type": "game_over", "result": result})
            return {"success": True, "san": san, "game_over": True, "result": result}

        return {"success": True, "san": san}

    async def play_robot_move(self):
        """Calcule et joue le coup du robot"""
        if not self.engine:
            return {"success": False, "error": "Stockfish non disponible"}

        self.set_status("thinking", "Analyse de la position...")
        await self.log("robot", "Robot analyse la position...")

        # Configurer selon la difficulté
        preset = DIFFICULTY_PRESETS.get(self.difficulty, DIFFICULTY_PRESETS['intermediate'])
        self.engine.configure({"Skill Level": preset['skill_level']})

        try:
            # Analyser
            info = self.engine.analyse(
                self.board,
                chess.engine.Limit(depth=preset['depth'], time=preset['time_limit'])
            )

            move = info.get("pv", [None])[0]
            if not move:
                return {"success": False, "error": "Pas de coup trouvé"}

            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)
            is_capture = self.board.is_capture(move)

            # Évaluation
            score = info.get("score")
            evaluation = 0.0
            if score and score.relative.score():
                evaluation = score.relative.score() / 100

            await self.log("robot", f"Coup choisi: {from_sq} → {to_sq} (eval: {evaluation:+.2f})")

            # Exécuter sur le robot
            await self.execute_move_on_robot(from_sq, to_sq, is_capture)

            # Jouer sur le plateau virtuel
            san = self.board.san(move)
            self.board.push(move)

            await self.broadcast({
                "type": "move",
                "player": "robot",
                "from": from_sq,
                "to": to_sq,
                "san": san,
                "evaluation": evaluation,
                "fen": self.board.fen()
            })

            self.set_status("idle")

            # Vérifier fin de partie
            if self.board.is_game_over():
                result = self.get_game_result()
                await self.broadcast({"type": "game_over", "result": result})
                return {"success": True, "from": from_sq, "to": to_sq, "san": san, "game_over": True, "result": result}

            return {"success": True, "from": from_sq, "to": to_sq, "san": san, "evaluation": evaluation}

        except Exception as e:
            self.set_status("error", str(e))
            return {"success": False, "error": str(e)}

    def get_game_result(self):
        """Retourne le résultat de la partie"""
        if self.board.is_checkmate():
            winner = "Noirs" if self.board.turn == chess.WHITE else "Blancs"
            return f"Échec et mat! {winner} gagnent"
        elif self.board.is_stalemate():
            return "Pat - Nulle"
        elif self.board.is_insufficient_material():
            return "Matériel insuffisant - Nulle"
        elif self.board.is_fifty_moves():
            return "Règle des 50 coups - Nulle"
        elif self.board.is_repetition():
            return "Répétition - Nulle"
        return "Partie en cours"

    def new_game(self, difficulty: str = "intermediate"):
        """Démarre une nouvelle partie"""
        self.board.reset()
        self.difficulty = difficulty
        self.defausse_index = 0
        self.set_status("idle")
        return {"success": True, "fen": self.board.fen()}

    def get_legal_moves(self, square: str):
        """Retourne les coups légaux pour une case"""
        try:
            sq = chess.parse_square(square.lower())
            piece = self.board.piece_at(sq)

            if not piece:
                return []

            legal_destinations = []
            for move in self.board.legal_moves:
                if move.from_square == sq:
                    legal_destinations.append(chess.square_name(move.to_square))

            return legal_destinations
        except:
            return []

    def close(self):
        """Ferme les connexions"""
        if self.engine:
            self.engine.quit()
        if self.rtde_c:
            self.rtde_c.stopScript()


# Instance globale du gestionnaire
manager = ChessRobotManager()


# ============================================================================
#                         ROUTES API
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialisation au démarrage"""
    manager.init_stockfish()
    manager.init_robot()


@app.on_event("shutdown")
async def shutdown():
    """Nettoyage à l'arrêt"""
    manager.close()


@app.get("/")
async def root():
    return {"message": "Chess Robot API", "version": "1.0.0"}


@app.get("/status")
async def get_status():
    """Retourne le statut du robot"""
    return {
        "connected": manager.connected,
        "status": manager.status,
        "difficulty": manager.difficulty,
        "fen": manager.board.fen(),
        "turn": "white" if manager.board.turn == chess.WHITE else "black",
        "is_game_over": manager.board.is_game_over()
    }


@app.post("/game/new")
async def new_game(config: GameConfig):
    """Démarre une nouvelle partie"""
    result = manager.new_game(config.difficulty)
    await manager.log("info", f"Nouvelle partie - Difficulté: {config.difficulty}")
    return result


@app.get("/game/fen")
async def get_fen():
    """Retourne la position FEN actuelle"""
    return {"fen": manager.board.fen()}


@app.get("/game/legal-moves/{square}")
async def get_legal_moves(square: str):
    """Retourne les coups légaux pour une case"""
    moves = manager.get_legal_moves(square)
    return {"square": square, "moves": moves}


@app.post("/game/move/human")
async def human_move(move: MoveRequest):
    """Joue le coup du joueur humain"""
    result = await manager.play_human_move(move.from_square, move.to_square)
    return result


@app.post("/game/move/robot")
async def robot_move():
    """Demande au robot de jouer son coup"""
    result = await manager.play_robot_move()
    return result


@app.get("/robot/position")
async def get_robot_position():
    """Retourne la position actuelle du robot"""
    if not manager.connected or not manager.rtde_r:
        return {"error": "Robot non connecté"}

    pose = manager.rtde_r.getActualTCPPose()
    return {
        "x": pose[0],
        "y": pose[1],
        "z": pose[2],
        "rx": pose[3],
        "ry": pose[4],
        "rz": pose[5]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les mises à jour en temps réel"""
    await websocket.accept()
    manager.websocket_clients.append(websocket)

    try:
        # Envoyer le statut initial
        await websocket.send_json({
            "type": "connected",
            "status": manager.status,
            "fen": manager.board.fen(),
            "robot_connected": manager.connected
        })

        while True:
            # Garder la connexion ouverte et écouter les messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Traiter les commandes WebSocket
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.websocket_clients.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
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
    print("\nDémarrage du serveur...")
    print("Interface: http://localhost:8000")
    print("Documentation: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)