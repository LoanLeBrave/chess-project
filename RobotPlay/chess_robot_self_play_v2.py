#!/usr/bin/env python3
"""
Script de jeu d'échecs autonome - Robot UR5e joue contre lui-même
Version FONCTIONNELLE avec contrôle robot réel via ControleRobotV2
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
        self.name = name
        self.color = color
        self.depth = depth
        self.time_limit = time_limit
        self.skill_level = skill_level

    @classmethod
    def from_preset(cls, name, color, preset_name):
        preset_name = preset_name.lower()
        if preset_name not in cls.PRESETS:
            print(f"⚠ Preset '{preset_name}' inconnu. Utilisation de 'intermediaire'")
            preset_name = 'intermediaire'

        preset = cls.PRESETS[preset_name]
        return cls(
            name=name, color=color,
            depth=preset['depth'],
            time_limit=preset['time_limit'],
            skill_level=preset['skill_level']
        )

    @classmethod
    def list_presets(cls):
        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║                    NIVEAUX DISPONIBLES                       ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        for name, config in cls.PRESETS.items():
            print(
                f"║  {name:14} │ Skill={config['skill_level']:2} │ Depth={config['depth']:2} │ {config['elo_range']:10} ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    def get_elo_estimate(self):
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


class ChessVisualizer:
    """Génère les visualisations SVG de la partie"""

    def __init__(self, output_dir="game_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.move_count = 0

    def save_position(self, board, last_move=None, move_info=None,
                      player_white=None, player_black=None):
        """Sauvegarde la position actuelle en SVG"""
        self.move_count += 1

        arrows = []
        if last_move:
            arrows.append(chess.svg.Arrow(
                last_move.from_square, last_move.to_square, color='#15803d'
            ))

        svg_content = chess.svg.board(board, arrows=arrows, lastmove=last_move,
                                      size=450, coordinates=True)

        move_str = last_move.uci() if last_move else "start"
        filename = f"move_{self.move_count:03d}_{move_str}.svg"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            f.write(svg_content)

        # Créer aussi un HTML enrichi
        self._create_html_view(board, last_move, move_info, player_white, player_black, move_str)

        return filepath

    def _create_html_view(self, board, last_move, move_info, player_white, player_black, move_str):
        """Crée une vue HTML enrichie"""
        arrows = []
        if last_move:
            arrows.append(chess.svg.Arrow(
                last_move.from_square, last_move.to_square, color='#15803d'
            ))

        board_svg = chess.svg.board(board, arrows=arrows, lastmove=last_move,
                                    size=450, coordinates=True)

        turn = "Blancs" if board.turn == chess.WHITE else "Noirs"
        eval_str = ""
        if move_info and 'evaluation' in move_info:
            ev = move_info['evaluation']
            eval_str = f"Eval: {ev:+.2f}" if isinstance(ev, (int, float)) else str(ev)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Coup {self.move_count}: {move_str}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #1e3a5f; margin: 0; padding: 20px;
               display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .container {{ background: white; border-radius: 16px; padding: 24px; max-width: 520px;
                     box-shadow: 0 20px 60px rgba(0,0,0,0.4); }}
        .header {{ text-align: center; margin-bottom: 16px; }}
        .move-num {{ font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 2px; }}
        .move-display {{ font-size: 32px; font-weight: bold; color: #1e3a5f; margin: 8px 0; }}
        .evaluation {{ font-size: 18px; color: #15803d; font-weight: 600; }}
        .board {{ border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .info {{ display: flex; justify-content: space-between; margin-top: 16px; padding: 12px;
                background: #f8f9fa; border-radius: 8px; }}
        .player {{ text-align: center; flex: 1; }}
        .player-label {{ font-size: 12px; color: #666; }}
        .player-name {{ font-size: 14px; font-weight: 600; }}
        .turn {{ text-align: center; margin-top: 12px; padding: 8px 16px;
                background: #f0fdf4; border-radius: 20px; display: inline-block; }}
        .footer {{ text-align: center; margin-top: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="move-num">Coup {self.move_count}</div>
            <div class="move-display">{move_str.upper()}</div>
            <div class="evaluation">{eval_str}</div>
        </div>
        <div class="board">{board_svg}</div>
        <div class="info">
            <div class="player">
                <div class="player-label">♔ Blancs</div>
                <div class="player-name">{player_white.name if player_white else 'Joueur 1'}</div>
            </div>
            <div class="player">
                <div class="player-label">♚ Noirs</div>
                <div class="player-name">{player_black.name if player_black else 'Joueur 2'}</div>
            </div>
        </div>
        <div class="footer">
            <span class="turn">Au tour des <strong>{turn}</strong></span>
        </div>
    </div>
</body>
</html>"""

        filepath = self.output_dir / f"move_{self.move_count:03d}_{move_str}.html"
        with open(filepath, 'w') as f:
            f.write(html)


