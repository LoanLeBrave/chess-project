#!/usr/bin/env python3
"""
Interface en ligne de commande (CLI).

Gere la boucle interactive : lecture des commandes utilisateur,
parsing, dispatch vers les bons modules.
"""

import sys
from typing import Tuple

from .config import SQUARE_PATTERN
from .board_reader import read_game_state, get_board_map, find_piece_at, format_age, get_metadata
from .board_display import print_board
from .robot_bridge import RobotBridge


# ---------------------------------------------------------------------------
#  Parsing des commandes
# ---------------------------------------------------------------------------

def parse_command(user_input: str) -> Tuple:
    """
    Interprete la saisie utilisateur.

    Returns:
        ("quit",)
        ("refresh",)
        ("status",)
        ("move", from_sq, to_sq)
        ("help",)
        ("invalid",)
    """
    # Nettoyer les caracteres non-ASCII (artefacts terminal Raspberry Pi)
    text = "".join(c for c in user_input if c.isascii()).strip().lower()

    if not text:
        return ("invalid",)

    if text in ("quit", "q", "exit"):
        return ("quit",)

    if text in ("refresh", "r", "photo", "p", "capture"):
        return ("refresh",)

    if text in ("status", "s", "info"):
        return ("status",)

    if text in ("help", "h", "?"):
        return ("help",)

    # Tenter de parser un mouvement : "e2 e4" ou "e2e4"
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


# ---------------------------------------------------------------------------
#  Affichage d'aide
# ---------------------------------------------------------------------------

HELP_TEXT = """
Commandes disponibles :
  e2 e4    Deplacer une piece (notation algebrique)
  refresh  Relire le fichier game_state.json
  status   Afficher les metadonnees (nombre de pieces, tour, etc.)
  help     Afficher cette aide
  quit     Quitter le programme
"""


# ---------------------------------------------------------------------------
#  Boucle interactive
# ---------------------------------------------------------------------------

async def run(robot: RobotBridge) -> None:
    """
    Boucle principale du CLI.

    Lit game_state.json, affiche le plateau, puis attend des commandes.
    """
    print()
    print("=" * 56)
    print("  TEST CAMERA - ROBOT")
    print("=" * 56)
    print(HELP_TEXT)

    # Premiere lecture
    game_state = _refresh_and_display()
    if game_state is None:
        return

    # Boucle de commandes
    while True:
        try:
            sys.stdout.write("> ")
            sys.stdout.flush()
            raw = sys.stdin.buffer.readline()
            user_input = raw.decode("utf-8", errors="ignore").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nArret.")
            break

        if not user_input:
            continue

        command = parse_command(user_input)

        # -- Quit --------------------------------------------------------
        if command[0] == "quit":
            print("Arret du programme.")
            break

        # -- Refresh -----------------------------------------------------
        elif command[0] == "refresh":
            game_state = _refresh_and_display()

        # -- Status ------------------------------------------------------
        elif command[0] == "status":
            if game_state:
                _print_status(game_state)
            else:
                print("  Aucun etat charge. Tapez 'refresh'.")

        # -- Help --------------------------------------------------------
        elif command[0] == "help":
            print(HELP_TEXT)

        # -- Move --------------------------------------------------------
        elif command[0] == "move":
            _, from_sq, to_sq = command

            if game_state is None:
                print("  Aucun etat charge. Tapez 'refresh'.")
                continue

            piece = find_piece_at(game_state, from_sq)
            if piece is None:
                print(f"  Aucune piece detectee sur {from_sq}.")
                continue

            print(f"\n  Deplacement : {from_sq} -> {to_sq}")
            try:
                await robot.move_piece(piece, to_sq)
            except Exception as exc:
                print(f"  [!] Erreur mouvement : {exc}")
                continue

            # Relecture automatique apres mouvement
            print("\n  Verification...")
            game_state = _refresh_and_display()

        # -- Invalide ----------------------------------------------------
        elif command[0] == "invalid":
            print("  Commande invalide. Tapez 'help' pour la liste des commandes.")


# ---------------------------------------------------------------------------
#  Helpers internes
# ---------------------------------------------------------------------------

def _refresh_and_display() -> dict | None:
    """Lit game_state.json, affiche le plateau et retourne le game_state."""
    game_state = read_game_state()
    if game_state is None:
        print("  [!] Impossible de lire game_state.json.")
        print("      Verifiez que infinite_chess_vision.py tourne en parallele.")
        return None

    board_map = get_board_map(game_state)
    pieces_on_board = sum(1 for p in game_state.get("pieces", []) if p.get("zone") == "board")
    freshness = format_age(game_state)

    print(f"  {pieces_on_board} pieces sur le plateau  |  {freshness}")
    print_board(board_map)

    return game_state


def _print_status(game_state: dict) -> None:
    """Affiche les metadonnees du game_state."""
    meta = get_metadata(game_state)
    print()
    print(f"  Tour          : {meta.get('turn', '?')}")
    print(f"  Coup n.       : {meta.get('move_count', '?')}")
    print(f"  Pieces totales: {meta.get('total_detected', '?')}")
    print(f"  Sur plateau   : {meta.get('on_board', '?')}")
    print(f"  Eliminees     : {meta.get('in_cemetery', '?')}")
    print(f"  Manquantes    : {meta.get('missing_count', '?')}")
    print(f"  Fraicheur     : {format_age(game_state)}")
    print()
