#!/usr/bin/env python3
"""
Script de TEST et DEBUG de calibration.
Version CLAVIER FRANÇAIS (AZERTY : Z/Q/S/D)
"""

import sys
import time
import termios
import tty
import select
import chess
from robot_controller import RobotController
from config import DELTA_TRANSIT, DELTA_APPROCHE

# Codes ANSI pour l'interface
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


def print_interface(case, off_x, off_y):
    """Affiche l'interface proprement"""
    print(CLEAR_SCREEN)
    print("=" * 60)
    print("🔧 TEST & DEBUG CALIBRATION (Mode AZERTY)")
    print("=" * 60)
    print(f"🎯 CASE VISÉE          : {case}")
    print(f"📏 OFFSET MANUEL       : X={off_x * 1000:+.1f} mm | Y={off_y * 1000:+.1f} mm")
    print("-" * 60)
    print("COMMANDES :")
    print("  [ENTRÉE]  : Déplacer le robot sur la case")
    print("  [C]       : Changer de case")
    print("  [R]       : Reset offset à 0")
    print("  [X]       : Quitter le script")
    print("-" * 60)
    print("AJUSTEMENT :")
    print("  [Z] : Haut   (Y +1mm)")
    print("  [S] : Bas    (Y -1mm)")
    print("  [D] : Droite (X +1mm)")
    print("  [Q] : Gauche (X -1mm)")
    print("=" * 60)


def main():
    robot = RobotController()
    if not robot.init_robot(): return
    if not robot.is_calibrated:
        print("❌ Lancez calibration.py d'abord.")
        return

    print("\n📍 Fermeture du gripper pour précision...")
    robot.gripper.close()

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
            # --- QUITTER ---
            if key.lower() == 'x':
                print("\n👋 Fin du test.")
                break

            # --- DÉPLACEMENT ---
            elif key == '\r':  # Touche ENTRÉE
                print(f"\n🚀 Déplacement vers {current_case}...")
                try:
                    cx, cy = robot.get_square_center(current_case)
                    target_pose = robot.cam_to_robot(cx, cy, use_piece_height=True)

                    # Appliquer l'offset manuel
                    target_pose[0] += manual_offset_x
                    target_pose[1] += manual_offset_y

                    pose_haute = list(target_pose)
                    pose_haute[2] = robot.calib_origin[2] + DELTA_TRANSIT

                    pose_basse = list(target_pose)
                    # On vise ras du plateau (5mm au dessus du 0 calibré)
                    pose_basse[2] = robot.calib_origin[2] + 0.005

                    robot.rtde_c.moveL(pose_haute, 0.5, 0.3)
                    robot.rtde_c.moveL(pose_basse, 0.1, 0.1)
                    print("✅ Arrivé sur position.")
                    time.sleep(1)
                    need_refresh = True
                except Exception as e:
                    print(f"❌ Erreur: {e}")
                    time.sleep(2)
                    need_refresh = True

            # --- CHANGER CASE ---
            elif key.lower() == 'c':
                print("\n⌨️  Entrez la case (ex: e4) : ", end='', flush=True)
                # Restauration temporaire du terminal pour input()
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, termios.tcgetattr(1))
                    new_case = sys.stdin.readline().strip().lower()
                finally:
                    # On ne remet pas en raw ici, get_key le fera
                    pass

                if len(new_case) == 2:
                    current_case = new_case
                need_refresh = True

            # --- RESET ---
            elif key.lower() == 'r':
                manual_offset_x = 0.0
                manual_offset_y = 0.0
                need_refresh = True

            # --- MOUVEMENTS AZERTY ---
            elif key.lower() == 'z':  # Haut (Y+)
                manual_offset_y += 0.001
                need_refresh = True
            elif key.lower() == 's':  # Bas (Y-)
                manual_offset_y -= 0.001
                need_refresh = True
            elif key.lower() == 'd':  # Droite (X+)
                manual_offset_x += 0.001
                need_refresh = True
            elif key.lower() == 'q':  # Gauche (X-)
                manual_offset_x -= 0.001
                need_refresh = True

        time.sleep(0.05)

    robot.close()


if __name__ == "__main__":
    main()