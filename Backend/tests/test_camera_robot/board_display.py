#!/usr/bin/env python3
"""
Affichage console de l'echiquier.

Transforme un mapping {case: code_piece} en representation
textuelle lisible dans le terminal.
"""

from .config import DISPLAY_SYMBOLS


def render_board(board_map: dict) -> str:
    """
    Produit une representation ASCII de l'echiquier.

    Args:
        board_map: dict {case: code_piece} (ex: {"a1": "WR", "e2": "WP"}).

    Returns:
        Chaine multi-lignes prete a etre affichee (print).
    """
    separator = "  +---+---+---+---+---+---+---+---+"
    lines = []

    lines.append("")
    lines.append("    a   b   c   d   e   f   g   h")
    lines.append(separator)

    for rank in range(8, 0, -1):
        row = f"{rank} |"
        for col in "abcdefgh":
            square = f"{col}{rank}"
            piece_code = board_map.get(square)
            symbol = DISPLAY_SYMBOLS.get(piece_code, " ") if piece_code else " "
            row += f" {symbol} |"
        row += f" {rank}"
        lines.append(row)
        lines.append(separator)

    lines.append("    a   b   c   d   e   f   g   h")
    lines.append("")

    return "\n".join(lines)


def print_board(board_map: dict) -> None:
    """Affiche l'echiquier dans le terminal."""
    print(render_board(board_map))
