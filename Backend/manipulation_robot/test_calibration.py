#!/usr/bin/env python3
"""
Script de TEST et DEBUG de calibration (Version Autonome)
Calcule les coordonnées directement depuis robot_calibration.json
pour bypasser les erreurs de robot_controller.py.
"""

import sys
import time
import json
import math
import termios
import tty
import select
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper

from config import ROBOT_IP, FICHIER_CALIBRATION, DELTA_TRANSIT

CLEAR_SCREEN = "\033[2J\033[H"


def get_key():
    """Lecture d'une touche non bloquante"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
        if rlist:
            ch = sys.stdin.read(1)
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def load_calibration():
    try:
        with open(FICHIER_CALIBRATION, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Fichier {FICHIER_CALIBRATION} introuvable. Lancez la calibration.")
        sys.exit(1)


def calculate_square_pose(case, calib_data, offset_x=0.0, offset_y=0.0):
    """Calcule la position XYZ de la case à partir des données de calibration"""
    col_char = case[0].lower()
    row_char = case[1]

    col = ord(col_char) - ord('a')  # 0 à 7 (a=0, h=7)
    row = int(row_char) - 1  # 0 à 7 (1=0, 8=7)

    # Taille d'une case
    square_size = calib_data['board_size'] / 8.0

    # Position relative au centre du plateau (avant rotation)
    # Le centre du plateau est entre 3.5 et 3.5
    rel_x = (col - 3.5) * square_size
    rel_y = (row - 3.5) * square_size

    # On applique la rotation du plateau mesurée lors de la calibration
    theta = calib_data['rotation']
    rot_x = rel_x * math.cos(theta) - rel_y * math.sin(theta)
    rot_y = rel_x * math.sin(theta) + rel_y * math.cos(theta)

    # On ajoute l'origine (centre du plateau) et les offsets manuels
    origin = calib_data['origin']
    target_x = origin[0] + rot_x + offset_x
    target_y = origin[1] + rot_y + offset_y
    target_z = origin[2]  # Le Z sera ajusté au moment du mouvement

    # On retourne une pose avec le TCP parfaitement vertical (Rx=Pi, Ry=0, Rz=0)
    return [target_x, target_y, target_z, 3.1415, 0.0, 0.0]


def print_interface(case, off_x, off_y):
    print(CLEAR_SCREEN)
    print("=" * 60)
    print("🔧 TEST & DEBUG CALIBRATION (Indépendant)")
    print("=" * 60)
    print(f"🎯 CASE VISÉE          : {case.upper()}")
    print(f"📏 OFFSET MANUEL       : X={off_x * 1000:+.1f} mm | Y={off_y * 1000:+.1f} mm")
    print("-" * 60)
    print("COMMANDES PRINCIPALES :")
    print("  [ENTRÉE]  : Descendre sur la case (Vérification)")
    print("  [ESPACE]  : REMONTER (Sécurité)")
    print("  [C]       : Changer de case")
    print("  [R]       : Reset offset à 0")
    print("  [X]       : Quitter")
    print("-" * 60)
    print("AJUSTEMENT PRÉCIS :")
    print("  [Z] Haut (+Y)  [S] Bas (-Y)  [Q] Gauche (-X)  [D] Droite (+X)")
    print("=" * 60)


def main():
    calib_data = load_calibration()

    print(f"🤖 Connexion au robot {ROBOT_IP}...")
    try:
        rtde_c = RTDEControlInterface(ROBOT_IP)
        rtde_r = RTDEReceiveInterface(ROBOT_IP)
        gripper = RobotiqGripper(rtde_c)
        gripper.activate()
        gripper.close()  # Pointe fine
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return

    manual_offset_x = 0.0
    manual_offset_y = 0.0
    current_case = "a1"
    need_refresh = True

    while True:
        if need_refresh:
            print_interface(current_case, manual_offset_x, manual_offset_y)
            need_refresh = False

        key = get_key()

        if key:
            if key.lower() == 'x':
                # Remontée de sécurité avant de quitter
                pose = rtde_r.getActualTCPPose()
                safe_z = calib_data['origin'][2] + DELTA_TRANSIT
                if pose[2] < safe_z - 0.05:
                    pose[2] = safe_z
                    rtde_c.moveL(pose, 0.5, 0.3)
                print("\n👋 Fin du test.")
                break

            elif key == ' ':
                pose = rtde_r.getActualTCPPose()
                pose[2] = calib_data['origin'][2] + DELTA_TRANSIT
                rtde_c.moveL(pose, 0.5, 0.3)
                need_refresh = True

            elif key == '\r':  # ENTRÉE
                try:
                    # Calcul de la pose Cible
                    target_pose = calculate_square_pose(current_case, calib_data, manual_offset_x, manual_offset_y)

                    pose_haute = list(target_pose)
                    pose_haute[2] = calib_data['origin'][2] + DELTA_TRANSIT

                    pose_basse = list(target_pose)
                    pose_basse[2] = calib_data['origin'][2] + 0.005  # 5mm au dessus du plateau

                    # Déplacement XYZ en haut d'abord si on est bas
                    current_z = rtde_r.getActualTCPPose()[2]
                    if current_z > pose_basse[2] + 0.05:
                        rtde_c.moveL(pose_haute, 0.5, 0.3)

                    # Descente
                    rtde_c.moveL(pose_basse, 0.1, 0.1)
                    need_refresh = True
                except Exception as e:
                    print(f"❌ Erreur mouvement: {e}")
                    time.sleep(2)
                    need_refresh = True

            elif key.lower() == 'c':
                print("\n⌨️  Entrez la case (ex: e4) : ", end='', flush=True)
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, termios.tcgetattr(1))
                new_case = sys.stdin.readline().strip().lower()
                if len(new_case) == 2 and new_case[0] in "abcdefgh" and new_case[1] in "12345678":
                    current_case = new_case
                need_refresh = True

            elif key.lower() == 'r':
                manual_offset_x = 0.0
                manual_offset_y = 0.0
                need_refresh = True
            elif key.lower() == 'z':
                manual_offset_y += 0.001; need_refresh = True
            elif key.lower() == 's':
                manual_offset_y -= 0.001; need_refresh = True
            elif key.lower() == 'd':
                manual_offset_x += 0.001; need_refresh = True
            elif key.lower() == 'q':
                manual_offset_x -= 0.001; need_refresh = True

        time.sleep(0.05)

    rtde_c.stopScript()


if __name__ == "__main__":
    main()