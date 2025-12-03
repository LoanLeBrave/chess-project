#!/usr/bin/env python3
"""
Script de contrôle robot pour jouer aux échecs
Utilise le mapping des cases pour déplacer les pièces
"""

from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper
import json
import time
import sys
import os

# Configuration robot
ROBOT_IP = "192.168.0.11"

# Paramètres de mouvement
VITESSE_JOINTS = 0.5  # rad/s
ACCELERATION_JOINTS = 0.3  # rad/s²
VITESSE_LINEAIRE = 0.1  # m/s
ACCELERATION_LINEAIRE = 0.3  # m/s²

# Hauteurs relatives PAR DÉFAUT (seront remplacées par celles du JSON)
# La position enregistrée = hauteur de PRISE
DELTA_HAUTEUR_SECURITE = 0.08  # 8cm au-dessus de la position de prise
DELTA_HAUTEUR_APPROCHE = 0.03  # 3cm au-dessus de la position de prise
DELTA_HAUTEUR_RELACHE = 0.002  # +2mm pour relâcher (évite d'appuyer sur le plexi)

# Gripper - ouverture limitée pour éviter de cogner les pièces voisines
# Le gripper Hand-E a une course de 50mm, 50% = 25mm
GRIPPER_OUVERTURE_MAX = 25  # mm


