#!/usr/bin/env python3
"""
Test de Saisie des Pions
========================
Ce script permet de tester si le robot peut aller chercher les pions
après la calibration automatique.

Fonctionnalités:
- Affiche toutes les pièces détectées avec leurs coordonnées
- Permet d'aller vers une pièce spécifique (par ID ArUco)
- Permet d'aller vers une case spécifique (notation algébrique)
- Mode interactif pour tester plusieurs pièces

Usage:
    python3 test_grab_pieces.py --robot 192.168.0.11
"""

import cv2
import numpy as np
import time
import json
import argparse
from typing import Optional, Tuple, Dict
from pathlib import Path

from chess_vision_system import ChessVisionSystem, PieceType, PIECES_REFERENCE
from auto_calibration import AutoCalibration, CalibrationConfig


class PieceGrabTester:
    """
    Testeur pour vérifier que le robot peut aller chercher les pions.
    """

    def __init__(self,
                 robot_ip: str = "192.168.0.11",
                 camera_index: int = 0,
                 calibration_file: str = "auto_calibration.json"):

        self.robot_ip = robot_ip
        self.camera_index = camera_index
        self.calibration_file = calibration_file

        # Vision
        self.vision: Optional[ChessVisionSystem] = None

        # Robot RTDE
        self.rtde_control = None
        self.rtde_receive = None

        # Calibration chargée
        self.transform_matrix: Optional[np.ndarray] = None
        self.z_offset_mm: float = 0
        self.is_calibrated: bool = False

        # Configuration plateau
        self.board_size_cm = 28.0
        self.square_size_cm = 3.5  # 28/8

        # Hauteurs (mm)
        self.heights = {
            'transit': 100,  # Hauteur de déplacement sécurisé
            'approach': 50,  # Hauteur d'approche
            'grip': {  # Hauteur de saisie par type de pièce
                PieceType.PAWN: 15,
                PieceType.ROOK: 20,
                PieceType.KNIGHT: 25,
                PieceType.BISHOP: 30,
                PieceType.QUEEN: 40,
                PieceType.KING: 45,
            }
        }

        # Vitesses (m/s)
        self.speed_fast = 0.2
        self.speed_slow = 0.05

    def connect(self) -> bool:
        """Connecte à la caméra et au robot."""
        print("\n" + "=" * 60)
        print("CONNEXION POUR TEST DE SAISIE")
        print("=" * 60)

        # 1. Vision
        print("\n[1/3] Connexion caméra...")
        self.vision = ChessVisionSystem(camera_index=self.camera_index)
        if not self.vision.connect_camera():
            print("❌ Échec connexion caméra")
            return False

        # Calibration caméra (pixels → cm)
        print("\n[2/3] Calibration caméra...")
        for attempt in range(5):
            frame = self.vision.get_frame()
            if frame is not None and self.vision.auto_calibrate_from_corners(frame):
                print("✅ Calibration caméra OK")
                break
            time.sleep(0.5)
        else:
            print("⚠️ Calibration caméra échouée")
            return False

        # 2. Charger la calibration robot
        print("\n[3/3] Chargement calibration robot...")
        if not self.load_calibration():
            print("❌ Pas de calibration trouvée!")
            print(f"   Lancez d'abord: python3 auto_calibration.py")
            return False

        # 3. Robot RTDE
        print("\n[4/4] Connexion robot RTDE...")
        try:
            import rtde_control
            import rtde_receive

            self.rtde_control = rtde_control.RTDEControlInterface(self.robot_ip)
            self.rtde_receive = rtde_receive.RTDEReceiveInterface(self.robot_ip)
            print(f"✅ Robot connecté: {self.robot_ip}")
        except Exception as e:
            print(f"❌ Erreur connexion robot: {e}")
            return False

        print("\n✅ Système prêt pour les tests!")
        return True

    def disconnect(self):
        """Déconnecte tout."""
        if self.vision:
            self.vision.disconnect_camera()
        if self.rtde_control:
            self.rtde_control.stopScript()
        print("🔌 Déconnecté")

    def load_calibration(self) -> bool:
        """Charge la calibration depuis le fichier JSON."""
        try:
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)

            self.transform_matrix = np.array(data['transform_matrix'])
            self.z_offset_mm = data['z_offset_mm']
            self.is_calibrated = True

            print(f"✅ Calibration chargée: {self.calibration_file}")
            return True
        except FileNotFoundError:
            print(f"❌ Fichier non trouvé: {self.calibration_file}")
            return False
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

    def camera_to_robot(self, x_cm: float, y_cm: float) -> Tuple[float, float, float]:
        """Convertit coordonnées caméra (cm) vers robot (mm)."""
        if not self.is_calibrated:
            raise ValueError("Calibration non chargée!")

        pt = np.array([x_cm, y_cm, 1])
        robot_pt = self.transform_matrix @ pt

        return (robot_pt[0], robot_pt[1], self.z_offset_mm)

    def get_robot_tcp(self) -> Tuple[float, float, float]:
        """Retourne la position TCP actuelle (mm)."""
        pose = self.rtde_receive.getActualTCPPose()
        return (pose[0] * 1000, pose[1] * 1000, pose[2] * 1000)

    def move_robot(self, x_mm: float, y_mm: float, z_mm: float,
                   speed: float = 0.1) -> bool:
        """Déplace le robot vers une position."""
        current_pose = self.rtde_receive.getActualTCPPose()
        target_pose = [
            x_mm / 1000,
            y_mm / 1000,
            z_mm / 1000,
            current_pose[3],
            current_pose[4],
            current_pose[5]
        ]
        return self.rtde_control.moveL(target_pose, speed, 0.3)

    def detect_all_pieces(self) -> Dict[int, dict]:
        """
        Détecte toutes les pièces et retourne leurs infos.

        Returns:
            Dict[aruco_id, {label, color, type, x_cm, y_cm, x_robot, y_robot}]
        """
        pieces_info = self.vision.detect_pieces()

        result = {}
        for aruco_id, piece in pieces_info.items():
            # Convertir en coordonnées robot
            robot_x, robot_y, robot_z = self.camera_to_robot(piece.x, piece.y)

            result[aruco_id] = {
                'label': piece.label,
                'color': piece.color,
                'type': piece.piece_type,
                'x_cm': piece.x,
                'y_cm': piece.y,
                'robot_x_mm': robot_x,
                'robot_y_mm': robot_y,
                'robot_z_mm': robot_z,
            }

        return result

    def print_detected_pieces(self):
        """Affiche toutes les pièces détectées."""
        pieces = self.detect_all_pieces()

        print(f"\n{'=' * 70}")
        print(f"PIÈCES DÉTECTÉES: {len(pieces)}")
        print(f"{'=' * 70}")
        print(f"{'ID':>4} | {'Pièce':<20} | {'Caméra (cm)':<15} | {'Robot (mm)':<20}")
        print(f"{'-' * 70}")

        for aruco_id in sorted(pieces.keys()):
            p = pieces[aruco_id]
            cam_pos = f"({p['x_cm']:>6.1f}, {p['y_cm']:>6.1f})"
            robot_pos = f"({p['robot_x_mm']:>7.1f}, {p['robot_y_mm']:>7.1f})"
            print(f"{aruco_id:>4} | {p['label']:<20} | {cam_pos:<15} | {robot_pos:<20}")

        print(f"{'=' * 70}")

    def move_to_piece(self, aruco_id: int, go_down: bool = False) -> bool:
        """
        Déplace le robot vers une pièce.

        Args:
            aruco_id: ID ArUco de la pièce
            go_down: Si True, descend jusqu'à la hauteur de saisie
        """
        pieces = self.detect_all_pieces()

        if aruco_id not in pieces:
            print(f"❌ Pièce ID {aruco_id} non détectée!")
            return False

        p = pieces[aruco_id]
        print(f"\n🎯 Déplacement vers: {p['label']} (ID {aruco_id})")
        print(f"   Position caméra: ({p['x_cm']:.1f}, {p['y_cm']:.1f}) cm")
        print(f"   Position robot: ({p['robot_x_mm']:.1f}, {p['robot_y_mm']:.1f}) mm")

        target_x = p['robot_x_mm']
        target_y = p['robot_y_mm']

        # 1. Monter à la hauteur de transit
        current_pos = self.get_robot_tcp()
        print(f"   [1/3] Montée à {self.heights['transit']}mm...")
        self.move_robot(current_pos[0], current_pos[1],
                        self.z_offset_mm + self.heights['transit'],
                        self.speed_fast)

        # 2. Déplacement horizontal
        print(f"   [2/3] Déplacement vers la pièce...")
        self.move_robot(target_x, target_y,
                        self.z_offset_mm + self.heights['transit'],
                        self.speed_fast)

        # 3. Descente
        if go_down:
            grip_height = self.heights['grip'].get(p['type'], 20)
            print(f"   [3/3] Descente à {grip_height}mm (hauteur de saisie)...")
            self.move_robot(target_x, target_y,
                            self.z_offset_mm + grip_height,
                            self.speed_slow)
        else:
            print(f"   [3/3] Descente à {self.heights['approach']}mm (approche)...")
            self.move_robot(target_x, target_y,
                            self.z_offset_mm + self.heights['approach'],
                            self.speed_slow)

        print(f"✅ Robot en position au-dessus de {p['label']}")
        return True

    def algebraic_to_cm(self, square: str) -> Tuple[float, float]:
        """Convertit notation algébrique vers coordonnées cm (origine au centre)."""
        col = ord(square[0].lower()) - ord('a')  # 0-7
        row = int(square[1]) - 1  # 0-7

        half = self.board_size_cm / 2  # 14cm

        x_cm = (col + 0.5) * self.square_size_cm - half
        y_cm = (row + 0.5) * self.square_size_cm - half

        return x_cm, y_cm

    def move_to_square(self, square: str, go_down: bool = False) -> bool:
        """
        Déplace le robot vers une case.

        Args:
            square: Notation algébrique (ex: "e4")
            go_down: Si True, descend à la hauteur d'approche
        """
        x_cm, y_cm = self.algebraic_to_cm(square)
        robot_x, robot_y, robot_z = self.camera_to_robot(x_cm, y_cm)

        print(f"\n🎯 Déplacement vers case {square.upper()}")
        print(f"   Position plateau: ({x_cm:.1f}, {y_cm:.1f}) cm")
        print(f"   Position robot: ({robot_x:.1f}, {robot_y:.1f}) mm")

        # 1. Monter
        current_pos = self.get_robot_tcp()
        print(f"   [1/3] Montée...")
        self.move_robot(current_pos[0], current_pos[1],
                        self.z_offset_mm + self.heights['transit'],
                        self.speed_fast)

        # 2. Déplacement horizontal
        print(f"   [2/3] Déplacement...")
        self.move_robot(robot_x, robot_y,
                        self.z_offset_mm + self.heights['transit'],
                        self.speed_fast)

        # 3. Descente
        if go_down:
            print(f"   [3/3] Descente...")
            self.move_robot(robot_x, robot_y,
                            self.z_offset_mm + self.heights['approach'],
                            self.speed_slow)

        print(f"✅ Robot en position sur {square.upper()}")
        return True

    def test_corners(self):
        """Test: aller aux 4 coins du plateau."""
        print("\n" + "=" * 60)
        print("TEST DES 4 COINS DU PLATEAU")
        print("=" * 60)

        corners = [
            ("a1", "Coin bas-gauche"),
            ("h1", "Coin bas-droite"),
            ("h8", "Coin haut-droite"),
            ("a8", "Coin haut-gauche"),
        ]

        for square, name in corners:
            print(f"\n➡️ {name} ({square})...")
            self.move_to_square(square, go_down=True)
            input("   Appuyez sur Entrée pour continuer...")

        print("\n✅ Test des coins terminé!")

    def test_center(self):
        """Test: aller au centre du plateau."""
        print("\n➡️ Centre du plateau (e4/d4)...")
        self.move_to_square("e4", go_down=True)

    def interactive_mode(self):
        """Mode interactif pour tester."""
        print("\n" + "=" * 60)
        print("MODE INTERACTIF")
        print("=" * 60)
        print("""
Commandes:
  d          - Détecter et afficher les pièces
  p <ID>     - Aller vers la pièce avec cet ID ArUco
  g <ID>     - Aller vers la pièce et descendre (grip)
  s <case>   - Aller vers une case (ex: s e4)
  corners    - Tester les 4 coins
  center     - Aller au centre
  home       - Remonter à la hauteur de transit
  q          - Quitter
        """)

        while True:
            try:
                cmd = input("\n> ").strip().lower()

                if cmd == 'q':
                    break

                elif cmd == 'd':
                    self.print_detected_pieces()

                elif cmd.startswith('p '):
                    try:
                        aruco_id = int(cmd[2:])
                        self.move_to_piece(aruco_id, go_down=False)
                    except ValueError:
                        print("Usage: p <ID>")

                elif cmd.startswith('g '):
                    try:
                        aruco_id = int(cmd[2:])
                        self.move_to_piece(aruco_id, go_down=True)
                    except ValueError:
                        print("Usage: g <ID>")

                elif cmd.startswith('s '):
                    square = cmd[2:].strip()
                    if len(square) == 2 and square[0] in 'abcdefgh' and square[1] in '12345678':
                        self.move_to_square(square, go_down=True)
                    else:
                        print("Usage: s <case> (ex: s e4)")

                elif cmd == 'corners':
                    self.test_corners()

                elif cmd == 'center':
                    self.test_center()

                elif cmd == 'home':
                    current = self.get_robot_tcp()
                    self.move_robot(current[0], current[1],
                                    self.z_offset_mm + self.heights['transit'],
                                    self.speed_fast)
                    print("✅ Robot remonté")

                else:
                    print("Commande inconnue. Tapez 'q' pour quitter.")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Erreur: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test de saisie des pions")
    parser.add_argument("--robot", default="192.168.0.11", help="IP du robot")
    parser.add_argument("--camera", type=int, default=0, help="Index caméra")
    parser.add_argument("--calibration", default="auto_calibration.json", help="Fichier calibration")

    args = parser.parse_args()

    tester = PieceGrabTester(
        robot_ip=args.robot,
        camera_index=args.camera,
        calibration_file=args.calibration
    )

    if not tester.connect():
        return

    try:
        # Afficher les pièces détectées
        tester.print_detected_pieces()

        # Mode interactif
        tester.interactive_mode()

    except KeyboardInterrupt:
        print("\n⏹️ Arrêt")
    finally:
        tester.disconnect()


if __name__ == "__main__":
    main()