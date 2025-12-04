"""
PARTIE 2 : CONVERSION COORDONNÉES PIÈCES → POSITIONS ROBOT
Ce script charge la calibration faite précédemment et convertit les coordonnées
des pièces d'échecs en positions robot utilisables.
"""

import json
import time
from pathlib import Path
from typing import Tuple, List, Dict, Optional

# Imports RTDE
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    from ur_rtde.rtde_control import RTDEControlInterface
    from ur_rtde.rtde_receive import RTDEReceiveInterface


class ChessBoardToRobotMapper:
    """
    Convertit les coordonnées des pièces d'échecs en positions robot.
    Utilise la calibration faite avec le script de calibration visuelle.
    """
    
    def __init__(
        self,
        robot_ip: str,
        calibration_file: str = "robot_calibration.json",
        board_size_cm: float = 27.7,
        half_range: float = 10.0,
        z_approach_offset: float = 0.08,
        z_pick_offset: float = 0.02
    ):
        """
        Initialise le mapper.
        
        Args:
            robot_ip: Adresse IP du robot
            calibration_file: Fichier de calibration (généré par script 1)
            board_size_cm: Taille du plateau en cm
            half_range: Demi-étendue des coordonnées (ex: 10 pour [-10, +10])
            z_approach_offset: Hauteur d'approche (m)
            z_pick_offset: Hauteur de prise (m)
        """
        self.robot_ip = robot_ip
        self.calibration_file = Path(calibration_file)
        self.board_size_cm = board_size_cm
        self.half_range = half_range
        self.z_approach_offset = z_approach_offset
        self.z_pick_offset = z_pick_offset
        
        # Facteur d'échelle : unités plateau → mètres
        self.scale_m = (board_size_cm / (2 * half_range)) / 100.0
        
        # Point central du plateau (chargé depuis calibration)
        self.x0: Optional[float] = None
        self.y0: Optional[float] = None
        self.z0: Optional[float] = None
        self.rx: float = 0.0
        self.ry: float = 0.0
        self.rz: float = 0.0
        
        # Connexion robot
        print(f"🤖 Connexion au robot {robot_ip}...")
        self.rtde_c = RTDEControlInterface(robot_ip)
        self.rtde_r = RTDEReceiveInterface(robot_ip)
        print("✅ Robot connecté")
        
        # Charger la calibration
        self.load_calibration()
    
    def load_calibration(self) -> bool:
        """Charge la calibration depuis le fichier."""
        if not self.calibration_file.exists():
            print(f"❌ Fichier de calibration introuvable : {self.calibration_file}")
            print("👉 Lance d'abord le script 1 pour faire la calibration !")
            return False
        
        try:
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)
            
            self.x0 = data['x0']
            self.y0 = data['y0']
            self.z0 = data['z0']
            self.rx = data.get('rx', 0.0)
            self.ry = data.get('ry', 0.0)
            self.rz = data.get('rz', 0.0)
            
            print("\n" + "="*60)
            print("✅ CALIBRATION CHARGÉE AVEC SUCCÈS")
            print("="*60)
            print(f"Centre du plateau (0,0) :")
            print(f"  Position    : X={self.x0:.4f} m, Y={self.y0:.4f} m, Z={self.z0:.4f} m")
            print(f"  Orientation : Rx={self.rx:.4f}, Ry={self.ry:.4f}, Rz={self.rz:.4f}")
            print(f"  Échelle     : {self.scale_m*1000:.3f} mm par unité plateau")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement : {e}")
            return False
    
    def is_calibrated(self) -> bool:
        """Vérifie si le mapper est calibré."""
        return self.x0 is not None
    
    def convert(
        self, 
        x_unit: float, 
        y_unit: float,
        custom_z_approach: Optional[float] = None,
        custom_z_pick: Optional[float] = None
    ) -> Tuple[List[float], List[float]]:
        """
        Convertit une coordonnée plateau en poses robot.
        
        Args:
            x_unit: Coordonnée X sur le plateau (ex: -10 à +10)
            y_unit: Coordonnée Y sur le plateau (ex: -10 à +10)
            custom_z_approach: Hauteur d'approche personnalisée
            custom_z_pick: Hauteur de prise personnalisée
            
        Returns:
            (pose_approach, pose_pick) : deux listes [X, Y, Z, Rx, Ry, Rz]
        """
        if not self.is_calibrated():
            raise RuntimeError(
                "❌ Pas de calibration ! Lance le script 1 d'abord."
            )
        
        # Conversion unités plateau → mètres
        dx = x_unit * self.scale_m
        dy = y_unit * self.scale_m
        
        # Position dans le repère robot
        x_robot = self.x0 + dx
        y_robot = self.y0 + dy
        
        # Hauteurs
        z_approach = self.z0 + (custom_z_approach or self.z_approach_offset)
        z_pick = self.z0 + (custom_z_pick or self.z_pick_offset)
        
        # Poses complètes
        pose_approach = [x_robot, y_robot, z_approach, self.rx, self.ry, self.rz]
        pose_pick = [x_robot, y_robot, z_pick, self.rx, self.ry, self.rz]
        
        return pose_approach, pose_pick
    
    def convert_pieces(self, pieces_data: List[Dict]) -> List[Dict]:
        """
        Convertit une liste de pièces avec leurs coordonnées.
        
        Args:
            pieces_data: Liste de dictionnaires avec clés 'x', 'y', et infos pièce
            
        Returns:
            Liste enrichie avec 'pose_approach' et 'pose_pick'
        """
        results = []
        
        for piece in pieces_data:
            try:
                pose_approach, pose_pick = self.convert(piece['x'], piece['y'])
                
                result = piece.copy()
                result['pose_approach'] = pose_approach
                result['pose_pick'] = pose_pick
                results.append(result)
                
            except Exception as e:
                print(f"⚠️ Erreur pour la pièce {piece}: {e}")
        
        return results
    
    def print_conversion(self, x: float, y: float, label: str = "Position"):
        """Affiche les détails d'une conversion."""
        pose_app, pose_pick = self.convert(x, y)
        
        print(f"\n{'='*60}")
        print(f"   {label} : ({x:+.1f}, {y:+.1f})")
        print(f"{'='*60}")
        print("Pose d'approche :")
        print(f"  Position    : X={pose_app[0]:.4f}, Y={pose_app[1]:.4f}, Z={pose_app[2]:.4f}")
        print(f"  Orientation : Rx={pose_app[3]:.4f}, Ry={pose_app[4]:.4f}, Rz={pose_app[5]:.4f}")
        print("\nPose de prise :")
        print(f"  Position    : X={pose_pick[0]:.4f}, Y={pose_pick[1]:.4f}, Z={pose_pick[2]:.4f}")
        print(f"  Orientation : Rx={pose_pick[3]:.4f}, Ry={pose_pick[4]:.4f}, Rz={pose_pick[5]:.4f}")
        print(f"{'='*60}")
    
    def move_to_piece(
        self, 
        x: float, 
        y: float, 
        pick: bool = True,
        speed: float = 0.1
    ) -> bool:
        """
        Déplace le robot vers une pièce.
        
        Args:
            x, y: Coordonnées de la pièce
            pick: Si True, descend jusqu'à la hauteur de prise
            speed: Vitesse de déplacement
            
        Returns:
            True si le mouvement a réussi
        """
        try:
            pose_app, pose_pick = self.convert(x, y)
            
            print(f"🚀 Déplacement vers ({x:+.1f}, {y:+.1f})...")
            
            # Approche
            print("   → Approche...")
            self.rtde_c.moveL(pose_app, speed=speed, acceleration=0.3)
            time.sleep(0.3)
            
            if pick:
                # Descente pour prise
                print("   → Descente...")
                self.rtde_c.moveL(pose_pick, speed=speed*0.5, acceleration=0.3)
                time.sleep(0.3)
                
                # Remontée
                print("   → Remontée...")
                self.rtde_c.moveL(pose_app, speed=speed, acceleration=0.3)
            
            print("   ✅ Mouvement terminé")
            return True
            
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            return False
    
    def execute_chess_moves(self, moves: List[Dict]) -> None:
        """
        Exécute une séquence de mouvements d'échecs.
        
        Args:
            moves: Liste de mouvements avec 'from' et 'to' (coordonnées)
        """
        print("\n" + "="*60)
        print("♟️  EXÉCUTION DES MOUVEMENTS D'ÉCHECS")
        print("="*60)
        
        for i, move in enumerate(moves, 1):
            print(f"\nMouvement {i}/{len(moves)}")
            print(f"  De : ({move['from']['x']:+.1f}, {move['from']['y']:+.1f})")
            print(f"  À  : ({move['to']['x']:+.1f}, {move['to']['y']:+.1f})")
            
            # Aller chercher la pièce
            if not self.move_to_piece(move['from']['x'], move['from']['y'], pick=True):
                print("❌ Échec du mouvement, arrêt")
                break
            
            # TODO: Activer la pince ici
            # self.rtde_c.setDigitalOut(...)
            
            # Déposer la pièce
            if not self.move_to_piece(move['to']['x'], move['to']['y'], pick=True):
                print("❌ Échec du mouvement, arrêt")
                break
            
            # TODO: Désactiver la pince ici
            
            time.sleep(0.5)
        
        print("\n✅ Séquence terminée !")


