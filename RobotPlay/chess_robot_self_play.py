#!/usr/bin/env python3
"""
Script de jeu d'échecs autonome - Robot UR5e joue contre lui-même
Utilise Stockfish pour les deux joueurs avec niveaux configurables
Génère des visualisations SVG de chaque coup
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

# Configuration par défaut
DEFAULT_ROBOT_IP = "192.168.0.11"
DEFAULT_MAPPING_FILE = "chess_board_positions.json"


class StockfishPlayer:
    """Représente un joueur Stockfish avec sa configuration"""

    PRESETS = {
        'debutant': {'depth': 8, 'time_limit': 0.5, 'skill_level': 3, 'elo_range': '800-1000'},
        'facile': {'depth': 10, 'time_limit': 0.8, 'skill_level': 6, 'elo_range': '1000-1200'},
        'intermediaire': {'depth': 12, 'time_limit': 1.0, 'skill_level': 10, 'elo_range': '1400-1600'},
        'avance': {'depth': 15, 'time_limit': 1.5, 'skill_level': 15, 'elo_range': '1800-2000'},
        'expert': {'depth': 18, 'time_limit': 2.0, 'skill_level': 18, 'elo_range': '2000-2200'},
        'maitre': {'depth': 22, 'time_limit': 3.0, 'skill_level': 20, 'elo_range': '2200+'}
    }

    def __init__(self, name, color, depth=15, time_limit=1.5, skill_level=15):
        """
        Initialise un joueur

        Args:
            name: Nom du joueur
            color: 'blanc' ou 'noir' (chess.WHITE ou chess.BLACK)
            depth: Profondeur d'analyse (1-30)
            time_limit: Temps limite en secondes
            skill_level: Niveau Stockfish (0-20)
        """
        self.name = name
        self.color = color
        self.depth = depth
        self.time_limit = time_limit
        self.skill_level = skill_level

    @classmethod
    def from_preset(cls, name, color, preset_name):
        """Crée un joueur depuis un preset"""
        preset_name = preset_name.lower()
        if preset_name not in cls.PRESETS:
            print(f"⚠ Preset '{preset_name}' inconnu. Presets disponibles: {list(cls.PRESETS.keys())}")
            preset_name = 'intermediaire'

        preset = cls.PRESETS[preset_name]
        return cls(
            name=name,
            color=color,
            depth=preset['depth'],
            time_limit=preset['time_limit'],
            skill_level=preset['skill_level']
        )

    @classmethod
    def list_presets(cls):
        """Affiche les presets disponibles"""
        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║                    NIVEAUX DISPONIBLES                       ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        for name, config in cls.PRESETS.items():
            print(
                f"║  {name:14} │ Skill={config['skill_level']:2} │ Depth={config['depth']:2} │ {config['elo_range']:10} ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    def get_elo_estimate(self):
        """Estime le Elo basé sur le skill level"""
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
        color_str = "Blancs" if self.color == chess.WHITE else "Noirs"
        return f"{self.name} ({color_str}) - Skill={self.skill_level}, Depth={self.depth}, Elo≈{self.get_elo_estimate()}"


class ChessGameVisualizer:
    """Gère la visualisation SVG des parties"""

    def __init__(self, output_dir="game_visualizations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.move_count = 0

    def generate_board_svg(self, board, last_move=None, move_info=None,
                           player_white=None, player_black=None):
        """
        Génère un SVG du plateau avec informations

        Args:
            board: Objet chess.Board
            last_move: Dernier coup joué
            move_info: Dict avec infos sur le coup
            player_white: StockfishPlayer blancs
            player_black: StockfishPlayer noirs
        """
        self.move_count += 1

        # Préparer les flèches
        arrows = []
        if last_move:
            arrows.append(chess.svg.Arrow(
                last_move.from_square,
                last_move.to_square,
                color='#15803d'  # Vert
            ))

        # Générer le SVG du plateau
        board_svg = chess.svg.board(
            board,
            arrows=arrows,
            lastmove=last_move,
            size=450,
            coordinates=True
        )

        # Créer un SVG enrichi avec infos
        turn = "Blancs" if board.turn == chess.WHITE else "Noirs"
        move_str = last_move.uci() if last_move else "Début"

        # Infos joueurs
        white_info = str(player_white) if player_white else "Blancs"
        black_info = str(player_black) if player_black else "Noirs"

        # Évaluation
        eval_str = ""
        if move_info and 'evaluation' in move_info:
            eval_val = move_info['evaluation']
            if isinstance(eval_val, str) and 'Mat' in eval_val:
                eval_str = f"⚡ {eval_val}"
            else:
                eval_str = f"Eval: {eval_val:+.2f}" if isinstance(eval_val, (int, float)) else f"Eval: {eval_val}"

        # HTML/SVG enrichi
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Coup {self.move_count}: {move_str}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            max-width: 520px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 16px;
        }}
        .move-number {{
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        .move-display {{
            font-size: 32px;
            font-weight: bold;
            color: #1e3a5f;
            margin: 8px 0;
        }}
        .evaluation {{
            font-size: 18px;
            color: #15803d;
            font-weight: 600;
        }}
        .board-container {{
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .players {{
            display: flex;
            justify-content: space-between;
            margin-top: 16px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .player {{
            text-align: center;
            flex: 1;
        }}
        .player-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .player-name {{
            font-size: 14px;
            font-weight: 600;
            color: #333;
        }}
        .player-skill {{
            font-size: 12px;
            color: #888;
        }}
        .turn-indicator {{
            text-align: center;
            margin-top: 12px;
            padding: 8px 16px;
            background: {('#f0fdf4' if board.turn == chess.WHITE else '#f5f5f5')};
            border-radius: 20px;
            display: inline-block;
        }}
        .footer {{
            text-align: center;
            margin-top: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="move-number">Coup {self.move_count}</div>
            <div class="move-display">{move_str.upper()}</div>
            <div class="evaluation">{eval_str}</div>
        </div>

        <div class="board-container">
            {board_svg}
        </div>

        <div class="players">
            <div class="player">
                <div class="player-label">♔ Blancs</div>
                <div class="player-name">{player_white.name if player_white else 'Joueur 1'}</div>
                <div class="player-skill">Skill {player_white.skill_level if player_white else '?'} • Elo {player_white.get_elo_estimate() if player_white else '?'}</div>
            </div>
            <div class="player">
                <div class="player-label">♚ Noirs</div>
                <div class="player-name">{player_black.name if player_black else 'Joueur 2'}</div>
                <div class="player-skill">Skill {player_black.skill_level if player_black else '?'} • Elo {player_black.get_elo_estimate() if player_black else '?'}</div>
            </div>
        </div>

        <div class="footer">
            <span class="turn-indicator">Au tour des <strong>{turn}</strong></span>
        </div>
    </div>
</body>
</html>"""

        # Sauvegarder
        filename = f"move_{self.move_count:03d}_{move_str}.html"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Aussi sauvegarder le SVG pur
        svg_filename = f"move_{self.move_count:03d}_{move_str}.svg"
        svg_filepath = self.output_dir / svg_filename
        with open(svg_filepath, 'w', encoding='utf-8') as f:
            f.write(board_svg)

        print(f"   📊 Visualisation: {svg_filename}")
        return svg_filepath

    def generate_game_summary(self, moves_history, result, player_white, player_black):
        """Génère un résumé HTML de la partie complète"""

        # Créer une galerie des coups
        moves_html = ""
        for i, (move, svg_file) in enumerate(moves_history, 1):
            moves_html += f"""
            <div class="move-card">
                <span class="move-num">{i}.</span>
                <span class="move-notation">{move}</span>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Résumé de la partie</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
            margin: 0;
            padding: 40px;
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
        }}
        h1 {{
            text-align: center;
            color: #1e3a5f;
            margin-bottom: 30px;
        }}
        .result {{
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            color: #15803d;
            padding: 20px;
            background: #f0fdf4;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        .players-summary {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 30px;
        }}
        .player-card {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            flex: 1;
            margin: 0 10px;
        }}
        .player-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .player-card p {{
            margin: 5px 0;
            color: #666;
        }}
        .moves-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
        }}
        .move-card {{
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .move-num {{
            color: #888;
            font-size: 12px;
        }}
        .move-notation {{
            font-weight: 600;
            color: #333;
        }}
        .stats {{
            margin-top: 30px;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>♔ Partie d'Échecs Robot ♚</h1>

        <div class="result">{result}</div>

        <div class="players-summary">
            <div class="player-card">
                <h3>♔ {player_white.name}</h3>
                <p>Blancs</p>
                <p>Skill Level: {player_white.skill_level}</p>
                <p>Elo ≈ {player_white.get_elo_estimate()}</p>
            </div>
            <div class="player-card">
                <h3>♚ {player_black.name}</h3>
                <p>Noirs</p>
                <p>Skill Level: {player_black.skill_level}</p>
                <p>Elo ≈ {player_black.get_elo_estimate()}</p>
            </div>
        </div>

        <h2>Coups joués ({len(moves_history)} coups)</h2>
        <div class="moves-list">
            {moves_html}
        </div>

        <div class="stats">
            <p>Partie générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            <p>Visualisations disponibles dans le dossier: {self.output_dir}</p>
        </div>
    </div>
</body>
</html>"""

        filepath = self.output_dir / "game_summary.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n📋 Résumé de la partie: {filepath}")
        return filepath


