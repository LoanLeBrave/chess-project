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
        self.calib_scale = 1.0  # Mètres par unité caméra
        self.is_calibrated = False

        # Piece actuellement manipulée (pour ajuster la hauteur Z)
        self.piece_courante = chess.PAWN

        # Zones d'élimination dynamiques (Points de départ)
        self.elim_white_start = None
        self.elim_black_start = None

        # Suivi des pièces
        self.pieces_blanches_eliminees: List[PieceEliminee] = []
        self.pieces_noires_eliminees: List[PieceEliminee] = []

        self.log_callback = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    async def log(self, log_type: str, message: str):
        if self.log_callback:
            await self.log_callback(log_type, message)

    def init_robot(self):
        """Initialise la connexion et charge la calibration"""
        try:
            # 1. Charger la calibration
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

            # 2. Calculer les zones d'élimination relatives au plateau
            self._calculate_dynamic_zones()

            # 3. Connexion Robot
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

    def _calculate_dynamic_zones(self):
        """Définit les zones d'élimination sur les côtés du plateau."""
        y_angle = self.calib_rotation + (math.pi / 2)
        board_half_width = (10.0 * self.calib_scale) + 0.05

        # Zone Blancs (Gauche)
        wb_x = self.calib_origin[0] + board_half_width * math.cos(y_angle)
        wb_y = self.calib_origin[1] + board_half_width * math.sin(y_angle)
        self.elim_white_start = [wb_x, wb_y, self.calib_origin[2]]

        # Zone Noirs (Droite)
        bn_x = self.calib_origin[0] - board_half_width * math.cos(y_angle)
        bn_y = self.calib_origin[1] - board_half_width * math.sin(y_angle)
        self.elim_black_start = [bn_x, bn_y, self.calib_origin[2]]

    def cam_to_robot(self, cam_x: float, cam_y: float, use_piece_height: bool = True) -> List[float]:
        """
        Transforme les coordonnées caméra en coordonnées Robot (mètres).
        AJOUTÉ: use_piece_height pour ajuster le Z selon le type de pièce.
        """
        # 1. Mise à l'échelle
        x_scaled = cam_x * self.calib_scale
        y_scaled = cam_y * self.calib_scale

        # 2. Rotation
        cos_t = math.cos(self.calib_rotation)
        sin_t = math.sin(self.calib_rotation)

        x_rot = x_scaled * cos_t - y_scaled * sin_t
        y_rot = x_scaled * sin_t + y_scaled * cos_t

        # 3. Translation (Origine)
        rx = self.calib_origin[0] + x_rot
        ry = self.calib_origin[1] + y_rot

        # 4. Gestion de la Hauteur Z (CORRECTION CRITIQUE)
        rz = self.calib_origin[2]  # Niveau du plateau

        if use_piece_height:
            # On ajoute la hauteur spécifique de la pièce (ex: Roi +18mm, Pion +5mm)
            z_offset = HAUTEUR_PIECES.get(self.piece_courante, 0.010)
            rz += z_offset

        # Orientation du TCP (pointe vers le bas)
        return [rx, ry, rz, 3.14, 0.0, 0.0]

    def get_square_center(self, square_name: str) -> Tuple[float, float]:
        """Retourne les coordonnées Caméra théoriques (x, y) du centre d'une case."""
        file_idx = chess.FILE_NAMES.index(square_name[0])
        rank_idx = int(square_name[1]) - 1
        unit_per_square = 2.5
        cam_x = (file_idx - 3.5) * unit_per_square
        cam_y = (rank_idx - 3.5) * unit_per_square
        return cam_x, cam_y

    async def _move_tcp(self, target_pose, speed=VITESSE, acc=ACCELERATION):
        """Déplacement linéaire sécurisé"""
        if self.connected:
            self.rtde_c.moveL(target_pose, speed, acc)
        else:
            await self.log("debug", f"Simu Move: {target_pose}")
            time.sleep(0.1)

    async def execute_move(self, from_sq: str, to_sq: str, is_capture: bool, captured_piece=None):
        """Exécute un coup complet"""
        if not self.is_calibrated:
            await self.log("error", "Robot non calibré !")
            return False

        try:
            # 1. Calculer les positions Robot

            # Départ : On prend la pièce, donc on utilise la hauteur de la pièce
            cx1, cy1 = self.get_square_center(from_sq)
            p_start = self.cam_to_robot(cx1, cy1, use_piece_height=True)

            # Arrivée : On pose la pièce, on utilise aussi la hauteur de la pièce (pour ne pas la lâcher de trop haut)
            cx2, cy2 = self.get_square_center(to_sq)
            p_end = self.cam_to_robot(cx2, cy2, use_piece_height=True)

            # 2. Gérer la Capture (D'abord retirer la pièce adverse)
            if is_capture and captured_piece:
                await self.log("robot", f"Capture en {to_sq}...")

                # Pour la capture, il faut temporairement changer la "pièce courante"
                # pour ajuster la hauteur de prise en fonction de la pièce attaquée
                piece_attaquante = self.piece_courante
                self.piece_courante = captured_piece.piece_type

                # Recalcul de la cible avec la bonne hauteur pour la pièce capturée
                p_capture = self.cam_to_robot(cx2, cy2, use_piece_height=True)

                await self._sequence_elimination(p_capture, captured_piece, to_sq)

                # On rétablit la pièce attaquante
                self.piece_courante = piece_attaquante

            # 3. Déplacer la Pièce
            await self.log("robot", f"Mouvement {from_sq} -> {to_sq}")
            await self._sequence_pick_and_place(p_start, p_end)

            # Retour position home ou sécurité
            p_safe = list(p_end)
            p_safe[2] = self.calib_origin[2] + DELTA_TRANSIT  # Retour hauteur transit absolue
            await self._move_tcp(p_safe)

            return True

        except Exception as e:
            await self.log("error", f"Erreur mouvement: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _sequence_pick_and_place(self, p_pick, p_place):
        """Séquence générique Prendre et Poser"""
        # Approche (Hauteur absolue relative au plateau)
        z_transit_absolu = self.calib_origin[2] + DELTA_TRANSIT

        p_high_pick = list(p_pick)
        p_high_pick[2] = z_transit_absolu

        p_app_pick = list(p_pick)
        p_app_pick[2] += DELTA_APPROCHE

        # PICK
        self.gripper.move(GRIPPER_OUVERTURE)  # On s'assure d'être ouvert
        await self._move_tcp(p_high_pick)  # Transit
        await self._move_tcp(p_app_pick)  # Approche
        await self._move_tcp(p_pick, VITESSE / 2)  # Descente finale (Z précis)
        self.gripper.close()
        time.sleep(0.5)
        await self._move_tcp(p_app_pick)  # Remontée
        await self._move_tcp(p_high_pick)  # Haut

        # PLACE
        p_high_place = list(p_place)
        p_high_place[2] = z_transit_absolu

        p_app_place = list(p_place)
        p_app_place[2] += DELTA_APPROCHE

        p_deposit = list(p_place)
        # On ajoute un petit delta pour lâcher sans cogner (défini dans config)
        p_deposit[2] += DELTA_RELACHE_BASE

        await self._move_tcp(p_high_place)
        await self._move_tcp(p_app_place)
        await self._move_tcp(p_deposit, VITESSE / 2)
        self.gripper.move(GRIPPER_OUVERTURE)
        time.sleep(0.3)
        await self._move_tcp(p_app_place)

    async def _sequence_elimination(self, p_capture, piece_obj, square_name):
        """Prend une pièce et la met dans la zone d'élimination"""
        is_white = (piece_obj.color == chess.WHITE)
        start_zone = self.elim_white_start if is_white else self.elim_black_start
        index = len(self.pieces_blanches_eliminees) if is_white else len(self.pieces_noires_eliminees)

        x_angle = self.calib_rotation
        offset_dist = index * ESPACEMENT_ELIMINATION

        p_drop = list(start_zone)
        p_drop[0] += offset_dist * math.cos(x_angle)
        p_drop[1] += offset_dist * math.sin(x_angle)
        # On dépose les pièces éliminées directement sur le plateau (Z origine + offset type pièce)
        z_offset = HAUTEUR_PIECES.get(piece_obj.piece_type, 0.010)
        p_drop[2] += z_offset

        await self._sequence_pick_and_place(p_capture, p_drop)

        elim = PieceEliminee(piece_obj.symbol(), piece_obj.color, square_name, p_drop, index)
        if is_white:
            self.pieces_blanches_eliminees.append(elim)
        else:
            self.pieces_noires_eliminees.append(elim)

    async def reset_plateau(self):
        """Remet les pièces éliminées à leur place"""
        if not self.connected: return {"success": True}

        # Pour le reset, on doit penser à ajuster la hauteur Z
        # pour la pièce qu'on est en train de ramener

        # 1. Remettre les Blanches
        for piece in reversed(self.pieces_blanches_eliminees):
            # On définit le type de pièce pour que cam_to_robot calcule le bon Z
            self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)

            cx, cy = self.get_square_center(piece.case_origine)
            p_origin = self.cam_to_robot(cx, cy, use_piece_height=True)

            # La position d'élimination a déjà le bon Z (enregistré lors de l'élimination)
            await self._sequence_pick_and_place(piece.position_elimination, p_origin)

        # 2. Remettre les Noires
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