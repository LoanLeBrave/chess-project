#!/usr/bin/env python3
"""
Module de conversion entre coordonnées Robot et coordonnées Plateau (-10/+10).
Utilise le fichier de calibration pour faire les transformations.
"""

import json
from pathlib import Path
from typing import Tuple, Optional


class CoordinateConverter:
    """Convertit entre coordonnées robot (mètres) et plateau (-10/+10)."""
    
    def __init__(self, calibration_file: str = "robot_calibration.json"):
        """
        Initialise le convertisseur avec un fichier de calibration.
        
        Args:
            calibration_file: Chemin vers robot_calibration.json
        """
        self.calibration_file = Path(calibration_file)
        self.center_robot: Optional[Tuple[float, float]] = None
        self.scale_factor: Optional[float] = None
        self.load_calibration()
    
    def load_calibration(self) -> bool:
        """
        Charge les paramètres de calibration depuis le fichier JSON.
        
        Returns:
            True si chargement réussi, False sinon
        """
        if not self.calibration_file.exists():
            print(f"❌ Fichier de calibration introuvable : {self.calibration_file}")
            print("➡️  Lancez d'abord calibrate_robot_v2.py pour créer ce fichier")
            return False
        
        try:
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)
            
            # Extraire les paramètres nécessaires
            self.center_robot = (
                data['center_robot']['x'],
                data['center_robot']['y']
            )
            self.scale_factor = data['SCALE_FACTOR']
            
            print(f"✅ Calibration chargée depuis {self.calibration_file}")
            print(f"   Centre robot (0,0 plateau) : x={self.center_robot[0]:.4f}m, y={self.center_robot[1]:.4f}m")
            print(f"   Facteur d'échelle : {self.scale_factor} m/unité")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement de la calibration : {e}")
            return False
    
    def robot_to_plateau(self, x_robot: float, y_robot: float) -> Tuple[float, float]:
        """
        Convertit coordonnées robot (mètres) → plateau (-10/+10).
        
        Formule avec axes inversés :
        - x_plateau = -(x_robot - center_x) / SCALE_FACTOR
        - y_plateau = -(y_robot - center_y) / SCALE_FACTOR
        
        Args:
            x_robot: Position X du robot en mètres
            y_robot: Position Y du robot en mètres
            
        Returns:
            (x_plateau, y_plateau) dans le repère -10/+10
        """
        if self.center_robot is None or self.scale_factor is None:
            raise ValueError("Calibration non chargée ! Appelez load_calibration() d'abord.")
        
        center_x, center_y = self.center_robot
        
        # Différence par rapport au centre + inversion des axes
        delta_x_robot = x_robot - center_x
        delta_y_robot = y_robot - center_y
        
        # Conversion en unités plateau avec axes inversés
        x_plateau = -delta_x_robot / self.scale_factor
        y_plateau = -delta_y_robot / self.scale_factor
        
        return (x_plateau, y_plateau)
    
    def plateau_to_robot(self, x_plateau: float, y_plateau: float) -> Tuple[float, float]:
        """
        Convertit coordonnées plateau (-10/+10) → robot (mètres).
        
        Formule inverse avec axes inversés :
        - x_robot = center_x - (x_plateau * SCALE_FACTOR)
        - y_robot = center_y - (y_plateau * SCALE_FACTOR)
        
        Args:
            x_plateau: Position X dans repère plateau (-10 à +10)
            y_plateau: Position Y dans repère plateau (-10 à +10)
            
        Returns:
            (x_robot, y_robot) en mètres
        """
        if self.center_robot is None or self.scale_factor is None:
            raise ValueError("Calibration non chargée ! Appelez load_calibration() d'abord.")
        
        center_x, center_y = self.center_robot
        
        # Conversion avec axes inversés
        x_robot = center_x - (x_plateau * self.scale_factor)
        y_robot = center_y - (y_plateau * self.scale_factor)
        
        return (x_robot, y_robot)
    
    def convert_positions_dict(self, robot_positions: dict) -> dict:
        """
        Convertit un dictionnaire de positions robot en positions plateau.
        
        Format entrée : {"E2": {"x": 0.5, "y": 0.3}, ...}
        Format sortie : {"E2": {"x": 5.2, "y": -3.1}, ...}
        
        Args:
            robot_positions: Dict avec cases → coordonnées robot
            
        Returns:
            Dict avec cases → coordonnées plateau (-10/+10)
        """
        plateau_positions = {}
        
        for square, robot_pos in robot_positions.items():
            x_robot = robot_pos['x']
            y_robot = robot_pos['y']
            
            x_plateau, y_plateau = self.robot_to_plateau(x_robot, y_robot)
            
            plateau_positions[square] = {
                'x': round(x_plateau, 2),
                'y': round(y_plateau, 2)
            }
            
            print(f"  {square}: robot({x_robot:.4f}, {y_robot:.4f}) → plateau({x_plateau:.2f}, {y_plateau:.2f})")
        
        return plateau_positions


