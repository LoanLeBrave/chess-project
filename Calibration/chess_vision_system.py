#!/usr/bin/env python3
"""
Système de Vision ArUco Unifié pour Robot d'Échecs
==================================================
Adapté au format existant du projet Yvi:
- IDs 0-15 : Pièces blanches
- IDs 16-31 : Pièces noires
- Coordonnées en cm relatives au centre du plateau
- Caméra Raspberry Pi (PiCamera ou USB)

Ce module:
- Détecte les ArUco des pions via la caméra sous le plateau
- Calcule leurs positions dans le repère plateau (cm)
- Transforme vers le repère robot pour saisie précise
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from dataclasses import field
import json
import time
from enum import Enum


class PieceType(Enum):
    """Types de pièces d'échecs."""
    PAWN = "Pawn"
    ROOK = "Rook"
    KNIGHT = "Knight"
    BISHOP = "Bishop"
    QUEEN = "Queen"
    KING = "King"


@dataclass
class PieceInfo:
    """Informations sur une pièce détectée."""
    aruco_id: int
    label: str
    color: str  # "white" ou "black"
    piece_type: PieceType
    x: float  # Position X en cm (repère plateau)
    y: float  # Position Y en cm (repère plateau)
    initial_piece: str  # Ex: "Pawn_B", "Rook_A"

    def to_dict(self) -> dict:
        return {
            "id": self.aruco_id,
            "label": self.label,
            "color": self.color,
            "piece_type": self.piece_type.value,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "initial_piece": self.initial_piece
        }


# =============================================================================
# CONFIGURATION DES PIÈCES (IDs 0-31)
# =============================================================================

PIECES_REFERENCE: Dict[int, Tuple[str, str, PieceType, str]] = {
    # Blancs (IDs 0-15)
    0: ("White Pawn #0", "white", PieceType.PAWN, "Pawn_A"),
    1: ("White Pawn #1", "white", PieceType.PAWN, "Pawn_B"),
    2: ("White Pawn #2", "white", PieceType.PAWN, "Pawn_C"),
    3: ("White Pawn #3", "white", PieceType.PAWN, "Pawn_D"),
    4: ("White Pawn #4", "white", PieceType.PAWN, "Pawn_E"),
    5: ("White Pawn #5", "white", PieceType.PAWN, "Pawn_F"),
    6: ("White Pawn #6", "white", PieceType.PAWN, "Pawn_G"),
    7: ("White Pawn #7", "white", PieceType.PAWN, "Pawn_H"),
    8: ("White Rook #8", "white", PieceType.ROOK, "Rook_A"),
    9: ("White Rook #9", "white", PieceType.ROOK, "Rook_H"),
    10: ("White Knight #10", "white", PieceType.KNIGHT, "Knight_B"),
    11: ("White Knight #11", "white", PieceType.KNIGHT, "Knight_G"),
    12: ("White Bishop #12", "white", PieceType.BISHOP, "Bishop_C"),
    13: ("White Bishop #13", "white", PieceType.BISHOP, "Bishop_F"),
    14: ("White Queen #14", "white", PieceType.QUEEN, "Queen"),
    15: ("White King #15", "white", PieceType.KING, "King"),

    # Noirs (IDs 16-31)
    16: ("Black Pawn #16", "black", PieceType.PAWN, "Pawn_A"),
    17: ("Black Pawn #17", "black", PieceType.PAWN, "Pawn_B"),
    18: ("Black Pawn #18", "black", PieceType.PAWN, "Pawn_C"),
    19: ("Black Pawn #19", "black", PieceType.PAWN, "Pawn_D"),
    20: ("Black Pawn #20", "black", PieceType.PAWN, "Pawn_E"),
    21: ("Black Pawn #21", "black", PieceType.PAWN, "Pawn_F"),
    22: ("Black Pawn #22", "black", PieceType.PAWN, "Pawn_G"),
    23: ("Black Pawn #23", "black", PieceType.PAWN, "Pawn_H"),
    24: ("Black Rook #24", "black", PieceType.ROOK, "Rook_A"),
    25: ("Black Rook #25", "black", PieceType.ROOK, "Rook_H"),
    26: ("Black Knight #26", "black", PieceType.KNIGHT, "Knight_B"),
    27: ("Black Knight #27", "black", PieceType.KNIGHT, "Knight_G"),
    28: ("Black Bishop #28", "black", PieceType.BISHOP, "Bishop_C"),
    29: ("Black Bishop #29", "black", PieceType.BISHOP, "Bishop_F"),
    30: ("Black Queen #30", "black", PieceType.QUEEN, "Queen"),
    31: ("Black King #31", "black", PieceType.KING, "King"),
}


