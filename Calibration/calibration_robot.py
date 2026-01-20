#!/usr/bin/env python3
"""
Calibration Plateau ↔ Robot avec ArUco
======================================
Ce module permet de calibrer précisément la transformation
entre le repère du plateau (en cm, origine au centre) et
le repère du robot UR5e (en mm).

Méthodes de calibration:
1. Avec ArUco aux coins du plateau
2. Avec points de référence manuels
3. Par apprentissage de positions robot

Le but: quand on détecte une pièce à (x_cm, y_cm) sur le plateau,
        obtenir la position robot (x_mm, y_mm, z_mm) pour l'attraper.
"""

import cv2
import numpy as np
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from pathlib import Path


@dataclass
class CalibrationPoint:
    """Point de calibration avec correspondance plateau/robot."""
    # Position dans le repère plateau (cm, origine au centre)
    board_x_cm: float
    board_y_cm: float

    # Position dans le repère robot (mm)
    robot_x_mm: float
    robot_y_mm: float
    robot_z_mm: float

    # Position pixel (optionnel, pour debug)
    pixel_x: float = 0
    pixel_y: float = 0

    # Label descriptif
    label: str = ""


class PlateauRobotCalibration:
    """
    Gère la calibration entre le repère plateau et le repère robot.
    """

    def __init__(self):
        # Points de calibration collectés
        self.calibration_points: List[CalibrationPoint] = []

        # Transformation calculée
        # P_robot = scale * R @ P_board + offset
        self.rotation_matrix: np.ndarray = np.eye(2)
        self.translation: np.ndarray = np.zeros(2)
        self.scale: float = 10.0  # cm -> mm par défaut
        self.z_offset_mm: float = 0.0

        # Transformation inverse
        self.inv_rotation: np.ndarray = np.eye(2)
        self.inv_translation: np.ndarray = np.zeros(2)

        # Erreur de calibration
        self.calibration_error_mm: float = float('inf')
        self.is_calibrated: bool = False

    def add_calibration_point(self,
                              board_x_cm: float, board_y_cm: float,
                              robot_x_mm: float, robot_y_mm: float, robot_z_mm: float,
                              label: str = "") -> None:
        """Ajoute un point de calibration."""
        self.calibration_points.append(CalibrationPoint(
            board_x_cm=board_x_cm,
            board_y_cm=board_y_cm,
            robot_x_mm=robot_x_mm,
            robot_y_mm=robot_y_mm,
            robot_z_mm=robot_z_mm,
            label=label
        ))
        print(f"📍 Point ajouté: plateau({board_x_cm:.1f}, {board_y_cm:.1f}) -> "
              f"robot({robot_x_mm:.1f}, {robot_y_mm:.1f}, {robot_z_mm:.1f})")

    def compute_calibration(self) -> bool:
        """
        Calcule la transformation à partir des points collectés.

        Nécessite au moins 3 points pour une transformation affine 2D.
        """
        n_points = len(self.calibration_points)

        if n_points < 3:
            print(f"❌ Pas assez de points: {n_points}/3 minimum")
            return False

        # Extraire les coordonnées
        board_pts = np.array([[p.board_x_cm, p.board_y_cm] for p in self.calibration_points])
        robot_pts = np.array([[p.robot_x_mm, p.robot_y_mm] for p in self.calibration_points])

        # Calculer la transformation affine (échelle, rotation, translation)
        # On cherche: P_robot = s * R @ P_board + t

        # Centrer les points
        board_center = board_pts.mean(axis=0)
        robot_center = robot_pts.mean(axis=0)

        board_centered = board_pts - board_center
        robot_centered = robot_pts - robot_center

        # Calculer l'échelle
        board_scale = np.sqrt((board_centered ** 2).sum() / n_points)
        robot_scale = np.sqrt((robot_centered ** 2).sum() / n_points)

        if board_scale < 1e-6:
            print("❌ Points plateau trop rapprochés")
            return False

        self.scale = robot_scale / board_scale

        # Calculer la rotation (SVD)
        board_normalized = board_centered / board_scale
        robot_normalized = robot_centered / robot_scale

        H = board_normalized.T @ robot_normalized
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # S'assurer que R est une rotation (det = 1)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        self.rotation_matrix = R

        # Calculer la translation
        # t = robot_center - scale * R @ board_center
        self.translation = robot_center - self.scale * (R @ board_center)

        # Calculer Z moyen
        z_values = [p.robot_z_mm for p in self.calibration_points]
        self.z_offset_mm = np.mean(z_values)

        # Calculer l'inverse
        self.inv_rotation = R.T
        self.inv_translation = -R.T @ self.translation / self.scale

        # Calculer l'erreur
        self._compute_error()

        self.is_calibrated = True

        print(f"\n✅ Calibration calculée:")
        print(f"   Échelle: {self.scale:.3f} (mm/cm)")
        print(f"   Rotation: {np.degrees(np.arctan2(R[1, 0], R[0, 0])):.1f}°")
        print(f"   Translation: ({self.translation[0]:.1f}, {self.translation[1]:.1f}) mm")
        print(f"   Z moyen: {self.z_offset_mm:.1f} mm")
        print(f"   Erreur RMS: {self.calibration_error_mm:.2f} mm")

        return True

    def _compute_error(self) -> None:
        """Calcule l'erreur de calibration."""
        errors = []

        for pt in self.calibration_points:
            # Prédire la position robot
            predicted = self.board_to_robot(pt.board_x_cm, pt.board_y_cm)

            # Erreur
            dx = predicted[0] - pt.robot_x_mm
            dy = predicted[1] - pt.robot_y_mm
            errors.append(np.sqrt(dx ** 2 + dy ** 2))

        self.calibration_error_mm = np.sqrt(np.mean(np.array(errors) ** 2))

    def board_to_robot(self, x_cm: float, y_cm: float, z_cm: float = 0) -> Tuple[float, float, float]:
        """
        Convertit une position plateau (cm) vers robot (mm).

        Args:
            x_cm, y_cm: Position sur le plateau (origine au centre)
            z_cm: Hauteur au-dessus du plateau (optionnel)

        Returns:
            (x_mm, y_mm, z_mm) dans le repère robot
        """
        board_pt = np.array([x_cm, y_cm])
        robot_pt = self.scale * (self.rotation_matrix @ board_pt) + self.translation

        return float(robot_pt[0]), float(robot_pt[1]), self.z_offset_mm + z_cm * 10

    def robot_to_board(self, x_mm: float, y_mm: float) -> Tuple[float, float]:
        """
        Convertit une position robot (mm) vers plateau (cm).
        """
        robot_pt = np.array([x_mm, y_mm])
        board_pt = self.inv_rotation @ (robot_pt - self.translation) / self.scale

        return float(board_pt[0]), float(board_pt[1])

    def save(self, filepath: str) -> None:
        """Sauvegarde la calibration."""
        data = {
            'calibration_points': [
                {
                    'board_x_cm': p.board_x_cm,
                    'board_y_cm': p.board_y_cm,
                    'robot_x_mm': p.robot_x_mm,
                    'robot_y_mm': p.robot_y_mm,
                    'robot_z_mm': p.robot_z_mm,
                    'label': p.label
                }
                for p in self.calibration_points
            ],
            'rotation_matrix': self.rotation_matrix.tolist(),
            'translation': self.translation.tolist(),
            'scale': self.scale,
            'z_offset_mm': self.z_offset_mm,
            'calibration_error_mm': self.calibration_error_mm,
            'is_calibrated': self.is_calibrated
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Calibration sauvegardée: {filepath}")

    def load(self, filepath: str) -> bool:
        """Charge une calibration."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.calibration_points = [
                CalibrationPoint(**pt) for pt in data['calibration_points']
            ]
            self.rotation_matrix = np.array(data['rotation_matrix'])
            self.translation = np.array(data['translation'])
            self.scale = data['scale']
            self.z_offset_mm = data['z_offset_mm']
            self.calibration_error_mm = data['calibration_error_mm']
            self.is_calibrated = data['is_calibrated']

            # Recalculer l'inverse
            self.inv_rotation = self.rotation_matrix.T
            self.inv_translation = -self.inv_rotation @ self.translation / self.scale

            print(f"✅ Calibration chargée: {filepath}")
            print(f"   {len(self.calibration_points)} points, erreur: {self.calibration_error_mm:.2f} mm")

            return True

        except Exception as e:
            print(f"❌ Erreur chargement: {e}")
            return False


class CalibrationWizard:
    """
    Assistant interactif pour la calibration.
    """

    def __init__(self,
                 vision_system,
                 robot_controller=None):
        """
        Args:
            vision_system: Instance de ChessVisionSystem
            robot_controller: Contrôleur robot (optionnel, pour mode automatique)
        """
        self.vision = vision_system
        self.robot = robot_controller
        self.calibration = PlateauRobotCalibration()

    def calibrate_with_4_corners(self) -> bool:
        """
        Calibration avec les 4 coins du plateau.

        L'utilisateur doit:
        1. Positionner le robot sur chaque coin
        2. Enregistrer la position robot
        """
        print("\n" + "=" * 60)
        print("CALIBRATION AVEC 4 COINS")
        print("=" * 60)

        # Position des coins dans le repère plateau (origine = centre)
        board_size_cm = self.vision.board_config.board_size_cm
        half = board_size_cm / 2

        corners = [
            (-half, -half, "Coin A1 (bas-gauche)"),
            (half, -half, "Coin H1 (bas-droite)"),
            (half, half, "Coin H8 (haut-droite)"),
            (-half, half, "Coin A8 (haut-gauche)"),
        ]

        print(f"\nPositionnez le gripper sur chaque coin du plateau.")
        print(f"Taille plateau: {board_size_cm}x{board_size_cm} cm")
        print(f"Origine: centre du plateau")

        for board_x, board_y, label in corners:
            print(f"\n📍 {label}")
            print(f"   Position plateau: ({board_x:.1f}, {board_y:.1f}) cm")

            if self.robot:
                # Mode automatique: lire la position du robot
                print("   Positionnez le gripper et appuyez sur Entrée...")
                input()

                pos = self.robot.getActualTCPPose()
                robot_x, robot_y, robot_z = pos[0] * 1000, pos[1] * 1000, pos[2] * 1000
                print(f"   Position robot: ({robot_x:.1f}, {robot_y:.1f}, {robot_z:.1f}) mm")
            else:
                # Mode manuel: saisie utilisateur
                print("   Entrez la position robot TCP (en mm):")
                try:
                    robot_x = float(input("   X (mm): "))
                    robot_y = float(input("   Y (mm): "))
                    robot_z = float(input("   Z (mm): "))
                except ValueError:
                    print("   ❌ Valeur invalide, coin ignoré")
                    continue

            self.calibration.add_calibration_point(
                board_x, board_y, robot_x, robot_y, robot_z, label
            )

        return self.calibration.compute_calibration()

    def calibrate_with_aruco_corners(self,
                                     corner_aruco_ids: Dict[int, Tuple[float, float]],
                                     robot_positions: Dict[int, Tuple[float, float, float]]) -> bool:
        """
        Calibration avec des ArUco aux coins.

        Args:
            corner_aruco_ids: Dict[aruco_id, (board_x_cm, board_y_cm)]
            robot_positions: Dict[aruco_id, (robot_x_mm, robot_y_mm, robot_z_mm)]
        """
        for aruco_id, (bx, by) in corner_aruco_ids.items():
            if aruco_id in robot_positions:
                rx, ry, rz = robot_positions[aruco_id]
                self.calibration.add_calibration_point(
                    bx, by, rx, ry, rz, f"ArUco {aruco_id}"
                )

        return self.calibration.compute_calibration()

    def calibrate_interactively(self) -> bool:
        """
        Calibration interactive avec visualisation.
        """
        print("\n" + "=" * 60)
        print("CALIBRATION INTERACTIVE")
        print("=" * 60)
        print("""
Touches:
  C: Ajouter un point de calibration
  R: Calculer la calibration
  T: Tester (afficher erreur)
  S: Sauvegarder
  Q: Quitter
        """)

        while True:
            frame = self.vision.get_frame()
            if frame is None:
                continue

            # Afficher les pièces détectées
            self.vision.detect_pieces(frame)
            display = self.vision.draw_overlay(frame)

            # Afficher les points de calibration
            for i, pt in enumerate(self.calibration.calibration_points):
                text = f"P{i}: ({pt.board_x_cm:.0f},{pt.board_y_cm:.0f})->({pt.robot_x_mm:.0f},{pt.robot_y_mm:.0f})"
                cv2.putText(display, text, (10, 40 + i * 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            cv2.imshow("Calibration", display)
            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                break

            elif key == ord('c'):
                # Ajouter un point
                print("\n--- Nouveau point de calibration ---")
                try:
                    bx = float(input("Position plateau X (cm): "))
                    by = float(input("Position plateau Y (cm): "))
                    rx = float(input("Position robot X (mm): "))
                    ry = float(input("Position robot Y (mm): "))
                    rz = float(input("Position robot Z (mm): "))

                    self.calibration.add_calibration_point(bx, by, rx, ry, rz)
                except ValueError:
                    print("Valeur invalide")

            elif key == ord('r'):
                # Calculer
                self.calibration.compute_calibration()

            elif key == ord('t'):
                # Tester
                if self.calibration.is_calibrated:
                    print("\n--- Test de transformation ---")
                    try:
                        bx = float(input("Position plateau X (cm): "))
                        by = float(input("Position plateau Y (cm): "))
                        rx, ry, rz = self.calibration.board_to_robot(bx, by)
                        print(f"Position robot: ({rx:.1f}, {ry:.1f}, {rz:.1f}) mm")
                    except ValueError:
                        print("Valeur invalide")

            elif key == ord('s'):
                self.calibration.save("calibration_robot.json")

        cv2.destroyAllWindows()
        return self.calibration.is_calibrated


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def quick_calibration_from_single_point(
        board_x_cm: float, board_y_cm: float,
        robot_x_mm: float, robot_y_mm: float, robot_z_mm: float,
        rotation_deg: float = 0.0
) -> PlateauRobotCalibration:
    """
    Crée une calibration rapide à partir d'un seul point connu.

    Utile pour une première estimation avant calibration précise.

    Args:
        board_x_cm, board_y_cm: Point de référence sur le plateau
        robot_x_mm, robot_y_mm, robot_z_mm: Même point dans le repère robot
        rotation_deg: Rotation estimée entre les repères
    """
    calib = PlateauRobotCalibration()

    # Rotation
    angle_rad = np.radians(rotation_deg)
    calib.rotation_matrix = np.array([
        [np.cos(angle_rad), -np.sin(angle_rad)],
        [np.sin(angle_rad), np.cos(angle_rad)]
    ])

    # Échelle (cm -> mm)
    calib.scale = 10.0

    # Translation: t = P_robot - scale * R @ P_board
    board_pt = np.array([board_x_cm, board_y_cm])
    robot_pt = np.array([robot_x_mm, robot_y_mm])
    calib.translation = robot_pt - calib.scale * (calib.rotation_matrix @ board_pt)

    calib.z_offset_mm = robot_z_mm
    calib.is_calibrated = True

    # Inverse
    calib.inv_rotation = calib.rotation_matrix.T
    calib.inv_translation = -calib.inv_rotation @ calib.translation / calib.scale

    print(f"✅ Calibration rapide créée:")
    print(f"   Point: plateau({board_x_cm}, {board_y_cm}) = robot({robot_x_mm}, {robot_y_mm})")
    print(f"   Rotation: {rotation_deg}°")

    return calib


def test_calibration():
    """Test de la calibration."""
    print("=== Test Calibration ===\n")

    # Créer une calibration avec 4 points simulés
    calib = PlateauRobotCalibration()

    # Simuler un plateau centré sur robot (300, 400) mm
    # avec une rotation de 0° et échelle 10

    # Coins du plateau (20cm = 200mm de côté)
    test_points = [
        (-10, -10, 200, 300, 50),  # Coin bas-gauche
        (10, -10, 400, 300, 50),  # Coin bas-droite
        (10, 10, 400, 500, 50),  # Coin haut-droite
        (-10, 10, 200, 500, 50),  # Coin haut-gauche
    ]

    for bx, by, rx, ry, rz in test_points:
        calib.add_calibration_point(bx, by, rx, ry, rz)

    calib.compute_calibration()

    # Tester
    print("\nTests de conversion:")
    test_cases = [
        (0, 0, "Centre"),
        (-10, -10, "A1"),
        (10, 10, "H8"),
        (5, -5, "F3"),
    ]

    for bx, by, label in test_cases:
        rx, ry, rz = calib.board_to_robot(bx, by)
        print(f"  {label}: plateau({bx}, {by}) -> robot({rx:.1f}, {ry:.1f}, {rz:.1f})")


if __name__ == "__main__":
    test_calibration()