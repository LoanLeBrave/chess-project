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

# Taille des cases de l'échiquier (en mètres)
TAILLE_CASE = 0.035  # 35mm

# Paramètres de vitesse pour le contrôle manuel
SPEED = 0.05  # Vitesse linéaire (m/s) - plus lent pour précision
SPEED_ROT = 0.2  # Vitesse rotation (rad/s)
ACCELERATION = 0.3  # Accélération

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

        # Vitesses pour le contrôle manuel (ajustables avec +/-)
        self.speed = SPEED
        self.speed_rot = SPEED_ROT

        # Taille des cases pour l'interpolation
        self.taille_case = TAILLE_CASE

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
            print("🔒 Freedrive DÉSACTIVÉ - Contrôle clavier actif")
        else:
            self.rtde_c.speedStop()  # Arrêter tout mouvement avant freedrive
            self.rtde_c.freedriveMode()
            self.freedrive_actif = True
            print("🆓 Freedrive ACTIVÉ - Déplace le robot à la main")

    def move_speed(self, vx=0, vy=0, vz=0, vrx=0, vry=0, vrz=0):
        """Déplace le robot en vitesse"""
        self.rtde_c.speedL([vx, vy, vz, vrx, vry, vrz], ACCELERATION, 0.1)

    def stop_robot(self):
        """Arrête le mouvement du robot"""
        self.rtde_c.speedStop()

    def calculer_position_interpolee(self, case):
        """
        Calcule la position estimée d'une case en fonction des cases déjà enregistrées.
        Utilise l'espacement de 35mm entre les cases.
        Retourne (tcp_estime, confiance) ou (None, 0) si impossible
        """
        col_idx = COLONNES.index(case[0])
        row_idx = RANGEES.index(case[1])

        if len(self.positions) == 0:
            return None, 0

        # Chercher les cases de référence les plus proches
        meilleures_refs = []

        for case_ref, data in self.positions.items():
            ref_col = COLONNES.index(case_ref[0])
            ref_row = RANGEES.index(case_ref[1])

            # Distance en cases
            delta_col = col_idx - ref_col
            delta_row = row_idx - ref_row
            distance = abs(delta_col) + abs(delta_row)

            meilleures_refs.append({
                'case': case_ref,
                'tcp': data['tcp'],
                'delta_col': delta_col,
                'delta_row': delta_row,
                'distance': distance
            })

        # Trier par distance
        meilleures_refs.sort(key=lambda x: x['distance'])

        if len(meilleures_refs) == 0:
            return None, 0

        # Utiliser la case la plus proche comme référence
        ref = meilleures_refs[0]
        tcp_ref = ref['tcp']

        # Calculer le décalage en mètres
        # Note: On suppose que X = colonnes (a->h) et Y = rangées (1->8)
        # Tu peux inverser si ton repère est différent
        delta_x = ref['delta_col'] * self.taille_case
        delta_y = ref['delta_row'] * self.taille_case

        # Si on a 2+ cases, on peut déduire l'orientation du plateau
        if len(meilleures_refs) >= 2:
            # Calculer le vecteur moyen entre cases adjacentes pour affiner
            vecteurs_x = []
            vecteurs_y = []

            for i, ref1 in enumerate(self.positions.items()):
                for ref2 in list(self.positions.items())[i + 1:]:
                    case1, data1 = ref1
                    case2, data2 = ref2

                    col1, row1 = COLONNES.index(case1[0]), RANGEES.index(case1[1])
                    col2, row2 = COLONNES.index(case2[0]), RANGEES.index(case2[1])

                    dcol = col2 - col1
                    drow = row2 - row1

                    if dcol != 0 or drow != 0:
                        dx = data2['tcp'][0] - data1['tcp'][0]
                        dy = data2['tcp'][1] - data1['tcp'][1]

                        if dcol != 0:
                            vecteurs_x.append(dx / dcol)
                        if drow != 0:
                            vecteurs_y.append(dy / drow)

            # Utiliser la moyenne des vecteurs si disponible
            if vecteurs_x:
                delta_x = ref['delta_col'] * (sum(vecteurs_x) / len(vecteurs_x))
            if vecteurs_y:
                delta_y = ref['delta_row'] * (sum(vecteurs_y) / len(vecteurs_y))

        # Calculer la position estimée
        tcp_estime = list(tcp_ref)
        tcp_estime[0] += delta_x
        tcp_estime[1] += delta_y
        # Z et rotations restent identiques

        # Confiance basée sur la distance et le nombre de références
        confiance = max(0, 100 - ref['distance'] * 15)
        if len(self.positions) >= 3:
            confiance = min(100, confiance + 20)

        return tcp_estime, confiance

    def aller_position_estimee(self, case=None):
        """
        Déplace le robot vers la position estimée de la case courante (ou spécifiée)
        """
        if case is None:
            case = self.get_case_courante()

        if case in self.positions:
            print(f"⚠ Case {case} déjà enregistrée, utilisation de la position existante")
            tcp = self.positions[case]['tcp']
            self.rtde_c.moveL(tcp, self.speed * 2, ACCELERATION)
            return True

        tcp_estime, confiance = self.calculer_position_interpolee(case)

        if tcp_estime is None:
            print(f"⚠ Impossible d'estimer la position de {case} - aucune référence")
            return False

        print(f"\n🎯 Position estimée pour {case} (confiance: {confiance:.0f}%):")
        print(f"   X={tcp_estime[0]:.4f} Y={tcp_estime[1]:.4f} Z={tcp_estime[2]:.4f}")
        print(f"   Déplacement en cours...")

        self.rtde_c.moveL(tcp_estime, self.speed * 2, ACCELERATION)
        print(f"   ✓ Arrivé - Ajuste finement avec les flèches puis ESPACE pour enregistrer")
        return True

    def afficher_estimation_case(self, case=None):
        """Affiche l'estimation de position pour une case"""
        if case is None:
            case = self.get_case_courante()

        if case in self.positions:
            tcp = self.positions[case]['tcp']
            print(f"\n📍 Case {case} (ENREGISTRÉE):")
            print(f"   X={tcp[0]:.4f} Y={tcp[1]:.4f} Z={tcp[2]:.4f}")
            return

        tcp_estime, confiance = self.calculer_position_interpolee(case)

        if tcp_estime is None:
            print(f"\n❓ Case {case}: impossible d'estimer (enregistre d'abord quelques cases)")
        else:
            print(f"\n🎯 Case {case} (ESTIMÉE - confiance {confiance:.0f}%):")
            print(f"   X={tcp_estime[0]:.4f} Y={tcp_estime[1]:.4f} Z={tcp_estime[2]:.4f}")
            print(f"   Appuie sur 'v' pour aller à cette position")

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
        print(
            f"║  Taille cases: {self.taille_case * 1000:.0f}mm x {self.taille_case * 1000:.0f}mm (pour interpolation)            ║")
        print(
            f"║  Hauteurs: sécurité +{self.delta_hauteur_securite * 1000:.0f}mm | approche +{self.delta_hauteur_approche * 1000:.0f}mm | relâche +{self.delta_hauteur_relache * 1000:.0f}mm ║")
        print(f"║  Vitesse actuelle: {self.speed * 1000:.0f} mm/s                                    ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")

        # Afficher l'estimation pour la case courante
        if self.get_case_courante() not in self.positions and len(self.positions) > 0:
            self.afficher_estimation_case()

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
║  Cases de 35mm x 35mm - interpolation automatique disponible      ║
╠═══════════════════════════════════════════════════════════════════╣
║  MODE FREEDRIVE:                                                  ║
║    f         : Activer/Désactiver freedrive                       ║
║                                                                   ║
║  CONTRÔLE MANUEL (hors freedrive) - positionnement précis:        ║
║    ↑/↓       : Avancer/Reculer (Y)                               ║
║    ←/→       : Gauche/Droite (X)                                 ║
║    z/s       : Monter/Descendre (Z)                              ║
║    a/e       : Rotation RX                                        ║
║    q/d       : Rotation RY                                        ║
║    w/x       : Rotation RZ                                        ║
║    +/-       : Ajuster la vitesse                                 ║
║                                                                   ║
║  INTERPOLATION (cases de 35mm):                                   ║
║    v         : Aller à la position ESTIMÉE de la case courante   ║
║    b         : Afficher l'estimation de la case courante         ║
║                                                                   ║
║  ENREGISTREMENT:                                                  ║
║    ESPACE    : Enregistrer case courante + passer à suivante      ║
║    ENTRÉE    : Enregistrer case courante (sans avancer)           ║
║    c         : Saisir une case spécifique (ex: e4)               ║
║    p         : Enregistrer position de sécurité GLOBALE          ║
║                                                                   ║
║  NAVIGATION CASES:                                                ║
║    n         : Case suivante                                      ║
║    N (maj)   : Case précédente                                    ║
║    u         : Rangée suivante                                    ║
║    j         : Rangée précédente                                  ║
║                                                                   ║
║  GRIPPER:                                                         ║
║    g         : Ouvrir/Fermer gripper                              ║
║    t         : Tester préhension (ferme puis ouvre)               ║
║                                                                   ║
║  AFFICHAGE:                                                       ║
║    m         : Afficher la grille de progression                  ║
║    i         : Afficher position TCP actuelle                     ║
║    h         : Afficher cette aide                                ║
║                                                                   ║
║  FICHIERS:                                                        ║
║    o         : Sauvegarder le mapping                             ║
║    l         : Charger un mapping existant                        ║
║                                                                   ║
║  QUITTER:                                                         ║
║    ECHAP/k   : Quitter (sauvegarde automatique)                   ║
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
        print("  Mode: CONTRÔLE CLAVIER (flèches pour bouger)")
        print("  Appuie sur 'f' pour freedrive, 'v' pour aller à position estimée")

        current_velocity = [0, 0, 0, 0, 0, 0]

        try:
            while True:
                key = self.get_key_non_blocking()

                new_velocity = [0, 0, 0, 0, 0, 0]

                if key is None:
                    # Pas de touche, arrêter si on bougeait
                    if not self.freedrive_actif and any(v != 0 for v in current_velocity):
                        self.stop_robot()
                    current_velocity = new_velocity
                    continue

                # === QUITTER ===
                if key in ['\x1b', '\x03', 'k']:
                    print("\n\nSauvegarde avant fermeture...")
                    self.stop_robot()
                    self.sauvegarder_mapping()
                    break

                # === FREEDRIVE ===
                elif key == 'f':
                    self.stop_robot()
                    self.toggle_freedrive()

                # === SI EN FREEDRIVE ===
                elif self.freedrive_actif:
                    if key == ' ':
                        self.enregistrer_case_courante()
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
                    elif key == 'g':
                        self.toggle_gripper()
                    elif key == 't':
                        self.tester_prehension()
                    elif key == 'n':
                        self.case_suivante()
                        print(f"▶ Case: {self.get_case_courante()}")
                        self.afficher_estimation_case()
                    elif key == 'N':
                        self.case_precedente()
                        print(f"▶ Case: {self.get_case_courante()}")
                    elif key == 'u':
                        self.row_index = min(7, self.row_index + 1)
                        print(f"▶ Case: {self.get_case_courante()}")
                    elif key == 'j':
                        self.row_index = max(0, self.row_index - 1)
                        print(f"▶ Case: {self.get_case_courante()}")
                    elif key == 'p':
                        self.enregistrer_position_securite()
                    elif key == 'm':
                        self.afficher_progression()
                    elif key == 'i':
                        pose = self.rtde_r.getActualTCPPose()
                        print(f"\nTCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
                        print(f"Mode: FREEDRIVE | Case: {self.get_case_courante()}")
                    elif key == 'b':
                        self.afficher_estimation_case()
                    elif key == 'h':
                        self.print_help()
                    elif key == 'o':
                        self.sauvegarder_mapping()
                    elif key == 'l':
                        self.charger_mapping()
                        self.afficher_progression()

                # === MODE CONTRÔLE MANUEL (hors freedrive) ===
                else:
                    # Déplacements linéaires (flèches et z/s)
                    if key == '\x1b[A':  # Haut - Y+
                        new_velocity[1] = self.speed
                    elif key == '\x1b[B':  # Bas - Y-
                        new_velocity[1] = -self.speed
                    elif key == '\x1b[C':  # Droite - X+
                        new_velocity[0] = self.speed
                    elif key == '\x1b[D':  # Gauche - X-
                        new_velocity[0] = -self.speed
                    elif key == 'z':  # Monter
                        new_velocity[2] = self.speed
                    elif key == 's':  # Descendre
                        new_velocity[2] = -self.speed

                    # Rotations
                    elif key == 'a':
                        new_velocity[3] = self.speed_rot
                    elif key == 'e':
                        new_velocity[3] = -self.speed_rot
                    elif key == 'q':
                        new_velocity[4] = self.speed_rot
                    elif key == 'd':
                        new_velocity[4] = -self.speed_rot
                    elif key == 'w':
                        new_velocity[5] = self.speed_rot
                    elif key == 'x':
                        new_velocity[5] = -self.speed_rot

                    # Vitesse
                    elif key == '+':
                        self.speed = min(self.speed + 0.01, 0.2)
                        self.speed_rot = min(self.speed_rot + 0.05, 0.5)
                        print(f"⚡ Vitesse: {self.speed * 1000:.0f} mm/s | {self.speed_rot:.2f} rad/s")
                    elif key == '-':
                        self.speed = max(self.speed - 0.01, 0.01)
                        self.speed_rot = max(self.speed_rot - 0.05, 0.05)
                        print(f"⚡ Vitesse: {self.speed * 1000:.0f} mm/s | {self.speed_rot:.2f} rad/s")

                    # Interpolation - aller à position estimée
                    elif key == 'v':
                        self.stop_robot()
                        self.aller_position_estimee()
                    elif key == 'b':
                        self.stop_robot()
                        self.afficher_estimation_case()

                    # Enregistrement
                    elif key == ' ':
                        self.stop_robot()
                        self.enregistrer_case_courante()
                    elif key == '\r' or key == '\n':
                        self.stop_robot()
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
                    elif key == 'c':
                        self.stop_robot()
                        fd = sys.stdin.fileno()
                        old = termios.tcgetattr(fd)
                        termios.tcsetattr(fd, termios.TCSADRAIN, old)

                        notation = input("\nEntrez la case (ex: e4): ").strip()
                        if self.aller_a_case(notation):
                            print(f"✓ Case courante: {self.get_case_courante()}")
                            self.afficher_estimation_case()
                        else:
                            print("⚠ Notation invalide")

                    # Navigation cases
                    elif key == 'n':
                        self.stop_robot()
                        self.case_suivante()
                        print(f"▶ Case: {self.get_case_courante()}")
                        self.afficher_estimation_case()
                    elif key == 'N':
                        self.stop_robot()
                        self.case_precedente()
                        print(f"▶ Case: {self.get_case_courante()}")
                    elif key == 'u':
                        self.stop_robot()
                        self.row_index = min(7, self.row_index + 1)
                        print(f"▶ Case: {self.get_case_courante()}")
                        self.afficher_estimation_case()
                    elif key == 'j':
                        self.stop_robot()
                        self.row_index = max(0, self.row_index - 1)
                        print(f"▶ Case: {self.get_case_courante()}")
                        self.afficher_estimation_case()

                    # Position sécurité
                    elif key == 'p':
                        self.stop_robot()
                        self.enregistrer_position_securite()

                    # Gripper
                    elif key == 'g':
                        self.stop_robot()
                        self.toggle_gripper()
                    elif key == 't':
                        self.stop_robot()
                        self.tester_prehension()

                    # Affichage
                    elif key == 'm':
                        self.stop_robot()
                        self.afficher_progression()
                    elif key == 'i':
                        self.stop_robot()
                        pose = self.rtde_r.getActualTCPPose()
                        print(f"\nTCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
                        print(f"Rot: RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
                        print(f"Case: {self.get_case_courante()} | Vitesse: {self.speed * 1000:.0f} mm/s")
                        print(f"Mode: CONTRÔLE CLAVIER")
                    elif key == 'h':
                        self.stop_robot()
                        self.print_help()

                    # Sauvegarde/Chargement
                    elif key == 'o':
                        self.stop_robot()
                        self.sauvegarder_mapping()
                    elif key == 'l':
                        self.stop_robot()
                        self.charger_mapping()
                        self.afficher_progression()

                    # Appliquer la vitesse
                    if any(v != 0 for v in new_velocity):
                        self.rtde_c.speedL(new_velocity, ACCELERATION, 0.1)
                    elif any(v != 0 for v in current_velocity):
                        self.stop_robot()

                current_velocity = new_velocity

        finally:
            if self.freedrive_actif:
                self.rtde_c.endFreedriveMode()
            self.stop_robot()
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