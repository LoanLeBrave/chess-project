#!/usr/bin/env python3
"""
API pour contrôler le robot d'échecs depuis une interface web
FastAPI + WebSocket pour communication temps réel

AJOUT: Suivi des pièces éliminées et remise en place en fin de partie
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import json
import chess
import chess.engine
from pathlib import Path
from datetime import datetime
import os
import time
import math

# ============================================================================
#                         CONFIGURATION
# ============================================================================

ROBOT_IP = "192.168.0.11"
VITESSE = 0.1
ACCELERATION = 0.3
GRIPPER_OUVERTURE = 25
DELTA_APPROCHE = 0.03  # 3cm - hauteur d'approche avant descente
DELTA_TRANSIT = 0.12  # 12cm - hauteur de déplacement à vide (AUGMENTÉ)
DELTA_RELACHE_BASE = 0.001  # 1mm - hauteur de relâche (DIMINUÉ)
ESPACEMENT_ELIMINATION = 0.02  # 2cm entre les pièces éliminées

FICHIER_POSITION_DEPART = "position_depart_robot.json"
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

# Position initiale des pièces (pour le reset)
POSITION_INITIALE = {
    'a1': ('R', chess.WHITE), 'b1': ('N', chess.WHITE), 'c1': ('B', chess.WHITE), 'd1': ('Q', chess.WHITE),
    'e1': ('K', chess.WHITE), 'f1': ('B', chess.WHITE), 'g1': ('N', chess.WHITE), 'h1': ('R', chess.WHITE),
    'a2': ('P', chess.WHITE), 'b2': ('P', chess.WHITE), 'c2': ('P', chess.WHITE), 'd2': ('P', chess.WHITE),
    'e2': ('P', chess.WHITE), 'f2': ('P', chess.WHITE), 'g2': ('P', chess.WHITE), 'h2': ('P', chess.WHITE),
    'a7': ('p', chess.BLACK), 'b7': ('p', chess.BLACK), 'c7': ('p', chess.BLACK), 'd7': ('p', chess.BLACK),
    'e7': ('p', chess.BLACK), 'f7': ('p', chess.BLACK), 'g7': ('p', chess.BLACK), 'h7': ('p', chess.BLACK),
    'a8': ('r', chess.BLACK), 'b8': ('n', chess.BLACK), 'c8': ('b', chess.BLACK), 'd8': ('q', chess.BLACK),
    'e8': ('k', chess.BLACK), 'f8': ('b', chess.BLACK), 'g8': ('n', chess.BLACK), 'h8': ('r', chess.BLACK),
}

# Mapping symbole -> type de pièce
PIECE_TYPE_MAP = {
    'P': chess.PAWN, 'p': chess.PAWN,
    'N': chess.KNIGHT, 'n': chess.KNIGHT,
    'B': chess.BISHOP, 'b': chess.BISHOP,
    'R': chess.ROOK, 'r': chess.ROOK,
    'Q': chess.QUEEN, 'q': chess.QUEEN,
    'K': chess.KING, 'k': chess.KING,
}

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
#                    STRUCTURE POUR PIÈCE ÉLIMINÉE
# ============================================================================

class PieceEliminee:
    """Représente une pièce éliminée et sa position de stockage"""

    def __init__(self, piece_symbol: str, color: bool, case_origine: str,
                 position_elimination: List[float], index: int):
        self.piece_symbol = piece_symbol  # 'P', 'N', 'B', 'R', 'Q', 'K' (majuscule)
        self.color = color  # chess.WHITE ou chess.BLACK
        self.case_origine = case_origine  # Case d'où la pièce a été capturée
        self.position_elimination = position_elimination  # Position TCP de stockage
        self.index = index  # Index dans la zone d'élimination

    def to_dict(self):
        return {
            "piece": self.piece_symbol,
            "color": "white" if self.color == chess.WHITE else "black",
            "case_origine": self.case_origine,
            "position": self.position_elimination,
            "index": self.index
        }


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
        self.status = "idle"
        self.piece_courante = None
        self.websocket_clients: List[WebSocket] = []

        # Position de départ du robot
        self.position_depart = None

        # === ZONES D'ÉLIMINATION (NOUVEAU) ===
        self.zone_elimination_blancs_min = None
        self.zone_elimination_blancs_max = None
        self.zone_elimination_noirs_min = None
        self.zone_elimination_noirs_max = None
        self.espacement_elimination = ESPACEMENT_ELIMINATION

        # === SUIVI DES PIÈCES ÉLIMINÉES (NOUVEAU) ===
        self.pieces_blanches_eliminees: List[PieceEliminee] = []
        self.pieces_noires_eliminees: List[PieceEliminee] = []
        self.index_elimination_blancs = 0
        self.index_elimination_noirs = 0

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
        stockfish_paths = [
            '/usr/games/stockfish',
            '/usr/bin/stockfish',
            '/usr/local/bin/stockfish',
            '/opt/homebrew/bin/stockfish',
            '/opt/homebrew/Cellar/stockfish/17/bin/stockfish',
            'stockfish'
        ]
        for path in stockfish_paths:
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
            if not os.path.exists(FICHIER_MAPPING):
                print(f"⚠ Mapping non trouvé: {FICHIER_MAPPING}")
                return False

            with open(FICHIER_MAPPING, 'r') as f:
                data = json.load(f)

            self.cases = data.get("cases", {})
            print(f"✓ Mapping: {len(self.cases)} cases")

            # === CHARGER ZONES D'ÉLIMINATION (NOUVEAU) ===
            self.zone_elimination_blancs_min = data.get("zone_elimination_blancs_min")
            self.zone_elimination_blancs_max = data.get("zone_elimination_blancs_max")
            self.zone_elimination_noirs_min = data.get("zone_elimination_noirs_min")
            self.zone_elimination_noirs_max = data.get("zone_elimination_noirs_max")
            self.espacement_elimination = data.get("espacement_elimination", ESPACEMENT_ELIMINATION)

            if self.zone_elimination_blancs_min and self.zone_elimination_blancs_max:
                nb = self._calculer_nb_positions_zone(
                    self.zone_elimination_blancs_min,
                    self.zone_elimination_blancs_max
                )
                print(f"✓ Zone élimination blancs: {nb} positions")
            if self.zone_elimination_noirs_min and self.zone_elimination_noirs_max:
                nb = self._calculer_nb_positions_zone(
                    self.zone_elimination_noirs_min,
                    self.zone_elimination_noirs_max
                )
                print(f"✓ Zone élimination noirs: {nb} positions")

            # Charger position de départ
            if os.path.exists(FICHIER_POSITION_DEPART):
                with open(FICHIER_POSITION_DEPART, 'r') as f:
                    self.position_depart = json.load(f).get("position_depart")

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

    # === NOUVELLES MÉTHODES POUR LES ZONES D'ÉLIMINATION ===

    def _calculer_nb_positions_zone(self, pos_min, pos_max):
        """Calcule le nombre de positions dans une zone d'élimination"""
        distance = math.sqrt(
            (pos_max[0] - pos_min[0]) ** 2 +
            (pos_max[1] - pos_min[1]) ** 2
        )
        return max(1, int(distance / self.espacement_elimination) + 1)

    def _get_position_elimination(self, color: bool):
        """
        Calcule la prochaine position d'élimination pour une couleur donnée.
        color: chess.WHITE ou chess.BLACK (pièce capturée)
        Retourne la position TCP ou None
        """
        if color == chess.WHITE:
            # Pièce blanche capturée -> zone blancs
            pos_min = self.zone_elimination_blancs_min
            pos_max = self.zone_elimination_blancs_max
            index = self.index_elimination_blancs
        else:
            # Pièce noire capturée -> zone noirs
            pos_min = self.zone_elimination_noirs_min
            pos_max = self.zone_elimination_noirs_max
            index = self.index_elimination_noirs

        if not pos_min or not pos_max:
            return None

        # Calculer la distance totale
        distance_totale = math.sqrt(
            (pos_max[0] - pos_min[0]) ** 2 +
            (pos_max[1] - pos_min[1]) ** 2
        )

        if distance_totale == 0:
            return list(pos_min)

        # Direction unitaire
        dir_x = (pos_max[0] - pos_min[0]) / distance_totale
        dir_y = (pos_max[1] - pos_min[1]) / distance_totale

        # Position = min + index * espacement * direction
        distance_parcourue = index * self.espacement_elimination

        # Vérifier qu'on ne dépasse pas
        if distance_parcourue > distance_totale:
            # Revenir au début (ou gérer autrement)
            distance_parcourue = distance_parcourue % (distance_totale + self.espacement_elimination)

        position = [
            pos_min[0] + distance_parcourue * dir_x,
            pos_min[1] + distance_parcourue * dir_y,
            pos_min[2],  # Garder la même hauteur Z
            pos_min[3],  # Garder l'orientation
            pos_min[4],
            pos_min[5],
        ]

        return position

    def _pos_avec_z(self, tcp, delta_z):
        """Retourne une position TCP avec un décalage en Z"""
        pos = list(tcp)
        pos[2] += delta_z
        return pos

    # === MÉTHODES DE MOUVEMENT ROBOT ===

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
        # D'abord aller en hauteur de transit au-dessus de la case
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.1)

        # Descendre en approche
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

        await self.log("robot", f"Descente...")
        self.rtde_c.moveL(tcp, VITESSE, ACCELERATION)
        time.sleep(0.2)

        await self.log("robot", f"Fermeture gripper...")
        self.gripper.close()
        time.sleep(0.3)

        await self.log("robot", f"Remontée...")
        # Remonter en approche
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

        # Monter à hauteur de transit pour le déplacement
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.1)

        return True

    async def _poser_piece(self, case: str):
        """Pose une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            await self.log("error", f"Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        # Hauteur de relâche = juste au-dessus de la position de prise
        # On ne rajoute PAS la hauteur de la pièce pour déposer plus bas
        delta_relache = DELTA_RELACHE_BASE

        await self.log("robot", f"Transit vers {case.upper()}...")
        # Rester à hauteur de transit pendant tout le déplacement
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        # Descendre en approche
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

        await self.log("robot", f"Dépose...")
        # Descendre pour relâcher (très proche de la surface)
        self.rtde_c.moveL(self._pos_avec_z(tcp, delta_relache), VITESSE, ACCELERATION)
        time.sleep(0.2)

        self.gripper.move(GRIPPER_OUVERTURE)
        time.sleep(0.3)

        # Remonter en approche puis transit
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.1)

        return True

    async def _deposer_elimination(self, piece_symbol: str, color: bool, case_origine: str):
        """
        Dépose une pièce capturée dans la zone d'élimination (MODIFIÉ)
        Enregistre la position pour pouvoir la récupérer plus tard
        """
        pos_elimination = self._get_position_elimination(color)

        if pos_elimination:
            await self.log("robot",
                           f"Dépôt pièce {'blanche' if color == chess.WHITE else 'noire'} en zone d'élimination...")

            # Mouvement vers la zone
            pos_haute = self._pos_avec_z(pos_elimination, DELTA_TRANSIT)
            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)

            pos_relache = self._pos_avec_z(pos_elimination, DELTA_RELACHE_BASE + 0.01)
            self.rtde_c.moveL(pos_relache, VITESSE, ACCELERATION)
            time.sleep(0.2)

            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)

            # === ENREGISTRER LA PIÈCE ÉLIMINÉE (NOUVEAU) ===
            if color == chess.WHITE:
                piece_eliminee = PieceEliminee(
                    piece_symbol=piece_symbol.upper(),
                    color=color,
                    case_origine=case_origine,
                    position_elimination=pos_elimination,
                    index=self.index_elimination_blancs
                )
                self.pieces_blanches_eliminees.append(piece_eliminee)
                self.index_elimination_blancs += 1
                await self.log("info", f"Pièce blanche {piece_symbol} stockée (index {piece_eliminee.index})")
            else:
                piece_eliminee = PieceEliminee(
                    piece_symbol=piece_symbol.upper(),
                    color=color,
                    case_origine=case_origine,
                    position_elimination=pos_elimination,
                    index=self.index_elimination_noirs
                )
                self.pieces_noires_eliminees.append(piece_eliminee)
                self.index_elimination_noirs += 1
                await self.log("info", f"Pièce noire {piece_symbol} stockée (index {piece_eliminee.index})")
        else:
            # Pas de zone configurée, lâcher en hauteur
            pose = self.rtde_r.getActualTCPPose()
            pose_haute = list(pose)
            pose_haute[2] += 0.05
            self.rtde_c.moveL(pose_haute, VITESSE, ACCELERATION)
            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)
            await self.log("warning", "Pas de zone d'élimination configurée!")

    async def _prendre_piece_elimination(self, position: List[float]):
        """Prend une pièce dans la zone d'élimination"""
        await self.log("robot", "Récupération pièce en zone d'élimination...")

        pos_haute = self._pos_avec_z(position, DELTA_TRANSIT)
        self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
        time.sleep(0.2)

        pos_approche = self._pos_avec_z(position, DELTA_APPROCHE)
        self.rtde_c.moveL(pos_approche, VITESSE, ACCELERATION)
        time.sleep(0.1)

        # Descendre pour prendre
        self.rtde_c.moveL(position, VITESSE, ACCELERATION)
        time.sleep(0.2)

        self.gripper.close()
        time.sleep(0.3)

        self.rtde_c.moveL(pos_approche, VITESSE, ACCELERATION)
        time.sleep(0.1)

        self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    async def execute_move_on_robot(self, from_sq: str, to_sq: str, is_capture: bool, captured_piece=None):
        """Exécute un mouvement sur le robot (MODIFIÉ pour enregistrer les captures)"""
        if not self.connected:
            await self.log("warning", "Robot non connecté - Simulation")
            return True

        try:
            self.set_status("moving", f"Déplacement {from_sq} → {to_sq}")

            if is_capture and captured_piece:
                await self.log("robot", f"Capture: {from_sq.upper()} prend {to_sq.upper()}")

                # Identifier la pièce capturée
                piece_symbol = captured_piece.symbol()
                piece_color = captured_piece.color

                # Retirer la pièce capturée
                await self._prendre_piece(to_sq)

                # Déposer en zone d'élimination avec enregistrement
                await self._deposer_elimination(piece_symbol, piece_color, to_sq)

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

    # === NOUVELLE MÉTHODE: RESET DU PLATEAU ===

    async def reset_plateau(self):
        """
        Remet toutes les pièces à leur position initiale.
        1. Récupère les pièces éliminées et les replace
        2. Remet les pièces déplacées à leur position d'origine
        """
        if not self.connected:
            await self.log("warning", "Robot non connecté - Simulation du reset")
            self._reset_tracking()
            return {"success": True, "message": "Reset simulé (robot non connecté)"}

        try:
            self.set_status("moving", "Remise en place du plateau...")
            await self.log("info", "=== DÉBUT RESET PLATEAU ===")

            # 1. Replacer les pièces blanches éliminées
            await self.log("info", f"Pièces blanches à replacer: {len(self.pieces_blanches_eliminees)}")
            for piece in self.pieces_blanches_eliminees:
                await self.log("robot", f"Replacement {piece.piece_symbol} blanc → {piece.case_origine}")

                # Prendre la pièce dans la zone d'élimination
                await self._prendre_piece_elimination(piece.position_elimination)
                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol, chess.PAWN)

                # La poser à sa case d'origine
                await self._poser_piece(piece.case_origine)

            # 2. Replacer les pièces noires éliminées
            await self.log("info", f"Pièces noires à replacer: {len(self.pieces_noires_eliminees)}")
            for piece in self.pieces_noires_eliminees:
                await self.log("robot", f"Replacement {piece.piece_symbol} noir → {piece.case_origine}")

                await self._prendre_piece_elimination(piece.position_elimination)
                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol, chess.PAWN)

                await self._poser_piece(piece.case_origine)

            # 3. Remettre les pièces sur le plateau à leur position initiale
            # On analyse la position actuelle vs position initiale
            await self._replacer_pieces_deplacees()

            # Retour position de départ
            if self.position_depart:
                self.rtde_c.moveL(self.position_depart, VITESSE, ACCELERATION)

            await self.log("info", "=== FIN RESET PLATEAU ===")

            # Réinitialiser le tracking
            self._reset_tracking()

            self.set_status("idle")
            return {"success": True, "message": "Plateau remis en place"}

        except Exception as e:
            await self.log("error", f"Erreur reset: {e}")
            self.set_status("error", str(e))
            return {"success": False, "error": str(e)}

    async def _replacer_pieces_deplacees(self):
        """Replace les pièces encore sur le plateau à leur position initiale"""
        # Obtenir la position actuelle du plateau
        current_board = self.board

        # Pour chaque case de la position initiale
        for case_init, (piece_symbol, color) in POSITION_INITIALE.items():
            square = chess.parse_square(case_init)
            piece_actuelle = current_board.piece_at(square)

            # Si la pièce attendue n'est pas à sa place
            if piece_actuelle is None or piece_actuelle.symbol().upper() != piece_symbol.upper():
                # Chercher où est cette pièce actuellement
                case_actuelle = self._trouver_piece_sur_plateau(piece_symbol, color, current_board)

                if case_actuelle and case_actuelle != case_init:
                    await self.log("robot", f"Déplacement {piece_symbol} de {case_actuelle} → {case_init}")
                    await self._prendre_piece(case_actuelle)
                    self.piece_courante = PIECE_TYPE_MAP.get(piece_symbol.upper(), chess.PAWN)
                    await self._poser_piece(case_init)

    def _trouver_piece_sur_plateau(self, piece_symbol: str, color: bool, board: chess.Board):
        """Trouve la position actuelle d'une pièce sur le plateau"""
        piece_type = PIECE_TYPE_MAP.get(piece_symbol.upper())
        if not piece_type:
            return None

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == piece_type and piece.color == color:
                # Vérifier si cette pièce n'est pas déjà à sa place initiale
                case_name = chess.square_name(square)
                if case_name in POSITION_INITIALE:
                    init_piece, init_color = POSITION_INITIALE[case_name]
                    if init_piece.upper() == piece_symbol.upper() and init_color == color:
                        continue  # Cette pièce est déjà à sa place
                return case_name
        return None

    def _reset_tracking(self):
        """Réinitialise le suivi des pièces éliminées"""
        self.pieces_blanches_eliminees = []
        self.pieces_noires_eliminees = []
        self.index_elimination_blancs = 0
        self.index_elimination_noirs = 0
        self.board.reset()

    def get_pieces_eliminees(self):
        """Retourne la liste des pièces éliminées"""
        return {
            "blanches": [p.to_dict() for p in self.pieces_blanches_eliminees],
            "noires": [p.to_dict() for p in self.pieces_noires_eliminees]
        }

    async def play_human_move(self, from_sq: str, to_sq: str):
        """Joue le coup du joueur humain (MODIFIÉ pour passer captured_piece)"""
        try:
            move = chess.Move.from_uci(f"{from_sq}{to_sq}")

            # Vérifier promotion
            piece = self.board.piece_at(chess.parse_square(from_sq))
            if piece and piece.piece_type == chess.PAWN:
                to_rank = to_sq[1]
                if (piece.color == chess.WHITE and to_rank == '8') or \
                        (piece.color == chess.BLACK and to_rank == '1'):
                    move = chess.Move.from_uci(f"{from_sq}{to_sq}q")

            if move not in self.board.legal_moves:
                move = chess.Move.from_uci(f"{from_sq}{to_sq}q")
                if move not in self.board.legal_moves:
                    return {"success": False, "error": "Coup illégal"}
        except:
            return {"success": False, "error": "Format de coup invalide"}

        is_capture = self.board.is_capture(move)

        # Récupérer la pièce capturée AVANT de jouer le coup
        captured_piece = None
        if is_capture:
            to_square = chess.parse_square(to_sq)
            captured_piece = self.board.piece_at(to_square)
            # En passant
            if captured_piece is None and piece and piece.piece_type == chess.PAWN:
                # La pièce capturée est sur une case différente (en passant)
                ep_square = self.board.ep_square
                if ep_square:
                    captured_piece = self.board.piece_at(ep_square - 8 if piece.color == chess.WHITE else ep_square + 8)

        # Exécuter sur le robot avec la pièce capturée
        await self.execute_move_on_robot(from_sq, to_sq, is_capture, captured_piece)

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
        """Calcule et joue le coup du robot (MODIFIÉ pour passer captured_piece)"""
        if not self.engine:
            return {"success": False, "error": "Stockfish non disponible"}

        self.set_status("thinking", "Analyse de la position...")
        await self.log("robot", "Robot analyse la position...")

        preset = DIFFICULTY_PRESETS.get(self.difficulty, DIFFICULTY_PRESETS['intermediate'])
        self.engine.configure({"Skill Level": preset['skill_level']})

        try:
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

            # Récupérer la pièce capturée AVANT de jouer le coup
            captured_piece = None
            if is_capture:
                captured_piece = self.board.piece_at(move.to_square)
                # En passant
                if captured_piece is None:
                    piece = self.board.piece_at(move.from_square)
                    if piece and piece.piece_type == chess.PAWN:
                        ep_square = self.board.ep_square
                        if ep_square:
                            captured_piece = self.board.piece_at(
                                ep_square - 8 if piece.color == chess.WHITE else ep_square + 8)

            # Évaluation
            score = info.get("score")
            evaluation = 0.0
            if score and score.relative.score():
                evaluation = score.relative.score() / 100

            await self.log("robot", f"Coup choisi: {from_sq} → {to_sq} (eval: {evaluation:+.2f})")

            # Exécuter sur le robot avec la pièce capturée
            await self.execute_move_on_robot(from_sq, to_sq, is_capture, captured_piece)

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
        """Démarre une nouvelle partie (MODIFIÉ pour reset le tracking)"""
        self.board.reset()
        self.difficulty = difficulty
        # Reset du suivi des éliminations
        self._reset_tracking()
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
    return {"message": "Chess Robot API", "version": "2.0.0"}


