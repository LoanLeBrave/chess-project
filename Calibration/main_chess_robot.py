#!/usr/bin/env python3
"""
Intégration Complète Vision + Robot pour Échecs
================================================
Ce script combine:
- Détection ArUco des pièces (IDs 0-31)
- Calibration plateau ↔ robot
- Commandes de mouvement pour saisir les pièces

Usage:
    python main_chess_robot.py --robot 192.168.0.11 --camera 0
"""

import cv2
import numpy as np
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple, Dict

# Imports locaux
from chess_vision_system import (
    ChessVisionSystem,
    ChessRobotIntegration,
    PieceType,
    PIECES_REFERENCE
)
from calibration_robot import (
    PlateauRobotCalibration,
    CalibrationWizard,
    quick_calibration_from_single_point
)


class ChessRobotMain:
    """
    Contrôleur principal pour le robot d'échecs.
    """

    def __init__(self,
                 robot_ip: str = "192.168.0.11",
                 camera_index: int = 0,
                 calibration_file: str = "calibration_robot.json"):

        self.robot_ip = robot_ip
        self.camera_index = camera_index
        self.calibration_file = calibration_file

        # Composants
        self.vision: Optional[ChessVisionSystem] = None
        self.calibration: Optional[PlateauRobotCalibration] = None
        self.integration: Optional[ChessRobotIntegration] = None

        # Robot RTDE
        self.rtde_control = None
        self.rtde_receive = None

        # Configuration des hauteurs (mm)
        self.heights = {
            'transit': 150,  # Hauteur de déplacement
            'approach': 50,  # Hauteur d'approche
            'grip': {  # Hauteur de saisie par pièce
                PieceType.PAWN: 25,
                PieceType.ROOK: 30,
                PieceType.KNIGHT: 35,
                PieceType.BISHOP: 40,
                PieceType.QUEEN: 50,
                PieceType.KING: 55,
            }
        }

        # État
        self.is_connected = False

    def connect(self) -> bool:
        """Établit toutes les connexions."""
        print("\n" + "=" * 50)
        print("CONNEXION DES COMPOSANTS")
        print("=" * 50)

        # 1. Vision
        print("\n[1/3] Caméra...")
        self.vision = ChessVisionSystem(camera_index=self.camera_index)
        if not self.vision.connect_camera():
            print("❌ Échec caméra")
            return False

        # Calibration automatique avec les 4 coins ArUco (32, 33, 34, 35)
        print("\n📐 Calibration caméra avec les ArUco des coins...")
        print("   Coins attendus: 32(A8), 33(H8), 34(A1), 35(H1)")

        # Essayer plusieurs fois
        for attempt in range(3):
            frame = self.vision.get_frame()
            if frame is not None and self.vision.auto_calibrate_from_corners(frame):
                print("✅ Calibration pixels→cm OK!")
                break
            time.sleep(0.5)
        else:
            print("⚠️ Calibration auto échouée - vérifiez que les 4 coins sont visibles")
            # Estimation de secours
            self.vision.calibrate_simple(pixels_per_cm=12.0, center_offset_px=(320, 240))

        # 2. Robot RTDE
        print("\n[2/3] Robot RTDE...")
        try:
            import rtde_control
            import rtde_receive

            self.rtde_control = rtde_control.RTDEControlInterface(self.robot_ip)
            self.rtde_receive = rtde_receive.RTDEReceiveInterface(self.robot_ip)
            print(f"✅ Robot connecté: {self.robot_ip}")
        except ImportError:
            print("⚠️ Modules RTDE non disponibles - mode simulation")
        except Exception as e:
            print(f"⚠️ Robot non connecté: {e}")
            print("   Mode simulation activé")

        # 3. Calibration plateau-robot
        print("\n[3/3] Calibration plateau→robot...")
        self.calibration = PlateauRobotCalibration()

        if Path(self.calibration_file).exists():
            self.calibration.load(self.calibration_file)
        else:
            print("⚠️ Pas de calibration plateau→robot trouvée")
            print(f"   Lancez: python main_chess_robot.py --calibrate")

        # Intégration
        self.integration = ChessRobotIntegration(self.vision)

        self.is_connected = True
        print("\n✅ Système prêt!")
        return True

    def disconnect(self):
        """Ferme les connexions."""
        if self.vision:
            self.vision.disconnect_camera()
        if self.rtde_control:
            self.rtde_control.stopScript()
        print("🔌 Déconnecté")

    def get_robot_position(self) -> Optional[Tuple[float, float, float]]:
        """Retourne la position TCP actuelle (mm)."""
        if self.rtde_receive:
            pose = self.rtde_receive.getActualTCPPose()
            return (pose[0] * 1000, pose[1] * 1000, pose[2] * 1000)
        return None

    def move_robot(self, x_mm: float, y_mm: float, z_mm: float,
                   speed: float = 0.3, acc: float = 0.3) -> bool:
        """
        Déplace le robot vers une position.

        Args:
            x_mm, y_mm, z_mm: Position cible en mm
            speed: Vitesse (m/s)
            acc: Accélération (m/s²)
        """
        if self.rtde_control is None:
            print(f"[SIM] moveL to ({x_mm:.1f}, {y_mm:.1f}, {z_mm:.1f}) mm")
            return True

        # Convertir mm -> m
        current_pose = self.rtde_receive.getActualTCPPose()
        target_pose = [
            x_mm / 1000,
            y_mm / 1000,
            z_mm / 1000,
            current_pose[3],
            current_pose[4],
            current_pose[5]
        ]

        return self.rtde_control.moveL(target_pose, speed, acc)

    def move_to_piece(self, aruco_id: int, approach_only: bool = True) -> bool:
        """
        Déplace le robot vers une pièce détectée.

        Args:
            aruco_id: ID ArUco de la pièce (0-31)
            approach_only: Si True, s'arrête au-dessus de la pièce
        """
        # Détecter les pièces
        pieces = self.vision.detect_pieces()

        if aruco_id not in pieces:
            print(f"❌ Pièce ID {aruco_id} non détectée")
            return False

        piece = pieces[aruco_id]
        print(f"📍 Pièce trouvée: {piece.label} à ({piece.x:.1f}, {piece.y:.1f}) cm")

        # Convertir vers coordonnées robot
        rx, ry, rz = self.calibration.board_to_robot(piece.x, piece.y)

        print(f"   -> Robot: ({rx:.1f}, {ry:.1f}, {rz:.1f}) mm")

        # Séquence de mouvement
        current_pos = self.get_robot_position()

        # 1. Monter à hauteur de transit
        if current_pos:
            self.move_robot(current_pos[0], current_pos[1], self.heights['transit'])

        # 2. Se déplacer au-dessus de la pièce
        self.move_robot(rx, ry, self.heights['transit'])

        # 3. Descendre à hauteur d'approche
        self.move_robot(rx, ry, self.heights['approach'])

        if not approach_only:
            # 4. Descendre à hauteur de saisie
            grip_z = rz + self.heights['grip'][piece.piece_type]
            self.move_robot(rx, ry, grip_z)

        return True

    def grab_piece(self, aruco_id: int) -> bool:
        """Saisit une pièce."""
        if not self.move_to_piece(aruco_id, approach_only=False):
            return False

        # Fermer gripper
        self._gripper_close()
        time.sleep(0.3)

        # Remonter
        pos = self.get_robot_position()
        if pos:
            self.move_robot(pos[0], pos[1], self.heights['transit'])

        return True

    def place_at_square(self, square: str, piece_type: PieceType = PieceType.PAWN) -> bool:
        """Pose la pièce tenue sur une case."""
        x_cm, y_cm = self.integration.algebraic_to_cm(square)
        rx, ry, rz = self.calibration.board_to_robot(x_cm, y_cm)

        print(f"📍 Case {square} -> ({rx:.1f}, {ry:.1f}) mm")

        # Se déplacer au-dessus
        self.move_robot(rx, ry, self.heights['transit'])

        # Descendre
        place_z = rz + self.heights['grip'][piece_type] + 5  # +5mm marge
        self.move_robot(rx, ry, place_z)

        # Ouvrir gripper
        self._gripper_open()
        time.sleep(0.3)

        # Remonter
        self.move_robot(rx, ry, self.heights['transit'])

        return True

    def execute_move(self, from_square: str, to_square: str,
                     is_capture: bool = False) -> bool:
        """
        Exécute un coup d'échecs complet.

        Args:
            from_square: Case de départ (ex: "e2")
            to_square: Case d'arrivée (ex: "e4")
            is_capture: True si capture
        """
        print(f"\n♟️ Coup: {from_square} -> {to_square}" +
              (" (capture)" if is_capture else ""))

        # Trouver la pièce sur la case de départ
        from_x, from_y = self.integration.algebraic_to_cm(from_square)
        piece_id = self.integration.find_piece_on_square(from_x, from_y)

        if piece_id is None:
            print(f"❌ Pas de pièce sur {from_square}")
            return False

        piece = self.vision._last_detection[piece_id]
        print(f"   Pièce: {piece.label}")

        # Si capture, d'abord retirer la pièce adverse
        if is_capture:
            to_x, to_y = self.integration.algebraic_to_cm(to_square)
            captured_id = self.integration.find_piece_on_square(to_x, to_y)

            if captured_id:
                print(f"   Capture: ID {captured_id}")
                self.grab_piece(captured_id)
                # TODO: poser dans zone de capture
                self._gripper_open()

        # Saisir la pièce à déplacer
        self._gripper_open()
        self.grab_piece(piece_id)

        # Poser sur la case d'arrivée
        self.place_at_square(to_square, piece.piece_type)

        print(f"✅ Coup exécuté!")
        return True

    def _gripper_open(self, width: float = 25.0):
        """Ouvre le gripper."""
        print(f"[GRIPPER] Ouvert ({width}mm)")
        # TODO: Intégrer ton contrôle gripper existant

    def _gripper_close(self, force: float = 50.0):
        """Ferme le gripper."""
        print(f"[GRIPPER] Fermé (force={force})")
        # TODO: Intégrer ton contrôle gripper existant

    def run_calibration(self):
        """Lance l'assistant de calibration plateau→robot."""
        print("\n" + "=" * 50)
        print("CALIBRATION PLATEAU → ROBOT")
        print("=" * 50)
        print("""
Cette calibration établit la correspondance entre:
- Les coordonnées du plateau (cm, origine au centre)
- Les coordonnées du robot UR5e (mm)

Plateau 28x28 cm, coins à ±14 cm du centre.
        """)

        # Positions des coins dans le repère plateau
        corners_info = [
            (34, -14, -14, "A1 (bas-gauche)"),
            (35, 14, -14, "H1 (bas-droite)"),
            (33, 14, 14, "H8 (haut-droite)"),
            (32, -14, 14, "A8 (haut-gauche)"),
        ]

        self.calibration = PlateauRobotCalibration()

        for aruco_id, bx, by, label in corners_info:
            print(f"\n📍 Coin {label} (ArUco {aruco_id})")
            print(f"   Position plateau: ({bx}, {by}) cm")
            print("   Positionnez le gripper SUR ce coin")

            if self.rtde_receive:
                input("   Appuyez sur Entrée quand le gripper est en position...")
                pose = self.rtde_receive.getActualTCPPose()
                rx, ry, rz = pose[0] * 1000, pose[1] * 1000, pose[2] * 1000
                print(f"   Position robot lue: ({rx:.1f}, {ry:.1f}, {rz:.1f}) mm")
            else:
                print("   Entrez la position robot TCP (en mm):")
                try:
                    rx = float(input("   X (mm): "))
                    ry = float(input("   Y (mm): "))
                    rz = float(input("   Z (mm): "))
                except ValueError:
                    print("   ❌ Valeur invalide, coin ignoré")
                    continue

            self.calibration.add_calibration_point(bx, by, rx, ry, rz, label)

        if self.calibration.compute_calibration():
            self.calibration.save(self.calibration_file)
            print(f"\n✅ Calibration sauvegardée: {self.calibration_file}")
        else:
            print("\n❌ Échec de la calibration")

    def interactive_mode(self):
        """Mode interactif pour tester."""
        print("\n" + "=" * 50)
        print("MODE INTERACTIF")
        print("=" * 50)
        print("""
Touches (fenêtre OpenCV):
  D: Détecter et afficher les pièces
  G: Aller à une pièce (saisir ID)
  M: Exécuter un coup (ex: e2e4)
  C: Calibrer
  S: Sauvegarder état
  Q: Quitter

Commandes console:
  Tapez un coup (ex: e2e4) puis Entrée
        """)

        while True:
            # Afficher la vue caméra
            frame = self.vision.get_frame()
            if frame is not None:
                self.vision.detect_pieces(frame)
                display = self.vision.draw_overlay(frame)

                # Afficher infos calibration
                if self.calibration.is_calibrated:
                    cv2.putText(display, f"Calib OK (err: {self.calibration.calibration_error_mm:.1f}mm)",
                                (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

                cv2.imshow("Chess Robot", display)

            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                break

            elif key == ord('d'):
                # Afficher les pièces
                pieces = self.vision.detect_pieces()
                print(f"\n📊 {len(pieces)} pièces détectées:")
                for aid, p in sorted(pieces.items()):
                    rx, ry, rz = self.calibration.board_to_robot(p.x, p.y)
                    print(f"   {p.label}: plateau({p.x:.1f}, {p.y:.1f}) -> robot({rx:.0f}, {ry:.0f})")

            elif key == ord('g'):
                try:
                    aid = int(input("\nID ArUco: "))
                    self.move_to_piece(aid)
                except ValueError:
                    pass

            elif key == ord('m'):
                move = input("\nCoup (ex: e2e4): ").strip()
                if len(move) >= 4:
                    capture = 'x' in move or len(move) > 4
                    self.execute_move(move[:2], move[2:4], capture)

            elif key == ord('c'):
                self.run_calibration()

            elif key == ord('s'):
                self.vision.export_game_state("game_state.json")

        cv2.destroyAllWindows()


def main():
    print("=" * 50)
    print("DÉMARRAGE DU SCRIPT")
    print("=" * 50)
    print()

    parser = argparse.ArgumentParser(description="Robot d'échecs avec vision ArUco")
    parser.add_argument("--robot", default="192.168.0.11", help="IP du robot UR5e")
    parser.add_argument("--camera", type=int, default=0, help="Index caméra")
    parser.add_argument("--config", default="calibration_robot.json", help="Fichier calibration")
    parser.add_argument("--calibrate", action="store_true", help="Lancer la calibration")

    args = parser.parse_args()

    print(f"Arguments:")
    print(f"  - Robot IP: {args.robot}")
    print(f"  - Caméra: {args.camera}")
    print(f"  - Config: {args.config}")
    print(f"  - Mode calibration: {args.calibrate}")
    print()

    robot = ChessRobotMain(
        robot_ip=args.robot,
        camera_index=args.camera,
        calibration_file=args.config
    )

    print("Connexion en cours...")

    if not robot.connect():
        print("❌ Échec de connexion")
        return

    try:
        if args.calibrate:
            robot.run_calibration()
        else:
            robot.interactive_mode()
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        robot.disconnect()


if __name__ == "__main__":
    print("Script main_chess_robot.py chargé")
    main()