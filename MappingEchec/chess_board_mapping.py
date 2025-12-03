#!/usr/bin/env python3
"""
Script de mapping des cases de l'échiquier pour robot UR5e + Robotiq Hand-E
Permet d'enregistrer les positions TCP de chaque case en mode freedrive
avec notation échiquéenne standard (a1-h8)
"""

from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper
import sys
import tty
import termios
import json
from datetime import datetime
import time
import select
import os

# Configuration robot
ROBOT_IP = "192.168.0.11"

# Colonnes et rangées de l'échiquier
COLONNES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
RANGEES = ['1', '2', '3', '4', '5', '6', '7', '8']

# Hauteurs de travail RELATIVES à la position enregistrée (en mètres)
# La position enregistrée = hauteur de PRISE (là où le gripper attrape la pièce)
DELTA_HAUTEUR_SECURITE = 0.08  # 8cm au-dessus de la position de prise
DELTA_HAUTEUR_APPROCHE = 0.03  # 3cm au-dessus de la position de prise
DELTA_HAUTEUR_RELACHE = 0.002  # +2mm pour relâcher la pièce (évite d'appuyer sur le plexi)


class ChessBoardMapper:
    def __init__(self):
        print("Connexion au robot...")
        self.rtde_c = RTDEControlInterface(ROBOT_IP)
        self.rtde_r = RTDEReceiveInterface(ROBOT_IP)

        print("Activation du gripper...")
        self.gripper = RobotiqGripper(self.rtde_c)
        self.gripper.activate()
        self.gripper.set_force(50)
        self.gripper.set_speed(100)

        self.freedrive_actif = False
        self.gripper_ouvert = True

        # Ouverture limitée à 50% pour éviter de cogner les pièces voisines
        # Le gripper Hand-E a une course de 50mm, donc 50% = 25mm
        self.GRIPPER_OUVERTURE_MAX = 25  # mm (50% de 50mm)
        self.gripper.move(self.GRIPPER_OUVERTURE_MAX)

        # Données de mapping
        self.positions = {}  # {"e4": {"tcp": [...], "joints": [...]}, ...}
        self.position_securite_globale = None  # Position de sécurité haute au-dessus de l'échiquier

        # Hauteurs relatives (sauvegardées dans le JSON pour le script de jeu)
        self.delta_hauteur_securite = DELTA_HAUTEUR_SECURITE
        self.delta_hauteur_approche = DELTA_HAUTEUR_APPROCHE
        self.delta_hauteur_relache = DELTA_HAUTEUR_RELACHE

        # Case courante pour navigation rapide
        self.col_index = 0  # a=0, b=1, ..., h=7
        self.row_index = 0  # 1=0, 2=1, ..., 8=7

        # Charger les données existantes si disponibles
        self.fichier_mapping = "chess_board_positions.json"
        self.charger_mapping()

        print("Système prêt !")

    def charger_mapping(self):
        """Charge un mapping existant s'il existe"""
        if os.path.exists(self.fichier_mapping):
            try:
                with open(self.fichier_mapping, 'r') as f:
                    data = json.load(f)
                    self.positions = data.get("cases", {})
                    self.position_securite_globale = data.get("position_securite_globale")
                    self.delta_hauteur_securite = data.get("delta_hauteur_securite", DELTA_HAUTEUR_SECURITE)
                    self.delta_hauteur_approche = data.get("delta_hauteur_approche", DELTA_HAUTEUR_APPROCHE)
                    self.delta_hauteur_relache = data.get("delta_hauteur_relache", DELTA_HAUTEUR_RELACHE)
                print(f"✓ Mapping chargé: {len(self.positions)} cases")
            except Exception as e:
                print(f"⚠ Erreur chargement: {e}")

    def sauvegarder_mapping(self):
        """Sauvegarde le mapping dans un fichier JSON"""
        data = {
            "cases": self.positions,
            "position_securite_globale": self.position_securite_globale,
            "delta_hauteur_securite": self.delta_hauteur_securite,
            "delta_hauteur_approche": self.delta_hauteur_approche,
            "delta_hauteur_relache": self.delta_hauteur_relache,
            "metadata": {
                "date_creation": datetime.now().isoformat(),
                "robot_ip": ROBOT_IP,
                "nb_cases": len(self.positions),
                "description": "Position TCP = hauteur de PRISE. Les hauteurs sont calculées relativement."
            }
        }

        with open(self.fichier_mapping, 'w') as f:
            json.dump(data, f, indent=2)

        # Backup horodaté
        backup_name = f"chess_board_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_name, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Sauvegardé: {self.fichier_mapping} (+ backup {backup_name})")
        print(
            f"  Hauteurs relatives: sécurité={self.delta_hauteur_securite * 1000:.0f}mm, approche={self.delta_hauteur_approche * 1000:.0f}mm, relâche=+{self.delta_hauteur_relache * 1000:.0f}mm")

    def get_case_courante(self):
        """Retourne la notation de la case courante"""
        return f"{COLONNES[self.col_index]}{RANGEES[self.row_index]}"

    def case_suivante(self):
        """Passe à la case suivante (parcours a1->h1, a2->h2, etc.)"""
        self.col_index += 1
        if self.col_index > 7:
            self.col_index = 0
            self.row_index += 1
            if self.row_index > 7:
                self.row_index = 0
                print("\n⚠ Retour au début de l'échiquier")

    def case_precedente(self):
        """Revient à la case précédente"""
        self.col_index -= 1
        if self.col_index < 0:
            self.col_index = 7
            self.row_index -= 1
            if self.row_index < 0:
                self.row_index = 7

    def aller_a_case(self, notation):
        """Parse une notation et positionne les index"""
        if len(notation) != 2:
            return False
        col = notation[0].lower()
        row = notation[1]
        if col in COLONNES and row in RANGEES:
            self.col_index = COLONNES.index(col)
            self.row_index = RANGEES.index(row)
            return True
        return False

    def enregistrer_case_courante(self):
        """Enregistre la position actuelle pour la case courante (position de PRISE)"""
        pose = self.rtde_r.getActualTCPPose()
        joints = self.rtde_r.getActualQ()

        case = self.get_case_courante()
        self.positions[case] = {
            "tcp": list(pose),
            "joints": list(joints),
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n✓ Case {case} enregistrée (position de PRISE):")
        print(f"  TCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
        print(
            f"  → Approche sera à Z={pose[2] + self.delta_hauteur_approche:.4f} (+{self.delta_hauteur_approche * 1000:.0f}mm)")
        print(
            f"  → Relâche sera à Z={pose[2] + self.delta_hauteur_relache:.4f} (+{self.delta_hauteur_relache * 1000:.0f}mm)")

        # Auto-avance à la case suivante
        self.case_suivante()
        print(f"  → Prochaine case: {self.get_case_courante()}")

    def enregistrer_position_securite(self):
        """Enregistre la position de sécurité globale au-dessus de l'échiquier"""
        pose = self.rtde_r.getActualTCPPose()
        self.position_securite_globale = list(pose)
        print(f"\n✓ Position de sécurité globale enregistrée:")
        print(f"  TCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
        print(f"  (Position haute pour les déplacements entre cases)")

    def toggle_freedrive(self):
        """Active/désactive le mode freedrive"""
        if self.freedrive_actif:
            self.rtde_c.endFreedriveMode()
            self.freedrive_actif = False
            print("🔒 Freedrive DÉSACTIVÉ")
        else:
            self.rtde_c.freedriveMode()
            self.freedrive_actif = True
            print("🆓 Freedrive ACTIVÉ - Positionne le robot sur la case")

    def toggle_gripper(self):
        """Ouvre/ferme le gripper (ouverture limitée à 50%)"""
        if self.gripper_ouvert:
            self.gripper.close()
            self.gripper_ouvert = False
            print("✊ Gripper FERMÉ")
        else:
            self.gripper.move(self.GRIPPER_OUVERTURE_MAX)
            self.gripper_ouvert = True
            print(f"✋ Gripper OUVERT ({self.GRIPPER_OUVERTURE_MAX}mm / 50%)")

    def tester_prehension(self):
        """Test de préhension: ferme puis ouvre le gripper (50%)"""
        print("🔄 Test de préhension...")
        self.gripper.close()
        time.sleep(0.5)
        # Lire la position du gripper pour vérifier si une pièce est présente
        # (le gripper ne se fermera pas complètement s'il y a une pièce)
        self.gripper.move(self.GRIPPER_OUVERTURE_MAX)
        print(f"✓ Test terminé (ouverture: {self.GRIPPER_OUVERTURE_MAX}mm)")

    def afficher_progression(self):
        """Affiche la grille avec les cases enregistrées"""
        print("\n╔═══════════════════════════════════════════════════════════════════╗")
        print("║                    ÉTAT DU MAPPING                                ║")
        print("╠═══════════════════════════════════════════════════════════════════╣")

        # Afficher l'échiquier (rangée 8 en haut)
        for row in range(7, -1, -1):
            ligne = f"║  {row + 1} │ "
            for col in range(8):
                case = f"{COLONNES[col]}{RANGEES[row]}"
                if case in self.positions:
                    ligne += " ✓ "
                elif case == self.get_case_courante():
                    ligne += " ▶ "
                else:
                    ligne += " · "
            ligne += f"│  {row + 1}   ║"
            print(ligne)

        print("║    ├─────────────────────────────┤      ║")
        print("║      a  b  c  d  e  f  g  h             ║")
        print("╠═══════════════════════════════════════════════════════════════════╣")
        print(f"║  Cases enregistrées: {len(self.positions)}/64                                   ║")
        print(f"║  Case courante: {self.get_case_courante()}                                          ║")
        print(
            f"║  Position sécurité globale: {'✓' if self.position_securite_globale else '✗'}                               ║")
        print("╠═══════════════════════════════════════════════════════════════════╣")
        print(f"║  Hauteurs relatives:                                              ║")
        print(
            f"║    Sécurité: +{self.delta_hauteur_securite * 1000:.0f}mm | Approche: +{self.delta_hauteur_approche * 1000:.0f}mm | Relâche: +{self.delta_hauteur_relache * 1000:.0f}mm   ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")

    def get_key_non_blocking(self):
        """Lecture non-bloquante du clavier"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    ch3 = sys.stdin.read(1)
                    return ch + ch2 + ch3
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def get_line_input(self, prompt):
        """Lecture d'une ligne complète (mode normal)"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return input(prompt)
        except:
            return ""

    def print_help(self):
        """Affiche l'aide"""
        print("""
╔═══════════════════════════════════════════════════════════════════╗
║         MAPPING ÉCHIQUIER - UR5e + Hand-E                         ║
╠═══════════════════════════════════════════════════════════════════╣
║  IMPORTANT: Enregistrer la position de PRISE (gripper sur pièce)  ║
║  Les hauteurs d'approche/relâche sont calculées automatiquement   ║
╠═══════════════════════════════════════════════════════════════════╣
║  MODE FREEDRIVE:                                                  ║
║    f         : Activer/Désactiver freedrive                       ║
║                                                                   ║
║  ENREGISTREMENT:                                                  ║
║    ESPACE    : Enregistrer case courante + passer à suivante      ║
║    ENTRÉE    : Enregistrer case courante (sans avancer)           ║
║    n         : Saisir une case spécifique (ex: e4)               ║
║    p         : Enregistrer position de sécurité GLOBALE          ║
║                                                                   ║
║  NAVIGATION:                                                      ║
║    →/←       : Case suivante/précédente                           ║
║    ↑/↓       : Rangée suivante/précédente                         ║
║                                                                   ║
║  GRIPPER:                                                         ║
║    g         : Ouvrir/Fermer gripper                              ║
║    t         : Tester préhension (ferme puis ouvre)               ║
║                                                                   ║
║  HAUTEURS (modifiables):                                          ║
║    1         : Ajuster delta sécurité (+/- avec +/-)              ║
║    2         : Ajuster delta approche                             ║
║    3         : Ajuster delta relâche                              ║
║                                                                   ║
║  AFFICHAGE:                                                       ║
║    m         : Afficher la grille de progression                  ║
║    i         : Afficher position TCP actuelle                     ║
║    h         : Afficher cette aide                                ║
║                                                                   ║
║  FICHIERS:                                                        ║
║    s         : Sauvegarder le mapping                             ║
║    l         : Charger un mapping existant                        ║
║                                                                   ║
║  QUITTER:                                                         ║
║    ECHAP/q   : Quitter (sauvegarde automatique)                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    def run(self):
        """Boucle principale"""
        print("\nConnexion établie!")
        pose = self.rtde_r.getActualTCPPose()
        print(f"TCP actuel: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")

        self.print_help()
        self.afficher_progression()

        print(f"\n▶ Case courante: {self.get_case_courante()}")
        print("  Appuie sur 'f' pour activer freedrive, puis ESPACE pour enregistrer")

        try:
            while True:
                key = self.get_key_non_blocking()

                if key is None:
                    continue

                # Quitter
                if key in ['\x1b', '\x03', 'q']:
                    print("\n\nSauvegarde avant fermeture...")
                    self.sauvegarder_mapping()
                    break

                # Freedrive
                elif key == 'f':
                    self.toggle_freedrive()

                # Enregistrer case courante + avancer
                elif key == ' ':
                    self.enregistrer_case_courante()

                # Enregistrer case courante sans avancer
                elif key == '\r' or key == '\n':
                    pose = self.rtde_r.getActualTCPPose()
                    joints = self.rtde_r.getActualQ()
                    case = self.get_case_courante()
                    self.positions[case] = {
                        "tcp": list(pose),
                        "joints": list(joints),
                        "timestamp": datetime.now().isoformat()
                    }
                    print(f"\n✓ Case {case} enregistrée (position maintenue)")

                # Saisir case spécifique
                elif key == 'n':
                    # Restaurer le terminal pour l'input
                    if self.freedrive_actif:
                        self.rtde_c.endFreedriveMode()
                        was_freedrive = True
                    else:
                        was_freedrive = False

                    fd = sys.stdin.fileno()
                    old = termios.tcgetattr(fd)
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)

                    notation = input("\nEntrez la case (ex: e4): ").strip()
                    if self.aller_a_case(notation):
                        print(f"✓ Case courante: {self.get_case_courante()}")
                    else:
                        print("⚠ Notation invalide")

                    if was_freedrive:
                        self.rtde_c.freedriveMode()
                        self.freedrive_actif = True

                # Position de sécurité globale
                elif key == 'p':
                    self.enregistrer_position_securite()

                # Navigation
                elif key == '\x1b[C':  # Droite
                    self.case_suivante()
                    print(f"▶ Case: {self.get_case_courante()}")
                elif key == '\x1b[D':  # Gauche
                    self.case_precedente()
                    print(f"▶ Case: {self.get_case_courante()}")
                elif key == '\x1b[A':  # Haut
                    self.row_index = min(7, self.row_index + 1)
                    print(f"▶ Case: {self.get_case_courante()}")
                elif key == '\x1b[B':  # Bas
                    self.row_index = max(0, self.row_index - 1)
                    print(f"▶ Case: {self.get_case_courante()}")

                # Gripper
                elif key == 'g':
                    self.toggle_gripper()
                elif key == 't':
                    self.tester_prehension()

                # Affichage
                elif key == 'm':
                    self.afficher_progression()
                elif key == 'i':
                    pose = self.rtde_r.getActualTCPPose()
                    print(f"\nTCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
                    print(f"Rot: RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
                    print(f"Case courante: {self.get_case_courante()}")
                    print(f"Freedrive: {'OUI' if self.freedrive_actif else 'NON'}")
                    print(f"Cette position = hauteur de PRISE")
                    print(
                        f"  → Approche: Z={pose[2] + self.delta_hauteur_approche:.4f} (+{self.delta_hauteur_approche * 1000:.0f}mm)")
                    print(
                        f"  → Relâche:  Z={pose[2] + self.delta_hauteur_relache:.4f} (+{self.delta_hauteur_relache * 1000:.0f}mm)")
                elif key == 'h':
                    self.print_help()

                # Sauvegarde/Chargement
                elif key == 's':
                    self.sauvegarder_mapping()
                elif key == 'l':
                    self.charger_mapping()
                    self.afficher_progression()

        finally:
            if self.freedrive_actif:
                self.rtde_c.endFreedriveMode()
            self.rtde_c.stopScript()
            print("Déconnecté")


def main():
    mapper = ChessBoardMapper()
    mapper.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterruption...")
    except Exception as e:
        print(f"\nErreur: {e}")
        import traceback

        traceback.print_exc()