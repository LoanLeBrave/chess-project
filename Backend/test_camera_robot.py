#!/usr/bin/env python3
"""
Test de connexion Camera-Robot.

Prend une photo du plateau via chess_vision, affiche l'echiquier en console,
et permet de deplacer des pieces en tapant des commandes (ex: e2 e4).
Le robot utilise les positions PRECISES detectees par la camera.

Usage:
    python test_camera_robot.py

Commandes:
    e2 e4    - Deplace la piece de e2 vers e4
    photo    - Reprend une photo sans bouger le robot
    quit     - Quitte le programme
"""

import sys
import os
import asyncio
import re

# Ajouter les chemins pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "manipulation_robot"))

import chess
from chess_vision import chess_vision
from manipulation_robot.robot_controller import RobotController

# Mapping type vision -> type chess (pour hauteur de piece)
VISION_TYPE_TO_CHESS = {
    "Pawn": chess.PAWN,
    "Knight": chess.KNIGHT,
    "Bishop": chess.BISHOP,
    "Rook": chess.ROOK,
    "Queen": chess.QUEEN,
    "King": chess.KING,
}

# Symboles d'affichage (board_state utilise "WP", "BR", etc.)
DISPLAY_SYMBOLS = {
    "WK": "K", "WQ": "Q", "WR": "R", "WB": "B", "WN": "N", "WP": "P",
    "BK": "k", "BQ": "q", "BR": "r", "BB": "b", "BN": "n", "BP": "p",
}

# Pattern pour valider une case d'echecs
SQUARE_PATTERN = re.compile(r'^[a-h][1-8]$')


def capture_board_state():
    """
    Prend une photo et analyse le plateau.

    Returns:
        (game_state, board_state) ou (None, None) en cas d'erreur.
    """
    print("\nCapture en cours...")
    result = chess_vision()

    if not result.get('success'):
        error = result.get('error', 'Erreur inconnue')
        print(f"Erreur vision: {error}")
        return None, None

    game_state = result.get('game_state')
    board_state = result.get('board_state')

    if not game_state or not board_state:
        print("Erreur: JSON de jeu non genere")
        return None, None

    pieces = result.get('pieces', [])
    board_pieces = [p for p in pieces if p.get('zone') == 'board']
    print(f"OK - {len(board_pieces)} pieces detectees sur le plateau")

    return game_state, board_state


def display_board(board_state):
    """
    Affiche l'echiquier en console a partir du board_state.

    Args:
        board_state: dict avec cle "board" -> {"a1": "WR"|null, ...}
    """
    board = board_state.get('board', {})
    separator = "  +---+---+---+---+---+---+---+---+"

    print("\n    a   b   c   d   e   f   g   h")
    print(separator)

    for rank in range(8, 0, -1):
        row = f"{rank} |"
        for col in "abcdefgh":
            square = f"{col}{rank}"
            piece_code = board.get(square)
            if piece_code:
                symbol = DISPLAY_SYMBOLS.get(piece_code, "?")
            else:
                symbol = " "
            row += f" {symbol} |"
        row += f" {rank}"
        print(row)
        print(separator)

    print("    a   b   c   d   e   f   g   h\n")


def find_piece_at_square(game_state, square):
    """
    Trouve la piece a une case donnee avec ses coordonnees precises.

    Args:
        game_state: dict game_state (format complet avec pieces[])
        square: case en notation echecs (ex: "e2")

    Returns:
        dict de la piece ou None
    """
    for piece in game_state.get('pieces', []):
        chess_pos = piece.get('position', {}).get('chess')
        if chess_pos and chess_pos.lower() == square.lower():
            if piece.get('zone') == 'board':
                return piece
    return None