def main():
    """Exemple d'utilisation du convertisseur."""
    
    print("=" * 60)
    print("CONVERTISSEUR DE COORDONNÉES ROBOT ↔ PLATEAU")
    print("=" * 60)
    
    # Créer le convertisseur
    converter = CoordinateConverter("../calibration/robot_calibration.json")
    
    if converter.center_robot is None:
        return
    
    print("\n" + "=" * 60)
    print("TEST 1 : Position Robot → Plateau")
    print("=" * 60)
    
    # Exemple : convertir une position robot
    x_robot, y_robot = 0.45, 0.32
    x_plateau, y_plateau = converter.robot_to_plateau(x_robot, y_robot)
    print(f"\nRobot ({x_robot}, {y_robot}) m")
    print(f"  ↓")
    print(f"Plateau ({x_plateau:.2f}, {y_plateau:.2f})")
    
    print("\n" + "=" * 60)
    print("TEST 2 : Position Plateau → Robot")
    print("=" * 60)
    
    # Exemple inverse
    x_plateau2, y_plateau2 = 5.0, -3.0
    x_robot2, y_robot2 = converter.plateau_to_robot(x_plateau2, y_plateau2)
    print(f"\nPlateau ({x_plateau2}, {y_plateau2})")
    print(f"  ↓")
    print(f"Robot ({x_robot2:.4f}, {y_robot2:.4f}) m")
    
    print("\n" + "=" * 60)
    print("TEST 3 : Conversion JSON ami (Robot → Plateau)")
    print("=" * 60)
    
    # Simuler le JSON de ton ami
    ami_positions = {
        "E2": {"x": 0.450, "y": 0.320},
        "E4": {"x": 0.450, "y": 0.240},
        "D5": {"x": 0.470, "y": 0.220},
    }
    
    print("\nPositions de ton ami (coordonnées robot) :")
    print(json.dumps(ami_positions, indent=2))
    
    print("\n📐 Conversion en coordonnées plateau (-10/+10) :")
    plateau_positions = converter.convert_positions_dict(ami_positions)
    
    print("\n✅ Résultat (coordonnées plateau) :")
    print(json.dumps(plateau_positions, indent=2))
    
    print("\n" + "=" * 60)
    print("💡 UTILISATION PRATIQUE")
    print("=" * 60)
    print("""
Maintenant toi et ton ami pouvez communiquer dans le même repère !

Exemple d'usage :
1. Ton ami te donne : "Le pion est en E2 → robot(0.450, 0.320)"
2. Tu convertis : E2 → plateau(5.2, -3.1) dans TON repère
3. Tu détectes un pion sur ton plateau à (5.2, -3.1)
4. Vous parlez du même pion ! ✅

Pour déplacer un pion :
- Tu détectes : pion à plateau(x=5.2, y=-3.1)
- Tu convertis : plateau → robot(x=0.450, y=0.320)
- Tu envoies le robot à cette position
""")


if __name__ == "__main__":
    main()
