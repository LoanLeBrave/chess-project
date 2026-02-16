#!/usr/bin/env python3
"""
Contrôle du robot UR5e - Version Dynamique
Utilise la calibration 2 points pour calculer toutes les positions.
"""

import time
import math
import json
import os
from typing import List, Optional, Tuple
import chess

from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper

from config import (
    ROBOT_IP, VITESSE, ACCELERATION,
    GRIPPER_OUVERTURE,
    DELTA_APPROCHE, DELTA_TRANSIT, DELTA_RELACHE_BASE,
    ESPACEMENT_ELIMINATION,
    FICHIER_CALIBRATION, FICHIER_POSITION_DEPART,
    PIECE_TYPE_MAP, HAUTEUR_PIECES
)
from models import PieceEliminee


class RobotController:
    """Contrôleur dynamique pour le robot UR5e"""

    def __init__(self):
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.connected = False

        # Données de calibration
        self.calib_origin = [0, 0, 0]
        self.calib_rotation = 0.0
        self.calib_scale = 1.0
        self.is_calibrated = False

        # Pièce courante pour ajuster la hauteur (Z)
        self.piece_courante = chess.PAWN

        # Zones d'élimination
        self.elim_white_start = None
        self.elim_black_start = None

        self.pieces_blanches_eliminees: List[PieceEliminee] = []
        self.pieces_noires_eliminees: List[PieceEliminee] = []

        self.log_callback = None

    def pause_urgence(self):
        """Met le robot en pause immédiate"""
        if self.connected and self.rtde_c:
            self.rtde_c.stopScript()  # Arrêt immédiat sécurisé

    def reprendre_script(self):
        """Tente de relancer le programme"""
        if self.connected and self.rtde_c:
            self.rtde_c.reuploadScript()  # Relance la connexion

    def set_log_callback(self, callback):
        self.log_callback = callback

    async def log(self, log_type: str, message: str):
        if self.log_callback:
            await self.log_callback(log_type, message)

    def init_robot(self):
        """Initialise la connexion et charge la calibration"""
        try:
            if not os.path.exists(FICHIER_CALIBRATION):
                print(f"⚠ Fichier calibration introuvable: {FICHIER_CALIBRATION}")
                return False

            with open(FICHIER_CALIBRATION, 'r') as f:
                data = json.load(f)
                self.calib_origin = data["origin"]
                self.calib_rotation = data["rotation"]
                if "camera_scale" in data:
                    self.calib_scale = data["camera_scale"]
                else:
                    self.calib_scale = data["board_size"] / 20.0

                self.is_calibrated = True
                print(f"✓ Calibration chargée (Scale: {self.calib_scale:.4f})")

            self._calculate_dynamic_zones()

            print(f"Connexion robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)
            self.gripper = RobotiqGripper(self.rtde_c)
            self.gripper.activate()
            self.gripper.set_force(50)
            self.gripper.set_speed(150)
            self.gripper.move(GRIPPER_OUVERTURE)

            self.connected = True
            print("✓ Robot connecté et prêt!")
            return True

        except Exception as e:
            print(f"⚠ Erreur initialisation: {e}")
            self.connected = False
            return False

    def get_position(self):
        """Retourne la position actuelle du TCP via l'interface de réception"""
        if self.connected and self.rtde_r:
            pose = self.rtde_r.getActualTCPPose()
            return {"x": pose[0], "y": pose[1], "z": pose[2], "rx": pose[3], "ry": pose[4], "rz": pose[5]}
        return None


    def _calculate_dynamic_zones(self):
        """Définit les zones d'élimination"""
        y_angle = self.calib_rotation + (math.pi / 2)
        board_half_width = (10.0 * self.calib_scale) + 0.05

        wb_x = self.calib_origin[0] + board_half_width * math.cos(y_angle)
        wb_y = self.calib_origin[1] + board_half_width * math.sin(y_angle)
        self.elim_white_start = [wb_x, wb_y, self.calib_origin[2]]

        bn_x = self.calib_origin[0] - board_half_width * math.cos(y_angle)
        bn_y = self.calib_origin[1] - board_half_width * math.sin(y_angle)
        self.elim_black_start = [bn_x, bn_y, self.calib_origin[2]]

    def cam_to_robot(self, cam_x: float, cam_y: float, use_piece_height: bool = True) -> List[float]:
        """
        Transforme Caméra -> Robot.
        use_piece_height: Ajoute la hauteur de la pièce au Z du plateau.
        """
        x_scaled = cam_x * self.calib_scale
        y_scaled = cam_y * self.calib_scale

        cos_t = math.cos(self.calib_rotation)
        sin_t = math.sin(self.calib_rotation)

        x_rot = x_scaled * cos_t - y_scaled * sin_t
        y_rot = x_scaled * sin_t + y_scaled * cos_t

        rx = self.calib_origin[0] + x_rot
        ry = self.calib_origin[1] + y_rot

        # GESTION HAUTEUR Z
        rz = self.calib_origin[2]

        if use_piece_height:
            z_offset = HAUTEUR_PIECES.get(self.piece_courante, 0.010)
            rz += z_offset

        return [rx, ry, rz, 3.14, 0.0, 0.0]

    def get_square_center(self, square_name: str) -> Tuple[float, float]:
        file_idx = chess.FILE_NAMES.index(square_name[0])
        rank_idx = int(square_name[1]) - 1
        unit_per_square = 2.5
        cam_x = (file_idx - 3.5) * unit_per_square
        cam_y = (rank_idx - 3.5) * unit_per_square
        return cam_x, cam_y

    async def _move_tcp(self, target_pose, speed=VITESSE, acc=ACCELERATION):
        if self.connected:
            self.rtde_c.moveL(target_pose, speed, acc)
        else:
            await self.log("debug", f"Simu Move: {target_pose}")
            time.sleep(0.1)

    async def execute_move(self, from_sq: str, to_sq: str, is_capture: bool, captured_piece=None):
        if not self.is_calibrated:
            await self.log("error", "Robot non calibré !")
            return False

        try:
            cx1, cy1 = self.get_square_center(from_sq)
            p_start = self.cam_to_robot(cx1, cy1, use_piece_height=True)

            cx2, cy2 = self.get_square_center(to_sq)
            p_end = self.cam_to_robot(cx2, cy2, use_piece_height=True)

            if is_capture and captured_piece:
                await self.log("robot", f"Capture en {to_sq}...")

                # Sauvegarde type pièce courante
                attaquant = self.piece_courante
                # On utilise la hauteur de la pièce capturée
                self.piece_courante = captured_piece.piece_type

                p_capture = self.cam_to_robot(cx2, cy2, use_piece_height=True)
                await self._sequence_elimination(p_capture, captured_piece, to_sq)

                # Restaure pièce courante
                self.piece_courante = attaquant

            await self.log("robot", f"Mouvement {from_sq} -> {to_sq}")
            await self._sequence_pick_and_place(p_start, p_end)

            p_safe = list(p_end)
            p_safe[2] = self.calib_origin[2] + DELTA_TRANSIT
            await self._move_tcp(p_safe)

            return True

        except Exception as e:
            await self.log("error", f"Erreur mouvement: {e}")
            return False

    async def _sequence_pick_and_place(self, p_pick, p_place):
        # Hauteur de transit absolue
        z_transit = self.calib_origin[2] + DELTA_TRANSIT

        p_high_pick = list(p_pick)
        p_high_pick[2] = z_transit
        p_app_pick = list(p_pick)
        p_app_pick[2] += DELTA_APPROCHE

        # PICK
        self.gripper.move(GRIPPER_OUVERTURE)
        await self._move_tcp(p_high_pick)
        await self._move_tcp(p_app_pick)
        await self._move_tcp(p_pick, VITESSE / 2)
        self.gripper.close()
        time.sleep(0.5)
        await self._move_tcp(p_app_pick)
        await self._move_tcp(p_high_pick)

        # PLACE
        p_high_place = list(p_place)
        p_high_place[2] = z_transit
        p_app_place = list(p_place)
        p_app_place[2] += DELTA_APPROCHE

        p_deposit = list(p_place)
        p_deposit[2] += DELTA_RELACHE_BASE

        await self._move_tcp(p_high_place)
        await self._move_tcp(p_app_place)
        await self._move_tcp(p_deposit, VITESSE / 2)
        self.gripper.move(GRIPPER_OUVERTURE)
        time.sleep(0.3)
        await self._move_tcp(p_app_place)

    async def _sequence_elimination(self, p_capture, piece_obj, square_name):
        is_white = (piece_obj.color == chess.WHITE)
        start_zone = self.elim_white_start if is_white else self.elim_black_start
        index = len(self.pieces_blanches_eliminees) if is_white else len(self.pieces_noires_eliminees)

        x_angle = self.calib_rotation
        offset_dist = index * ESPACEMENT_ELIMINATION

        p_drop = list(start_zone)
        p_drop[0] += offset_dist * math.cos(x_angle)
        p_drop[1] += offset_dist * math.sin(x_angle)
        # Hauteur pièce pour dépôt
        p_drop[2] += HAUTEUR_PIECES.get(piece_obj.piece_type, 0.010)

        await self._sequence_pick_and_place(p_capture, p_drop)

        elim = PieceEliminee(piece_obj.symbol(), piece_obj.color, square_name, p_drop, index)
        if is_white:
            self.pieces_blanches_eliminees.append(elim)
        else:
            self.pieces_noires_eliminees.append(elim)

    async def reset_plateau(self):
        if not self.connected: return {"success": True}

        # Reset Blancs
        for piece in reversed(self.pieces_blanches_eliminees):
            self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)
            cx, cy = self.get_square_center(piece.case_origine)
            p_origin = self.cam_to_robot(cx, cy, use_piece_height=True)
            await self._sequence_pick_and_place(piece.position_elimination, p_origin)

        # Reset Noirs
        for piece in reversed(self.pieces_noires_eliminees):
            self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)
            cx, cy = self.get_square_center(piece.case_origine)
            p_origin = self.cam_to_robot(cx, cy, use_piece_height=True)
            await self._sequence_pick_and_place(piece.position_elimination, p_origin)

        self.pieces_blanches_eliminees.clear()
        self.pieces_noires_eliminees.clear()
        return {"success": True}

    def get_pieces_eliminees(self):
        return {
            "blanches": [p.to_dict() for p in self.pieces_blanches_eliminees],
            "noires": [p.to_dict() for p in self.pieces_noires_eliminees]
        }

    def close(self):
        if self.rtde_c:
            self.rtde_c.stopScript()