#!/usr/bin/env python3
"""
Script de jeu d'Ã©checs autonome - Robot UR5e joue contre lui-mÃªme
VERSION FINALE avec:
- Position de dÃ©part configurable
- Position reculÃ©e pour laisser jouer
- Hauteurs adaptÃ©es par type de piÃ¨ce
"""

import chess
import chess.engine
import chess.svg
from pathlib import Path
import json
import time
import argparse
import os
import sys
import tty
import termios
import select
from datetime import datetime

# ============================================================================
#                         CONFIGURATION
# ============================================================================

ROBOT_IP = "192.168.0.11"
VITESSE = 0.1
ACCELERATION = 0.3
GRIPPER_OUVERTURE = 25
DELTA_APPROCHE = 0.03  # 3cm au-dessus pour approche/remontÃ©e locale
DELTA_TRANSIT = 0.08  # 8cm au-dessus pour le trajet entre cases
DELTA_RELACHE_BASE = 0.004  # 4mm minimum au-dessus pour poser

# Position reculÃ©e : offset par rapport Ã  la position de dÃ©part (en mÃ¨tres)
OFFSET_RECUL_X = 0.0  # Pas de dÃ©calage en X
OFFSET_RECUL_Y = -0.15  # Recul de 15cm en Y (vers l'arriÃ¨re)
OFFSET_RECUL_Z = 0.05  # Monte de 5cm en Z

# Fichier pour sauvegarder la position de dÃ©part
FICHIER_POSITION_DEPART = "position_depart_robot.json"

# Fichier pour sauvegarder la zone de dÃ©fausse
FICHIER_ZONE_DEFAUSSE = "zone_defausse_robot.json"

# Hauteur de dÃ©pose par type de piÃ¨ce (en mÃ¨tres)
HAUTEUR_PIECES = {
    chess.PAWN: 0.005,  # Pion: +5mm
    chess.KNIGHT: 0.010,  # Cavalier: +10mm
    chess.BISHOP: 0.012,  # Fou: +12mm
    chess.ROOK: 0.008,  # Tour: +8mm
    chess.QUEEN: 0.015,  # Dame: +15mm
    chess.KING: 0.018,  # Roi: +18mm
}

NOMS_PIECES = {
    chess.PAWN: "Pion",
    chess.KNIGHT: "Cavalier",
    chess.BISHOP: "Fou",
    chess.ROOK: "Tour",
    chess.QUEEN: "Dame",
    chess.KING: "Roi",
}


# ============================================================================
#                         JOUEUR STOCKFISH
# ============================================================================

class StockfishPlayer:
    PRESETS = {
        'debutant': {'depth': 8, 'time_limit': 0.5, 'skill_level': 3},
        'facile': {'depth': 10, 'time_limit': 0.8, 'skill_level': 6},
        'intermediaire': {'depth': 12, 'time_limit': 1.0, 'skill_level': 10},
        'avance': {'depth': 15, 'time_limit': 1.5, 'skill_level': 15},
        'expert': {'depth': 18, 'time_limit': 2.0, 'skill_level': 18},
        'maitre': {'depth': 22, 'time_limit': 3.0, 'skill_level': 20}
    }

    def __init__(self, name, color, depth=15, time_limit=1.5, skill_level=15):
        self.name = name
        self.color = color
        self.depth = depth
        self.time_limit = time_limit
        self.skill_level = skill_level

    @classmethod
    def from_preset(cls, name, color, preset_name):
        preset = cls.PRESETS.get(preset_name.lower(), cls.PRESETS['intermediaire'])
        return cls(name, color, preset['depth'], preset['time_limit'], preset['skill_level'])

    @classmethod
    def list_presets(cls):
        print("\nNiveaux disponibles:")
        for name, cfg in cls.PRESETS.items():
            print(f"  {name:14} - Skill={cfg['skill_level']:2}, Depth={cfg['depth']:2}")

    def get_elo(self):
        if self.skill_level <= 3:
            return "~900"
        elif self.skill_level <= 6:
            return "~1100"
        elif self.skill_level <= 10:
            return "~1500"
        elif self.skill_level <= 15:
            return "~1900"
        elif self.skill_level <= 18:
            return "~2100"
        else:
            return "2200+"

    def __str__(self):
        c = "Blancs" if self.color == chess.WHITE else "Noirs"
        return f"{self.name} ({c}) - Skill={self.skill_level}, Eloâ{self.get_elo()}"


