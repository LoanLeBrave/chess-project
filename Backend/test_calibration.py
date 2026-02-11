#!/usr/bin/env python3
"""
Script de TEST et DEBUG de calibration.
Version CLAVIER FRANÇAIS (AZERTY) + REMONTÉE SÉCURISÉE
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
    print("COMMANDES PRINCIPALES :")
    print("  [ENTRÉE]  : Descendre sur la case (Vérification)")
    print("  [ESPACE]  : REMONTER (Sécurité)")
    print("  [C]       : Changer de case")
    print("  [R]       : Reset offset à 0")
    print("  [X]       : Quitter")
    print("-" * 60)
    print("AJUSTEMENT PRÉCIS (Quand le robot est en bas) :")
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
                # Sécurité avant de quitter : on remonte si on est bas
                pose = robot.rtde_r.getActualTCPPose()
                safe_z = robot.calib_origin[2] + DELTA_TRANSIT
                if pose[2] < safe_z - 0.05:
                    print("\n⬆️ Remontée avant de quitter...")
                    pose[2] = safe_z
                    robot.rtde_c.moveL(pose, 0.5, 0.3)
                print("\n👋 Fin du test.")
                break

            # --- REMONTER (SÉCURITÉ) ---
            elif key == ' ':
                print("\n⬆️  Remontée vers position de sécurité...")
                # On récupère la pose actuelle pour garder X/Y, on change juste Z
                current_pose = robot.rtde_r.getActualTCPPose()
                target_up = list(current_pose)
                # Hauteur de transit définie dans config (+12cm)
                target_up[2] = robot.calib_origin[2] + DELTA_TRANSIT
                robot.rtde_c.moveL(target_up, 0.5, 0.3)
                need_refresh = True

            # --- DESCENDRE (VÉRIFICATION) ---
            elif key == '\r':  # Touche ENTRÉE
                print(f"\n🚀 Descente vers {current_case}...")
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

                    # Si on est déjà en haut, on se déplace en XY d'abord
                    current_z = robot.rtde_r.getActualTCPPose()[2]
                    if current_z > pose_basse[2] + 0.05:
                        robot.rtde_c.moveL(pose_haute, 0.5, 0.3)

                    # Puis on descend
                    robot.rtde_c.moveL(pose_basse, 0.1, 0.1)
                    print("✅ Arrivé en bas.")
                    need_refresh = True
                except Exception as e:
                    print(f"❌ Erreur: {e}")
                    time.sleep(2)
                    need_refresh = True

            # --- CHANGER CASE ---
            elif key.lower() == 'c':
                print("\n⌨️  Entrez la case (ex: e4) : ", end='', flush=True)
                fd = sys.stdin.fileno()
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, termios.tcgetattr(1))
                    new_case = sys.stdin.readline().strip().lower()
                finally:
                    pass

                if len(new_case) == 2:
                    current_case = new_case
                need_refresh = True

            # --- RESET ---
            elif key.lower() == 'r':
                manual_offset_x = 0.0
                manual_offset_y = 0.0
                need_refresh = True

            # --- AJUSTEMENTS AZERTY ---
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

            # Si on a bougé l'offset alors qu'on est en bas, on applique le mouvement tout de suite
            if key.lower() in ['z', 'q', 's', 'd']:
                # Petit mouvement relatif immédiat pour voir le résultat
                # On ne recalcule pas tout le chemin, on bouge juste le TCP relatif
                # (Optionnel mais plus fluide, sinon l'utilisateur doit refaire Entrée)
                # Pour simplifier et éviter les erreurs, on ne bouge pas physiquement ici
                # mais l'utilisateur verra la valeur changer et fera Entrée pour appliquer.
                pass

        time.sleep(0.05)

    robot.close()


if __name__ == "__main__":
    main()