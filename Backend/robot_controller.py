#!/usr/bin/env python3
"""
Contrôle du robot UR5e et du gripper Robotiq
Gère les mouvements physiques et la manipulation des pièces
"""

import time
import math
import json
import os
from typing import List, Optional
from pathlib import Path

from config import (
    ROBOT_IP, VITESSE, ACCELERATION, GRIPPER_OUVERTURE,
    DELTA_APPROCHE, DELTA_TRANSIT, DELTA_RELACHE_BASE,
    ESPACEMENT_ELIMINATION, FICHIER_POSITION_DEPART, FICHIER_MAPPING,
    PIECE_TYPE_MAP
)
from models import PieceEliminee
import chess


class RobotController:
    """Contrôleur pour le robot UR5e avec gripper Robotiq"""

    def __init__(self):
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.cases = {}
        self.connected = False
        self.position_depart = None
        self.piece_courante = None

        # Zones d'élimination
        self.zone_elimination_blancs_min = None
        self.zone_elimination_blancs_max = None
        self.zone_elimination_noirs_min = None
        self.zone_elimination_noirs_max = None
        self.espacement_elimination = ESPACEMENT_ELIMINATION

        # Suivi des pièces éliminées
        self.pieces_blanches_eliminees: List[PieceEliminee] = []
        self.pieces_noires_eliminees: List[PieceEliminee] = []
        self.index_elimination_blancs = 0
        self.index_elimination_noirs = 0

        # Callback pour logging
        self.log_callback = None

    def set_log_callback(self, callback):
        """Définit le callback pour les logs"""
        self.log_callback = callback

    async def log(self, log_type: str, message: str):
        """Envoie un log via le callback"""
        if self.log_callback:
            await self.log_callback(log_type, message)

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

            # Charger zones d'élimination
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
            pos_min = self.zone_elimination_blancs_min
            pos_max = self.zone_elimination_blancs_max
            index = self.index_elimination_blancs
        else:
            pos_min = self.zone_elimination_noirs_min
            pos_max = self.zone_elimination_noirs_max
            index = self.index_elimination_noirs

        if not pos_min or not pos_max:
            return None

        distance_totale = math.sqrt(
            (pos_max[0] - pos_min[0]) ** 2 +
            (pos_max[1] - pos_min[1]) ** 2
        )

        if distance_totale == 0:
            return list(pos_min)

        dir_x = (pos_max[0] - pos_min[0]) / distance_totale
        dir_y = (pos_max[1] - pos_min[1]) / distance_totale

        distance_parcourue = index * self.espacement_elimination

        if distance_parcourue > distance_totale:
            distance_parcourue = distance_parcourue % (distance_totale + self.espacement_elimination)

        position = [
            pos_min[0] + distance_parcourue * dir_x,
            pos_min[1] + distance_parcourue * dir_y,
            pos_min[2],
            pos_min[3],
            pos_min[4],
            pos_min[5],
        ]

        return position

    def _pos_avec_z(self, tcp, delta_z):
        """Retourne une position TCP avec un décalage en Z"""
        pos = list(tcp)
        pos[2] += delta_z
        return pos

    async def _prendre_piece(self, case: str):
        """Prend une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            await self.log("error", f"Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        # Identifier la pièce (sera définie par l'appelant)
        await self.log("robot", f"Approche {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.1)

        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_APPROCHE), VITESSE, ACCELERATION)
        time.sleep(0.1)

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
        time.sleep(0.1)

        return True

    async def _poser_piece(self, case: str):
        """Pose une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            await self.log("error", f"Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        delta_relache = DELTA_RELACHE_BASE

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
        time.sleep(0.1)

        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.1)

        return True

    async def _deposer_elimination(self, piece_symbol: str, color: bool, case_origine: str):
        """
        Dépose une pièce capturée dans la zone d'élimination
        Enregistre la position pour pouvoir la récupérer plus tard
        """
        pos_elimination = self._get_position_elimination(color)

        if pos_elimination:
            await self.log("robot",
                           f"Dépôt pièce {'blanche' if color == chess.WHITE else 'noire'} en zone d'élimination...")

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

            # Enregistrer la pièce éliminée
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

        self.rtde_c.moveL(position, VITESSE, ACCELERATION)
        time.sleep(0.2)

        self.gripper.close()
        time.sleep(0.3)

        self.rtde_c.moveL(pos_approche, VITESSE, ACCELERATION)
        time.sleep(0.1)

        self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    async def execute_move(self, from_sq: str, to_sq: str, is_capture: bool, captured_piece=None):
        """Exécute un mouvement sur le robot"""
        if not self.connected:
            await self.log("warning", "Robot non connecté - Simulation")
            return True

        try:
            if is_capture and captured_piece:
                await self.log("robot", f"Capture: {from_sq.upper()} prend {to_sq.upper()}")

                piece_symbol = captured_piece.symbol()
                piece_color = captured_piece.color

                await self._prendre_piece(to_sq)
                await self._deposer_elimination(piece_symbol, piece_color, to_sq)

                await self._prendre_piece(from_sq)
                await self._poser_piece(to_sq)
            else:
                await self.log("robot", f"Déplacement: {from_sq.upper()} → {to_sq.upper()}")
                await self._prendre_piece(from_sq)
                await self._poser_piece(to_sq)

            if self.position_depart:
                self.rtde_c.moveL(self.position_depart, VITESSE, ACCELERATION)

            return True

        except Exception as e:
            await self.log("error", f"Erreur robot: {e}")
            return False

    async def reset_plateau(self):
        """
        Remet toutes les pièces à leur position initiale
        """
        if not self.connected:
            await self.log("warning", "Robot non connecté - Simulation du reset")
            self.reset_tracking()
            return {"success": True, "message": "Reset simulé (robot non connecté)"}

        try:
            await self.log("info", "=== DÉBUT RESET PLATEAU ===")

            # Replacer les pièces blanches éliminées
            await self.log("info", f"Pièces blanches à replacer: {len(self.pieces_blanches_eliminees)}")
            for piece in self.pieces_blanches_eliminees:
                await self.log("robot", f"Replacement {piece.piece_symbol} blanc → {piece.case_origine}")

                await self._prendre_piece_elimination(piece.position_elimination)
                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol, chess.PAWN)

                await self._poser_piece(piece.case_origine)

            # Replacer les pièces noires éliminées
            await self.log("info", f"Pièces noires à replacer: {len(self.pieces_noires_eliminees)}")
            for piece in self.pieces_noires_eliminees:
                await self.log("robot", f"Replacement {piece.piece_symbol} noir → {piece.case_origine}")

                await self._prendre_piece_elimination(piece.position_elimination)
                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol, chess.PAWN)

                await self._poser_piece(piece.case_origine)

            if self.position_depart:
                self.rtde_c.moveL(self.position_depart, VITESSE, ACCELERATION)

            await self.log("info", "=== FIN RESET PLATEAU ===")

            self.reset_tracking()

            return {"success": True, "message": "Plateau remis en place"}

        except Exception as e:
            await self.log("error", f"Erreur reset: {e}")
            return {"success": False, "error": str(e)}

    def reset_tracking(self):
        """Réinitialise le suivi des pièces éliminées"""
        self.pieces_blanches_eliminees = []
        self.pieces_noires_eliminees = []
        self.index_elimination_blancs = 0
        self.index_elimination_noirs = 0

    def get_pieces_eliminees(self):
        """Retourne la liste des pièces éliminées"""
        return {
            "blanches": [p.to_dict() for p in self.pieces_blanches_eliminees],
            "noires": [p.to_dict() for p in self.pieces_noires_eliminees]
        }

    def get_position(self):
        """Retourne la position actuelle du robot"""
        if not self.connected or not self.rtde_r:
            return None

        pose = self.rtde_r.getActualTCPPose()
        return {
            "x": pose[0],
            "y": pose[1],
            "z": pose[2],
            "rx": pose[3],
            "ry": pose[4],
            "rz": pose[5]
        }

    def close(self):
        """Ferme la connexion au robot"""
        if self.rtde_c:
            self.rtde_c.stopScript()
