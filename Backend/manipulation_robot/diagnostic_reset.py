#!/usr/bin/env python3
"""
Diagnostic pour identifier les problemes de board_reset.

Affiche :
- Le contenu du game_state.json
- Les coordonnees vision vs coordonnees calculees
- Les associations piece -> case initiale
- L'orientation du plateau
"""

import json
import os
import sys
from typing import Dict, List, Tuple

import chess

# Import des configs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import POSITION_INITIALE, PIECE_TYPE_MAP

# Constantes
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_STATE_PATH = os.path.join(
    _BACKEND_DIR, "chess_vision", "output", "latest", "game_state.json"
)

_VISION_TYPE_MAP: Dict[str, int] = {
    "Pawn": chess.PAWN,
    "Knight": chess.KNIGHT,
    "Bishop": chess.BISHOP,
    "Rook": chess.ROOK,
    "Queen": chess.QUEEN,
    "King": chess.KING,
}


def square_center_cam(square: str) -> Tuple[float, float]:
    """Calcule le centre d'une case (meme formule que robot_controller)."""
    file_idx = chess.FILE_NAMES.index(square[0])
    rank_idx = int(square[1]) - 1
    unit = 2.5
    return (file_idx - 3.5) * unit, (rank_idx - 3.5) * unit


def read_game_state() -> dict:
    """Lit le game_state.json."""
    if not os.path.exists(GAME_STATE_PATH):
        print(f"ERREUR: Fichier introuvable: {GAME_STATE_PATH}")
        sys.exit(1)
    
    with open(GAME_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("=" * 80)
    print("  DIAGNOSTIC BOARD RESET")
    print("=" * 80)
    print()

    # 1. Lire le game_state
    print(f"Lecture: {GAME_STATE_PATH}")
    state = read_game_state()
    pieces = state.get("pieces", [])
    
    print(f"\nPieces detectees: {len(pieces)}")
    print()

    # 2. Afficher toutes les pieces avec leurs coordonnees
    print("-" * 80)
    print("PIECES DETECTEES PAR LA VISION")
    print("-" * 80)
    print(f"{'ID':<6} {'Code':<8} {'Type':<12} {'Color':<8} {'Zone':<10} {'Chess':<8} "
          f"{'Vision X':>10} {'Vision Y':>10}")
    print("-" * 80)

    pieces_on_board = []
    for p in pieces:
        pid = p.get("id", "?")
        code = p.get("code", "?")
        ptype = p.get("type", "?")
        color = p.get("color", "?")
        zone = p.get("zone", "?")
        chess_sq = p.get("position", {}).get("chess", "---")
        vision_x = p.get("position", {}).get("board", {}).get("x", 0.0)
        vision_y = p.get("position", {}).get("board", {}).get("y", 0.0)

        print(f"{pid:<6} {code:<8} {ptype:<12} {color:<8} {zone:<10} {chess_sq:<8} "
              f"{vision_x:>10.3f} {vision_y:>10.3f}")
        
        if zone == "board":
            pieces_on_board.append(p)

    print()

    # 3. Comparer coordonnees vision vs coordonnees calculees
    print("-" * 80)
    print("COMPARAISON COORDONNEES VISION vs CALCUL (pour pieces sur plateau)")
    print("-" * 80)
    print(f"{'Chess':<8} {'Vision X':>10} {'Vision Y':>10} {'Calc X':>10} {'Calc Y':>10} "
          f"{'Delta X':>10} {'Delta Y':>10}")
    print("-" * 80)

    for p in pieces_on_board:
        chess_sq = p.get("position", {}).get("chess", "").lower()
        if not chess_sq:
            continue
        
        vision_x = p.get("position", {}).get("board", {}).get("x", 0.0)
        vision_y = p.get("position", {}).get("board", {}).get("y", 0.0)
        
        calc_x, calc_y = square_center_cam(chess_sq)
        
        delta_x = vision_x - calc_x
        delta_y = vision_y - calc_y
        
        print(f"{chess_sq:<8} {vision_x:>10.3f} {vision_y:>10.3f} {calc_x:>10.3f} "
              f"{calc_y:>10.3f} {delta_x:>10.3f} {delta_y:>10.3f}")

    print()

    # 4. Verifier l'orientation du plateau
    print("-" * 80)
    print("VERIFICATION ORIENTATION DU PLATEAU")
    print("-" * 80)

    # Trouver les tours blanches
    white_rooks = [p for p in pieces_on_board 
                   if p.get("type") == "Rook" and p.get("color") == "white"]
    black_rooks = [p for p in pieces_on_board 
                   if p.get("type") == "Rook" and p.get("color") == "black"]

    print("\nTours blanches detectees:")
    for r in white_rooks:
        sq = r.get("position", {}).get("chess", "?")
        y = r.get("position", {}).get("board", {}).get("y", 0.0)
        print(f"  {sq}: y={y:.3f}")
        if sq in ["a1", "h1"]:
            print(f"    -> Position initiale correcte (blanc en bas)")
        elif sq in ["a8", "h8"]:
            print(f"    -> WARNING: Tour blanche en haut! Plateau inverse?")

    print("\nTours noires detectees:")
    for r in black_rooks:
        sq = r.get("position", {}).get("chess", "?")
        y = r.get("position", {}).get("board", {}).get("y", 0.0)
        print(f"  {sq}: y={y:.3f}")
        if sq in ["a8", "h8"]:
            print(f"    -> Position initiale correcte (noir en haut)")
        elif sq in ["a1", "h1"]:
            print(f"    -> WARNING: Tour noire en bas! Plateau inverse?")

    print()

    # 5. Simuler l'association greedy
    print("-" * 80)
    print("SIMULATION ASSOCIATION GREEDY (TYPE=Pawn, COLOR=white)")
    print("-" * 80)

    # Cibles pour les pions blancs
    white_pawn_targets = [sq for sq, (symbol, color) in POSITION_INITIALE.items()
                         if symbol == 'P' and color == chess.WHITE]
    print(f"\nCases cibles pour pions blancs: {sorted(white_pawn_targets)}")

    # Pions blancs detectes
    white_pawns = [p for p in pieces 
                   if p.get("type") == "Pawn" and p.get("color") == "white"]
    print(f"Pions blancs detectes: {len(white_pawns)}")

    print("\nAssociations calculees:")
    print(f"{'Piece':<15} {'Actuel':<8} {'Vision X':>10} {'Vision Y':>10} "
          f"{'Cible':<8} {'Dist':>8}")
    print("-" * 80)

    available = list(white_pawns)
    remaining_targets = list(white_pawn_targets)

    while remaining_targets and available:
        best_dist = float("inf")
        best_piece = None
        best_target = None

        for target in remaining_targets:
            tx, ty = square_center_cam(target)
            for piece in available:
                px = piece["position"]["board"]["x"]
                py = piece["position"]["board"]["y"]
                d = ((px - tx) ** 2 + (py - ty) ** 2) ** 0.5
                if d < best_dist:
                    best_dist = d
                    best_piece = piece
                    best_target = target

        if best_piece is None:
            break

        current_sq = best_piece.get("position", {}).get("chess", "---")
        px = best_piece["position"]["board"]["x"]
        py = best_piece["position"]["board"]["y"]

        print(f"{best_piece.get('code', '?'):<15} {current_sq:<8} {px:>10.3f} {py:>10.3f} "
              f"{best_target:<8} {best_dist:>8.3f}")

        available.remove(best_piece)
        remaining_targets.remove(best_target)

    print()
    print("=" * 80)
    print("FIN DIAGNOSTIC")
    print("=" * 80)


if __name__ == "__main__":
    main()
