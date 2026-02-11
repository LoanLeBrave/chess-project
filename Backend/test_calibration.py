#!/usr/bin/env python3
"""
Script de vérification de la calibration.
Permet d'envoyer le robot sur des cases spécifiques pour vérifier l'alignement.
"""

import sys
import time
import chess
from robot_controller import RobotController
from config import DELTA_TRANSIT, DELTA_APPROCHE


def main():
    print("=" * 60)
    print("🤖 TEST DE CALIBRATION ROBOT")
    print("=" * 60)

    # 1. Initialisation
    robot = RobotController()
    if not robot.init_robot():
        print("❌ Impossible de connecter le robot ou de charger la calibration.")
        return

    if not robot.is_calibrated:
        print("❌ Le robot n'est pas calibré ! Lancez calibration.py d'abord.")
        return

    print("\n✅ Robot prêt.")
    print("   Le gripper va se fermer pour servir de pointeur.")
    robot.gripper.close()
    time.sleep(1.0)

    # Liste des coins pour tester rapidement
    coins = ['a1', 'h1', 'h8', 'a8', 'e4', 'e5']
    print(f"\n💡 Cases suggérées pour le test : {', '.join(coins)}")

    while True:
        print("\n" + "-" * 40)
        user_input = input("👉 Entrez une case (ex: 'a1') ou 'q' pour quitter : ").strip().lower()

        if user_input == 'q':
            print("👋 Fin du test.")
            break

        # Vérification format case
        if len(user_input) != 2 or user_input[0] not in "abcdefgh" or user_input[1] not in "12345678":
            print("⚠ Format invalide. Utilisez le format échecs (ex: a1, h8).")
            continue

        try:
            print(f"🔄 Calcul de la position pour {user_input}...")

            # 1. Récupérer les coordonnées théoriques caméra
            cx, cy = robot.get_square_center(user_input)

            # 2. Convertir en coordonnées Robot
            # On demande la position sans offset de pièce pour viser le "sol" ou juste au-dessus
            # Mais comme cam_to_robot ajoute par défaut un offset, on va gérer le Z manuellement pour le test

            # On force le type de pièce à PAWN pour avoir une référence basse standard
            robot.piece_courante = chess.PAWN
            target_pose = robot.cam_to_robot(cx, cy, use_piece_height=True)

            # --- SÉQUENCE DE MOUVEMENT SÉCURISÉE ---

            # A. Position de Transit (Haute)
            pose_haute = list(target_pose)
            pose_haute[2] = robot.calib_origin[2] + DELTA_TRANSIT

            # B. Position d'Approche (Moyenne)
            pose_approche = list(target_pose)
            pose_approche[2] = robot.calib_origin[2] + DELTA_APPROCHE

            # C. Position de Visée (Basse - au niveau d'un pion)
            pose_visee = list(target_pose)
            # On garde le Z calculé par cam_to_robot (qui inclut la hauteur du pion)

            print(f"📍 Déplacement au-dessus de {user_input}...")

            # Mouvement 1 : Monter en sécurité (si on est bas)
            current_pose = robot.rtde_r.getActualTCPPose()
            if current_pose[2] < pose_haute[2]:
                current_pose[2] = pose_haute[2]
                robot.rtde_c.moveL(current_pose, 0.5, 0.3)

            # Mouvement 2 : Aller au-dessus de la case (Haut)
            robot.rtde_c.moveL(pose_haute, 0.5, 0.3)

            # Mouvement 3 : Descendre à l'approche
            robot.rtde_c.moveL(pose_approche, 0.3, 0.3)

            print("⬇️  Descente de précision...")
            # Mouvement 4 : Descendre doucement pour viser
            robot.rtde_c.moveL(pose_visee, 0.1, 0.1)  # Vitesse lente

            print(f"✅ Robot sur {user_input}. Vérifiez l'alignement.")
            time.sleep(1.0)

            input("   [Appuyez sur ENTRÉE pour remonter]")

            # Mouvement 5 : Remonter
            robot.rtde_c.moveL(pose_haute, 0.5, 0.3)

        except Exception as e:
            print(f"❌ Erreur lors du mouvement : {e}")
            # En cas d'erreur, on essaie de stopper
            robot.rtde_c.stopScript()

    # Fin du script
    robot.close()


if __name__ == "__main__":
    main()