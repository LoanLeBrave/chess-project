#!/usr/bin/env python3
"""
Script de jeu d'échecs autonome - Robot UR5e joue contre lui-même
VERSION FINALE - Avec contrôle robot RÉEL intégré
"""

import chess
import chess.engine
import chess.svg
from pathlib import Path
import json
import time
import argparse
import os
from datetime import datetime

# ============================================================================
#                         CONFIGURATION
# ============================================================================

ROBOT_IP = "192.168.0.11"
VITESSE = 0.1
ACCELERATION = 0.3
GRIPPER_OUVERTURE = 25
DELTA_APPROCHE = 0.04  # 4cm au-dessus (était 3cm, +10mm)
DELTA_RELACHE = 0.004  # 4mm au-dessus pour poser (était 2mm, +2mm)


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

        if not simulate:
            self._init_robot(mapping_file)
        else:
            print("⚠ Mode SIMULATION - Le robot ne bougera pas")

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
        self.delta_relache = data.get("delta_hauteur_relache", DELTA_RELACHE)
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
        except Exception as e:
            print(f"⚠ Erreur robot: {e}")
            self.simulate = True

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

        print(f"      → Approche {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Descente...")
        self.rtde_c.moveL(tcp, VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Fermeture gripper...")
        self.gripper.close()
        time.sleep(0.3)

        print(f"      → Remontée...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        return True

    def _poser_piece(self, case):
        """Pose une pièce sur une case"""
        case = case.lower()
        if case not in self.cases:
            print(f"      ⚠ Case {case} non mappée!")
            return False

        tcp = self.cases[case]["tcp"]

        print(f"      → Approche {case.upper()}...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_approche), VITESSE, ACCELERATION)
        time.sleep(0.2)

        print(f"      → Descente (relâche)...")
        self.rtde_c.moveL(self._pos_avec_z(tcp, self.delta_relache), VITESSE, ACCELERATION)
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

        # Déposer hors de l'échiquier (on monte juste et on lâche)
        pose = self.rtde_r.getActualTCPPose()
        pose_haute = list(pose)
        pose_haute[2] += 0.05  # +5cm
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

        self.board.reset()
        self.visualizer.move_count = 0
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

            # EXÉCUTER SUR LE ROBOT
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

    args = parser.parse_args()

    if args.list_levels:
        StockfishPlayer.list_presets()
        return

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