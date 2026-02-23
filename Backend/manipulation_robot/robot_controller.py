#!/usr/bin/env python3
"""
Contrôle du robot UR5e - Version Dynamique Complète
Utilise la calibration 2 points pour calculer toutes les positions.
Compatible avec chess_manager_updated.py et api_updated.py
"""

import time
import math
import json
import os
import asyncio
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

        # Position de départ (home)
        self.position_depart = None

        # Zones d'élimination
        self.elim_white_start = None
        self.elim_black_start = None

        self.pieces_blanches_eliminees: List[PieceEliminee] = []
        self.pieces_noires_eliminees: List[PieceEliminee] = []

        # Callback pour logs
        self.log_callback = None

        # Flag de pause
        self.is_paused = False

    def pause_urgence(self):
        """Met le robot en pause immédiate (arrêt d'urgence)"""
        if self.connected and self.rtde_c:
            try:
                self.rtde_c.stopScript()  # Arrêt immédiat sécurisé
                self.is_paused = True
                print("⚠️ Robot arrêté en urgence")
            except Exception as e:
                print(f"❌ Erreur pause urgence: {e}")

    def reprendre_script(self):
        """Tente de relancer le programme après une pause"""
        if self.connected and self.rtde_c:
            try:
                self.rtde_c.reuploadScript()  # Relance la connexion
                self.is_paused = False
                print("✅ Robot repris")
            except Exception as e:
                print(f"❌ Erreur reprise: {e}")

    def set_log_callback(self, callback):
        """Définit le callback pour les logs"""
        self.log_callback = callback

    async def log(self, log_type: str, message: str):
        """Envoie un log via le callback"""
        if self.log_callback:
            await self.log_callback(log_type, message)

    def reset_tracking(self):
        """Réinitialise le suivi des pièces éliminées"""
        self.pieces_blanches_eliminees.clear()
        self.pieces_noires_eliminees.clear()
        self.is_paused = False

    def init_robot(self):
        """Initialise la connexion et charge la calibration"""
        try:
            # Charger la calibration
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

            # Charger la position de départ (home)
            if os.path.exists(FICHIER_POSITION_DEPART):
                with open(FICHIER_POSITION_DEPART, 'r') as f:
                    data = json.load(f)
                    self.position_depart = data.get("position_depart")
                    print("✓ Position de départ chargée")

            # Calculer les zones d'élimination
            self._calculate_dynamic_zones()

            # Connexion au robot
            print(f"Connexion robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)
            
            # Initialisation du gripper
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
            try:
                pose = self.rtde_r.getActualTCPPose()
                return {
                    "x": pose[0],
                    "y": pose[1],
                    "z": pose[2],
                    "rx": pose[3],
                    "ry": pose[4],
                    "rz": pose[5]
                }
            except Exception as e:
                print(f"Erreur lecture position: {e}")
                return None
        return None

    def _calculate_dynamic_zones(self):
        """Définit les zones d'élimination de chaque côté du plateau"""
        y_angle = self.calib_rotation + (math.pi / 2)
        board_half_width = (10.0 * self.calib_scale) + 0.05

        # Zone blanche (côté + Y)
        wb_x = self.calib_origin[0] + board_half_width * math.cos(y_angle)
        wb_y = self.calib_origin[1] + board_half_width * math.sin(y_angle)
        self.elim_white_start = [wb_x, wb_y, self.calib_origin[2]]

        # Zone noire (côté - Y)
        bn_x = self.calib_origin[0] - board_half_width * math.cos(y_angle)
        bn_y = self.calib_origin[1] - board_half_width * math.sin(y_angle)
        self.elim_black_start = [bn_x, bn_y, self.calib_origin[2]]

    def cam_to_robot(self, cam_x: float, cam_y: float, use_piece_height: bool = True) -> List[float]:
        """
        Transforme coordonnées Caméra -> Robot.
        use_piece_height: Ajoute la hauteur de la pièce au Z du plateau.
        """
        # Mise à l'échelle
        x_scaled = cam_x * self.calib_scale
        y_scaled = cam_y * self.calib_scale

        # Rotation
        cos_t = math.cos(self.calib_rotation)
        sin_t = math.sin(self.calib_rotation)

        x_rot = x_scaled * cos_t - y_scaled * sin_t
        y_rot = x_scaled * sin_t + y_scaled * cos_t

        # Translation
        rx = self.calib_origin[0] + x_rot
        ry = self.calib_origin[1] + y_rot

        # GESTION HAUTEUR Z
        rz = self.calib_origin[2]

        if use_piece_height:
            z_offset = HAUTEUR_PIECES.get(self.piece_courante, 0.010)
            rz += z_offset

        # Orientation fixe
        return [rx, ry, rz, 3.14, 0.0, 0.0]

    def get_square_center(self, square_name: str) -> Tuple[float, float]:
        """Calcule le centre d'une case en coordonnées caméra"""
        file_idx = chess.FILE_NAMES.index(square_name[0])
        rank_idx = int(square_name[1]) - 1
        unit_per_square = 2.5
        cam_x = (file_idx - 3.5) * unit_per_square
        cam_y = (rank_idx - 3.5) * unit_per_square
        return cam_x, cam_y

    async def _wait_with_pause_check(self, duration):
        """Attend avec vérifications fréquentes de la pause (toutes les 10ms)"""
        start = time.time()
        while time.time() - start < duration:
            if self.is_paused:
                return False
            await asyncio.sleep(0.01)  # Vérifier toutes les 10ms
        return True

    async def _move_tcp(self, target_pose, speed=VITESSE, acc=ACCELERATION):
        """Déplace le TCP avec gestion de la pause"""
        if self.is_paused:
            return False
            
        if self.connected:
            self.rtde_c.moveL(target_pose, speed, acc)
            return True
        else:
            await self.log("debug", f"Simu Move: {target_pose}")
            await asyncio.sleep(0.1)
            return True

    async def execute_move(self, from_sq: str, to_sq: str, is_capture: bool, captured_piece=None, precise_pick_coords=None):
        """
        Exécute un mouvement complet sur le robot
        Retourne True si succès, False si interrompu par pause

        precise_pick_coords: tuple (x, y) en coordonnees camera precises pour le pick.
                             Si None, utilise le centre geometrique de la case.
        """
        if not self.is_calibrated:
            await self.log("error", "Robot non calibré !")
            return False

        try:
            # Position de depart : coords precises camera si dispo, sinon centre geometrique
            if precise_pick_coords:
                cx1, cy1 = precise_pick_coords
            else:
                cx1, cy1 = self.get_square_center(from_sq)
            p_start = self.cam_to_robot(cx1, cy1, use_piece_height=True)

            cx2, cy2 = self.get_square_center(to_sq)
            p_end = self.cam_to_robot(cx2, cy2, use_piece_height=True)

            # Gestion de la capture
            if is_capture and captured_piece:
                await self.log("robot", f"Capture en {to_sq}...")

                # Sauvegarde type pièce courante
                attaquant = self.piece_courante
                
                # On utilise la hauteur de la pièce capturée
                self.piece_courante = captured_piece.piece_type

                p_capture = self.cam_to_robot(cx2, cy2, use_piece_height=True)
                success = await self._sequence_elimination(p_capture, captured_piece, to_sq)
                
                if not success:
                    return False  # Interrompu par pause

                # Restaure pièce courante
                self.piece_courante = attaquant

            # Déplacement de la pièce
            await self.log("robot", f"Mouvement {from_sq} → {to_sq}")
            success = await self._sequence_pick_and_place(p_start, p_end)
            
            if not success:
                return False  # Interrompu par pause

            # Retour en position de sécurité
            p_safe = list(p_end)
            p_safe[2] = self.calib_origin[2] + DELTA_TRANSIT
            success = await self._move_tcp(p_safe)
            
            if not success:
                return False

            # Retour position home si définie
            if self.position_depart and not self.is_paused:
                await self._move_tcp(self.position_depart)

            return True

        except Exception as e:
            await self.log("error", f"Erreur mouvement: {e}")
            return False

    async def _prendre_piece(self, case: str):
        """
        Prend une pièce sur une case (utilisé par chess_manager pour reset).
        Z monte en premier pour éviter les collisions diagonales.
        Retourne True si succès, False si interrompu.
        """
        try:
            cx, cy = self.get_square_center(case)
            p_pick = self.cam_to_robot(cx, cy, use_piece_height=True)

            z_transit = self.calib_origin[2] + DELTA_TRANSIT

            p_high = list(p_pick)
            p_high[2] = z_transit

            # Ouvrir le gripper
            if self.connected:
                self.gripper.move(GRIPPER_OUVERTURE)
            if not await self._wait_with_pause_check(0.2):
                return False

            # 1. Monter Z en premier (mouvement vertical pur)
            if not await self._raise_to_transit():
                return False
            if not await self._wait_with_pause_check(0.1):
                return False

            # 2. Déplacement horizontal vers au-dessus de la case
            if not await self._move_tcp(p_high):
                return False
            if not await self._wait_with_pause_check(0.1):
                return False

            # 3. Descente verticale vers la pièce
            if not await self._move_tcp(p_pick, VITESSE / 2):
                return False
            if not await self._wait_with_pause_check(0.1):
                return False

            # Fermer le gripper
            if self.connected:
                self.gripper.close()
            if not await self._wait_with_pause_check(0.5):
                return False

            # 4. Remontée verticale pure
            if not await self._move_tcp(p_high):
                return False

            return True

        except Exception as e:
            await self.log("error", f"Erreur prise pièce: {e}")
            return False

    async def _poser_piece(self, case: str):
        """
        Pose une pièce sur une case (utilisé par chess_manager pour reset).
        Z monte en premier pour éviter les collisions diagonales.
        Retourne True si succès, False si interrompu.
        """
        try:
            cx, cy = self.get_square_center(case)
            p_place = self.cam_to_robot(cx, cy, use_piece_height=True)

            z_transit = self.calib_origin[2] + DELTA_TRANSIT

            p_high = list(p_place)
            p_high[2] = z_transit

            p_deposit = list(p_place)
            p_deposit[2] += DELTA_RELACHE_BASE

            # 1. Monter Z en premier (mouvement vertical pur)
            if not await self._raise_to_transit():
                return False
            if not await self._wait_with_pause_check(0.1):
                return False

            # 2. Déplacement horizontal vers au-dessus de la case
            if not await self._move_tcp(p_high):
                return False
            if not await self._wait_with_pause_check(0.1):
                return False

            # 3. Descente verticale vers le dépôt
            if not await self._move_tcp(p_deposit, VITESSE / 2):
                return False
            if not await self._wait_with_pause_check(0.1):
                return False

            # Ouvrir le gripper
            if self.connected:
                self.gripper.move(GRIPPER_OUVERTURE)
            if not await self._wait_with_pause_check(0.3):
                return False

            # 4. Remontée verticale pure
            if not await self._move_tcp(p_high):
                return False

            return True

        except Exception as e:
            await self.log("error", f"Erreur dépose pièce: {e}")
            return False

    async def _raise_to_transit(self):
        """
        Monte verticalement jusqu'à la hauteur de transit en gardant X/Y courants.
        Evite les mouvements diagonaux qui risquent de renverser des pièces.
        Retourne True si succès, False si interrompu ou position indisponible.
        """
        z_transit = self.calib_origin[2] + DELTA_TRANSIT
        current = self.get_position()
        if current is None:
            return True  # Mode simulation, on continue
        if current["z"] >= z_transit - 0.005:
            return True  # Déjà suffisamment haut, rien à faire
        p_raise = [current["x"], current["y"], z_transit, 3.14, 0.0, 0.0]
        return await self._move_tcp(p_raise)

    async def _sequence_pick_and_place(self, p_pick, p_place):
        """
        Séquence complète prendre et poser.
        Les mouvements Z et XY sont toujours séparés pour éviter les collisions.
        Retourne True si succès, False si interrompu.
        """
        z_transit = self.calib_origin[2] + DELTA_TRANSIT

        # Positions hautes (transit) au-dessus de chaque case
        p_high_pick = list(p_pick)
        p_high_pick[2] = z_transit

        p_high_place = list(p_place)
        p_high_place[2] = z_transit

        p_deposit = list(p_place)
        p_deposit[2] += DELTA_RELACHE_BASE

        # ===== PICK =====
        if self.connected:
            self.gripper.move(GRIPPER_OUVERTURE)
        if not await self._wait_with_pause_check(0.2):
            return False

        # 1. Monter Z en premier (mouvement vertical pur, évite collision)
        if not await self._raise_to_transit():
            return False
        if not await self._wait_with_pause_check(0.1):
            return False

        # 2. Déplacement horizontal vers au-dessus du pick
        if not await self._move_tcp(p_high_pick):
            return False
        if not await self._wait_with_pause_check(0.1):
            return False

        # 3. Descente verticale vers la pièce
        if not await self._move_tcp(p_pick, VITESSE / 2):
            return False
        if not await self._wait_with_pause_check(0.1):
            return False

        # Fermeture gripper
        if self.connected:
            self.gripper.close()
        if not await self._wait_with_pause_check(0.5):
            return False

        # 4. Remontée verticale pure jusqu'au transit
        if not await self._move_tcp(p_high_pick):
            return False
        if not await self._wait_with_pause_check(0.1):
            return False

        # ===== PLACE =====
        # 5. Déplacement horizontal vers au-dessus de la destination
        if not await self._move_tcp(p_high_place):
            return False
        if not await self._wait_with_pause_check(0.1):
            return False

        # 6. Descente verticale vers le dépôt
        if not await self._move_tcp(p_deposit, VITESSE / 2):
            return False
        if not await self._wait_with_pause_check(0.1):
            return False

        # Ouverture gripper
        if self.connected:
            self.gripper.move(GRIPPER_OUVERTURE)
        if not await self._wait_with_pause_check(0.3):
            return False

        # 7. Remontée verticale pure
        if not await self._move_tcp(p_high_place):
            return False

        return True

    async def _sequence_elimination(self, p_capture, piece_obj, square_name):
        """
        Séquence d'élimination d'une pièce capturée
        Retourne True si succès, False si interrompu
        """
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

        # Exécuter le pick and place
        success = await self._sequence_pick_and_place(p_capture, p_drop)
        
        if not success:
            return False  # Interrompu par pause

        # Enregistrer la pièce éliminée
        elim = PieceEliminee(piece_obj.symbol(), piece_obj.color, square_name, p_drop, index)
        if is_white:
            self.pieces_blanches_eliminees.append(elim)
        else:
            self.pieces_noires_eliminees.append(elim)

        return True

    async def reset_plateau(self):
        """
        Remet toutes les pièces éliminées à leur position d'origine
        Retourne dict avec success: True/False
        """
        if not self.connected:
            return {"success": True, "message": "Mode simulation"}

        try:
            await self.log("info", "Début du reset des pièces éliminées...")

            # Reset Blancs (en ordre inverse)
            for piece in reversed(self.pieces_blanches_eliminees):
                if self.is_paused:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)
                cx, cy = self.get_square_center(piece.case_origine)
                p_origin = self.cam_to_robot(cx, cy, use_piece_height=True)
                
                await self.log("robot", f"Replacement {piece.piece_symbol} → {piece.case_origine}")
                success = await self._sequence_pick_and_place(piece.position_elimination, p_origin)
                
                if not success:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

            # Reset Noirs (en ordre inverse)
            for piece in reversed(self.pieces_noires_eliminees):
                if self.is_paused:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)
                cx, cy = self.get_square_center(piece.case_origine)
                p_origin = self.cam_to_robot(cx, cy, use_piece_height=True)
                
                await self.log("robot", f"Replacement {piece.piece_symbol} → {piece.case_origine}")
                success = await self._sequence_pick_and_place(piece.position_elimination, p_origin)
                
                if not success:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

            # Clear les listes
            self.pieces_blanches_eliminees.clear()
            self.pieces_noires_eliminees.clear()

            await self.log("info", "✓ Reset des pièces terminé")
            return {"success": True, "message": "Toutes les pièces replacées"}

        except Exception as e:
            await self.log("error", f"Erreur lors du reset: {e}")
            return {"success": False, "message": str(e)}

    def get_pieces_eliminees(self):
        """Retourne la liste des pièces éliminées"""
        return {
            "blanches": [p.to_dict() for p in self.pieces_blanches_eliminees],
            "noires": [p.to_dict() for p in self.pieces_noires_eliminees]
        }

    def close(self):
        """Ferme la connexion au robot"""
        if self.rtde_c:
            try:
                self.rtde_c.stopScript()
                print("✓ Robot arrêté proprement")
            except:
                pass
