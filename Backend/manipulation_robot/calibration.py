#!/usr/bin/env python3
"""
Module de calibration dynamique à 2 points pour robot d'échecs.
Détermine automatiquement : position, rotation et taille du plateau.
Intègre une fonction d'Auto-Level et une vitesse réduite pour la précision.
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
            print(" Robot connecté.")
            return True
        except Exception as e:
            print(f"Erreur connexion: {e}")
            return False

    def enable_freedrive(self):
        """Active le mode Freedrive CONTRAINT sur X et Y uniquement"""
        # [X, Y, Z, Rx, Ry, Rz] -> 1=Libre, 0=Bloqué
        self.rtde_c.freedriveMode([1, 1, 0, 0, 0, 0])

    def disable_freedrive(self):
        """Désactive Freedrive et recharge le script"""
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
            rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                    ch3 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                    if ch2 == '[':
                        if ch3 == 'A': return 'w'
                        if ch3 == 'B': return 's'
                    return '\x1b'
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def interactive_positioning(self, step_name):
        """
        Permet à l'utilisateur de positionner le robot dans le trou.
        Combine Freedrive, Ajustement clavier et Auto-Level.
        """
        print("\n" + "=" * 60)
        print(f" ÉTAPE : {step_name}")
        print("=" * 60)
        print("COMMANDES :")
        print("  [F]      : Activer/Désactiver FREEDRIVE (X/Y SEULEMENT)")
        print("  [S] / [↓]: Descendre (Z-) - Vitesse LENTE")
        print("  [W] / [↑]: Monter (Z+)    - Vitesse LENTE")
        print("  [L]      : AUTO-LEVEL (Rendre le gripper parfaitement vertical)")
        print("  [Q]      : VALIDER la position et passer à la suite")
        print("  [ESC]    : Annuler")
        print("-" * 60)

        freedrive_active = False

        # --- MODIFICATION VITESSE ---
        velocity_z = 0.01  # 1 cm/s (au lieu de 5 cm/s) pour plus de précision
        # ----------------------------

        last_key_time = 0
        is_moving = False
        SSH_KEY_TIMEOUT = 0.25

        while True:
            # Lecture position et affichage info orientation
            pose = self.rtde_r.getActualTCPPose()
            state_str = "LIBRE (X/Y)" if freedrive_active else "BLOQUÉ (Clavier)"
            # On affiche Rx et Ry pour aider à voir si on est droit
            print(f"\r Z={pose[2]:.4f} | RX={pose[3]:.2f} RY={pose[4]:.2f} | {state_str}   ", end="", flush=True)

            key = self.get_key_non_blocking()

            # --- GESTION DES COMMANDES UNIQUES ---
            if key:
                # Annulation
                if key == '\x1b':
                    self.rtde_c.speedStop()
                    if freedrive_active: self.disable_freedrive()
                    print("\n Annulation.")
                    sys.exit(0)

                # Validation
                elif key.lower() == 'q':
                    self.rtde_c.speedStop()
                    if freedrive_active: self.disable_freedrive()
                    print(f"\n Position {step_name} enregistrée.")
                    return pose

                # Toggle Freedrive
                elif key.lower() == 'f':
                    self.rtde_c.speedStop()
                    is_moving = False
                    if freedrive_active:
                        self.disable_freedrive()
                        freedrive_active = False
                    else:
                        self.enable_freedrive()
                        freedrive_active = True
                    time.sleep(0.3)
                    continue

                # --- AUTO-LEVEL ---
                elif key.lower() == 'l':
                    if freedrive_active:
                        self.disable_freedrive()
                        freedrive_active = False

                    print("\n  Correction de la verticalité...")
                    current = self.rtde_r.getActualTCPPose()

                    # Vertical standard [pi, 0, 0]
                    vertical_pose = [current[0], current[1], current[2], 3.1415, 0.0, 0.0]

                    self.rtde_c.moveL(vertical_pose, 0.2, 0.2)
                    print(" Gripper verticalisé.")
                    time.sleep(0.5)
                    continue

            # --- GESTION DU MOUVEMENT Z (Continu) ---
            if not freedrive_active:
                target_vel_z = 0.0
                if key:
                    if key.lower() == 's':
                        target_vel_z = -velocity_z
                        last_key_time = time.time()
                    elif key.lower() == 'w':
                        target_vel_z = velocity_z
                        last_key_time = time.time()

                if target_vel_z != 0:
                    # On utilise ACCELERATION=0.5 pour que ça réagisse vite mais sans à-coups violents
                    self.rtde_c.speedL([0, 0, target_vel_z, 0, 0, 0], 0.5, 0.3)
                    is_moving = True
                elif is_moving:
                    if time.time() - last_key_time > SSH_KEY_TIMEOUT:
                        self.rtde_c.speedStop()
                        is_moving = False

    def calculate_geometry(self, p1, p2, p_z):
        """Calcule la géométrie du plateau d'après le DXF exact."""
        x1, y1 = p1[0], p1[1]  # Trou A8
        x2, y2 = p2[0], p2[1]  # Trou H1

        # 1. Centre du plateau (X/Y viennent des trous, Z vient de la surface)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        center_z = p_z[2]  # <--- LE Z DE LA SURFACE EST ICI

        # 2. Rotation
        dx_robot = x2 - x1
        dy_robot = y2 - y1
        angle_robot = math.atan2(dy_robot, dx_robot)

        # === NOUVELLES VALEURS DU DXF 269.6 mm ===
        # Vecteur théorique d'après le DXF en MÈTRES
        dx_dxf = 0.3021  # 302.1 mm
        dy_dxf = -0.2481  # -248.1 mm
        angle_dxf = math.atan2(dy_dxf, dx_dxf)

        rotation = angle_robot - angle_dxf

        # 3. Taille et Échelle
        dist_mesuree = math.sqrt(dx_robot ** 2 + dy_robot ** 2)
        dist_theorique = math.sqrt(dx_dxf ** 2 + dy_dxf ** 2)  # Environ 0.3909 m

        scale = dist_mesuree / dist_theorique

        # === NOUVELLE TAILLE DU PLATEAU ===
        # 8 cases de 33.7 mm = 269.6 mm (0.2696 m)
        board_size = 0.2696 * scale
        square_size = board_size / 8.0
        camera_scale = board_size / 20.0

        # === AFFICHAGE DÉTAILLÉ ===
        print("\n" + "=" * 50)
        print(" RÉSULTATS DE LA CALIBRATION")
        print("=" * 50)
        print(f" Échelle calculée (DXF vs Réel) : {scale:.4f}")
        print(f" Angle de rotation corrigé    : {math.degrees(rotation):.2f}°")
        print(f"↕  Hauteur Z fixée à            : {center_z:.4f} m")
        print("-" * 50)
        print(f" TAILLE DU PLATEAU ESTIMÉE    : {board_size * 1000:.1f} mm")
        print(f" TAILLE D'UNE CASE            : {square_size * 1000:.1f} mm")
        print("=" * 50 + "\n")

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
            print(f" Sauvegardé dans {FICHIER_CALIBRATION}")
        except Exception as e:
            print(f" Erreur sauvegarde: {e}")

    def run(self):
        if not self.init_robot():
            return

        print("\nPRÉPARATION :")

        # Point 1 : Trou Haut-Gauche
        p1 = self.interactive_positioning("TROU HAUT-GAUCHE (Côté A8)")

        # Sécurité
        print(" Remontée de sécurité...")
        self.rtde_c.moveL([p1[0], p1[1], p1[2] + 0.1, p1[3], p1[4], p1[5]], 0.5, 0.3)

        # Point 2 : Trou Bas-Droite
        p2 = self.interactive_positioning("TROU BAS-DROITE (Côté H1)")

        # Remontée
        print("Remontée de sécurité...")
        self.rtde_c.moveL([p2[0], p2[1], p2[2] + 0.1, p2[3], p2[4], p2[5]], 0.5, 0.3)

        # Point 3 : Surface Z
        p_z = self.interactive_positioning("SURFACE DU PLATEAU (Posez le bout du gripper au ras du plateau)")

        # Remontée finale
        print(" Remontée finale...")
        self.rtde_c.moveL([p_z[0], p_z[1], p_z[2] + 0.1, p_z[3], p_z[4], p_z[5]], 0.5, 0.3)

        # Calcul et Sauvegarde (avec les 3 points)
        data = self.calculate_geometry(p1, p2, p_z)
        self.save(data)

        self.rtde_c.stopScript()
        print("\n CALIBRATION TERMINÉE AVEC SUCCÈS")

if __name__ == "__main__":
    calib = TwoPointCalibration()
    calib.run()