class ChessRobotSelfPlay:
    """Contrôleur principal pour le jeu autonome"""

    def __init__(self, stockfish_path=None, mapping_file=None,
                 robot_ip=None, simulate_robot=False):
        """
        Initialise le système de jeu autonome

        Args:
            stockfish_path: Chemin vers Stockfish
            mapping_file: Fichier JSON de mapping des cases
            robot_ip: IP du robot UR5e
            simulate_robot: Si True, simule les mouvements robot
        """
        self.simulate_robot = simulate_robot
        self.robot = None
        self.engine = None
        self.board = chess.Board()
        self.visualizer = ChessGameVisualizer()
        self.moves_history = []

        # Trouver Stockfish
        self.stockfish_path = self._find_stockfish(stockfish_path)
        if self.stockfish_path:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
                print(f"✓ Stockfish chargé: {self.stockfish_path}")
            except Exception as e:
                print(f"⚠ Erreur Stockfish: {e}")
                self.engine = None

        # Charger le mapping
        self.mapping_file = mapping_file or DEFAULT_MAPPING_FILE
        self.mapping_data = self._load_mapping()

        # Initialiser le robot (si pas en simulation)
        if not simulate_robot and self.mapping_data:
            self._init_robot(robot_ip or DEFAULT_ROBOT_IP)

    def _find_stockfish(self, path=None):
        """Cherche l'exécutable Stockfish"""
        paths_to_try = [
            path,
            '/opt/homebrew/bin/stockfish',
            '/usr/local/bin/stockfish',
            '/usr/games/stockfish',
            '/usr/bin/stockfish',
            'stockfish'
        ]

        for p in paths_to_try:
            if p and Path(p).exists():
                return p

        # Essayer avec which
        import subprocess
        try:
            result = subprocess.run(['which', 'stockfish'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        print("⚠ Stockfish non trouvé - Mode simulation activé")
        return None

    def _load_mapping(self):
        """Charge le fichier de mapping des cases"""
        if not os.path.exists(self.mapping_file):
            print(f"⚠ Fichier de mapping non trouvé: {self.mapping_file}")
            print("  Le robot sera simulé")
            self.simulate_robot = True
            return None

        try:
            with open(self.mapping_file, 'r') as f:
                data = json.load(f)
            print(f"✓ Mapping chargé: {len(data.get('cases', {}))} cases")
            return data
        except Exception as e:
            print(f"⚠ Erreur chargement mapping: {e}")
            self.simulate_robot = True
            return None

    def _init_robot(self, robot_ip):
        """Initialise la connexion au robot"""
        try:
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface
            from robotiq_gripper_control import RobotiqGripper

            print(f"Connexion au robot {robot_ip}...")
            self.rtde_c = RTDEControlInterface(robot_ip)
            self.rtde_r = RTDEReceiveInterface(robot_ip)

            print("Activation du gripper...")
            self.gripper = RobotiqGripper(self.rtde_c)
            self.gripper.activate()
            self.gripper.set_force(40)
            self.gripper.set_speed(150)
            self.gripper.move(25)  # Ouverture 50%

            self.robot = {
                'control': self.rtde_c,
                'receive': self.rtde_r,
                'gripper': self.gripper,
                'piece_en_main': False
            }
            print("✓ Robot connecté!")

        except ImportError:
            print("⚠ Bibliothèques robot non disponibles - Simulation activée")
            self.simulate_robot = True
        except Exception as e:
            print(f"⚠ Erreur connexion robot: {e} - Simulation activée")
            self.simulate_robot = True

    def configure_player(self, player):
        """Configure Stockfish pour un joueur"""
        if self.engine:
            try:
                self.engine.configure({
                    "Skill Level": player.skill_level,
                    "Threads": 1
                })
            except Exception as e:
                print(f"⚠ Erreur config Stockfish: {e}")

    def get_best_move(self, player):
        """Obtient le meilleur coup pour un joueur"""
        if not self.engine:
            # Mode simulation: retourne un coup légal aléatoire
            import random
            legal_moves = list(self.board.legal_moves)
            if legal_moves:
                return random.choice(legal_moves), {'evaluation': 0.0, 'mode': 'random'}
            return None, {'error': 'Aucun coup légal'}

        self.configure_player(player)

        try:
            info = self.engine.analyse(
                self.board,
                chess.engine.Limit(depth=player.depth, time=player.time_limit)
            )

            best_move = info.get("pv", [None])[0]
            if not best_move:
                legal_moves = list(self.board.legal_moves)
                best_move = legal_moves[0] if legal_moves else None

            # Extraire l'évaluation
            score = info.get("score")
            evaluation = 0.0
            if score:
                if score.relative.score() is not None:
                    evaluation = score.relative.score() / 100
                elif score.relative.mate() is not None:
                    mate_in = score.relative.mate()
                    evaluation = f"Mat en {abs(mate_in)}"

            return best_move, {
                'evaluation': evaluation,
                'depth': info.get('depth', player.depth),
                'mode': 'stockfish'
            }

        except Exception as e:
            print(f"⚠ Erreur analyse: {e}")
            return None, {'error': str(e)}

    def execute_robot_move(self, move):
        """Exécute un mouvement sur le robot physique"""
        if self.simulate_robot:
            print(f"   🤖 [SIMULATION] Déplacement: {move.uci()}")
            time.sleep(0.5)  # Simulation du temps de mouvement
            return True

        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)

        # Vérifier si c'est une capture
        is_capture = self.board.is_capture(move)

        if is_capture:
            print(f"   🤖 Capture: {from_square} prend {to_square}")
            # TODO: Implémenter la capture avec le robot
            # 1. Prendre la pièce capturée
            # 2. La déplacer vers une zone de capture
            # 3. Prendre la pièce qui capture
            # 4. La déplacer vers la case cible
        else:
            print(f"   🤖 Déplacement: {from_square} → {to_square}")
            # TODO: Implémenter le déplacement simple
            # 1. Prendre la pièce sur from_square
            # 2. La déplacer vers to_square

        return True

    def play_game(self, player_white, player_black, max_moves=200, delay=1.0):
        """
        Joue une partie complète

        Args:
            player_white: StockfishPlayer pour les blancs
            player_black: StockfishPlayer pour les noirs
            max_moves: Nombre maximum de coups
            delay: Délai entre les coups (secondes)
        """
        print("\n" + "=" * 70)
        print("                    ♔ PARTIE D'ÉCHECS ROBOT ♚")
        print("=" * 70)
        print(f"\n  {player_white}")
        print(f"  {player_black}")
        print("\n" + "-" * 70)

        # Position de départ
        self.board.reset()
        self.moves_history = []
        self.visualizer.move_count = 0

        # Générer la visualisation initiale
        initial_svg = self.visualizer.generate_board_svg(
            self.board,
            player_white=player_white,
            player_black=player_black
        )

        move_number = 0

        while not self.board.is_game_over() and move_number < max_moves:
            # Déterminer le joueur actuel
            current_player = player_white if self.board.turn == chess.WHITE else player_black
            color = "Blancs" if self.board.turn == chess.WHITE else "Noirs"

            move_number += 1
            print(f"\n{'─' * 50}")
            print(f"  Coup {move_number} - {current_player.name} ({color})")
            print(f"{'─' * 50}")

            # Obtenir le meilleur coup
            best_move, move_info = self.get_best_move(current_player)

            if not best_move:
                print("⚠ Aucun coup possible!")
                break

            # Afficher le coup
            move_san = self.board.san(best_move)
            print(f"   📍 Coup: {best_move.uci()} ({move_san})")

            if 'evaluation' in move_info:
                eval_val = move_info['evaluation']
                if isinstance(eval_val, (int, float)):
                    print(f"   📊 Évaluation: {eval_val:+.2f}")
                else:
                    print(f"   📊 Évaluation: {eval_val}")

            # Exécuter sur le robot
            self.execute_robot_move(best_move)

            # Jouer le coup sur le plateau
            self.board.push(best_move)

            # Générer la visualisation
            svg_path = self.visualizer.generate_board_svg(
                self.board,
                last_move=best_move,
                move_info=move_info,
                player_white=player_white,
                player_black=player_black
            )

            self.moves_history.append((move_san, svg_path))

            # Pause entre les coups
            time.sleep(delay)

        # Fin de partie
        result = self._get_game_result()
        print("\n" + "=" * 70)
        print(f"                    FIN DE PARTIE: {result}")
        print("=" * 70)

        # Générer le résumé
        self.visualizer.generate_game_summary(
            self.moves_history, result, player_white, player_black
        )

        return result

    def _get_game_result(self):
        """Détermine le résultat de la partie"""
        if self.board.is_checkmate():
            winner = "Noirs" if self.board.turn == chess.WHITE else "Blancs"
            return f"Échec et mat! {winner} gagnent"
        elif self.board.is_stalemate():
            return "Pat - Partie nulle"
        elif self.board.is_insufficient_material():
            return "Matériel insuffisant - Partie nulle"
        elif self.board.is_fifty_moves():
            return "Règle des 50 coups - Partie nulle"
        elif self.board.is_repetition():
            return "Triple répétition - Partie nulle"
        else:
            return "Partie incomplète"

    def close(self):
        """Ferme proprement les ressources"""
        if self.engine:
            self.engine.quit()
            print("✓ Stockfish fermé")

        if self.robot:
            try:
                self.robot['gripper'].move(25)
                self.robot['control'].stopScript()
                print("✓ Robot déconnecté")
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Robot d'échecs autonome - Joue contre lui-même",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Partie débutant vs expert
  python chess_robot_self_play.py --blanc debutant --noir expert

  # Partie avec niveaux personnalisés
  python chess_robot_self_play.py --blanc-skill 5 --noir-skill 15

  # Afficher les niveaux disponibles
  python chess_robot_self_play.py --list-levels

  # Mode simulation (sans robot)
  python chess_robot_self_play.py --simulate --blanc facile --noir avance
        """
    )

    parser.add_argument('--blanc', type=str, default='intermediaire',
                        help='Niveau du joueur blanc (preset)')
    parser.add_argument('--noir', type=str, default='intermediaire',
                        help='Niveau du joueur noir (preset)')
    parser.add_argument('--blanc-skill', type=int,
                        help='Skill level personnalisé pour les blancs (0-20)')
    parser.add_argument('--noir-skill', type=int,
                        help='Skill level personnalisé pour les noirs (0-20)')
    parser.add_argument('--blanc-depth', type=int, default=15,
                        help='Profondeur d\'analyse pour les blancs')
    parser.add_argument('--noir-depth', type=int, default=15,
                        help='Profondeur d\'analyse pour les noirs')
    parser.add_argument('--max-coups', type=int, default=100,
                        help='Nombre maximum de coups')
    parser.add_argument('--delai', type=float, default=0.5,
                        help='Délai entre les coups (secondes)')
    parser.add_argument('--simulate', action='store_true',
                        help='Mode simulation (pas de robot)')
    parser.add_argument('--stockfish', type=str,
                        help='Chemin vers Stockfish')
    parser.add_argument('--mapping', type=str,
                        help='Fichier de mapping des cases')
    parser.add_argument('--robot-ip', type=str, default=DEFAULT_ROBOT_IP,
                        help='IP du robot UR5e')
    parser.add_argument('--list-levels', action='store_true',
                        help='Afficher les niveaux disponibles')
    parser.add_argument('--output-dir', type=str, default='game_visualizations',
                        help='Dossier de sortie pour les SVG')

    args = parser.parse_args()

    # Afficher les niveaux si demandé
    if args.list_levels:
        StockfishPlayer.list_presets()
        return

    print("=" * 70)
    print("     ♔ ROBOT ÉCHECS - MODE JEU AUTONOME ♚")
    print("=" * 70)
    print()

    # Créer les joueurs
    if args.blanc_skill is not None:
        player_white = StockfishPlayer(
            name="Robot Blancs",
            color=chess.WHITE,
            skill_level=args.blanc_skill,
            depth=args.blanc_depth
        )
    else:
        player_white = StockfishPlayer.from_preset(
            name="Robot Blancs",
            color=chess.WHITE,
            preset_name=args.blanc
        )

    if args.noir_skill is not None:
        player_black = StockfishPlayer(
            name="Robot Noirs",
            color=chess.BLACK,
            skill_level=args.noir_skill,
            depth=args.noir_depth
        )
    else:
        player_black = StockfishPlayer.from_preset(
            name="Robot Noirs",
            color=chess.BLACK,
            preset_name=args.noir
        )

    # Afficher la configuration
    print("Configuration des joueurs:")
    print(f"  ♔ {player_white}")
    print(f"  ♚ {player_black}")
    print()

    # Initialiser le système
    game = ChessRobotSelfPlay(
        stockfish_path=args.stockfish,
        mapping_file=args.mapping,
        robot_ip=args.robot_ip,
        simulate_robot=args.simulate
    )

    # Configurer le dossier de sortie
    game.visualizer.output_dir = Path(args.output_dir)
    game.visualizer.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Jouer la partie
        result = game.play_game(
            player_white=player_white,
            player_black=player_black,
            max_moves=args.max_coups,
            delay=args.delai
        )

        print(f"\n✓ Partie terminée!")
        print(f"  Résultat: {result}")
        print(f"  Visualisations: {game.visualizer.output_dir}/")

    except KeyboardInterrupt:
        print("\n\n⚠ Partie interrompue")
    finally:
        game.close()


if __name__ == "__main__":
    main()