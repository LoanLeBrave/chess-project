"""
PARTIE 1 : CALIBRATION VISUELLE AVEC ARUCO
Ce script compare la position actuelle du robot avec l'image de référence
et envoie des commandes de déplacement jusqu'à atteindre la position exacte.
"""

import cv2
import numpy as np
import json
import time
from pathlib import Path
from typing import Tuple, Optional, Dict
from dataclasses import dataclass

# Imports RTDE
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    from ur_rtde.rtde_control import RTDEControlInterface
    from ur_rtde.rtde_receive import RTDEReceiveInterface


@dataclass
class ArucoPosition:
    """Position d'un marqueur ArUco détecté."""
    detected: bool
    center_x: float = 0.0
    center_y: float = 0.0
    angle: float = 0.0
    corners: Optional[np.ndarray] = None


class ArucoVisualCalibrator:
    """
    Gère la détection ArUco et compare avec l'image de référence.
    Envoie des commandes au robot pour l'aligner.
    """
    
    def __init__(
        self,
        robot_ip: str,
        camera_index: int = 0,
        aruco_id: int = 0,
        reference_image_path: str = "reference_calibration.jpg",
        tolerance_pixels: int = 5,
        pixel_to_meter_ratio: float = 0.0001
    ):
        """
        Initialise le calibrateur visuel.
        
        Args:
            robot_ip: Adresse IP du robot
            camera_index: Index de la caméra
            aruco_id: ID du marqueur ArUco sur la pince
            reference_image_path: Chemin de l'image de référence
            tolerance_pixels: Tolérance d'alignement en pixels
            pixel_to_meter_ratio: Ratio de conversion pixels → mètres
        """
        self.robot_ip = robot_ip
        self.camera_index = camera_index
        self.aruco_id = aruco_id
        self.reference_path = Path(reference_image_path)
        self.tolerance_pixels = tolerance_pixels
        self.pixel_to_meter = pixel_to_meter_ratio
        
        # Connexion robot
        print(f"🤖 Connexion au robot {robot_ip}...")
        self.rtde_c = RTDEControlInterface(robot_ip)
        self.rtde_r = RTDEReceiveInterface(robot_ip)
        print("✅ Robot connecté")
        
        # Configuration ArUco
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # Caméra
        self.cap = None
        
        # Position de référence
        self.reference_position: Optional[Tuple[float, float]] = None
        self.reference_angle: Optional[float] = None
        
    def start_camera(self) -> bool:
        """Démarre la caméra."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"❌ Impossible d'ouvrir la caméra {self.camera_index}")
            return False
        
        # Configuration haute résolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        
        print(f"✅ Caméra {self.camera_index} démarrée")
        return True
    
    def stop_camera(self):
        """Arrête la caméra."""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
    
    def detect_aruco_in_frame(self, frame: np.ndarray) -> ArucoPosition:
        """
        Détecte le marqueur ArUco dans une image.
        
        Args:
            frame: Image OpenCV (BGR)
            
        Returns:
            Position du marqueur détecté
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        if ids is None or self.aruco_id not in ids:
            return ArucoPosition(detected=False)
        
        # Trouver le marqueur recherché
        idx = np.where(ids == self.aruco_id)[0][0]
        marker_corners = corners[idx][0]
        
        # Calculer le centre
        center_x = np.mean(marker_corners[:, 0])
        center_y = np.mean(marker_corners[:, 1])
        
        # Calculer l'angle
        top_left = marker_corners[0]
        top_right = marker_corners[1]
        angle = np.degrees(np.arctan2(
            top_right[1] - top_left[1],
            top_right[0] - top_left[0]
        ))
        
        return ArucoPosition(
            detected=True,
            center_x=center_x,
            center_y=center_y,
            angle=angle,
            corners=marker_corners
        )
    
    def capture_reference_image(self) -> bool:
        """
        Capture l'image de référence à la position (0,0) du plateau.
        """
        if not self.start_camera():
            return False
        
        print("\n" + "="*60)
        print("📸 CAPTURE DE L'IMAGE DE RÉFÉRENCE")
        print("="*60)
        print("1. Positionne le robot EXACTEMENT au centre du plateau (0,0)")
        print("2. Le QR code ArUco doit être bien visible par la caméra")
        print("3. Appuie sur Entrée quand c'est prêt...")
        input()
        
        # Capturer plusieurs frames pour stabilité
        print("Capture en cours...")
        time.sleep(0.5)
        
        frames = []
        for _ in range(5):
            ret, frame = self.cap.read()
            if ret:
                frames.append(frame)
            time.sleep(0.1)
        
        if not frames:
            print("❌ Échec de capture")
            self.stop_camera()
            return False
        
        # Utiliser la frame du milieu
        frame = frames[len(frames)//2]
        
        # Détecter l'ArUco
        position = self.detect_aruco_in_frame(frame)
        
        if not position.detected:
            print(f"❌ Marqueur ArUco ID {self.aruco_id} non détecté !")
            print("Vérifie que :")
            print("  - Le QR code est visible dans le champ de la caméra")
            print("  - L'éclairage est suffisant")
            print("  - Le bon ID ArUco est configuré")
            self.stop_camera()
            return False
        
        # Sauvegarder la position de référence
        self.reference_position = (position.center_x, position.center_y)
        self.reference_angle = position.angle
        
        # Annoter l'image
        annotated_frame = frame.copy()
        cv2.aruco.drawDetectedMarkers(annotated_frame, [position.corners.reshape(1, 4, 2)])
        cv2.circle(annotated_frame, (int(position.center_x), int(position.center_y)), 
                   15, (0, 255, 0), -1)
        
        # Ajouter texte
        cv2.putText(annotated_frame, "REFERENCE POSITION (0,0)", 
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        cv2.putText(annotated_frame, f"Center: ({position.center_x:.1f}, {position.center_y:.1f})", 
                    (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(annotated_frame, f"Angle: {position.angle:.2f}°", 
                    (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Sauvegarder l'image
        cv2.imwrite(str(self.reference_path), annotated_frame)
        
        # Sauvegarder les métadonnées
        metadata = {
            'center_x': float(position.center_x),
            'center_y': float(position.center_y),
            'angle': float(position.angle),
            'aruco_id': self.aruco_id,
            'timestamp': time.time(),
            'robot_pose': self.rtde_r.getActualTCPPose()
        }
        
        metadata_path = self.reference_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        print("\n✅ IMAGE DE RÉFÉRENCE CAPTURÉE AVEC SUCCÈS !")
        print(f"   Fichier image : {self.reference_path}")
        print(f"   Métadonnées   : {metadata_path}")
        print(f"   Position      : ({position.center_x:.1f}, {position.center_y:.1f})")
        print(f"   Angle         : {position.angle:.2f}°")
        
        self.stop_camera()
        return True
    
    def load_reference_position(self) -> bool:
        """Charge la position de référence depuis les métadonnées."""
        metadata_path = self.reference_path.with_suffix('.json')
        
        if not metadata_path.exists():
            print(f"⚠️ Aucune référence trouvée : {metadata_path}")
            return False
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            self.reference_position = (metadata['center_x'], metadata['center_y'])
            self.reference_angle = metadata['angle']
            
            print("✅ Position de référence chargée :")
            print(f"   Position : ({self.reference_position[0]:.1f}, {self.reference_position[1]:.1f})")
            print(f"   Angle    : {self.reference_angle:.2f}°")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement : {e}")
            return False
    
    def calculate_movement(self, current: ArucoPosition) -> Tuple[float, float, float]:
        """
        Calcule le mouvement nécessaire pour atteindre la référence.
        
        Args:
            current: Position actuelle du marqueur
            
        Returns:
            (delta_x, delta_y, distance) en mètres et pixels
        """
        if not self.reference_position:
            raise RuntimeError("Position de référence non définie")
        
        # Offset en pixels
        offset_x_px = self.reference_position[0] - current.center_x
        offset_y_px = self.reference_position[1] - current.center_y
        
        # Distance totale
        distance_px = np.sqrt(offset_x_px**2 + offset_y_px**2)
        
        # Conversion en mètres (déplacement robot)
        delta_x_m = offset_x_px * self.pixel_to_meter
        delta_y_m = offset_y_px * self.pixel_to_meter
        
        return delta_x_m, delta_y_m, distance_px
    
    def move_robot_relative(self, dx: float, dy: float, speed: float = 0.05):
        """
        Déplace le robot de manière relative.
        
        Args:
            dx, dy: Déplacement en mètres (X, Y)
            speed: Vitesse de déplacement
        """
        # Obtenir la pose actuelle
        current_pose = self.rtde_r.getActualTCPPose()
        
        # Nouvelle pose
        new_pose = current_pose.copy()
        new_pose[0] += dx
        new_pose[1] += dy
        
        # Limiter les mouvements pour la sécurité
        MAX_MOVE = 0.01  # 1 cm max par mouvement
        if abs(dx) > MAX_MOVE or abs(dy) > MAX_MOVE:
            print(f"⚠️ Mouvement trop grand : ({dx:.4f}, {dy:.4f}) m")
            return False
        
        # Déplacer
        self.rtde_c.moveL(new_pose, speed=speed, acceleration=0.3)
        return True
    
    def auto_align_to_reference(
        self, 
        max_iterations: int = 50,
        show_video: bool = True
    ) -> bool:
        """
        Aligne automatiquement le robot avec la position de référence.
        
        Args:
            max_iterations: Nombre maximum d'itérations
            show_video: Afficher le flux vidéo avec annotations
            
        Returns:
            True si l'alignement a réussi
        """
        if not self.load_reference_position():
            print("❌ Charge d'abord une image de référence !")
            return False
        
        if not self.start_camera():
            return False
        
        print("\n" + "="*60)
        print("🎯 ALIGNEMENT AUTOMATIQUE EN COURS")
        print("="*60)
        print(f"Tolérance : {self.tolerance_pixels} pixels")
        print(f"Max itérations : {max_iterations}")
        print("Appuie sur 'q' pour arrêter")
        print()
        
        iteration = 0
        aligned = False
        
        try:
            while iteration < max_iterations:
                # Capturer une frame
                ret, frame = self.cap.read()
                if not ret:
                    print("❌ Erreur de capture")
                    break
                
                # Détecter l'ArUco
                current = self.detect_aruco_in_frame(frame)
                
                if not current.detected:
                    print(f"⚠️ [{iteration}] ArUco non détecté - attente...")
                    time.sleep(0.2)
                    iteration += 1
                    continue
                
                # Calculer le mouvement nécessaire
                dx, dy, distance = self.calculate_movement(current)
                
                # Vérifier si aligné
                if distance <= self.tolerance_pixels:
                    print(f"\n✅ ALIGNEMENT RÉUSSI ! (distance: {distance:.2f} px)")
                    aligned = True
                    break
                
                print(f"[{iteration:02d}] Distance: {distance:3.1f}px | "
                      f"Mouvement: X={dx*1000:+5.2f}mm, Y={dy*1000:+5.2f}mm")
                
                # Déplacer le robot
                if not self.move_robot_relative(dx, dy, speed=0.03):
                    print("❌ Mouvement annulé (trop grand)")
                    break
                
                # Attendre stabilisation
                time.sleep(0.3)
                
                # Afficher le flux vidéo
                if show_video:
                    annotated = self._annotate_frame(frame, current, distance)
                    cv2.imshow("Alignement Automatique", annotated)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("\n⚠️ Arrêt demandé par l'utilisateur")
                        break
                
                iteration += 1
            
            if not aligned and iteration >= max_iterations:
                print(f"\n❌ Échec : Maximum d'itérations atteint ({max_iterations})")
            
            return aligned
            
        finally:
            self.stop_camera()
    
    def _annotate_frame(
        self, 
        frame: np.ndarray, 
        current: ArucoPosition, 
        distance: float
    ) -> np.ndarray:
        """Ajoute des annotations visuelles sur l'image."""
        annotated = frame.copy()
        
        if current.detected:
            # Dessiner le marqueur
            cv2.aruco.drawDetectedMarkers(annotated, [current.corners.reshape(1, 4, 2)])
            
            # Position actuelle (vert)
            cv2.circle(annotated, (int(current.center_x), int(current.center_y)), 
                      12, (0, 255, 0), -1)
            
            # Position de référence (rouge)
            if self.reference_position:
                ref_x, ref_y = self.reference_position
                cv2.circle(annotated, (int(ref_x), int(ref_y)), 15, (0, 0, 255), 3)
                
                # Ligne de connexion
                cv2.line(annotated, 
                        (int(current.center_x), int(current.center_y)),
                        (int(ref_x), int(ref_y)),
                        (255, 0, 255), 2)
            
            # Informations textuelles
            status = "ALIGNÉ ✓" if distance <= self.tolerance_pixels else "NON ALIGNÉ"
            status_color = (0, 255, 0) if distance <= self.tolerance_pixels else (0, 0, 255)
            
            cv2.putText(annotated, status, (20, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, status_color, 3)
            cv2.putText(annotated, f"Distance: {distance:.1f} px", (20, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(annotated, f"Tolerance: {self.tolerance_pixels} px", (20, 140),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return annotated
    
    def get_calibrated_pose(self) -> Dict:
        """
        Récupère la pose du robot une fois aligné.
        À appeler après un alignement réussi.
        
        Returns:
            Dictionnaire avec la pose calibrée
        """
        pose = self.rtde_r.getActualTCPPose()
        
        calibration_data = {
            'x0': pose[0],
            'y0': pose[1],
            'z0': pose[2],
            'rx': pose[3],
            'ry': pose[4],
            'rz': pose[5],
            'timestamp': time.time()
        }
        
        return calibration_data


def main():
    """Programme principal de calibration visuelle."""
    
    # CONFIGURATION
    ROBOT_IP = "192.168.0.2"
    CAMERA_INDEX = 0
    ARUCO_ID = 0
    REFERENCE_IMAGE = "reference_calibration.jpg"
    
    print("="*60)
    print("   CALIBRATION VISUELLE ARUCO - PARTIE 1")
    print("="*60)
    
    # Initialiser le calibrateur
    calibrator = ArucoVisualCalibrator(
        robot_ip=ROBOT_IP,
        camera_index=CAMERA_INDEX,
        aruco_id=ARUCO_ID,
        reference_image_path=REFERENCE_IMAGE,
        tolerance_pixels=5,
        pixel_to_meter_ratio=0.0001  # À ajuster selon ta caméra
    )
    
    # Menu
    while True:
        print("\n" + "="*60)
        print("MENU")
        print("="*60)
        print("1. Capturer nouvelle image de référence")
        print("2. Aligner le robot avec la référence existante")
        print("3. Quitter")
        print()
        
        choice = input("Choix : ").strip()
        
        if choice == "1":
            calibrator.capture_reference_image()
            
        elif choice == "2":
            success = calibrator.auto_align_to_reference(
                max_iterations=50,
                show_video=True
            )
            
            if success:
                # Récupérer les coordonnées calibrées
                calibration = calibrator.get_calibrated_pose()
                
                # Sauvegarder
                output_file = "robot_calibration.json"
                with open(output_file, 'w') as f:
                    json.dump(calibration, f, indent=4)
                
                print(f"\n✅ Calibration sauvegardée : {output_file}")
                print("   Position du robot au centre du plateau (0,0) :")
                print(f"   X = {calibration['x0']:.4f} m")
                print(f"   Y = {calibration['y0']:.4f} m")
                print(f"   Z = {calibration['z0']:.4f} m")
                print("\n👉 Lance maintenant le script 2 pour la conversion des pièces !")
                
        elif choice == "3":
            print("👋 Au revoir !")
            break
        
        else:
            print("❌ Choix invalide")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Programme interrompu")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()