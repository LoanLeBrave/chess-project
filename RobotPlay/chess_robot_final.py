#!/usr/bin/env python3
"""
Script de jeu d'échecs autonome - Robot UR5e joue contre lui-même
VERSION FINALE avec:
- Position de départ configurable
- Position reculée pour laisser jouer
- Hauteurs adaptées par type de pièce
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
DELTA_APPROCHE = 0.03  # 3cm au-dessus pour approche/remontée locale
DELTA_TRANSIT = 0.08  # 8cm au-dessus pour le trajet entre cases
DELTA_RELACHE_BASE = 0.004  # 4mm minimum au-dessus pour poser

# Position reculée : offset par rapport à la position de départ (en mètres)
OFFSET_RECUL_X = 0.0  # Pas de décalage en X
OFFSET_RECUL_Y = -0.15  # Recul de 15cm en Y (vers l'arrière)
OFFSET_RECUL_Z = 0.05  # Monte de 5cm en Z

# Fichier pour sauvegarder la position de départ
FICHIER_POSITION_DEPART = "position_depart_robot.json"

# Fichier pour sauvegarder la zone de défausse
FICHIER_ZONE_DEFAUSSE = "zone_defausse_robot.json"

# Hauteur de dépose par type de pièce (en mètres)
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
        return f"{self.name} ({c}) - Skill={self.skill_level}, Elo≈{self.get_elo()}"


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
#                         CONTRÔLEUR DE PARTIE
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
                    print(f"✓ Stockfish: {path}")
                    break
                except:
                    pass

        if not self.engine:
            print("⚠ Stockfish non trouvé")

        # Robot
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.cases = {}
        self.piece_courante = None
        self.position_depart = None
        self.zone_defausse_debut = None
        self.zone_defausse_fin = None
        self.defausse_index = 0  # Compteur de pièces défaussées

        if not simulate:
            self._init_robot(mapping_file)

    def _init_robot(self, mapping_file):
        """Initialise le robot"""
        # Charger mapping
        if not os.path.exists(mapping_file):
            print(f"⚠ Mapping non trouvé: {mapping_file}")
            self.simulate = True
            return

        with open(mapping_file, 'r') as f:
            data = json.load(f)
        self.cases = data.get("cases", {})
        self.delta_approche = data.get("delta_hauteur_approche", DELTA_APPROCHE)
        self.delta_relache = data.get("delta_hauteur_relache", DELTA_RELACHE_BASE)
        print(f"✓ Mapping: {len(self.cases)} cases")

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

            print("✓ Robot prêt!")

            # Charger ou configurer la position de départ
            self._setup_position_depart()

            # Charger ou configurer la zone de défausse
            self._setup_zone_defausse()

        except Exception as e:
            print(f"⚠ Erreur robot: {e}")
            self.simulate = True

    def _charger_position_depart(self):
        """Charge la position de départ depuis le fichier"""
        if os.path.exists(FICHIER_POSITION_DEPART):
            try:
                with open(FICHIER_POSITION_DEPART, 'r') as f:
                    data = json.load(f)
                return data.get("position_depart")
            except:
                pass
        return None

    def _sauvegarder_position_depart(self, position):
        """Sauvegarde la position de départ"""
        data = {
            "position_depart": position,
            "date": datetime.now().isoformat(),
            "description": "Position de départ du robot au-dessus de l'échiquier"
        }
        with open(FICHIER_POSITION_DEPART, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Position de départ sauvegardée dans {FICHIER_POSITION_DEPART}")

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
        print(f"   Déplacez le robot à la main vers la {nom}")
        print("\n   Appuyez sur ESPACE pour enregistrer la position")
        print("   Appuyez sur Q pour annuler")
        print("=" * 60)

        # Activer freedrive
        self.rtde_c.freedriveMode()
        print("\n🆓 Freedrive ACTIVÉ - Déplacez le robot...")

        try:
            while True:
                key = self._get_key_non_blocking()

                if key == ' ':
                    # Enregistrer la position
                    self.rtde_c.endFreedriveMode()
                    position = list(self.rtde_r.getActualTCPPose())
                    print(f"\n✓ Position enregistrée:")
                    print(f"   X={position[0]:.4f} Y={position[1]:.4f} Z={position[2]:.4f}")
                    return position

                elif key in ['q', 'Q', '\x1b']:
                    self.rtde_c.endFreedriveMode()
                    print("\n⚠ Annulé")
                    return None

                # Afficher position actuelle
                pose = self.rtde_r.getActualTCPPose()
                print(f"\r   Position: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}    ", end='', flush=True)

        except KeyboardInterrupt:
            self.rtde_c.endFreedriveMode()
            return None

    def _setup_position_depart(self):
        """Configure la position de départ"""
        print("\n" + "=" * 60)
        print("   CONFIGURATION POSITION DE DÉPART")
        print("=" * 60)

        # Charger position existante
        position_saved = self._charger_position_depart()

        if position_saved:
            print(f"\n📍 Position de départ enregistrée:")
            print(f"   X={position_saved[0]:.4f} Y={position_saved[1]:.4f} Z={position_saved[2]:.4f}")

            # Demander si on veut l'utiliser
            print("\n   [O] Utiliser cette position")
            print("   [N] Enregistrer une nouvelle position (freedrive)")
            print("   [A] Aller à cette position maintenant")

            while True:
                rep = input("\n   Choix (O/N/A): ").strip().upper()

                if rep == 'O':
                    self.position_depart = position_saved
                    print("✓ Position de départ chargée")
                    break

                elif rep == 'N':
                    nouvelle_pos = self._enregistrer_position_freedrive("position de départ")
                    if nouvelle_pos:
                        self.position_depart = nouvelle_pos
                        self._sauvegarder_position_depart(nouvelle_pos)
                    else:
                        self.position_depart = position_saved
                    break

                elif rep == 'A':
                    self.position_depart = position_saved
                    print("   Déplacement vers la position de départ...")
                    self.rtde_c.moveL(position_saved, VITESSE, ACCELERATION)
                    print("✓ Position atteinte")
                    break
        else:
            print("\n⚠ Aucune position de départ enregistrée!")
            print("   Vous devez enregistrer une position de départ.")

            rep = input("\n   Enregistrer maintenant? (O/N): ").strip().upper()

            if rep == 'O':
                nouvelle_pos = self._enregistrer_position_freedrive("position de départ")
                if nouvelle_pos:
                    self.position_depart = nouvelle_pos
                    self._sauvegarder_position_depart(nouvelle_pos)
                else:
                    print("⚠ Position non enregistrée - Utilisation position actuelle")
                    self.position_depart = list(self.rtde_r.getActualTCPPose())
            else:
                print("   Utilisation de la position actuelle comme départ")
                self.position_depart = list(self.rtde_r.getActualTCPPose())

    def _charger_zone_defausse(self):
        """Charge la zone de défausse depuis le fichier"""
        if os.path.exists(FICHIER_ZONE_DEFAUSSE):
            try:
                with open(FICHIER_ZONE_DEFAUSSE, 'r') as f:
                    data = json.load(f)
                return data.get("debut"), data.get("fin")
            except:
                pass
        return None, None

    def _sauvegarder_zone_defausse(self, debut, fin):
        """Sauvegarde la zone de défausse"""
        data = {
            "debut": debut,
            "fin": fin,
            "date": datetime.now().isoformat(),
            "description": "Zone de défausse pour les pièces capturées"
        }
        with open(FICHIER_ZONE_DEFAUSSE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Zone de défausse sauvegardée dans {FICHIER_ZONE_DEFAUSSE}")

    def _setup_zone_defausse(self):
        """Configure la zone de défausse"""
        print("\n" + "=" * 60)
        print("   CONFIGURATION ZONE DE DÉFAUSSE")
        print("=" * 60)

        # Charger zone existante
        debut_saved, fin_saved = self._charger_zone_defausse()

        if debut_saved and fin_saved:
            print(f"\n📍 Zone de défausse enregistrée:")
            print(f"   DÉBUT: X={debut_saved[0]:.4f} Y={debut_saved[1]:.4f} Z={debut_saved[2]:.4f}")
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
                    print("✓ Zone de défausse chargée")
                    break

                elif rep == 'N':
                    self._enregistrer_zone_defausse_freedrive()
                    break
        else:
            print("\n⚠ Aucune zone de défausse enregistrée!")
            print("   Vous devez enregistrer une zone pour les pièces capturées.")

            rep = input("\n   Enregistrer maintenant? (O/N): ").strip().upper()

            if rep == 'O':
                self._enregistrer_zone_defausse_freedrive()
            else:
                print("⚠ Zone non enregistrée - Les pièces seront lâchées en l'air")

    def _enregistrer_zone_defausse_freedrive(self):
        """Enregistre la zone de défausse en deux points via freedrive"""
        print("\n" + "-" * 60)
        print("   ENREGISTREMENT ZONE DE DÉFAUSSE")
        print("-" * 60)
        print("   Vous allez enregistrer 2 points:")
        print("   1. Point de DÉBUT de la zone")
        print("   2. Point de FIN de la zone")
        print("   Les pièces seront déposées le long de cette ligne.")
        print("-" * 60)

        # Point de début
        print("\n📍 POINT 1: Début de la zone de défausse")
        debut = self._enregistrer_position_freedrive("début zone défausse")

        if not debut:
            print("⚠ Enregistrement annulé")
            return

        # Point de fin
        print("\n📍 POINT 2: Fin de la zone de défausse")
        fin = self._enregistrer_position_freedrive("fin zone défausse")

        if not fin:
            print("⚠ Enregistrement annulé")
            return

        # Sauvegarder
        self.zone_defausse_debut = debut
        self.zone_defausse_fin = fin
        self._sauvegarder_zone_defausse(debut, fin)

        # Afficher résumé
        import math
        distance = math.sqrt(
            (fin[0] - debut[0]) ** 2 +
            (fin[1] - debut[1]) ** 2
        )
        print(f"\n✓ Zone de défausse configurée:")
        print(f"   Longueur: {distance * 100:.1f} cm")
        print(f"   Capacité: ~{int(distance / 0.03)} pièces")

    def _get_position_defausse(self):
        """Calcule la prochaine position de défausse"""
        if not self.zone_defausse_debut or not self.zone_defausse_fin:
            return None

        # Calculer la position le long de la ligne
        # On espace les pièces de 3cm environ
        max_pieces = 16  # Maximum de pièces capturables

        if self.defausse_index >= max_pieces:
            self.defausse_index = 0  # Recommencer au début si plein

        # Interpolation linéaire entre début et fin
        t = self.defausse_index / max(max_pieces - 1, 1)

        position = [
            self.zone_defausse_debut[0] + t * (self.zone_defausse_fin[0] - self.zone_defausse_debut[0]),
            self.zone_defausse_debut[1] + t * (self.zone_defausse_fin[1] - self.zone_defausse_debut[1]),
            self.zone_defausse_debut[2] + t * (self.zone_defausse_fin[2] - self.zone_defausse_debut[2]),
            self.zone_defausse_debut[3],  # Garder l'orientation du point de début
            self.zone_defausse_debut[4],
            self.zone_defausse_debut[5],
        ]

        self.defausse_index += 1

        return position

    def aller_position_depart(self):
        """Va à la position de départ"""
        if self.simulate or not self.position_depart:
            return

        print("   → Retour position de départ...")
        self.rtde_c.moveL(self.position_depart, VITESSE, ACCELERATION)

    def aller_position_reculee(self):
        """Va à la position reculée (pour laisser le joueur jouer)"""
        if self.simulate or not self.position_depart:
            return

        position_reculee = list(self.position_depart)
        position_reculee[0] += OFFSET_RECUL_X
        position_reculee[1] += OFFSET_RECUL_Y
        position_reculee[2] += OFFSET_RECUL_Z

        print("   → Position reculée (attente joueur)...")
        self.rtde_c.moveL(position_reculee, VITESSE, ACCELERATION)

    def _pos_avec_z(self, tcp, delta_z):
        """Ajoute un delta Z à une position TCP"""
        pos = list(tcp)
        pos[2] += delta_z
        return pos

    def _prendre_piece(self, case):
        """Prend une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            print(f"      ⚠ Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        # Identifier la pièce depuis le plateau
        square = chess.parse_square(case)
        piece = self.board.piece_at(square)

        if piece:
            self.piece_courante = piece.piece_type
            nom = NOMS_PIECES.get(piece.piece_type, "?")
            hauteur = HAUTEUR_PIECES.get(piece.piece_type, 0.005)
            print(f"      📏 Pièce: {nom} → hauteur dépose +{hauteur * 1000:.0f}mm")
        else:
            self.piece_courante = None

        print(f"      → Approche {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Descente...")
        self.rtde_c.moveL(tcp, VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Fermeture gripper...")
        self.gripper.close()
        time.sleep(0.3)

        print(f"      → Remontée locale...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.1)

        print(f"      → Montée transit...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    def _poser_piece(self, case):
        """Pose une pièce sur une case avec hauteur adaptée"""
        case = case.lower()
        if case not in self.cases:
            print(f"      ⚠ Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        # Calculer la hauteur de relâche selon la pièce
        hauteur_piece = HAUTEUR_PIECES.get(self.piece_courante, 0.005)
        delta_relache = DELTA_RELACHE_BASE + hauteur_piece

        print(f"      → Transit vers {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, DELTA_TRANSIT), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Descente approche...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.1)

        print(f"      → Descente relâche (+{delta_relache * 1000:.0f}mm)...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, delta_relache), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Ouverture gripper...")
        self.gripper.move(GRIPPER_OUVERTURE)
        time.sleep(0.3)

        print(f"      → Remontée...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    def _deplacer_piece(self, from_sq, to_sq):
        """Déplace une pièce"""
        print(f"      [ROBOT] {from_sq.upper()} → {to_sq.upper()}")

        if not self._prendre_piece(from_sq):
            return False

        if not self._poser_piece(to_sq):
            return False

        return True

    def _capturer_piece(self, from_sq, to_sq):
        """Capture: retire la pièce adverse puis déplace"""
        print(f"      [ROBOT] Capture: {from_sq.upper()} prend {to_sq.upper()}")

        # 1. Retirer la pièce capturée
        print(f"      --- Retrait pièce capturée sur {to_sq.upper()} ---")
        if not self._prendre_piece(to_sq):
            return False

        # Déposer dans la zone de défausse
        pos_defausse = self._get_position_defausse()

        if pos_defausse:
            print(f"      → Dépôt en zone de défausse (position {self.defausse_index})...")

            # Aller au-dessus de la position de défausse
            pos_haute = list(pos_defausse)
            pos_haute[2] += DELTA_TRANSIT
            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)

            # Descendre pour déposer
            pos_relache = list(pos_defausse)
            pos_relache[2] += DELTA_RELACHE_BASE + 0.01  # +1cm pour la défausse
            self.rtde_c.moveL(pos_relache, VITESSE, ACCELERATION)
            time.sleep(0.2)

            # Ouvrir gripper
            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

            # Remonter
            self.rtde_c.moveL(pos_haute, VITESSE, ACCELERATION)
            time.sleep(0.2)
        else:
            # Pas de zone de défausse, lâcher en l'air
            print(f"      → Dépôt hors échiquier...")
            pose = self.rtde_r.getActualTCPPose()
            pose_haute = list(pose)
            pose_haute[2] += 0.05
            self.rtde_c.moveL(pose_haute, VITESSE, ACCELERATION)
            self.gripper.move(GRIPPER_OUVERTURE)
            time.sleep(0.3)

        # 2. Déplacer la pièce qui capture
        print(f"      --- Déplacement {from_sq.upper()} → {to_sq.upper()} ---")
        if not self._deplacer_piece(from_sq, to_sq):
            return False

        return True

    def execute_move(self, move):
        """Exécute un mouvement sur le robot"""
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)

        if self.simulate or self.rtde_c is None:
            print(f"   🤖 [SIMULATION] {from_sq} → {to_sq}")
            time.sleep(0.3)
            return True

        is_capture = self.board.is_capture(move)

        try:
            if is_capture:
                return self._capturer_piece(from_sq, to_sq)
            else:
                return self._deplacer_piece(from_sq, to_sq)
        except Exception as e:
            print(f"   ⚠ Erreur: {e}")
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
        print("         ♔ PARTIE D'ÉCHECS ROBOT ♚")
        print("=" * 60)
        print(f"\n  {player_w}")
        print(f"  {player_b}")
        print(f"  Mode: {'🔴 SIMULATION' if self.simulate else '🟢 ROBOT RÉEL'}")
        print("-" * 60)

        if not self.simulate:
            print("\n⚠️ Le robot va bouger!")
            rep = input("Continuer? (o/n): ").strip().lower()
            if rep not in ['o', 'oui', 'y']:
                return "Annulé"

            # Aller à la position de départ
            self.aller_position_depart()

        self.board.reset()
        self.visualizer.move_count = 0
        self.defausse_index = 0  # Réinitialiser le compteur de défausse
        self.visualizer.save(self.board, player_w=player_w, player_b=player_b)

        num = 0
        while not self.board.is_game_over() and num < max_moves:
            player = player_w if self.board.turn == chess.WHITE else player_b
            color = "Blancs" if self.board.turn == chess.WHITE else "Noirs"

            num += 1
            print(f"\n{'─' * 50}")
            print(f"  Coup {num} - {player.name} ({color})")
            print(f"{'─' * 50}")

            move, ev = self.get_move(player)
            if not move:
                break

            san = self.board.san(move)
            print(f"   📍 {move.uci()} ({san})")
            if isinstance(ev, float):
                print(f"   📊 Eval: {ev:+.2f}")
            else:
                print(f"   📊 {ev}")

            # Exécuter sur le robot
            if not self.execute_move(move):
                print("   ⚠ Erreur mouvement!")
                rep = input("   Continuer en simulation? (o/n): ")
                if rep.lower() in ['o', 'oui']:
                    self.simulate = True
                else:
                    break

            self.board.push(move)
            svg = self.visualizer.save(self.board, move, player_w, player_b)
            print(f"   📊 {svg.name}")

            # Retour position de départ après chaque coup
            if not self.simulate:
                self.aller_position_depart()

            if pause:
                input("   [ENTRÉE]...")
            else:
                time.sleep(delay)

        # Résultat
        if self.board.is_checkmate():
            winner = "Noirs" if self.board.turn == chess.WHITE else "Blancs"
            result = f"Échec et mat! {winner} gagnent"
        elif self.board.is_stalemate():
            result = "Pat"
        else:
            result = "Partie terminée"

        print("\n" + "=" * 60)
        print(f"  {result}")
        print("=" * 60)

        # Position reculée à la fin
        if not self.simulate:
            self.aller_position_reculee()

        return result

    def close(self):
        if self.engine:
            self.engine.quit()
        if self.rtde_c:
            self.rtde_c.stopScript()
        print("✓ Fermé")


def main():
    parser = argparse.ArgumentParser(description="Robot échecs autonome")
    parser.add_argument('--blanc', default='intermediaire')
    parser.add_argument('--noir', default='intermediaire')
    parser.add_argument('--simulate', action='store_true', help='Mode simulation')
    parser.add_argument('--pause', action='store_true', help='Pause entre coups')
    parser.add_argument('--mapping', default='chess_board_positions.json')
    parser.add_argument('--max-coups', type=int, default=150)
    parser.add_argument('--delai', type=float, default=1.0)
    parser.add_argument('--list-levels', action='store_true')
    parser.add_argument('--reset-position', action='store_true', help='Réenregistrer la position de départ')
    parser.add_argument('--reset-defausse', action='store_true', help='Réenregistrer la zone de défausse')
    parser.add_argument('--reset-all', action='store_true', help='Réenregistrer toutes les positions')

    args = parser.parse_args()

    if args.list_levels:
        StockfishPlayer.list_presets()
        return

    # Si on veut réinitialiser les positions
    if args.reset_all:
        args.reset_position = True
        args.reset_defausse = True

    if args.reset_position:
        if os.path.exists(FICHIER_POSITION_DEPART):
            os.remove(FICHIER_POSITION_DEPART)
            print(f"✓ Position de départ supprimée ({FICHIER_POSITION_DEPART})")

    if args.reset_defausse:
        if os.path.exists(FICHIER_ZONE_DEFAUSSE):
            os.remove(FICHIER_ZONE_DEFAUSSE)
            print(f"✓ Zone de défausse supprimée ({FICHIER_ZONE_DEFAUSSE})")

    print("=" * 60)
    print("     ♔ ROBOT ÉCHECS ♚")
    print("=" * 60)

    player_w = StockfishPlayer.from_preset("Blancs", chess.WHITE, args.blanc)
    player_b = StockfishPlayer.from_preset("Noirs", chess.BLACK, args.noir)

    print(f"\n  {player_w}")
    print(f"  {player_b}")

    game = ChessRobotGame(args.mapping, args.simulate)

    try:
        game.play(player_w, player_b, args.max_coups, args.delai, args.pause)
    except KeyboardInterrupt:
        print("\n⚠ Interrompu")
    finally:
        game.close()


if __name__ == "__main__":
    main()