def main():
    """Programme principal de conversion."""
    
    # CONFIGURATION
    ROBOT_IP = "192.168.0.2"
    CALIBRATION_FILE = "robot_calibration.json"
    
    print("="*60)
    print("   CONVERSION PIÈCES ÉCHECS → ROBOT - PARTIE 2")
    print("="*60)
    
    # Initialiser le mapper
    mapper = ChessBoardToRobotMapper(
        robot_ip=ROBOT_IP,
        calibration_file=CALIBRATION_FILE,
        board_size_cm=27.7,
        half_range=10.0
    )
    
    if not mapper.is_calibrated():
        print("\n❌ Pas de calibration disponible !")
        print("👉 Lance d'abord le script 1 (calibration visuelle)")
        return
    
    # EXEMPLE 1 : Données de pièces venant de la détection caméra
    pieces_data = {
        "coordinates": [
            {
                "id": 1,
                "color": "white",
                "piece_type": "Queen",
                "x": 1,
                "y": -8
            },
            {
                "id": 2,
                "color": "white",
                "piece_type": "Rook",
                "x": 8,
                "y": -1
            },
            {
                "id": 3,
                "color": "black",
                "piece_type": "Pawn",
                "x": -3,
                "y": 5
            }
        ]
    }
    
    print("\n📊 CONVERSION DES PIÈCES DÉTECTÉES")
    print("="*60)
    
    # Convertir toutes les pièces
    converted_pieces = mapper.convert_pieces(pieces_data["coordinates"])
    
    # Afficher les résultats
    for piece in converted_pieces:
        label = f"{piece['color']} {piece['piece_type']}"
        mapper.print_conversion(piece['x'], piece['y'], label=label)
    
    # Menu interactif
    while True:
        print("\n" + "="*60)
        print("MENU")
        print("="*60)
        print("1. Convertir une position spécifique")
        print("2. Tester un mouvement vers une pièce")
        print("3. Exécuter une séquence de mouvements")
        print("4. Charger positions depuis fichier JSON")
        print("5. Quitter")
        print()
        
        choice = input("Choix : ").strip()
        
        if choice == "1":
            try:
                x = float(input("Coordonnée X : "))
                y = float(input("Coordonnée Y : "))
                mapper.print_conversion(x, y)
            except ValueError:
                print("❌ Valeurs invalides")
        
        elif choice == "2":
            try:
                x = float(input("Coordonnée X : "))
                y = float(input("Coordonnée Y : "))
                confirm = input(f"Déplacer le robot vers ({x}, {y}) ? (o/n) : ")
                if confirm.lower() == 'o':
                    mapper.move_to_piece(x, y, pick=True, speed=0.1)
            except ValueError:
                print("❌ Valeurs invalides")
        
        elif choice == "3":
            # Exemple de séquence de mouvements
            moves = [
                {"from": {"x": 1, "y": -8}, "to": {"x": 1, "y": -5}},
                {"from": {"x": 8, "y": -1}, "to": {"x": 5, "y": -1}}
            ]
            
            confirm = input(f"Exécuter {len(moves)} mouvements ? (o/n) : ")
            if confirm.lower() == 'o':
                mapper.execute_chess_moves(moves)
        
        elif choice == "4":
            filepath = input("Chemin du fichier JSON : ").strip()
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                if "coordinates" in data:
                    converted = mapper.convert_pieces(data["coordinates"])
                    print(f"\n✅ {len(converted)} pièces converties")
                    
                    # Sauvegarder les résultats
                    output_file = "converted_positions.json"
                    with open(output_file, 'w') as f:
                        json.dump(converted, f, indent=4)
                    print(f"💾 Résultats sauvegardés : {output_file}")
                else:
                    print("❌ Format JSON invalide (clé 'coordinates' manquante)")
                    
            except FileNotFoundError:
                print(f"❌ Fichier introuvable : {filepath}")
            except json.JSONDecodeError:
                print("❌ Erreur de décodage JSON")
        
        elif choice == "5":
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