#!/usr/bin/env python3
"""
Script de TEST et DEBUG de calibration.
Permet d'ajuster manuellement l'offset pour trouver la valeur parfaite.
"""

import sys
import time
import termios
import tty
import select
import chess
from robot_controller import RobotController
from config import DELTA_TRANSIT, DELTA_APPROCHE


def get_key():
    """Lecture d'une touche non bloquante"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
        if rlist:
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                return ch + ch2 + ch3
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main():
    print("=" * 60)
    print("🔧 TEST & DEBUG CALIBRATION")
    print("=" * 60)
    print("Ce script vous permet de corriger l'offset en temps réel.")

    robot = RobotController()
    if not robot.init_robot(): return
    if not robot.is_calibrated:
        print("❌ Lancez calibration.py d'abord.")
        return

    print("\n📍 Fermeture du gripper pour précision...")
    robot.gripper.close()

    # Offset temporaire accumulé
    manual_offset_x = 0.0
    manual_offset_y = 0.0

    current_case = "a1"  # Case par défaut

    while True:
        print("\n" + "-" * 60)
        print(f"CASE VISÉE : {current_case}")
        print(f"OFFSET ACTUEL APPLIQUÉ : X={manual_offset_x * 1000:.1f}mm, Y={manual_offset_y * 1000:.1f}mm")
        print("-" * 60)
        print("COMMANDES :")
        print("  [ENTER] : Aller à la case (avec l'offset actuel)")
        print("  [C]     : Changer de case")
        print("  [R]     : Reset offset à 0")
        print("  [Q]     : Quitter")
        print("  ↑/↓/←/→ : Ajuster l'offset (1mm)")
        print("-" * 60)

        # Calculer la position théorique + offset manuel
        cx, cy = robot.get_square_center(current_case)
        # On triche en ajoutant l'offset manuel aux coordonnées caméra avant conversion
        # Attention: c'est une approximation, idéalement on l'ajoute en mètres après
        # Mais pour debug visuel c'est suffisant.

        # Conversion
        target_pose = robot.cam_to_robot(cx, cy, use_piece_height=True)

        # Appliquer l'offset manuel (en mètres) sur le repère robot
        target_pose[0] += manual_offset_x
        target_pose[1] += manual_offset_y

        # Afficher menu et attendre touche
        key = get_key()

        if key:
            if key == '\r':  # ENTER -> Mouvement
                print(f"🚀 Déplacement vers {current_case}...")

                pose_haute = list(target_pose)
                pose_haute[2] = robot.calib_origin[2] + DELTA_TRANSIT

                pose_basse = list(target_pose)
                # On vise ras du plateau pour bien voir
                pose_basse[2] = robot.calib_origin[2] + 0.005

                robot.rtde_c.moveL(pose_haute, 0.5, 0.3)
                robot.rtde_c.moveL(pose_basse, 0.1, 0.1)
                print("✅ Arrivé.")

            elif key == 'c':
                new_case = input("Entrez la case (ex: h8): ").strip().lower()
                if len(new_case) == 2: current_case = new_case

            elif key == 'r':
                manual_offset_x = 0.0
                manual_offset_y = 0.0
                print("🔄 Offset remis à zéro.")

            elif key == 'q':
                break

            # Flèches (Code ANSI)
            elif key == '\x1b[A':  # Haut (Y+ ou X- selon orientation base)
                manual_offset_y += 0.001
                print("⬆️  Y +1mm")
            elif key == '\x1b[B':  # Bas
                manual_offset_y -= 0.001
                print("⬇️  Y -1mm")
            elif key == '\x1b[C':  # Droite
                manual_offset_x += 0.001
                print("➡️  X +1mm")
            elif key == '\x1b[D':  # Gauche
                manual_offset_x -= 0.001
                print("⬅️  X -1mm")

        time.sleep(0.05)

    robot.close()


if __name__ == "__main__":
    main()