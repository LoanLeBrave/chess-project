#!/usr/bin/env python3
"""
Calibration Automatique Robot-Plateau
=====================================
Ce module permet au robot de se calibrer automatiquement sans intervention humaine.

Principe:
1. Un ArUco est fixé sur le gripper du robot (ID 50)
2. La caméra sous le plateau voit cet ArUco
3. Le robot bouge et la caméra détecte sa position
4. En comparant position robot (RTDE) et position caméra (ArUco), on calcule la transformation

Processus:
1. Si l'ArUco robot n'est pas visible, le robot fait une recherche en spirale
2. Une fois trouvé, le robot va sur plusieurs points connus
3. À chaque point, on enregistre (position_robot, position_camera)
4. On calcule la transformation plateau → robot
"""

import cv2
import numpy as np
import time
import json
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

# Import du système de vision
from chess_vision_system import ChessVisionSystem, PICAMERA2_AVAILABLE


@dataclass
class CalibrationConfig:
    """Configuration pour la calibration automatique."""
    # ID de l'ArUco sur le robot
    robot_aruco_id: int = 50

    # IDs des ArUco aux coins du plateau
    corner_aruco_ids: Tuple[int, ...] = (32, 33, 34, 35)

    # Taille du plateau en cm
    board_size_cm: float = 28.0

    # Zone de recherche (mm) - autour de la position initiale
    search_range_mm: float = 200.0

    # Pas de recherche (mm) - 2cm = 20mm
    search_step_mm: float = 20.0

    # Vitesse de déplacement pour la recherche (m/s)
    search_speed: float = 0.1

    # Vitesse de déplacement pour la calibration (m/s)
    calibration_speed: float = 0.05