async def execute_robot_move(robot, piece_data, to_square):
    """
    Execute un deplacement robot: pick a la position precise, place au centre de la case cible.

    Args:
        robot: instance RobotController connectee
        piece_data: dict de la piece (depuis game_state)
        to_square: case destination (ex: "e4")
    """
    # Position precise de la piece (detectee par la camera)
    precise_x = piece_data['position']['board']['x']
    precise_y = piece_data['position']['board']['y']

    # Type de piece pour la hauteur
    piece_type = VISION_TYPE_TO_CHESS.get(piece_data['type'], chess.PAWN)
    robot.piece_courante = piece_type

    # Position pick: coordonnees PRECISES de la camera
    p_pick = robot.cam_to_robot(precise_x, precise_y, use_piece_height=True)

    # Position place: centre geometrique de la case cible
    cx, cy = robot.get_square_center(to_square)
    p_place = robot.cam_to_robot(cx, cy, use_piece_height=True)

    from_square = piece_data['position'].get('chess', '??')
    piece_name = piece_data.get('code', '??')

    print(f"  Pick  {piece_name} @ {from_square} -> coords ({precise_x:.2f}, {precise_y:.2f})")
    print(f"  Place -> {to_square} (centre case)")
    print(f"  Type: {piece_data['type']} | Hauteur piece active")
    print("  Execution du mouvement...")

    await robot._sequence_pick_and_place(p_pick, p_place)

    # Retour en position haute
    from manipulation_robot.config import DELTA_TRANSIT
    p_safe = list(p_place)
    p_safe[2] = robot.calib_origin[2] + DELTA_TRANSIT
    await robot._move_tcp(p_safe)

    print("  Mouvement termine!")


def parse_command(user_input):
    """
    Parse une commande utilisateur.

    Returns:
        ("move", from_sq, to_sq) ou ("photo",) ou ("quit",) ou ("invalid",)
    """
    text = user_input.strip().lower()

    if text in ('quit', 'q', 'exit'):
        return ("quit",)

    if text in ('photo', 'p', 'capture'):
        return ("photo",)

    # Tenter de parser "e2 e4" ou "e2e4"
    parts = text.split()
    if len(parts) == 2:
        from_sq, to_sq = parts
    elif len(parts) == 1 and len(text) == 4:
        from_sq, to_sq = text[:2], text[2:]
    else:
        return ("invalid",)

    if SQUARE_PATTERN.match(from_sq) and SQUARE_PATTERN.match(to_sq):
        return ("move", from_sq, to_sq)

    return ("invalid",)


async def main():
    print("=" * 60)
    print("  TEST CONNEXION CAMERA - ROBOT")
    print("=" * 60)
    print()
    print("Commandes:")
    print("  e2 e4  - Deplacer une piece")
    print("  photo  - Reprendre une photo")
    print("  quit   - Quitter")
    print()

    # Initialiser le robot
    print("Initialisation du robot...")
    robot = RobotController()
    if not robot.init_robot():
        print("ERREUR: Impossible de se connecter au robot.")
        print("Verifiez que le robot est allume et accessible sur le reseau.")
        return

    print()

    # Premiere capture
    game_state, board_state = capture_board_state()
    if game_state is None:
        print("ERREUR: Impossible de capturer l'etat du plateau.")
        print("Verifiez la camera et la calibration (board_calibration.json).")
        robot.close()
        return

    display_board(board_state)

    # Boucle principale
    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nArret.")
            break

        if not user_input:
            continue

        command = parse_command(user_input)

        if command[0] == "quit":
            print("Arret du programme.")
            break

        elif command[0] == "photo":
            game_state, board_state = capture_board_state()
            if game_state is not None:
                display_board(board_state)

        elif command[0] == "move":
            _, from_sq, to_sq = command

            # Verifier qu'une piece existe sur la case source
            piece = find_piece_at_square(game_state, from_sq)
            if piece is None:
                print(f"Aucune piece detectee sur {from_sq}")
                continue

            print(f"\nDeplacement: {from_sq} -> {to_sq}")

            # Executer le mouvement robot
            try:
                await execute_robot_move(robot, piece, to_sq)
            except Exception as e:
                print(f"Erreur mouvement robot: {e}")
                continue

            # Reprendre une photo pour verifier
            print("\nVerification...")
            game_state, board_state = capture_board_state()
            if game_state is not None:
                display_board(board_state)

        elif command[0] == "invalid":
            print("Commande invalide. Exemples: 'e2 e4', 'photo', 'quit'")

    # Fermeture propre
    robot.close()
    print("Robot deconnecte. Au revoir!")


if __name__ == "__main__":
    asyncio.run(main())