class ChessRobotGame:
    """Contrôleur principal pour le jeu autonome avec robot réel"""

    def __init__(self, stockfish_path=None, mapping_file="chess_board_positions.json",
                 simulate_robot=False, output_dir="game_output"):

        self.simulate_robot = simulate_robot
        self.robot = None
        self.engine = None
        self.board = chess.Board()
        self.visualizer = ChessVisualizer(output_dir)
        self.moves_history = []

        # Trouver Stockfish
        self.stockfish_path = self._find_stockfish(stockfish_path)
        if self.stockfish_path:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
                print(f"✓ Stockfish: {self.stockfish_path}")
            except Exception as e:
                print(f"⚠ Erreur Stockfish: {e}")
        else:
            print("⚠ Stockfish non trouvé - Coups aléatoires")

        # Initialiser le robot (si pas en simulation)
        if not simulate_robot:
            self._init_robot(mapping_file)
        else:
            print("⚠ Mode SIMULATION activé - Le robot ne bougera pas")

    def _find_stockfish(self, path=None):
        paths = [path, '/opt/homebrew/bin/stockfish', '/usr/local/bin/stockfish',
                 '/usr/games/stockfish', '/usr/bin/stockfish', 'stockfish']

        for p in paths:
            if p and Path(p).exists():
                return p

        # Essayer avec which
        import subprocess
        try:
            result = subprocess.run(['which', 'stockfish'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        return None

    def _init_robot(self, mapping_file):
        """Initialise la connexion au robot via ControleRobotV2"""
        try:
            # Essayer d'importer ControleRobotV2
            from ControleRobotV2 import ChessRobotPlayer

            self.robot = ChessRobotPlayer(mapping_file)
            print(f"✓ Robot connecté!")
            print(f"✓ Mapping chargé: {len(self.robot.cases)} cases")

        except ImportError as e:
            print(f"⚠ Module ControleRobotV2 non trouvé: {e}")
            print("  → Mode SIMULATION activé")
            self.simulate_robot = True

        except FileNotFoundError as e:
            print(f"⚠ Fichier de mapping non trouvé: {e}")
            print("  → Mode SIMULATION activé")
            self.simulate_robot = True

        except Exception as e:
            print(f"⚠ Erreur connexion robot: {e}")
            print("  → Mode SIMULATION activé")
            self.simulate_robot = True

    def configure_engine(self, player):
        """Configure Stockfish pour un joueur"""
        if self.engine:
            try:
                self.engine.configure({"Skill Level": player.skill_level, "Threads": 1})
            except Exception as e:
                print(f"⚠ Config engine: {e}")

    def get_best_move(self, player):
        """Obtient le meilleur coup via Stockfish"""
        if not self.engine:
            # Mode aléatoire si pas de Stockfish
            import random
            legal = list(self.board.legal_moves)
            return (random.choice(legal), {'evaluation': 0.0, 'mode': 'random'}) if legal else (None,
                                                                                                {'error': 'No moves'})

        self.configure_engine(player)

        try:
            info = self.engine.analyse(self.board,
                                       chess.engine.Limit(depth=player.depth, time=player.time_limit))

            best = info.get("pv", [None])[0]
            if not best:
                legal = list(self.board.legal_moves)
                best = legal[0] if legal else None

            score = info.get("score")
            evaluation = 0.0
            if score:
                if score.relative.score() is not None:
                    evaluation = score.relative.score() / 100
                elif score.relative.mate() is not None:
                    evaluation = f"Mat en {abs(score.relative.mate())}"

            return best, {'evaluation': evaluation, 'depth': info.get('depth'), 'mode': 'stockfish'}

        except Exception as e:
            print(f"⚠ Analyse: {e}")
            return None, {'error': str(e)}

    def execute_move_on_robot(self, move):
        """Exécute le coup sur le robot physique"""
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)

        # Mode simulation
        if self.simulate_robot or self.robot is None:
            print(f"   🤖 [SIMULATION] {from_sq} → {to_sq}")
            time.sleep(0.3)
            return True

        # Mode robot réel
        is_capture = self.board.is_capture(move)

        try:
            if is_capture:
                print(f"   🤖 CAPTURE: {from_sq} prend {to_sq}")
                # Utiliser la méthode capturer_piece de ControleRobotV2
                success = self.robot.capturer_piece(from_sq, to_sq)
            else:
                print(f"   🤖 DÉPLACEMENT: {from_sq} → {to_sq}")
                # Utiliser la méthode deplacer_piece de ControleRobotV2
                success = self.robot.deplacer_piece(from_sq, to_sq)

            if not success:
                print(f"   ⚠ Échec du mouvement robot!")

            return success

        except Exception as e:
            print(f"   ⚠ Erreur robot: {e}")
            return False

    def play_game(self, player_white, player_black, max_moves=200, delay=1.0,
                  pause_between_moves=False):
        """
        Joue une partie complète
        """
        print("\n" + "=" * 70)
        print("                    ♔ PARTIE D'ÉCHECS ROBOT ♚")
        print("=" * 70)
        print(f"\n  {player_white}")
        print(f"  {player_black}")
        print(f"\n  Mode: {'🔴 SIMULATION' if self.simulate_robot else '🟢 ROBOT RÉEL'}")
        print("-" * 70)

        # Confirmation avant de lancer avec le robot réel
        if not self.simulate_robot:
            print("\n⚠️  Le robot va bouger physiquement!")
            print("   Assurez-vous que l'échiquier est prêt et que la zone est dégagée.")
            reponse = input("   Continuer? (o/n): ").strip().lower()
            if reponse != 'o' and reponse != 'oui':
                print("   Partie annulée.")
                return "Annulée"

        self.board.reset()
        self.moves_history = []
        self.visualizer.move_count = 0

        # Position initiale
        self.visualizer.save_position(self.board, player_white=player_white, player_black=player_black)

        move_num = 0

        while not self.board.is_game_over() and move_num < max_moves:
            current_player = player_white if self.board.turn == chess.WHITE else player_black
            color = "Blancs" if self.board.turn == chess.WHITE else "Noirs"

            move_num += 1
            print(f"\n{'─' * 50}")
            print(f"  Coup {move_num} - {current_player.name} ({color})")
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
                ev = move_info['evaluation']
                if isinstance(ev, (int, float)):
                    print(f"   📊 Eval: {ev:+.2f}")
                else:
                    print(f"   📊 Eval: {ev}")

            # Exécuter sur le robot
            if not self.execute_move_on_robot(best_move):
                print("⚠ Erreur robot - Voulez-vous continuer en simulation? (o/n)")
                if input().strip().lower() in ['o', 'oui']:
                    self.simulate_robot = True
                else:
                    print("Partie arrêtée.")
                    break

            # Jouer sur l'échiquier virtuel
            self.board.push(best_move)

            # Générer la visualisation
            svg_path = self.visualizer.save_position(
                self.board, last_move=best_move, move_info=move_info,
                player_white=player_white, player_black=player_black
            )
            print(f"   📊 SVG: {svg_path.name}")

            self.moves_history.append((move_san, svg_path))

            # Pause
            if pause_between_moves:
                input("   [Appuie ENTRÉE pour continuer...]")
            else:
                time.sleep(delay)

        # Résultat
        result = self._get_result()
        print("\n" + "=" * 70)
        print(f"                    FIN: {result}")
        print("=" * 70)

        # Sauvegarder le résumé
        self._save_game_summary(result, player_white, player_black)

        return result

    def _get_result(self):
        if self.board.is_checkmate():
            winner = "Noirs" if self.board.turn == chess.WHITE else "Blancs"
            return f"Échec et mat! {winner} gagnent"
        elif self.board.is_stalemate():
            return "Pat - Nulle"
        elif self.board.is_insufficient_material():
            return "Matériel insuffisant - Nulle"
        elif self.board.is_fifty_moves():
            return "50 coups - Nulle"
        elif self.board.is_repetition():
            return "Répétition - Nulle"
        return "Partie incomplète"

    def _save_game_summary(self, result, player_white, player_black):
        """Sauvegarde le résumé de la partie"""
        moves_str = " ".join([m[0] for m in self.moves_history])

        summary = {
            'date': datetime.now().isoformat(),
            'result': result,
            'total_moves': len(self.moves_history),
            'player_white': {
                'name': player_white.name,
                'skill_level': player_white.skill_level,
                'depth': player_white.depth,
                'elo_estimate': player_white.get_elo_estimate()
            },
            'player_black': {
                'name': player_black.name,
                'skill_level': player_black.skill_level,
                'depth': player_black.depth,
                'elo_estimate': player_black.get_elo_estimate()
            },
            'pgn_moves': moves_str,
            'final_fen': self.board.fen(),
            'mode': 'simulation' if self.simulate_robot else 'robot'
        }

        filepath = self.visualizer.output_dir / "game_summary.json"
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n📋 Résumé: {filepath}")

    def close(self):
        """Ferme proprement les ressources"""
        if self.engine:
            self.engine.quit()
            print("✓ Stockfish fermé")

        if self.robot and not self.simulate_robot:
            try:
                self.robot.fermer()
                print("✓ Robot déconnecté")
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Robot échecs autonome - Le robot joue contre lui-même",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Partie avec robot réel
  python chess_robot_self_play.py --blanc debutant --noir expert

  # Mode simulation (sans robot)
  python chess_robot_self_play.py --simulate --blanc facile --noir avance

  # Avec pause entre chaque coup
  python chess_robot_self_play.py --blanc intermediaire --noir maitre --pause
        """
    )

    parser.add_argument('--blanc', type=str, default='intermediaire', help='Niveau blancs')
    parser.add_argument('--noir', type=str, default='intermediaire', help='Niveau noirs')
    parser.add_argument('--blanc-skill', type=int, help='Skill personnalisé blancs (0-20)')
    parser.add_argument('--noir-skill', type=int, help='Skill personnalisé noirs (0-20)')
    parser.add_argument('--max-coups', type=int, default=150, help='Limite de coups')
    parser.add_argument('--delai', type=float, default=1.0, help='Délai entre coups (s)')
    parser.add_argument('--pause', action='store_true', help='Pause manuelle entre coups')
    parser.add_argument('--simulate', action='store_true', help='Mode simulation (pas de robot)')
    parser.add_argument('--stockfish', type=str, help='Chemin Stockfish')
    parser.add_argument('--mapping', type=str, default='chess_board_positions.json', help='Fichier mapping')
    parser.add_argument('--output', type=str, default='game_output', help='Dossier sortie')
    parser.add_argument('--list-levels', action='store_true', help='Afficher niveaux')

    args = parser.parse_args()

    if args.list_levels:
        StockfishPlayer.list_presets()
        return

    print("=" * 70)
    print("     ♔ ROBOT ÉCHECS - JEU AUTONOME ♚")
    print("=" * 70)

    # Créer les joueurs
    if args.blanc_skill is not None:
        player_white = StockfishPlayer("Robot Blancs", chess.WHITE,
                                       skill_level=args.blanc_skill, depth=15)
    else:
        player_white = StockfishPlayer.from_preset("Robot Blancs", chess.WHITE, args.blanc)

    if args.noir_skill is not None:
        player_black = StockfishPlayer("Robot Noirs", chess.BLACK,
                                       skill_level=args.noir_skill, depth=15)
    else:
        player_black = StockfishPlayer.from_preset("Robot Noirs", chess.BLACK, args.noir)

    print(f"\n  ♔ {player_white}")
    print(f"  ♚ {player_black}")

    # Initialiser le jeu
    game = ChessRobotGame(
        stockfish_path=args.stockfish,
        mapping_file=args.mapping,
        simulate_robot=args.simulate,
        output_dir=args.output
    )

    try:
        result = game.play_game(
            player_white, player_black,
            max_moves=args.max_coups,
            delay=args.delai,
            pause_between_moves=args.pause
        )

        print(f"\n✓ Terminé: {result}")
        print(f"  Visualisations: {game.visualizer.output_dir}/")

    except KeyboardInterrupt:
        print("\n\n⚠ Partie interrompue (Ctrl+C)")
    finally:
        game.close()


if __name__ == "__main__":
    main()