@app.get("/status")
async def get_status():
    """Retourne le statut du robot"""
    return {
        "connected": manager.connected,
        "status": manager.status,
        "difficulty": manager.difficulty,
        "fen": manager.board.fen(),
        "turn": "white" if manager.board.turn == chess.WHITE else "black",
        "is_game_over": manager.board.is_game_over(),
        "pieces_eliminees": manager.get_pieces_eliminees()
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


@app.get("/game/best-move")
async def get_best_move():
    """Retourne le meilleur coup pour le joueur actuel"""
    if not manager.engine:
        return {"success": False, "error": "Stockfish non disponible"}

    try:
        manager.engine.configure({"Skill Level": 20})

        info = manager.engine.analyse(
            manager.board,
            chess.engine.Limit(depth=15, time=1.0)
        )

        move = info.get("pv", [None])[0]
        if not move:
            return {"success": False, "error": "Pas de coup trouvé"}

        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)

        return {
            "success": True,
            "from": from_sq,
            "to": to_sq
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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


# === NOUVELLES ROUTES ===

@app.get("/game/pieces-eliminees")
async def get_pieces_eliminees():
    """Retourne la liste des pièces éliminées"""
    return manager.get_pieces_eliminees()


@app.post("/game/reset-plateau")
async def reset_plateau():
    """Remet toutes les pièces à leur position initiale"""
    await manager.log("info", "Demande de reset du plateau")
    result = await manager.reset_plateau()
    return result


@app.post("/game/stop")
async def stop_game():
    """Arrête la partie et remet le plateau en place"""
    await manager.log("info", "Arrêt de la partie demandé")

    # Remettre le plateau en place
    result = await manager.reset_plateau()

    if result.get("success"):
        await manager.broadcast({"type": "game_stopped", "message": "Partie arrêtée, plateau remis en place"})

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
        await websocket.send_json({
            "type": "connected",
            "status": manager.status,
            "fen": manager.board.fen(),
            "robot_connected": manager.connected,
            "pieces_eliminees": manager.get_pieces_eliminees()
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


# ============================================================================
#                         MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("     ♔ CHESS ROBOT API v2.0 ♚")
    print("=" * 60)
    print("\nNouvelles fonctionnalités:")
    print("  - Suivi des pièces éliminées")
    print("  - Zones d'élimination configurables")
    print("  - Reset automatique du plateau")
    print("\nDémarrage du serveur...")
    print("Interface: http://localhost:8000")
    print("Documentation: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)