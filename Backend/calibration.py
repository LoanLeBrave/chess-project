#!/usr/bin/env python3
"""
Module de calibration dynamique à 2 points pour robot d'échecs.
Détermine automatiquement : position, rotation et taille du plateau.
"""

import json
import time
import sys
import os
import math
import termios
import tty
import select
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper

from config import (
    ROBOT_IP,
    ACCELERATION,
    FICHIER_CALIBRATION,
    OFFSET_TROU_M
)


class TwoPointCalibration:
    def __init__(self):
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.connected = False

    def init_robot(self):
        """Connexion au robot"""
        try:
            print(f"🤖 Connexion au robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)
            self.gripper = RobotiqGripper(self.rtde_c)
            self.gripper.activate()
            self.gripper.set_force(40)
            self.gripper.set_speed(150)
            # On ferme le gripper pour qu'il rentre bien dans le trou (pointe fine)
            self.gripper.close()
            self.connected = True
            print("✅ Robot connecté.")
            return True
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return False

    def enable_freedrive(self):
        """Active le mode Freedrive"""
        self.rtde_c.freedriveMode()

    def disable_freedrive(self):
        """Désactive Freedrive et recharge le script (Correctif vital)"""
        self.rtde_c.endFreedriveMode()
        time.sleep(0.1)
        self.rtde_c.reuploadScript()
        time.sleep(0.1)

    def get_key_non_blocking(self):
        """Lecture clavier non bloquante"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                    ch3 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                    if ch2 == '[':
                        if ch3 == 'A': return 'w'  # Haut
                        if ch3 == 'B': return 's'  # Bas
                    return '\x1b'
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def interactive_positioning(self, step_name):
        """
        Permet à l'utilisateur de positionner le robot dans le trou.
        Combine Freedrive et ajustement fin au clavier.
        """
        print("\n" + "=" * 60)
        print(f"🎯 ÉTAPE : {step_name}")
        print("=" * 60)
        print("COMMANDES :")
        print("  [F]      : Activer/Désactiver FREEDRIVE (Bouger à la main)")
        print("  [S] / [↓]: Descendre (Z-)")
        print("  [W] / [↑]: Monter (Z+)")
        print("  [Q]      : VALIDER la position et passer à la suite")
        print("  [ESC]    : Annuler")
        print("-" * 60)

        freedrive_active = False
        velocity_z = 0.05  # Vitesse jogging Z
        current_vel = [0, 0, 0, 0, 0, 0]

        while True:
            # Affichage status
            pose = self.rtde_r.getActualTCPPose()
            state_str = "LIBRE (Main)" if freedrive_active else "BLOQUÉ (Clavier)"
            print(f"\r📍 Z={pose[2]:.4f} | Mode: {state_str} | [Q] pour valider   ", end="", flush=True)

            key = self.get_key_non_blocking()
            target_vel = [0, 0, 0, 0, 0, 0]

            if key:
                if key == '\x1b':  # ESC
                    self.rtde_c.speedStop()
                    if freedrive_active: self.disable_freedrive()
                    print("\n❌ Annulation.")
                    sys.exit(0)

                elif key.lower() == 'q':  # Valider
                    self.rtde_c.speedStop()
                    if freedrive_active: self.disable_freedrive()
                    print(f"\n✅ Position {step_name} enregistrée.")
                    return pose

                elif key.lower() == 'f':  # Toggle Freedrive
                    self.rtde_c.speedStop()
                    if freedrive_active:
                        self.disable_freedrive()
                        freedrive_active = False
                    else:
                        self.enable_freedrive()
                        freedrive_active = True
                    time.sleep(0.3)

                elif not freedrive_active:
                    if key.lower() == 's':
                        target_vel[2] = -velocity_z
                    elif key.lower() == 'w':
                        target_vel[2] = velocity_z

            # Application vélocité (si pas en freedrive)
            if not freedrive_active:
                if any(v != 0 for v in target_vel):
                    self.rtde_c.speedL(target_vel, ACCELERATION, 0.1)
                elif any(v != 0 for v in current_vel):
                    self.rtde_c.speedStop()
                current_vel = target_vel

    def calculate_geometry(self, p1, p2):
        """
        Calcule la géométrie du plateau.
        P1 = Haut-Gauche (A8)
        P2 = Bas-Droite (H1)
        """
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]

        # 1. Centre du plateau
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        center_z = (p1[2] + p2[2]) / 2  # Moyenne des Z

        # 2. Distance et Taille
        dist_trous = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Formule : DiagonaleCarré = Côté * sqrt(2)
        # Le carré formé par les trous a pour diagonale dist_trous.
        # Son côté est donc dist_trous / sqrt(2).
        # La taille totale = Côté_Entre_Trous + 2 * Marge
        side_inner = dist_trous / math.sqrt(2)
        board_size = side_inner + (2 * OFFSET_TROU_M)

        # 3. Rotation
        # Vecteur P1 -> P2
        dx = x2 - x1
        dy = y2 - y1
        angle_diag = math.atan2(dy, dx)

        # La diagonale A8->H1 pointe vers -45° (ou 315°) dans le repère plateau
        # Rotation = AngleMesuré - (-45°) = AngleMesuré + 45°
        rotation = angle_diag + (math.pi / 4)

        # 4. Échelle Caméra
        # La caméra renvoie des coordonnées entre -10 et +10 (donc largeur 20)
        # Scale = TailleRéelle / 20
        camera_scale = board_size / 20.0

        print("\n📊 RÉSULTATS :")
        print(f"  - Distance trous : {dist_trous * 1000:.1f} mm")
        print(f"  - Taille plateau : {board_size * 1000:.1f} mm")
        print(f"  - Rotation       : {math.degrees(rotation):.2f}°")
        print(f"  - Échelle Caméra : {camera_scale:.5f} m/unité")

        return {
            "origin": [center_x, center_y, center_z],
            "rotation": rotation,
            "board_size": board_size,
            "camera_scale": camera_scale,
            "timestamp": time.time()
        }

    def save(self, data):
        try:
            with open(FICHIER_CALIBRATION, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"💾 Sauvegardé dans {FICHIER_CALIBRATION}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")

    def run(self):
        if not self.init_robot():
            return

        print("\nPRÉPARATION :")
        print("Le robot va avoir besoin de deux points de référence.")
        print(f"Les trous doivent être à {OFFSET_TROU_M * 1000:.0f}mm des coins du damier.")

        # Point 1
        p1 = self.interactive_positioning("TROU HAUT-GAUCHE (Côté A8)")

        # Sécurité : on remonte un peu avant d'aller au point 2
        print("⬆️ Remontée de sécurité...")
        self.rtde_c.moveL([p1[0], p1[1], p1[2] + 0.1, p1[3], p1[4], p1[5]], 0.5, 0.3)

        # Point 2
        p2 = self.interactive_positioning("TROU BAS-DROITE (Côté H1)")

        # Remontée finale
        print("⬆️ Remontée finale...")
        self.rtde_c.moveL([p2[0], p2[1], p2[2] + 0.1, p2[3], p2[4], p2[5]], 0.5, 0.3)

        # Calcul et Sauvegarde
        data = self.calculate_geometry(p1, p2)
        self.save(data)

        self.rtde_c.stopScript()
        print("\n✅ CALIBRATION TERMINÉE AVEC SUCCÈS")


if __name__ == "__main__":
    calib = TwoPointCalibration()
    calib.run()