@dataclass
class BoardConfig:
    """Configuration du plateau d'échecs."""
    # Taille du plateau en cm
    board_size_cm: float = 28.0  # 28x28 cm

    # Taille d'une case en cm
    square_size_cm: float = 3.5  # 28/8 = 3.5cm par case

    # Taille des marqueurs ArUco en cm
    aruco_marker_size_cm: float = 2.0

    # IDs des marqueurs de coins pour calibration
    # A1=34 (bas-gauche), H1=35 (bas-droite), H8=33 (haut-droite), A8=32 (haut-gauche)
    corner_aruco_ids: Tuple[int, ...] = (34, 35, 33, 32)

    # Position des coins dans le repère plateau (origine = centre)
    # Demi-taille = 14cm
    corner_positions_cm: Dict[int, Tuple[float, float]] = None

    def __post_init__(self):
        half = self.board_size_cm / 2  # 14cm
        self.corner_positions_cm = {
            34: (-half, -half),  # A1 bas-gauche
            35: (half, -half),  # H1 bas-droite
            33: (half, half),  # H8 haut-droite
            32: (-half, half),  # A8 haut-gauche
        }


@dataclass
class RobotTransform:
    """Transformation du repère plateau vers repère robot."""
    # Offset de l'origine plateau dans le repère robot (en mm)
    offset_x_mm: float = 0.0
    offset_y_mm: float = 0.0
    offset_z_mm: float = 0.0

    # Rotation (en degrés) - généralement 0 ou 90
    rotation_deg: float = 0.0

    # Facteur d'échelle (si nécessaire)
    scale: float = 1.0

    def board_to_robot(self, x_cm: float, y_cm: float, z_cm: float = 0) -> Tuple[float, float, float]:
        """
        Convertit des coordonnées plateau (cm) vers robot (mm).

        Le repère plateau a son origine au CENTRE (x=0, y=0).
        """
        # Conversion cm -> mm
        x_mm = x_cm * 10 * self.scale
        y_mm = y_cm * 10 * self.scale
        z_mm = z_cm * 10 * self.scale

        # Rotation si nécessaire
        if self.rotation_deg != 0:
            angle_rad = np.radians(self.rotation_deg)
            cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
            x_rot = x_mm * cos_a - y_mm * sin_a
            y_rot = x_mm * sin_a + y_mm * cos_a
            x_mm, y_mm = x_rot, y_rot

        # Appliquer l'offset
        robot_x = x_mm + self.offset_x_mm
        robot_y = y_mm + self.offset_y_mm
        robot_z = z_mm + self.offset_z_mm

        return robot_x, robot_y, robot_z


