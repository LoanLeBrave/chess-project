#!/usr/bin/env python3
"""
Pont vers le robot UR5e.

Encapsule l'initialisation et l'execution de mouvements
a partir des donnees de game_state.json.
"""

import sys
import os
import asyncio
from typing import Optional

from .config import MANIP_DIR, VISION_TYPE_TO_CHESS

# Ajouter manipulation_robot au path et fixer le cwd
# pour que les chemins relatifs de config.py fonctionnent.
sys.path.insert(0, os.path.dirname(MANIP_DIR))
sys.path.insert(0, MANIP_DIR)
os.chdir(MANIP_DIR)

from manipulation_robot.robot_controller import RobotController
from manipulation_robot.config import FICHIER_CALIBRATION, DELTA_TRANSIT


class RobotBridge:
    """Interface simplifiee pour piloter le robot depuis les donnees vision."""

    def __init__(self):
        self._ctrl: Optional[RobotController] = None

    # ------------------------------------------------------------------
    #  Cycle de vie
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Initialise et connecte le robot.

        Returns:
            True si la connexion et la calibration sont OK.
        """
        calib_path = os.path.join(MANIP_DIR, FICHIER_CALIBRATION)
        if not os.path.exists(calib_path):
            print(f"  [!] Fichier de calibration introuvable : {calib_path}")
            print("      Lancez d'abord : cd manipulation_robot && python calibration.py")
            return False

        self._ctrl = RobotController()
        if not self._ctrl.init_robot():
            print("  [!] Connexion au robot impossible.")
            print("      Verifiez que le robot est allume (192.168.0.11).")
            return False

        return True

    def close(self) -> None:
        """Ferme proprement la connexion au robot."""
        if self._ctrl:
            self._ctrl.close()
            self._ctrl = None

    # ------------------------------------------------------------------
    #  Mouvement
    # ------------------------------------------------------------------

    async def move_piece(self, piece_data: dict, to_square: str) -> None:
        """
        Deplace une piece du plateau en utilisant les coordonnees
        precises fournies par la vision.

        Args:
            piece_data: dict d'une piece issue de game_state.json.
            to_square:  case destination (notation algebrique, ex: "e4").
        """
        ctrl = self._ctrl
        if ctrl is None:
            raise RuntimeError("Robot non connecte. Appelez connect() d'abord.")

        # Coordonnees precises de la piece (detectees par la camera)
        precise_x = piece_data["position"]["board"]["x"]
        precise_y = piece_data["position"]["board"]["y"]

        # Ajuster la hauteur selon le type de piece
        piece_type = VISION_TYPE_TO_CHESS.get(piece_data.get("type"), None)
        if piece_type is not None:
            ctrl.piece_courante = piece_type

        # Position pick : coordonnees camera precises
        p_pick = ctrl.cam_to_robot(precise_x, precise_y, use_piece_height=True)

        # Position place : centre geometrique de la case cible
        cx, cy = ctrl.get_square_center(to_square)
        p_place = ctrl.cam_to_robot(cx, cy, use_piece_height=True)

        from_square = piece_data.get("position", {}).get("chess", "??")
        code = piece_data.get("code", "??")

        print(f"  Pick  {code} @ {from_square}  ->  coords ({precise_x:.2f}, {precise_y:.2f})")
        print(f"  Place -> {to_square} (centre case)")
        print(f"  Type  : {piece_data.get('type', '?')}")
        print("  Execution...")

        await ctrl._sequence_pick_and_place(p_pick, p_place)

        # Retour en position de securite
        p_safe = list(p_place)
        p_safe[2] = ctrl.calib_origin[2] + DELTA_TRANSIT
        await ctrl._move_tcp(p_safe)

        print("  Mouvement termine.")