class AutoCalibration:
    """
    Système de calibration automatique.
    Le robot trouve son ArUco et se calibre sans intervention humaine.
    """

    def __init__(self,
                 robot_ip: str = "192.168.0.11",
                 camera_index: int = 0,
                 config: CalibrationConfig = None):

        self.robot_ip = robot_ip
        self.camera_index = camera_index
        self.config = config or CalibrationConfig()

        # Vision
        self.vision: Optional[ChessVisionSystem] = None

        # Robot RTDE
        self.rtde_control = None
        self.rtde_receive = None

        # Points de calibration collectés
        self.calibration_points: List[Dict] = []

        # Transformation calculée
        self.transform_matrix: Optional[np.ndarray] = None
        self.is_calibrated: bool = False

    def connect(self) -> bool:
        """Connecte à la caméra et au robot."""
        print("\n" + "=" * 60)
        print("CONNEXION POUR CALIBRATION AUTOMATIQUE")
        print("=" * 60)

        # 1. Vision
        print("\n[1/2] Connexion caméra...")
        self.vision = ChessVisionSystem(camera_index=self.camera_index)
        if not self.vision.connect_camera():
            print("❌ Échec connexion caméra")
            return False

        # Calibrer la caméra avec les coins du plateau
        print("\n📐 Calibration caméra (pixels → cm)...")
        for attempt in range(5):
            frame = self.vision.get_frame()
            if frame is not None and self.vision.auto_calibrate_from_corners(frame):
                print("✅ Calibration caméra OK")
                break
            time.sleep(0.5)
        else:
            print("⚠️ Calibration caméra échouée - les 4 coins ne sont pas visibles")
            print("   Vérifiez que les ArUco 32, 33, 34, 35 sont visibles")
            return False

        # 2. Robot RTDE
        print("\n[2/2] Connexion robot RTDE...")
        try:
            import rtde_control
            import rtde_receive

            self.rtde_control = rtde_control.RTDEControlInterface(self.robot_ip)
            self.rtde_receive = rtde_receive.RTDEReceiveInterface(self.robot_ip)
            print(f"✅ Robot connecté: {self.robot_ip}")
        except ImportError:
            print("❌ Modules RTDE non installés")
            print("   pip install rtde-control rtde-receive")
            return False
        except Exception as e:
            print(f"❌ Erreur connexion robot: {e}")
            return False

        print("\n✅ Système prêt pour calibration automatique!")
        return True

    def disconnect(self):
        """Déconnecte tout."""
        if self.vision:
            self.vision.disconnect_camera()
        if self.rtde_control:
            self.rtde_control.stopScript()
        print("🔌 Déconnecté")

    def get_robot_tcp(self) -> Tuple[float, float, float]:
        """Retourne la position TCP actuelle (mm)."""
        pose = self.rtde_receive.getActualTCPPose()
        return (pose[0] * 1000, pose[1] * 1000, pose[2] * 1000)

    def move_robot(self, x_mm: float, y_mm: float, z_mm: float,
                   speed: float = 0.1) -> bool:
        """Déplace le robot vers une position."""
        current_pose = self.rtde_receive.getActualTCPPose()
        target_pose = [
            x_mm / 1000,  # mm → m
            y_mm / 1000,
            z_mm / 1000,
            current_pose[3],  # Garder l'orientation
            current_pose[4],
            current_pose[5]
        ]
        return self.rtde_control.moveL(target_pose, speed, 0.3)

    def detect_robot_aruco(self) -> Optional[Tuple[float, float]]:
        """
        Détecte l'ArUco du robot et retourne sa position en cm.

        Returns:
            (x_cm, y_cm) ou None si non détecté
        """
        frame = self.vision.get_frame()
        if frame is None:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.vision.detector.detectMarkers(gray)

        if ids is None:
            return None

        ids = ids.flatten()
        idx = np.where(ids == self.config.robot_aruco_id)[0]

        if len(idx) == 0:
            return None

        # Centre du marqueur en pixels
        center_px = corners[idx[0]][0].mean(axis=0)

        # Convertir en cm
        x_cm, y_cm = self.vision.pixel_to_cm(center_px[0], center_px[1])

        return (x_cm, y_cm)

    def search_robot_aruco(self) -> bool:
        """
        Recherche l'ArUco du robot en déplaçant le bras en spirale.
        Part de la position ACTUELLE du robot et fait des pas de 2cm.

        Returns:
            True si trouvé
        """
        print("\n🔍 Recherche de l'ArUco robot (ID {})...".format(self.config.robot_aruco_id))

        # Vérifier d'abord si déjà visible
        pos = self.detect_robot_aruco()
        if pos is not None:
            print(f"✅ ArUco robot trouvé immédiatement à ({pos[0]:.1f}, {pos[1]:.1f}) cm")
            return True

        # Position INITIALE du robot (point de départ)
        initial_pos = self.get_robot_tcp()
        start_x = initial_pos[0]
        start_y = initial_pos[1]
        z = initial_pos[2]  # Garder la même hauteur Z

        print(f"   Position initiale du robot: ({start_x:.1f}, {start_y:.1f}, {z:.1f}) mm")
        print(f"   Recherche avec pas de {self.config.search_step_mm} mm (2 cm)")

        # Recherche en spirale carrée (plus simple et progressif)
        step = self.config.search_step_mm  # 20mm = 2cm
        max_range = self.config.search_range_mm

        # Générer les points en spirale carrée progressive
        # Partant du centre, on fait des carrés de plus en plus grands
        spiral_points = []

        # Direction: droite, haut, gauche, bas
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]

        x, y = 0, 0  # Position relative au point de départ
        spiral_points.append((start_x, start_y))

        layer = 1
        while layer * step <= max_range:
            # Pour chaque couche de la spirale
            for dir_idx, (dx, dy) in enumerate(directions):
                # Nombre de pas dans cette direction
                steps_in_dir = layer if dir_idx < 2 else layer
                if dir_idx >= 2:
                    steps_in_dir = layer + 1

                for _ in range(layer):
                    x += dx * step
                    y += dy * step

                    # Vérifier qu'on ne dépasse pas la zone
                    if abs(x) <= max_range and abs(y) <= max_range:
                        spiral_points.append((start_x + x, start_y + y))

            layer += 1

        # Simplifier: utiliser une vraie spirale carrée
        spiral_points = []
        for ring in range(1, int(max_range / step) + 1):
            offset = ring * step

            # Côté droit (de bas en haut)
            for i in range(-ring, ring + 1):
                spiral_points.append((start_x + offset, start_y + i * step))

            # Côté haut (de droite à gauche)
            for i in range(ring - 1, -ring - 1, -1):
                spiral_points.append((start_x + i * step, start_y + offset))

            # Côté gauche (de haut en bas)
            for i in range(ring - 1, -ring - 1, -1):
                spiral_points.append((start_x - offset, start_y + i * step))

            # Côté bas (de gauche à droite)
            for i in range(-ring + 1, ring + 1):
                spiral_points.append((start_x + i * step, start_y - offset))

        print(f"   Recherche progressive: {len(spiral_points)} positions (spirale carrée)")

        for i, (x, y) in enumerate(spiral_points):
            # Déplacer le robot progressivement
            print(f"   [{i + 1}/{len(spiral_points)}] Déplacement vers ({x:.0f}, {y:.0f}) mm...", end=" ")

            self.move_robot(x, y, z, self.config.search_speed)
            time.sleep(0.3)  # Attendre la stabilisation

            # Vérifier si l'ArUco est visible
            pos = self.detect_robot_aruco()
            if pos is not None:
                print(f"TROUVÉ!")
                print(f"✅ ArUco robot trouvé!")
                print(f"   Position caméra: ({pos[0]:.1f}, {pos[1]:.1f}) cm")
                print(f"   Position robot: ({x:.0f}, {y:.0f}, {z:.0f}) mm")
                return True
            else:
                print("non visible")

        print("❌ ArUco robot non trouvé après recherche complète")

        # Retourner à la position initiale
        print("   Retour à la position initiale...")
        self.move_robot(start_x, start_y, z, self.config.search_speed)

        return False

    def collect_calibration_point(self) -> bool:
        """
        Collecte un point de calibration à la position actuelle.

        Returns:
            True si réussi
        """
        # Position robot
        robot_pos = self.get_robot_tcp()

        # Position caméra (plusieurs mesures pour moyenne)
        camera_positions = []
        for _ in range(5):
            pos = self.detect_robot_aruco()
            if pos is not None:
                camera_positions.append(pos)
            time.sleep(0.1)

        if len(camera_positions) < 3:
            print("⚠️ ArUco robot pas assez stable")
            return False

        # Moyenne des positions caméra
        avg_x = np.mean([p[0] for p in camera_positions])
        avg_y = np.mean([p[1] for p in camera_positions])

        point = {
            'robot_x_mm': robot_pos[0],
            'robot_y_mm': robot_pos[1],
            'robot_z_mm': robot_pos[2],
            'camera_x_cm': avg_x,
            'camera_y_cm': avg_y,
        }

        self.calibration_points.append(point)
        print(f"   📍 Point {len(self.calibration_points)}: "
              f"robot({robot_pos[0]:.1f}, {robot_pos[1]:.1f}) mm → "
              f"caméra({avg_x:.1f}, {avg_y:.1f}) cm")

        return True

    def collect_calibration_points(self, n_points: int = 9) -> bool:
        """
        Collecte plusieurs points de calibration en déplaçant le robot.
        Utilise des pas de 2cm (20mm) à partir de la position actuelle.

        Args:
            n_points: Nombre de points à collecter (grille 3x3 par défaut)
        """
        print(f"\n📐 Collecte de {n_points} points de calibration...")

        # D'abord, trouver l'ArUco robot
        if not self.search_robot_aruco():
            return False

        # Position actuelle (là où l'ArUco a été trouvé)
        current_pos = self.get_robot_tcp()
        center_x = current_pos[0]
        center_y = current_pos[1]
        z = current_pos[2]  # Garder la même hauteur Z

        print(f"   Position de référence: ({center_x:.1f}, {center_y:.1f}, {z:.1f}) mm")

        # Définir une grille de points avec pas de 2cm (20mm)
        grid_size = int(np.sqrt(n_points))
        step = 20.0  # 2cm = 20mm

        # Grille centrée sur la position actuelle
        points_to_visit = []
        half_grid = (grid_size - 1) / 2

        for i in range(grid_size):
            for j in range(grid_size):
                x = center_x + (i - half_grid) * step
                y = center_y + (j - half_grid) * step
                points_to_visit.append((x, y))

        print(f"   Grille {grid_size}x{grid_size} avec pas de 2cm")
        print(f"   Zone couverte: {(grid_size - 1) * step:.0f} x {(grid_size - 1) * step:.0f} mm")

        self.calibration_points = []

        for i, (x, y) in enumerate(points_to_visit):
            print(f"\n   Point {i + 1}/{len(points_to_visit)}: ({x:.0f}, {y:.0f}) mm")

            # Déplacer le robot progressivement (2cm)
            self.move_robot(x, y, z, self.config.calibration_speed)
            time.sleep(0.5)  # Attendre la stabilisation

            # Collecter le point
            if not self.collect_calibration_point():
                print(f"   ⚠️ ArUco non visible au point {i + 1}, on continue...")
                continue

        print(f"\n✅ {len(self.calibration_points)} points collectés sur {len(points_to_visit)}")
        return len(self.calibration_points) >= 4

    def compute_transformation(self) -> bool:
        """
        Calcule la transformation caméra → robot.

        La transformation: P_robot = scale * R @ P_camera + T
        """
        if len(self.calibration_points) < 4:
            print("❌ Pas assez de points de calibration")
            return False

        print("\n🧮 Calcul de la transformation...")

        # Extraire les points
        camera_pts = np.array([
            [p['camera_x_cm'], p['camera_y_cm']]
            for p in self.calibration_points
        ])
        robot_pts = np.array([
            [p['robot_x_mm'], p['robot_y_mm']]
            for p in self.calibration_points
        ])

        # Calculer la transformation affine
        # On utilise cv2.estimateAffine2D pour robustesse
        transform, inliers = cv2.estimateAffine2D(
            camera_pts.reshape(-1, 1, 2).astype(np.float32),
            robot_pts.reshape(-1, 1, 2).astype(np.float32)
        )

        if transform is None:
            print("❌ Échec du calcul de transformation")
            return False

        # Convertir en matrice 3x3
        self.transform_matrix = np.vstack([transform, [0, 0, 1]])

        # Extraire les paramètres pour affichage
        scale_x = np.sqrt(transform[0, 0] ** 2 + transform[0, 1] ** 2)
        scale_y = np.sqrt(transform[1, 0] ** 2 + transform[1, 1] ** 2)
        rotation = np.arctan2(transform[1, 0], transform[0, 0])

        # Calculer l'erreur
        errors = []
        for p in self.calibration_points:
            camera_pt = np.array([p['camera_x_cm'], p['camera_y_cm'], 1])
            predicted_robot = self.transform_matrix @ camera_pt
            actual_robot = np.array([p['robot_x_mm'], p['robot_y_mm']])
            error = np.linalg.norm(predicted_robot[:2] - actual_robot)
            errors.append(error)

        rms_error = np.sqrt(np.mean(np.array(errors) ** 2))
        max_error = max(errors)

        print(f"\n✅ Transformation calculée:")
        print(f"   Échelle X: {scale_x:.3f} (mm/cm, attendu ~10)")
        print(f"   Échelle Y: {scale_y:.3f} (mm/cm, attendu ~10)")
        print(f"   Rotation: {np.degrees(rotation):.1f}°")
        print(f"   Translation: ({transform[0, 2]:.1f}, {transform[1, 2]:.1f}) mm")
        print(f"   Erreur RMS: {rms_error:.2f} mm")
        print(f"   Erreur max: {max_error:.2f} mm")

        # Stocker la hauteur Z moyenne
        self.z_offset_mm = np.mean([p['robot_z_mm'] for p in self.calibration_points])

        self.is_calibrated = True
        return True

    def camera_to_robot(self, x_cm: float, y_cm: float, z_cm: float = 0) -> Tuple[float, float, float]:
        """
        Convertit des coordonnées caméra/plateau (cm) vers robot (mm).
        """
        if not self.is_calibrated:
            raise ValueError("Calibration non effectuée!")

        pt = np.array([x_cm, y_cm, 1])
        robot_pt = self.transform_matrix @ pt

        return (robot_pt[0], robot_pt[1], self.z_offset_mm + z_cm * 10)

    def save_calibration(self, filepath: str = "auto_calibration.json"):
        """Sauvegarde la calibration."""
        data = {
            'transform_matrix': self.transform_matrix.tolist(),
            'z_offset_mm': self.z_offset_mm,
            'calibration_points': self.calibration_points,
            'config': {
                'robot_aruco_id': self.config.robot_aruco_id,
                'board_size_cm': self.config.board_size_cm,
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Calibration sauvegardée: {filepath}")

    def load_calibration(self, filepath: str = "auto_calibration.json") -> bool:
        """Charge une calibration existante."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.transform_matrix = np.array(data['transform_matrix'])
            self.z_offset_mm = data['z_offset_mm']
            self.calibration_points = data['calibration_points']
            self.is_calibrated = True

            print(f"✅ Calibration chargée: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Erreur chargement: {e}")
            return False

    def run_full_calibration(self) -> bool:
        """
        Exécute la calibration automatique complète.

        Returns:
            True si calibration réussie
        """
        print("\n" + "=" * 60)
        print("CALIBRATION AUTOMATIQUE")
        print("=" * 60)
        print(f"""
Configuration:
  - ArUco robot: ID {self.config.robot_aruco_id}
  - ArUco coins: {self.config.corner_aruco_ids}
  - Plateau: {self.config.board_size_cm}x{self.config.board_size_cm} cm
  - Zone de recherche: ±{self.config.search_range_mm} mm
        """)

        # Étape 1: Trouver l'ArUco robot
        print("\n[Étape 1/3] Recherche de l'ArUco robot...")
        if not self.search_robot_aruco():
            print("❌ Calibration échouée: ArUco robot non trouvé")
            return False

        # Étape 2: Collecter les points
        print("\n[Étape 2/3] Collecte des points de calibration...")
        if not self.collect_calibration_points(n_points=9):
            print("❌ Calibration échouée: pas assez de points")
            return False

        # Étape 3: Calculer la transformation
        print("\n[Étape 3/3] Calcul de la transformation...")
        if not self.compute_transformation():
            print("❌ Calibration échouée: erreur de calcul")
            return False

        # Sauvegarder
        self.save_calibration()

        print("\n" + "=" * 60)
        print("✅ CALIBRATION AUTOMATIQUE TERMINÉE!")
        print("=" * 60)

        return True


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Calibration automatique robot-plateau")
    parser.add_argument("--robot", default="192.168.0.11", help="IP du robot UR5e")
    parser.add_argument("--camera", type=int, default=0, help="Index caméra")
    parser.add_argument("--aruco-id", type=int, default=50, help="ID ArUco sur le robot")
    parser.add_argument("--search-range", type=float, default=200, help="Zone de recherche en mm")
    parser.add_argument("--step", type=float, default=20, help="Pas de recherche en mm (défaut: 20 = 2cm)")

    args = parser.parse_args()

    # Configuration
    config = CalibrationConfig(
        robot_aruco_id=args.aruco_id,
        search_range_mm=args.search_range,
        search_step_mm=args.step,
    )

    print("\n" + "=" * 60)
    print("CALIBRATION AUTOMATIQUE ROBOT-PLATEAU")
    print("=" * 60)
    print(f"""
⚠️  IMPORTANT: Positionnez le robot manuellement AU-DESSUS du plateau
    avant de lancer ce script. Le robot va chercher l'ArUco à partir
    de sa position ACTUELLE avec des pas de {args.step}mm ({args.step / 10}cm).

Configuration:
  - ArUco robot: ID {args.aruco_id}
  - Pas de recherche: {args.step} mm ({args.step / 10} cm)
  - Zone de recherche: ±{args.search_range} mm
    """)

    input("Appuyez sur Entrée quand le robot est en position...")

    # Calibration
    calib = AutoCalibration(
        robot_ip=args.robot,
        camera_index=args.camera,
        config=config
    )

    if not calib.connect():
        return

    try:
        calib.run_full_calibration()
    except KeyboardInterrupt:
        print("\n⏹️ Calibration interrompue")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        calib.disconnect()


if __name__ == "__main__":
    main()