class ChessVisionSystem:
    """
    Système de vision pour le robot d'échecs.
    Détecte les pièces via ArUco et fournit leurs coordonnées.
    """

    def __init__(self,
                 camera_index: int = 0,
                 camera_matrix: np.ndarray = None,
                 dist_coeffs: np.ndarray = None,
                 aruco_dict_type: int = cv2.aruco.DICT_4X4_50):
        """
        Initialise le système de vision.

        Args:
            camera_index: Index de la caméra (0 pour PiCamera via V4L2)
            camera_matrix: Matrice intrinsèque (3x3)
            dist_coeffs: Coefficients de distorsion
            aruco_dict_type: Type de dictionnaire ArUco (DICT_4X4_50 pour IDs 0-49)
        """
        self.camera_index = camera_index
        self.cap = None

        # Configuration
        self.board_config = BoardConfig()
        self.robot_transform = RobotTransform()

        # Paramètres caméra (valeurs par défaut pour PiCamera v2)
        if camera_matrix is None:
            # Estimation pour PiCamera v2 en 640x480
            self.camera_matrix = np.array([
                [500, 0, 320],
                [0, 500, 240],
                [0, 0, 1]
            ], dtype=np.float32)
        else:
            self.camera_matrix = camera_matrix

        if dist_coeffs is None:
            self.dist_coeffs = np.zeros(5, dtype=np.float32)
        else:
            self.dist_coeffs = dist_coeffs

        # Détecteur ArUco
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_type)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        # Cache des détections
        self._last_detection: Dict[int, PieceInfo] = {}
        self._last_frame_time = 0

        # Calibration plateau (transformation pixel -> cm)
        self._calibration_matrix: Optional[np.ndarray] = None
        self._calibration_offset: Optional[np.ndarray] = None

    def connect_camera(self) -> bool:
        """Connecte à la caméra."""
        print(f"📷 Connexion caméra index {self.camera_index}...")

        try:
            self.cap = cv2.VideoCapture(self.camera_index)
        except Exception as e:
            print(f"❌ Exception lors de VideoCapture: {e}")
            return False

        if not self.cap.isOpened():
            print("❌ Impossible d'ouvrir la caméra")
            print("   Vérifiez que la caméra est connectée et pas utilisée ailleurs")
            return False

        # Configuration pour Raspberry Pi
        print("   Configuration de la caméra...")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        print("   Lecture d'une frame de test...")
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"✅ Caméra connectée: {w}x{h}")

            # Mettre à jour le centre de la caméra
            self.camera_matrix[0, 2] = w / 2
            self.camera_matrix[1, 2] = h / 2

            return True

        print("❌ Impossible de lire depuis la caméra")
        return False

    def disconnect_camera(self):
        """Déconnecte la caméra."""
        if self.cap:
            self.cap.release()
            self.cap = None
            print("📷 Caméra déconnectée")

    def get_frame(self) -> Optional[np.ndarray]:
        """Capture une frame."""
        if self.cap is None:
            return None
        ret, frame = self.cap.read()
        return frame if ret else None

    def calibrate_with_corners(self, frame: np.ndarray,
                               corner_positions_cm: Dict[int, Tuple[float, float]]) -> bool:
        """
        Calibre le système en utilisant des ArUco aux coins connus.

        Args:
            frame: Image de calibration
            corner_positions_cm: Dict[aruco_id, (x_cm, y_cm)] positions connues

        Returns:
            True si calibration réussie
        """
        corners, ids, _ = self.detector.detectMarkers(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        )

        if ids is None:
            print("❌ Aucun marqueur détecté")
            return False

        ids = ids.flatten()

        # Collecter les points correspondants
        src_points = []  # Points pixels
        dst_points = []  # Points cm

        for corner_id, (x_cm, y_cm) in corner_positions_cm.items():
            idx = np.where(ids == corner_id)[0]
            if len(idx) > 0:
                center_px = corners[idx[0]][0].mean(axis=0)
                src_points.append(center_px)
                dst_points.append([x_cm, y_cm])

        if len(src_points) < 4:
            print(f"❌ Pas assez de coins détectés: {len(src_points)}/4")
            return False

        src_points = np.array(src_points, dtype=np.float32)
        dst_points = np.array(dst_points, dtype=np.float32)

        # Calculer l'homographie
        H, _ = cv2.findHomography(src_points, dst_points)

        if H is None:
            print("❌ Échec calcul homographie")
            return False

        self._calibration_matrix = H
        print("✅ Calibration réussie!")
        return True

    def auto_calibrate_from_corners(self, frame: np.ndarray = None) -> bool:
        """
        Calibration automatique en détectant les 4 ArUco des coins.

        Utilise les IDs configurés: 32 (A8), 33 (H8), 34 (A1), 35 (H1)
        """
        if frame is None:
            frame = self.get_frame()

        if frame is None:
            print("❌ Pas d'image disponible")
            return False

        # Utiliser les positions des coins configurées
        corner_positions = self.board_config.corner_positions_cm

        print(f"🔍 Recherche des ArUco coins: {list(corner_positions.keys())}")

        return self.calibrate_with_corners(frame, corner_positions)

    def calibrate_simple(self,
                         pixels_per_cm: float,
                         center_offset_px: Tuple[float, float] = (0, 0)) -> None:
        """
        Calibration simple avec un ratio pixel/cm.

        Args:
            pixels_per_cm: Nombre de pixels par cm
            center_offset_px: Décalage du centre en pixels
        """
        # Matrice de transformation simple (échelle + translation)
        scale = 1.0 / pixels_per_cm

        self._calibration_matrix = np.array([
            [scale, 0, -center_offset_px[0] * scale],
            [0, -scale, center_offset_px[1] * scale],  # Y inversé
            [0, 0, 1]
        ], dtype=np.float32)

        print(f"✅ Calibration simple: {pixels_per_cm:.2f} px/cm")

    def pixel_to_cm(self, px: float, py: float) -> Tuple[float, float]:
        """Convertit des coordonnées pixel vers cm."""
        if self._calibration_matrix is None:
            # Calibration par défaut si non configurée
            # Suppose que le centre de l'image = centre du plateau
            if self.cap:
                w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            else:
                w, h = 640, 480

            # Estimation: plateau de 40cm visible sur ~400 pixels
            pixels_per_cm = 10.0
            x_cm = (px - w / 2) / pixels_per_cm
            y_cm = -(py - h / 2) / pixels_per_cm  # Y inversé
            return x_cm, y_cm

        # Appliquer l'homographie
        pt = np.array([[[px, py]]], dtype=np.float32)
        pt_transformed = cv2.perspectiveTransform(pt, self._calibration_matrix)
        return float(pt_transformed[0, 0, 0]), float(pt_transformed[0, 0, 1])

    def detect_pieces(self, frame: np.ndarray = None) -> Dict[int, PieceInfo]:
        """
        Détecte toutes les pièces dans l'image.

        Returns:
            Dict[aruco_id, PieceInfo]
        """
        if frame is None:
            frame = self.get_frame()

        if frame is None:
            return {}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        if ids is None:
            self._last_detection = {}
            return {}

        ids = ids.flatten()
        pieces = {}

        for i, aruco_id in enumerate(ids):
            # Vérifier que c'est un ID de pièce valide (0-31)
            if aruco_id not in PIECES_REFERENCE:
                continue

            # Obtenir les infos de la pièce
            label, color, piece_type, initial = PIECES_REFERENCE[aruco_id]

            # Calculer le centre du marqueur en pixels
            center_px = corners[i][0].mean(axis=0)

            # Convertir en cm
            x_cm, y_cm = self.pixel_to_cm(center_px[0], center_px[1])

            pieces[aruco_id] = PieceInfo(
                aruco_id=aruco_id,
                label=label,
                color=color,
                piece_type=piece_type,
                x=x_cm,
                y=y_cm,
                initial_piece=initial
            )

        self._last_detection = pieces
        self._last_frame_time = time.time()

        return pieces

    def get_piece_robot_position(self, aruco_id: int,
                                 z_offset_mm: float = 0) -> Optional[Tuple[float, float, float]]:
        """
        Obtient la position robot d'une pièce.

        Args:
            aruco_id: ID de la pièce
            z_offset_mm: Décalage Z additionnel (pour hauteur de saisie)

        Returns:
            (x_mm, y_mm, z_mm) dans le repère robot, ou None
        """
        if aruco_id not in self._last_detection:
            # Essayer une nouvelle détection
            self.detect_pieces()

        if aruco_id not in self._last_detection:
            return None

        piece = self._last_detection[aruco_id]

        # Convertir plateau (cm) -> robot (mm)
        x_mm, y_mm, z_mm = self.robot_transform.board_to_robot(
            piece.x, piece.y, 0
        )

        return x_mm, y_mm, z_mm + z_offset_mm

    def export_game_state(self, filepath: str = None) -> dict:
        """
        Exporte l'état du jeu au format JSON compatible.

        Format identique à format_jeu.json
        """
        pieces = self.detect_pieces()

        game_state = {
            "coordinates": [p.to_dict() for p in pieces.values()],
            "game_metadata": {
                "turn": "white",
                "move_count": 0,
                "pieces_detected": len(pieces),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            },
            "pieces_reference": {
                str(k): f"{v[1].capitalize()} {v[2].value} ({v[3]})"
                for k, v in PIECES_REFERENCE.items()
            }
        }

        if filepath:
            with open(filepath, 'w') as f:
                json.dump(game_state, f, indent=2)
            print(f"✅ État exporté: {filepath}")

        return game_state

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Dessine les détections sur l'image."""
        output = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(output, corners, ids)

            ids = ids.flatten()

            for i, aruco_id in enumerate(ids):
                center = corners[i][0].mean(axis=0).astype(int)

                if aruco_id in PIECES_REFERENCE:
                    label, color, piece_type, _ = PIECES_REFERENCE[aruco_id]

                    # Couleur selon la pièce
                    draw_color = (255, 255, 255) if color == "white" else (50, 50, 50)

                    # Position en cm
                    x_cm, y_cm = self.pixel_to_cm(center[0], center[1])

                    # Texte
                    text = f"{piece_type.value[0]}{aruco_id} ({x_cm:.1f},{y_cm:.1f})"
                    cv2.putText(output, text, (center[0] - 40, center[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, draw_color, 1)
                else:
                    # Marqueur inconnu
                    cv2.putText(output, f"?{aruco_id}", (center[0] - 10, center[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Afficher le nombre de pièces
        cv2.putText(output, f"Pieces: {len(self._last_detection)}/32",
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return output

    def interactive_view(self):
        """Mode visualisation interactive."""
        print("\n=== MODE VISUALISATION ===")
        print("Touches: Q=Quitter, S=Sauvegarder, C=Calibrer")

        while True:
            frame = self.get_frame()
            if frame is None:
                continue

            # Détecter et afficher
            self.detect_pieces(frame)
            display = self.draw_overlay(frame)

            cv2.imshow("Chess Vision", display)
            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('s'):
                self.export_game_state("game_state.json")
            elif key == ord('c'):
                # Calibration interactive simple
                print("\nCalibration - Entrez pixels par cm:")
                try:
                    ppcm = float(input("Pixels/cm: "))
                    self.calibrate_simple(ppcm, (320, 240))
                except:
                    pass

        cv2.destroyAllWindows()


# =============================================================================
# INTÉGRATION ROBOT
# =============================================================================

class ChessRobotIntegration:
    """
    Intègre le système de vision avec le contrôle robot existant.
    """

    def __init__(self, vision: ChessVisionSystem):
        self.vision = vision

        # Hauteurs de saisie par type de pièce (en mm)
        self.grip_heights = {
            PieceType.PAWN: 25,
            PieceType.ROOK: 30,
            PieceType.KNIGHT: 35,
            PieceType.BISHOP: 40,
            PieceType.QUEEN: 50,
            PieceType.KING: 55,
        }

        # Hauteur de transit
        self.transit_height_mm = 150

    def get_piece_grip_position(self, aruco_id: int) -> Optional[Tuple[float, float, float]]:
        """
        Obtient la position de saisie pour une pièce.

        Returns:
            (x_mm, y_mm, z_mm) position pour fermer le gripper
        """
        if aruco_id not in self.vision._last_detection:
            self.vision.detect_pieces()

        if aruco_id not in self.vision._last_detection:
            return None

        piece = self.vision._last_detection[aruco_id]
        grip_z = self.grip_heights.get(piece.piece_type, 25)

        return self.vision.get_piece_robot_position(aruco_id, z_offset_mm=grip_z)

    def find_piece_on_square(self, square_x_cm: float, square_y_cm: float,
                             tolerance_cm: float = 2.5) -> Optional[int]:
        """
        Trouve la pièce sur une case donnée.

        Args:
            square_x_cm, square_y_cm: Centre de la case en cm
            tolerance_cm: Tolérance (demi-taille de case)

        Returns:
            aruco_id de la pièce, ou None
        """
        pieces = self.vision.detect_pieces()

        for aruco_id, piece in pieces.items():
            dx = abs(piece.x - square_x_cm)
            dy = abs(piece.y - square_y_cm)

            if dx < tolerance_cm and dy < tolerance_cm:
                return aruco_id

        return None

    def algebraic_to_cm(self, square: str) -> Tuple[float, float]:
        """
        Convertit notation algébrique vers coordonnées cm.

        L'origine (0, 0) est au CENTRE du plateau.
        a1 est en bas-gauche.
        Plateau 28x28cm, cases 3.5x3.5cm
        """
        col = ord(square[0].lower()) - ord('a')  # 0-7
        row = int(square[1]) - 1  # 0-7

        square_size = self.vision.board_config.square_size_cm  # 3.5cm
        board_half = self.vision.board_config.board_size_cm / 2  # 14cm

        # Centre de la case
        x_cm = (col + 0.5) * square_size - board_half
        y_cm = (row + 0.5) * square_size - board_half

        return x_cm, y_cm

    def get_move_coordinates(self, from_square: str, to_square: str) -> dict:
        """
        Calcule toutes les coordonnées nécessaires pour un coup.

        Returns:
            {
                'from': (x_mm, y_mm, z_mm),
                'to': (x_mm, y_mm, z_mm),
                'piece_id': aruco_id,
                'piece_type': PieceType,
                'capture_piece_id': aruco_id or None
            }
        """
        from_x_cm, from_y_cm = self.algebraic_to_cm(from_square)
        to_x_cm, to_y_cm = self.algebraic_to_cm(to_square)

        # Trouver la pièce à déplacer
        piece_id = self.find_piece_on_square(from_x_cm, from_y_cm)

        if piece_id is None:
            return {'error': f"Pas de pièce sur {from_square}"}

        piece = self.vision._last_detection[piece_id]
        grip_z = self.grip_heights[piece.piece_type]

        # Vérifier s'il y a une capture
        capture_id = self.find_piece_on_square(to_x_cm, to_y_cm)

        # Coordonnées robot
        from_robot = self.vision.robot_transform.board_to_robot(
            piece.x, piece.y, grip_z / 10  # cm
        )

        to_robot = self.vision.robot_transform.board_to_robot(
            to_x_cm, to_y_cm, grip_z / 10
        )

        return {
            'from': from_robot,
            'to': to_robot,
            'piece_id': piece_id,
            'piece_type': piece.piece_type,
            'capture_piece_id': capture_id
        }


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Test du système."""
    print("=== Système Vision Échecs ===")
    print("Configuration:")
    print(f"  - Plateau: 28x28 cm")
    print(f"  - Cases: 3.5x3.5 cm")
    print(f"  - Pièces blanches: IDs 0-15")
    print(f"  - Pièces noires: IDs 16-31")
    print(f"  - Coins: 32(A8), 33(H8), 34(A1), 35(H1)")
    print(f"  - Coordonnées: cm relatif au centre")

    vision = ChessVisionSystem(camera_index=0)

    if not vision.connect_camera():
        print("Échec connexion caméra")
        return

    # Calibration automatique avec les ArUco des coins
    print("\n📐 Calibration automatique...")
    print("   Assurez-vous que les 4 coins (IDs 32,33,34,35) sont visibles")

    input("   Appuyez sur Entrée quand prêt...")

    if vision.auto_calibrate_from_corners():
        print("✅ Calibration pixels→cm réussie!")
    else:
        print("⚠️ Calibration auto échouée, utilisation estimation")
        vision.calibrate_simple(pixels_per_cm=10.0, center_offset_px=(320, 240))

    try:
        vision.interactive_view()
    finally:
        vision.disconnect_camera()


if __name__ == "__main__":
    main()