# ============================================================================
#                         VISUALISATIONS
# ============================================================================

class ChessVisualizer:
    def __init__(self, output_dir="game_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.move_count = 0

    def save(self, board, last_move=None, player_w=None, player_b=None):
        self.move_count += 1
        arrows = []
        if last_move:
            arrows.append(chess.svg.Arrow(last_move.from_square, last_move.to_square, color='#15803d'))

        svg = chess.svg.board(board, arrows=arrows, lastmove=last_move, size=450, coordinates=True)
        move_str = last_move.uci() if last_move else "start"

        filepath = self.output_dir / f"move_{self.move_count:03d}_{move_str}.svg"
        with open(filepath, 'w') as f:
            f.write(svg)

        return filepath


# ============================================================================
#                         CONTRÃLEUR DE PARTIE
# ============================================================================

class ChessRobotGame:
    def __init__(self, mapping_file="chess_board_positions.json", simulate=False):
        self.simulate = simulate
        self.board = chess.Board()
        self.visualizer = ChessVisualizer()

        # Stockfish
        self.engine = None
        for path in ['/usr/games/stockfish', '/usr/bin/stockfish', '/usr/local/bin/stockfish', 'stockfish']:
            if Path(path).exists():
                try:
                    self.engine = chess.engine.SimpleEngine.popen_uci(path)
                    print(f"â Stockfish: {path}")
                    break
                except:
                    pass

        if not self.engine:
            print("â  Stockfish non trouvÃ©")

        # Robot
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.cases = {}
        self.piece_courante = None
        self.position_depart = None
        self.zone_defausse_debut = None
        self.zone_defausse_fin = None
        self.defausse_index = 0  # Compteur de piÃ¨ces dÃ©faussÃ©es

        if not simulate:
            self._init_robot(mapping_file)

    def _init_robot(self, mapping_file):
        """Initialise le robot"""
        # Charger mapping
        if not os.path.exists(mapping_file):
            print(f"â  Mapping non trouvÃ©: {mapping_file}")
            self.simulate = True
            return

        with open(mapping_file, 'r') as f:
            data = json.load(f)
        self.cases = data.get("cases", {})
        self.delta_approche = data.get("delta_hauteur_approche", DELTA_APPROCHE)
        self.delta_relache = data.get("delta_hauteur_relache", DELTA_RELACHE_BASE)
        print(f"â Mapping: {len(self.cases)} cases")

        # Connexion robot
        try:
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface
            from robotiq_gripper_control import RobotiqGripper

            print(f"Connexion robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)

            print("Activation gripper...")
            self.gripper = RobotiqGripper(self.rtde_c)
            self.gripper.activate()
            self.gripper.set_force(40)
            self.gripper.set_speed(150)
            self.gripper.move(GRIPPER_OUVERTURE)

            print("â Robot prÃªt!")

            # Charger ou configurer la position de dÃ©part
            self._setup_position_depart()

            # Charger ou configurer la zone de dÃ©fausse
            self._setup_zone_defausse()

        except Exception as e:
            print(f"â  Erreur robot: {e}")
            self.simulate = True

    def _charger_position_depart(self):
        """Charge la position de dÃ©part depuis le fichier"""
        if os.path.exists(FICHIER_POSITION_DEPART):
            try:
                with open(FICHIER_POSITION_DEPART, 'r') as f:
                    data = json.load(f)
                return data.get("position_depart")
            except:
                pass
        return None

    def _sauvegarder_position_depart(self, position):
        """Sauvegarde la position de dÃ©part"""
        data = {
            "position_depart": position,
            "date": datetime.now().isoformat(),
            "description": "Position de dÃ©part du robot au-dessus de l'Ã©chiquier"
        }
        with open(FICHIER_POSITION_DEPART, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"â Position de dÃ©part sauvegardÃ©e dans {FICHIER_POSITION_DEPART}")

    def _get_key_non_blocking(self):
        """Lecture non-bloquante du clavier"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _enregistrer_position_freedrive(self, nom="position"):
        """Active le freedrive et attend que l'utilisateur positionne le robot"""
        print("\n" + "=" * 60)
        print(f"   MODE FREEDRIVE - Enregistrer {nom}")
        print("=" * 60)
        print(f"   DÃ©placez le robot Ã  la main vers la {nom}")
        print("\n   Appuyez sur ESPACE pour enregistrer la position")
        print("   Appuyez sur Q pour annuler")
        print("=" * 60)

        # Activer freedrive
        self.rtde_c.freedriveMode()
        print("\nð Freedrive ACTIVÃ - DÃ©placez le robot...")

        try:
            while True:
                key = self._get_key_non_blocking()

                if key == ' ':
                    # Enregistrer la position
                    self.rtde_c.endFreedriveMode()
                    position = list(self.rtde_r.getActualTCPPose())
                    print(f"\nâ Position enregistrÃ©e:")
                    print(f"   X={position[0]:.4f} Y={position[1]:.4f} Z={position[2]:.4f}")
                    return position

                elif key in ['q', 'Q', '\x1b']:
                    self.rtde_c.endFreedriveMode()
                    print("\nâ  AnnulÃ©")
                    return None

                # Afficher position actuelle
                pose = self.rtde_r.getActualTCPPose()
                print(f"\r   Position: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}    ", end='', flush=True)

        except KeyboardInterrupt:
            self.rtde_c.endFreedriveMode()
            return None

    def _setup_position_depart(self):
        """Configure la position de dÃ©part"""
        print("\n" + "=" * 60)
        print("   CONFIGURATION POSITION DE DÃPART")
        print("=" * 60)

        # Charger position existante
        position_saved = self._charger_position_depart()

        if position_saved:
            print(f"\nð Position de dÃ©part enregistrÃ©e:")
            print(f"   X={position_saved[0]:.4f} Y={position_saved[1]:.4f} Z={position_saved[2]:.4f}")

            # Demander si on veut l'utiliser
            print("\n   [O] Utiliser cette position")
            print("   [N] Enregistrer une nouvelle position (freedrive)")
            print("   [A] Aller Ã  cette position maintenant")

            while True:
                rep = input("\n   Choix (O/N/A): ").strip().upper()

                if rep == 'O':
                    self.position_depart = position_saved
                    print("â Position de dÃ©part chargÃ©e")
                    break

                elif rep == 'N':
                    nouvelle_pos = self._enregistrer_position_freedrive("position de dÃ©part")
                    if nouvelle_pos:
                        self.position_depart = nouvelle_pos
                        self._sauvegarder_position_depart(nouvelle_pos)
                    else:
                        self.position_depart = position_saved
                    break

                elif rep == 'A':
                    self.position_depart = position_saved
                    print("   DÃ©placement vers la position de dÃ©part...")
                    self.rtde_c.moveL(position_saved, VITESSE, ACCELERATION)
                    print("â Position atteinte")
                    break
        else:
            print("\nâ  Aucune position de dÃ©part enregistrÃ©e!")
            print("   Vous devez enregistrer une position de dÃ©part.")

            rep = input("\n   Enregistrer maintenant? (O/N): ").strip().upper()

            if rep == 'O':
                nouvelle_pos = self._enregistrer_position_freedrive("position de dÃ©part")
                if nouvelle_pos:
                    self.position_depart = nouvelle_pos
                    self._sauvegarder_position_depart(nouvelle_pos)
                else:
                    print("â  Position non enregistrÃ©e - Utilisation position actuelle")
                    self.position_depart = list(self.rtde_r.getActualTCPPose())
            else:
                print("   Utilisation de la position actuelle comme dÃ©part")
                self.position_depart = list(self.rtde_r.getActualTCPPose())

    def _charger_zone_defausse(self):
        """Charge la zone de dÃ©fausse depuis le fichier"""
        if os.path.exists(FICHIER_ZONE_DEFAUSSE):
            try:
                with open(FICHIER_ZONE_DEFAUSSE, 'r') as f:
                    data = json.load(f)
                return data.get("debut"), data.get("fin")
            except:
                pass
        return None, None

    def _sauvegarder_zone_defausse(self, debut, fin):
        """Sauvegarde la zone de dÃ©fausse"""
        data = {
            "debut": debut,
            "fin": fin,
            "date": datetime.now().isoformat(),
            "description": "Zone de dÃ©fausse pour les piÃ¨ces capturÃ©es"
        }
        with open(FICHIER_ZONE_DEFAUSSE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"â Zone de dÃ©fausse sauvegardÃ©e dans {FICHIER_ZONE_DEFAUSSE}")

    def _setup_zone_defausse(self):
        """Configure la zone de dÃ©fausse"""
        print("\n" + "=" * 60)
        print("   CONFIGURATION ZONE DE DÃFAUSSE")
        print("=" * 60)

        # Charger zone existante
        debut_saved, fin_saved = self._charger_zone_defausse()

        if debut_saved and fin_saved:
            print(f"\nð Zone de dÃ©fausse enregistrÃ©e:")
            print(f"   DÃBUT: X={debut_saved[0]:.4f} Y={debut_saved[1]:.4f} Z={debut_saved[2]:.4f}")
            print(f"   FIN:   X={fin_saved[0]:.4f} Y={fin_saved[1]:.4f} Z={fin_saved[2]:.4f}")

            # Calculer la distance
            import math
            distance = math.sqrt(
                (fin_saved[0] - debut_saved[0]) ** 2 +
                (fin_saved[1] - debut_saved[1]) ** 2
            )
            print(f"   Longueur: {distance * 100:.1f} cm")

            print("\n   [O] Utiliser cette zone")
            print("   [N] Enregistrer une nouvelle zone (freedrive)")

            while True:
                rep = input("\n   Choix (O/N): ").strip().upper()

                if rep == 'O':
                    self.zone_defausse_debut = debut_saved
                    self.zone_defausse_fin = fin_saved
                    print("â Zone de dÃ©fausse chargÃ©e")
                    break

                elif rep == 'N':
                    self._enregistrer_zone_defausse_freedrive()
                    break
        else:
            print("\nâ  Aucune zone de dÃ©fausse enregistrÃ©e!")
            print("   Vous devez enregistrer une zone pour les piÃ¨ces capturÃ©es.")

            rep = input("\n   Enregistrer maintenant? (O/N): ").strip().upper()

            if rep == 'O':
                self._enregistrer_zone_defausse_freedrive()
            else:
                print("â  Zone non enregistrÃ©e - Les piÃ¨ces seront lÃ¢chÃ©es en l'air")

    def _enregistrer_zone_defausse_freedrive(self):
        """Enregistre la zone de dÃ©fausse en deux points via freedrive"""
        print("\n" + "-" * 60)
        print("   ENREGISTREMENT ZONE DE DÃFAUSSE")
        print("-" * 60)
        print("   Vous allez enregistrer 2 points:")
        print("   1. Point de DÃBUT de la zone")
        print("   2. Point de FIN de la zone")
        print("   Les piÃ¨ces seront dÃ©posÃ©es le long de cette ligne.")
        print("-" * 60)

        # Point de dÃ©but
        print("\nð POINT 1: DÃ©but de la zone de dÃ©fausse")
        debut = self._enregistrer_position_freedrive("dÃ©but zone dÃ©fausse")

        if not debut:
            print("â  Enregistrement annulÃ©")
            return

        # Point de fin
        print("\nð POINT 2: Fin de la zone de dÃ©fausse")
        fin = self._enregistrer_position_freedrive("fin zone dÃ©fausse")

        if not fin:
            print("â  Enregistrement annulÃ©")
            return

        # Sauvegarder
        self.zone_defausse_debut = debut
        self.zone_defausse_fin = fin
        self._sauvegarder_zone_defausse(debut, fin)

        # Afficher rÃ©sumÃ©
        import math
        distance = math.sqrt(
            (fin[0] - debut[0]) ** 2 +
            (fin[1] - debut[1]) ** 2
        )
        print(f"\nâ Zone de dÃ©fausse configurÃ©e:")
        print(f"   Longueur: {distance * 100:.1f} cm")
        print(f"   CapacitÃ©: ~{int(distance / 0.03)} piÃ¨ces")

    def _get_position_defausse(self):
        """Calcule la prochaine position de dÃ©fausse"""
        if not self.zone_defausse_debut or not self.zone_defausse_fin:
            return None

        # Calculer la position le long de la ligne
        # On espace les piÃ¨ces de 3cm environ
        max_pieces = 16  # Maximum de piÃ¨ces capturables

        if self.defausse_index >= max_pieces:
            self.defausse_index = 0  # Recommencer au dÃ©but si plein

        # Interpolation linÃ©aire entre dÃ©but et fin
        t = self.defausse_index / max(max_pieces - 1, 1)

        position = [
            self.zone_defausse_debut[0] + t * (self.zone_defausse_fin[0] - self.zone_defausse_debut[0]),
            self.zone_defausse_debut[1] + t * (self.zone_defausse_fin[1] - self.zone_defausse_debut[1]),
            self.zone_defausse_debut[2] + t * (self.zone_defausse_fin[2] - self.zone_defausse_debut[2]),
            self.zone_defausse_debut[3],  # Garder l'orientation du point de dÃ©but
            self.zone_defausse_debut[4],
            self.zone_defausse_debut[5],
        ]

        self.defausse_index += 1

        return position

    def aller_position_depart(self):
        """Va Ã  la position de dÃ©part"""
        if self.simulate or not self.position_depart:
            return

        print("   â Retour position de dÃ©part...")
        self.rtde_c.moveL(self.position_depart, VITESSE, ACCELERATION)

    def aller_position_reculee(self):
        """Va Ã  la position reculÃ©e (pour laisser le joueur jouer)"""
        if self.simulate or not self.position_depart:
            return

        position_reculee = list(self.position_depart)
        position_reculee[0] += OFFSET_RECUL_X
        position_reculee[1] += OFFSET_RECUL_Y
        position_reculee[2] += OFFSET_RECUL_Z

        print("   â Position reculÃ©e (attente joueur)...")
        self.rtde_c.moveL(position_reculee, VITESSE, ACCELERATION)

    def _pos_avec_z(self, tcp, delta_z):
        """Ajoute un delta Z Ã  une position TCP"""
        pos = list(tcp)
        pos[2] += delta_z
        return pos

    def _prendre_piece(self, case):
        """Prend une piÃ¨ce sur une case"""
        case = case.lower()
        if case not in self.cases:
            print(f"      â  Case {case} non mappÃ©e!")
            return False

        tcp = self.cases[case]["tcp"]

        # Identifier la piÃ¨ce depuis le plateau
        square = chess.parse_square(case)
        piece = self.board.piece_at(square)

        if piece:
            self.piece_courante = piece.piece_type
            nom = NOMS_PIECES.get(piece.piece_type, "?")
            hauteur = HAUTEUR_PIECES.get(piece.piece_type, 0.005)
            print(f"      ð PiÃ¨ce: {nom} â hauteur dÃ©pose +{hauteur * 1000:.0f}mm")
        else:
            self.piece_courante = None

        print(f"      â Approche {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      â Descente...")
        self.rtde_c.moveL(tcp, VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      â Fermeture gripper...")
        self.gripper.close()
        time.sleep(0.3)

        print(f"      â RemontÃ©e locale...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.1)

        print(f"      â MontÃ©e transit...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    def _poser_piece(self, case):
        """Pose une piÃ¨ce sur une case avec hauteur adaptÃ©e"""
        case = case.lower()
        if case not in self.cases:
            print(f"      â  Case {case} non mappÃ©e!")
            return False

        tcp = self.cases[case]["tcp"]

        # Calculer la hauteur de relÃ¢che selon la piÃ¨ce
        hauteur_piece = HAUTEUR_PIECES.get(self.piece_courante, 0.005)
        delta_relache = DELTA_RELACHE_BASE + hauteur_piece

        print(f"      â Transit vers {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      â Descente approche...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.1)

        print(f"      â Descente relÃ¢che (+{delta_relache * 1000:.0f}mm)...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, delta_relache), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      â Ouverture gripper...")
        self.gripper.move(GRIPPER_OUVERTURE)
        time.sleep(0.3)

        print(f"      â RemontÃ©e...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    def _deplacer_piece(self, from_sq, to_sq):
        """DÃ©place une piÃ¨ce"""
        print(f"      [ROBOT] {from_sq.upper()} â {to_sq.upper()}")

        if not self._prendre_piece(from_sq):
            return False

        if not self._poser_piece(to_sq):
            return False

        return True

    def _capturer_piece(self, from_sq, to_sq):
        """Capture: retire la piÃ¨ce adverse puis dÃ©place"""
        print(f"      [ROBOT] Capture: {from_sq.upper()} prend {to_sq.upper()}")

        # 1. Retirer la piÃ¨ce capturÃ©e
        print(f"      --- Retrait piÃ¨ce capturÃ©e sur {to_sq.upper()} ---")
        if not self._prendre_piece(to_sq):
            return False

        # DÃ©poser dans la zone de dÃ©fausse
        pos_defausse = self._get_position_defausse()

        if pos_defausse:
            print(f"      â DÃ©pÃ´t en zone de dÃ©fausse (position {self.defausse_index})...")

            # Aller au-dessus de la position de dÃ©fausse
            pos_haute = list(pos_defausse)
            pos_haute[2] += DELTA_TRANSIT
            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)

            # Descendre pour dÃ©poser
            pos_relache = list(pos_defausse)
            pos_relache[2] += DELTA_RELACHE_BASE + 0.01  # +1cm pour la dÃ©fausse
            self.rtde_c.moveL(pos_relache, VITESSE, ACCELERATION)
            time.sleep(0.2)

            # Ouvrir gripper
            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

            # Remonter
            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)
        else:
            # Pas de zone de dÃ©fausse, lÃ¢cher en l'air
            print(f"      â DÃ©pÃ´t hors Ã©chiquier...")
            pose = self.rtde_r.getActualTCPPose()
            pose_haute = list(pose)
            pose_haute[2] += 0.05
            self.rtde_c.moveL(pose_haute, VITESSE, ACCELERATION)
            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

        # 2. DÃ©placer la piÃ¨ce qui capture
        print(f"      --- DÃ©placement {from_sq.upper()} â {to_sq.upper()} ---")
        if not self._deplacer_piece(from_sq, to_sq):
            return False

        return True

    def execute_move(self, move):
        """ExÃ©cute un mouvement sur le robot"""
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)

        if self.simulate or self.rtde_c is None:
            print(f"   ð¤ [SIMULATION] {from_sq} â {to_sq}")
            time.sleep(0.3)
            return True

        is_capture = self.board.is_capture(move)

        try:
            if is_capture:
                return self._capturer_piece(from_sq, to_sq)
            else:
                return self._deplacer_piece(from_sq, to_sq)
        except Exception as e:
            print(f"   â  Erreur: {e}")
            return False

    def get_move(self, player):
        """Obtient le meilleur coup"""
        if not self.engine:
            import random
            legal = list(self.board.legal_moves)
            return random.choice(legal) if legal else None, 0.0

        self.engine.configure({"Skill Level": player.skill_level})

        try:
            info = self.engine.analyse(self.board,
                                       chess.engine.Limit(depth=player.depth, time=player.time_limit))

            move = info.get("pv", [None])[0]
            score = info.get("score")

            ev = 0.0
            if score and score.relative.score():
                ev = score.relative.score() / 100
            elif score and score.relative.mate():
                ev = f"Mat en {abs(score.relative.mate())}"

            return move, ev
        except:
            return None, 0.0

    def play(self, player_w, player_b, max_moves=150, delay=1.0, pause=False):
        """Joue une partie"""
        print("\n" + "=" * 60)
        print("         â PARTIE D'ÃCHECS ROBOT â")
        print("=" * 60)
        print(f"\n  {player_w}")
        print(f"  {player_b}")
        print(f"  Mode: {'ð´ SIMULATION' if self.simulate else 'ð¢ ROBOT RÃEL'}")
        print("-" * 60)

        if not self.simulate:
            print("\nâ ï¸ Le robot va bouger!")
            rep = input("Continuer? (o/n): ").strip().lower()
            if rep not in ['o', 'oui', 'y']:
                return "AnnulÃ©"

            # Aller Ã  la position de dÃ©part
            self.aller_position_depart()

        self.board.reset()
        self.visualizer.move_count = 0
        self.defausse_index = 0  # RÃ©initialiser le compteur de dÃ©fausse
        self.visualizer.save(self.board, player_w=player_w, player_b=player_b)

        num = 0
        while not self.board.is_game_over() and num < max_moves:
            player = player_w if self.board.turn == chess.WHITE else player_b
            color = "Blancs" if self.board.turn == chess.WHITE else "Noirs"

            num += 1
            print(f"\n{'â€' * 50}")
            print(f"  Coup {num} - {player.name} ({color})")
            print(f"{'â€' * 50}")

            move, ev = self.get_move(player)
            if not move:
                break

            san = self.board.san(move)
            print(f"   ð {move.uci()} ({san})")
            if isinstance(ev, float):
                print(f"   ð Eval: {ev:+.2f}")
            else:
                print(f"   ð {ev}")

            # ExÃ©cuter sur le robot
            if not self.execute_move(move):
                print("   â  Erreur mouvement!")
                rep = input("   Continuer en simulation? (o/n): ")
                if rep.lower() in ['o', 'oui']:
                    self.simulate = True
                else:
                    break

            self.board.push(move)
            svg = self.visualizer.save(self.board, move, player_w, player_b)
            print(f"   ð {svg.name}")

            # Retour position de dÃ©part aprÃ¨s chaque coup
            if not self.simulate:
                self.aller_position_depart()

            if pause:
                input("   [ENTRÃE]...")
            else:
                time.sleep(delay)

        # RÃ©sultat
        if self.board.is_checkmate():
            winner = "Noirs" if self.board.turn == chess.WHITE else "Blancs"
            result = f"Ãchec et mat! {winner} gagnent"
        elif self.board.is_stalemate():
            result = "Pat"
        else:
            result = "Partie terminÃ©e"

        print("\n" + "=" * 60)
        print(f"  {result}")
        print("=" * 60)

        # Position reculÃ©e Ã  la fin
        if not self.simulate:
            self.aller_position_reculee()

        return result

    def close(self):
        if self.engine:
            self.engine.quit()
        if self.rtde_c:
            self.rtde_c.stopScript()
        print("â FermÃ©")


def main():
    parser = argparse.ArgumentParser(description="Robot Ã©checs autonome")
    parser.add_argument('--blanc', default='intermediaire')
    parser.add_argument('--noir', default='intermediaire')
    parser.add_argument('--simulate', action='store_true', help='Mode simulation')
    parser.add_argument('--pause', action='store_true', help='Pause entre coups')
    parser.add_argument('--mapping', default='chess_board_positions.json')
    parser.add_argument('--max-coups', type=int, default=150)
    parser.add_argument('--delai', type=float, default=1.0)
    parser.add_argument('--list-levels', action='store_true')
    parser.add_argument('--reset-position', action='store_true', help='RÃ©enregistrer la position de dÃ©part')
    parser.add_argument('--reset-defausse', action='store_true', help='RÃ©enregistrer la zone de dÃ©fausse')
    parser.add_argument('--reset-all', action='store_true', help='RÃ©enregistrer toutes les positions')

    args = parser.parse_args()

    if args.list_levels:
        StockfishPlayer.list_presets()
        return

    # Si on veut rÃ©initialiser les positions
    if args.reset_all:
        args.reset_position = True
        args.reset_defausse = True

    if args.reset_position:
        if os.path.exists(FICHIER_POSITION_DEPART):
            os.remove(FICHIER_POSITION_DEPART)
            print(f"â Position de dÃ©part supprimÃ©e ({FICHIER_POSITION_DEPART})")

    if args.reset_defausse:
        if os.path.exists(FICHIER_ZONE_DEFAUSSE):
            os.remove(FICHIER_ZONE_DEFAUSSE)
            print(f"â Zone de dÃ©fausse supprimÃ©e ({FICHIER_ZONE_DEFAUSSE})")

    print("=" * 60)
    print("     â ROBOT ÃCHECS â")
    print("=" * 60)

    player_w = StockfishPlayer.from_preset("Blancs", chess.WHITE, args.blanc)
    player_b = StockfishPlayer.from_preset("Noirs", chess.BLACK, args.noir)

    print(f"\n  {player_w}")
    print(f"  {player_b}")

    game = ChessRobotGame(args.mapping, args.simulate)

    try:
        game.play(player_w, player_b, args.max_coups, args.delai, args.pause)
    except KeyboardInterrupt:
        print("\nâ  Interrompu")
    finally:
        game.close()


if __name__ == "__main__":