class ChessRobotPlayer:
    def __init__(self, fichier_mapping="chess_board_positions.json"):
        self.fichier_mapping = fichier_mapping

        # Charger le mapping
        if not os.path.exists(fichier_mapping):
            raise FileNotFoundError(f"Fichier de mapping non trouvé: {fichier_mapping}")

        with open(fichier_mapping, 'r') as f:
            data = json.load(f)

        self.cases = data.get("cases", {})
        self.position_securite_globale = data.get("position_securite_globale")

        # Charger les hauteurs relatives depuis le JSON (ou utiliser les défauts)
        self.delta_hauteur_securite = data.get("delta_hauteur_securite", DELTA_HAUTEUR_SECURITE)
        self.delta_hauteur_approche = data.get("delta_hauteur_approche", DELTA_HAUTEUR_APPROCHE)
        self.delta_hauteur_relache = data.get("delta_hauteur_relache", DELTA_HAUTEUR_RELACHE)

        print(f"✓ Mapping chargé: {len(self.cases)} cases")
        print(
            f"  Hauteurs: sécurité=+{self.delta_hauteur_securite * 1000:.0f}mm, approche=+{self.delta_hauteur_approche * 1000:.0f}mm, relâche=+{self.delta_hauteur_relache * 1000:.0f}mm")

        # Connexion robot
        print("Connexion au robot...")
        self.rtde_c = RTDEControlInterface(ROBOT_IP)
        self.rtde_r = RTDEReceiveInterface(ROBOT_IP)

        # Initialisation gripper
        print("Activation du gripper...")
        self.gripper = RobotiqGripper(self.rtde_c)
        self.gripper.activate()
        self.gripper.set_force(40)  # Force modérée pour les pièces
        self.gripper.set_speed(150)

        # Ouverture limitée à 50% pour éviter de cogner les pièces voisines
        self.gripper_ouverture_max = GRIPPER_OUVERTURE_MAX
        self.gripper.move(self.gripper_ouverture_max)

        self.piece_en_main = False

        print(f"✓ Robot prêt! (gripper ouverture max: {self.gripper_ouverture_max}mm)")

    def get_case_position(self, case):
        """Retourne la position TCP d'une case"""
        case = case.lower()
        if case not in self.cases:
            raise ValueError(f"Case {case} non mappée")
        return self.cases[case]["tcp"]

    def get_case_joints(self, case):
        """Retourne les angles joints d'une case"""
        case = case.lower()
        if case not in self.cases:
            raise ValueError(f"Case {case} non mappée")
        return self.cases[case]["joints"]

    def position_avec_delta_z(self, tcp, delta_z):
        """Retourne une position TCP avec un décalage en Z"""
        pos = list(tcp)
        pos[2] += delta_z
        return pos

    def aller_position_securite(self):
        """Va à la position de sécurité globale au-dessus de l'échiquier"""
        if self.position_securite_globale:
            print("↑ Position de sécurité globale...")
            self.rtde_c.moveL(self.position_securite_globale, VITESSE_LINEAIRE, ACCELERATION_LINEAIRE)
        else:
            # Si pas de position de sécurité globale, on monte depuis la position actuelle
            pose = self.rtde_r.getActualTCPPose()
            pose_haute = self.position_avec_delta_z(pose, self.delta_hauteur_securite)
            print(f"↑ Montée de {self.delta_hauteur_securite * 1000:.0f}mm...")
            self.rtde_c.moveL(pose_haute, VITESSE_LINEAIRE, ACCELERATION_LINEAIRE)

    def aller_case(self, case, hauteur="approche"):
        """
        Déplace le robot vers une case
        hauteur: "securite", "approche", "prise", ou "relache"
        Les hauteurs sont relatives à la position de prise enregistrée
        """
        case = case.lower()
        if case not in self.cases:
            print(f"⚠ Case {case} non mappée!")
            return False

        tcp_prise = self.get_case_position(case)  # Position de prise enregistrée

        # Calculer le delta Z selon la hauteur demandée
        if hauteur == "securite":
            delta_z = self.delta_hauteur_securite
        elif hauteur == "approche":
            delta_z = self.delta_hauteur_approche
        elif hauteur == "relache":
            delta_z = self.delta_hauteur_relache
        else:  # prise
            delta_z = 0.0

        position_cible = self.position_avec_delta_z(tcp_prise, delta_z)

        print(f"→ Case {case.upper()} (hauteur: {hauteur}, Z={position_cible[2]:.4f})")
        self.rtde_c.moveL(position_cible, VITESSE_LINEAIRE, ACCELERATION_LINEAIRE)
        return True

    def prendre_piece(self, case):
        """
        Prend une pièce sur une case
        Séquence: approche -> descente -> fermer gripper -> remontée
        """
        case = case.lower()
        print(f"\n🎯 Prise de pièce sur {case.upper()}...")

        # 1. Position au-dessus de la case
        if not self.aller_case(case, "approche"):
            return False
        time.sleep(0.2)

        # 2. Descente vers la pièce
        self.aller_case(case, "prise")
        time.sleep(0.3)

        # 3. Fermer le gripper
        print("✊ Fermeture gripper...")
        self.gripper.close()
        time.sleep(0.3)
        self.piece_en_main = True

        # 4. Remonter
        self.aller_case(case, "approche")
        time.sleep(0.2)

        print(f"✓ Pièce prise sur {case.upper()}")
        return True

    def poser_piece(self, case):
        """
        Pose une pièce sur une case
        Séquence: approche -> descente à hauteur RELACHE (+2mm) -> ouvrir gripper -> remontée
        """
        case = case.lower()

        if not self.piece_en_main:
            print("⚠ Pas de pièce en main!")
            return False

        print(f"\n🎯 Pose de pièce sur {case.upper()}...")

        # 1. Position au-dessus de la case
        if not self.aller_case(case, "approche"):
            return False
        time.sleep(0.2)

        # 2. Descente à hauteur de RELÂCHE (+2mm par rapport à prise)
        # Cela évite que la pièce appuie sur le plexiglas
        self.aller_case(case, "relache")
        time.sleep(0.3)

        # 3. Ouvrir le gripper (ouverture limitée)
        print(
            f"✋ Ouverture gripper ({self.gripper_ouverture_max}mm) - hauteur relâche +{self.delta_hauteur_relache * 1000:.0f}mm")
        self.gripper.move(self.gripper_ouverture_max)
        time.sleep(0.3)
        self.piece_en_main = False

        # 4. Remonter
        self.aller_case(case, "approche")
        time.sleep(0.2)

        print(f"✓ Pièce posée sur {case.upper()}")
        return True

    def deplacer_piece(self, case_depart, case_arrivee):
        """
        Déplace une pièce d'une case à une autre
        """
        print(f"\n{'=' * 50}")
        print(f"  DÉPLACEMENT: {case_depart.upper()} → {case_arrivee.upper()}")
        print(f"{'=' * 50}")

        # Prendre la pièce
        if not self.prendre_piece(case_depart):
            return False

        # Poser la pièce
        if not self.poser_piece(case_arrivee):
            return False

        print(f"\n✓ Déplacement {case_depart.upper()} → {case_arrivee.upper()} terminé!")
        return True

    def capturer_piece(self, case_depart, case_arrivee, case_capture=None):
        """
        Capture une pièce:
        1. Retire la pièce capturée (vers une zone de capture)
        2. Déplace la pièce qui capture

        case_capture: zone où déposer la pièce capturée (si None, utilise une position par défaut)
        """
        print(f"\n{'=' * 50}")
        print(f"  CAPTURE: {case_depart.upper()} prend {case_arrivee.upper()}")
        print(f"{'=' * 50}")

        # 1. Retirer la pièce capturée
        print("\n1. Retrait de la pièce capturée...")
        if not self.prendre_piece(case_arrivee):
            return False

        # Aller à la zone de capture (ou position de sécurité si non définie)
        if case_capture and case_capture in self.cases:
            self.poser_piece(case_capture)
        else:
            # Poser à côté de l'échiquier (position de sécurité)
            self.aller_position_securite()
            print(f"✋ Ouverture gripper (zone de capture, {self.gripper_ouverture_max}mm)...")
            self.gripper.move(self.gripper_ouverture_max)
            self.piece_en_main = False

        # 2. Déplacer la pièce qui capture
        print("\n2. Déplacement de la pièce capturante...")
        if not self.deplacer_piece(case_depart, case_arrivee):
            return False

        print(f"\n✓ Capture terminée!")
        return True

    def executer_coup(self, coup):
        """
        Exécute un coup en notation simplifiée
        Formats supportés:
        - "e2e4" ou "e2-e4": déplacement simple
        - "e4xd5" ou "e4d5x": capture (retire d5 puis déplace e4->d5)
        """
        coup = coup.lower().replace("-", "").replace(" ", "")

        # Détecter si c'est une capture
        if 'x' in coup:
            parts = coup.split('x')
            if len(parts) == 2:
                if len(parts[0]) == 2 and len(parts[1]) == 2:
                    return self.capturer_piece(parts[0], parts[1])
                elif len(parts[0]) == 4:
                    return self.capturer_piece(parts[0][:2], parts[0][2:])

        # Déplacement simple
        if len(coup) == 4:
            case_depart = coup[:2]
            case_arrivee = coup[2:]
            return self.deplacer_piece(case_depart, case_arrivee)

        print(f"⚠ Format de coup non reconnu: {coup}")
        print("  Formats valides: e2e4, e2-e4, e4xd5")
        return False

    def test_case(self, case):
        """Test: va sur une case et fait un cycle gripper"""
        print(f"\n🔧 Test case {case.upper()}...")

        self.aller_case(case, "approche")
        time.sleep(0.5)

        self.aller_case(case, "prise")
        time.sleep(0.3)

        print("Test gripper...")
        self.gripper.close()
        time.sleep(0.5)
        self.gripper.move(self.gripper_ouverture_max)
        time.sleep(0.3)

        self.aller_case(case, "approche")
        print(f"✓ Test {case.upper()} terminé")

    def afficher_cases_disponibles(self):
        """Affiche les cases mappées"""
        print("\n╔═══════════════════════════════════════════════════════════════════╗")
        print("║                    CASES DISPONIBLES                              ║")
        print("╠═══════════════════════════════════════════════════════════════════╣")

        colonnes = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        rangees = ['1', '2', '3', '4', '5', '6', '7', '8']

        for row in range(7, -1, -1):
            ligne = f"║  {row + 1} │ "
            for col in range(8):
                case = f"{colonnes[col]}{rangees[row]}"
                if case in self.cases:
                    ligne += " ✓ "
                else:
                    ligne += " · "
            ligne += f"│  {row + 1}   ║"
            print(ligne)

        print("║    ├─────────────────────────────┤      ║")
        print("║      a  b  c  d  e  f  g  h             ║")
        print("╠═══════════════════════════════════════════════════════════════════╣")
        print(f"║  Total: {len(self.cases)} cases mappées                                      ║")
        print(
            f"║  Position sécurité globale: {'✓' if self.position_securite_globale else '✗'}                               ║")
        print("╠═══════════════════════════════════════════════════════════════════╣")
        print(f"║  Hauteurs relatives (par rapport à position de prise):           ║")
        print(
            f"║    Sécurité: +{self.delta_hauteur_securite * 1000:.0f}mm                                            ║")
        print(
            f"║    Approche: +{self.delta_hauteur_approche * 1000:.0f}mm                                            ║")
        print(f"║    Relâche:  +{self.delta_hauteur_relache * 1000:.0f}mm (pour poser sans appuyer sur plexi)       ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")

    def mode_interactif(self):
        """Mode interactif pour exécuter des coups"""
        print("\n" + "=" * 60)
        print("  MODE INTERACTIF - CONTRÔLE ROBOT ÉCHECS")
        print("=" * 60)
        print("""
Commandes:
  <coup>     : Exécuter un coup (ex: e2e4, e4xd5)
  go <case>  : Aller à une case (ex: go e4)
  test <case>: Tester une case (cycle gripper)
  take <case>: Prendre pièce sur une case
  drop <case>: Poser pièce sur une case
  open       : Ouvrir gripper
  close      : Fermer gripper
  home       : Position de sécurité
  map        : Afficher cases disponibles
  pos        : Position actuelle
  quit       : Quitter
""")

        while True:
            try:
                cmd = input("\n♟ > ").strip().lower()

                if not cmd:
                    continue

                parts = cmd.split()
                action = parts[0]

                if action in ['quit', 'exit', 'q']:
                    break

                elif action == 'go' and len(parts) > 1:
                    self.aller_case(parts[1], "approche")

                elif action == 'test' and len(parts) > 1:
                    self.test_case(parts[1])

                elif action == 'take' and len(parts) > 1:
                    self.prendre_piece(parts[1])

                elif action == 'drop' and len(parts) > 1:
                    self.poser_piece(parts[1])

                elif action == 'open':
                    self.gripper.move(self.gripper_ouverture_max)
                    self.piece_en_main = False
                    print(f"✋ Gripper ouvert ({self.gripper_ouverture_max}mm)")

                elif action == 'close':
                    self.gripper.close()
                    self.piece_en_main = True
                    print("✊ Gripper fermé")

                elif action == 'home':
                    self.aller_position_securite()

                elif action == 'map':
                    self.afficher_cases_disponibles()

                elif action == 'pos':
                    pose = self.rtde_r.getActualTCPPose()
                    print(f"TCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
                    print(f"Rot: RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
                    print(f"Pièce en main: {'OUI' if self.piece_en_main else 'NON'}")

                elif len(cmd) >= 4:
                    # Essayer d'interpréter comme un coup
                    self.executer_coup(cmd)

                else:
                    print("⚠ Commande non reconnue. Tapez 'quit' pour quitter.")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠ Erreur: {e}")

        print("\nFermeture...")

    def fermer(self):
        """Ferme proprement les connexions"""
        self.gripper.move(self.gripper_ouverture_max)
        self.rtde_c.stopScript()
        print("Déconnecté")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Contrôle robot pour échecs")
    parser.add_argument("-f", "--fichier", default="chess_board_positions.json",
                        help="Fichier de mapping des cases")
    parser.add_argument("-c", "--coup", help="Exécuter un coup et quitter")
    parser.add_argument("-t", "--test", help="Tester une case")
    parser.add_argument("-i", "--interactif", action="store_true",
                        help="Mode interactif")

    args = parser.parse_args()

    try:
        robot = ChessRobotPlayer(args.fichier)

        if args.coup:
            robot.executer_coup(args.coup)
        elif args.test:
            robot.test_case(args.test)
        else:
            # Mode interactif par défaut
            robot.afficher_cases_disponibles()
            robot.mode_interactif()

        robot.fermer()

    except FileNotFoundError as e:
        print(f"Erreur: {e}")
        print("Exécutez d'abord le script de mapping: python chess_board_mapping.py")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()