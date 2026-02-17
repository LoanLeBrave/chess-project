#!/usr/bin/env python3
"""
Outil de debug pour comprendre le mapping game_state.json -> affichage.

Affiche:
- Toutes les pieces detectees avec leurs positions
- Le board_map construit
- L'affichage ASCII
- Comparaison zone par zone (board vs cemetery)
"""

import sys
import os
import json

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board_reader import read_game_state, get_board_map
from board_display import render_board


def main():
    print("=" * 70)
    print("  DEBUG GAME_STATE.JSON -> AFFICHAGE")
    print("=" * 70)
    
    game_state = read_game_state()
    if not game_state:
        print("\n[!] Impossible de lire game_state.json")
        return
    
    # ----------------------------------------------------------------
    # 1. Métadonnées
    # ----------------------------------------------------------------
    meta = game_state.get("metadata", {})
    print(f"\n[METADATA]")
    print(f"  Timestamp      : {meta.get('timestamp', 'N/A')}")
    print(f"  Tour           : {meta.get('turn', 'N/A')}")
    print(f"  Pieces totales : {meta.get('total_detected', 0)}")
    print(f"  Sur plateau    : {meta.get('on_board', 0)}")
    print(f"  Au cimetiere   : {meta.get('in_cemetery', 0)}")
    print(f"  Manquantes     : {meta.get('missing_count', 0)}")
    
    # ----------------------------------------------------------------
    # 2. Pieces detectees par zone
    # ----------------------------------------------------------------
    pieces = game_state.get("pieces", [])
    
    board_pieces = [p for p in pieces if p.get("zone") == "board"]
    cemetery_pieces = [p for p in pieces if p.get("zone") == "cemetery"]
    
    print(f"\n[PIECES DETECTEES]")
    print(f"  Board    : {len(board_pieces)} pieces")
    print(f"  Cemetery : {len(cemetery_pieces)} pieces")
    
    # ----------------------------------------------------------------
    # 3. Details des pieces sur le plateau
    # ----------------------------------------------------------------
    print(f"\n[PIECES SUR LE PLATEAU (zone='board')]")
    print(f"  {'Code':<6} {'Type':<8} {'Couleur':<7} {'Chess':<6} Board(x,y)")
    print("  " + "-" * 60)
    
    for piece in sorted(board_pieces, key=lambda p: p.get("position", {}).get("chess", "")):
        code = piece.get("code", "??")
        ptype = piece.get("type", "?")
        color = piece.get("color", "?")
        chess_pos = piece.get("position", {}).get("chess", "null")
        board_pos = piece.get("position", {}).get("board", {})
        bx = board_pos.get("x", 0.0)
        by = board_pos.get("y", 0.0)
        
        print(f"  {code:<6} {ptype:<8} {color:<7} {chess_pos:<6} ({bx:6.2f}, {by:6.2f})")
    
    # ----------------------------------------------------------------
    # 4. Details des pieces au cimetiere
    # ----------------------------------------------------------------
    if cemetery_pieces:
        print(f"\n[PIECES AU CIMETIERE (zone='cemetery')]")
        print(f"  {'Code':<6} {'Type':<8} {'Couleur':<7} {'Grid':<6} Board(x,y)")
        print("  " + "-" * 60)
        
        for piece in cemetery_pieces:
            code = piece.get("code", "??")
            ptype = piece.get("type", "?")
            color = piece.get("color", "?")
            grid_pos = piece.get("position", {}).get("grid", "?")
            board_pos = piece.get("position", {}).get("board", {})
            bx = board_pos.get("x", 0.0)
            by = board_pos.get("y", 0.0)
            
            print(f"  {code:<6} {ptype:<8} {color:<7} {grid_pos:<6} ({bx:6.2f}, {by:6.2f})")
    
    # ----------------------------------------------------------------
    # 5. Board map construit
    # ----------------------------------------------------------------
    board_map = get_board_map(game_state)
    
    print(f"\n[BOARD_MAP CONSTRUIT]")
    print(f"  Nombre de cases occupees : {len(board_map)}")
    print(f"  Contenu :")
    
    # Regrouper par rang pour affichage compact
    for rank in range(8, 0, -1):
        row_items = []
        for col in "abcdefgh":
            square = f"{col}{rank}"
            code = board_map.get(square)
            if code:
                row_items.append(f"{square}:{code}")
        if row_items:
            print(f"    Rang {rank} : {', '.join(row_items)}")
    
    # ----------------------------------------------------------------
    # 6. Affichage ASCII
    # ----------------------------------------------------------------
    print(f"\n[AFFICHAGE ASCII]")
    board_text = render_board(board_map)
    print(board_text)
    
    # ----------------------------------------------------------------
    # 7. Pieces manquantes
    # ----------------------------------------------------------------
    missing = game_state.get("missing_pieces", [])
    if missing:
        print(f"\n[PIECES MANQUANTES ({len(missing)})]")
        white_missing = [p["code"] for p in missing if p.get("color") == "white"]
        black_missing = [p["code"] for p in missing if p.get("color") == "black"]
        
        if white_missing:
            print(f"  Blanches : {', '.join(white_missing)}")
        if black_missing:
            print(f"  Noires   : {', '.join(black_missing)}")
    
    print("\n" + "=" * 70)
    print("  ANALYSE TERMINEE")
    print("=" * 70)
    print("\nPour comparer avec la realite physique:")
    print("  1. Regardez les positions 'chess' des pieces sur le plateau")
    print("  2. Verifiez que l'affichage ASCII correspond")
    print("  3. Si decalage: le probleme vient de la calibration camera")
    print("     -> Voir Backend/chess_vision/config.py (board_calibration.json)")
    print()


if __name__ == "__main__":
    main()
