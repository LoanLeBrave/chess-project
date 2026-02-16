#!/usr/bin/env python3
"""
Script de capture et analyse en boucle infinie.
Appelle chess_vision() en continu pour une surveillance permanente du plateau.

Usage:
    python3 chess_vision/infinite_chess_vision.py
    ou
    python3 -m chess_vision.infinite_chess_vision

Arrêt: Ctrl+C
"""

import sys
import os
import time
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_vision import chess_vision


def main():
    """Boucle infinie d'analyse du plateau."""
    print("=" * 60)
    print("♟️  INFINITE CHESS VISION - Analyse continue du plateau")
    print("=" * 60)
    print("\n⚡ Mode: Enchainement dynamique (max vitesse)")
    print("🛑 Arrêt: Ctrl+C\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            start_time = time.time()
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{timestamp}] Itération #{iteration}")
            print("-" * 40)
            
            try:
                # Appel de la fonction chess_vision
                result = chess_vision()
                
                if result.get('success'):
                    pieces = result.get('pieces', [])
                    board_pieces = [p for p in pieces if p.get('zone') == 'board']
                    
                    elapsed = time.time() - start_time
                    print(f"✅ Succès | {len(board_pieces)} pièces sur plateau | {elapsed:.2f}s")
                    
                    # Afficher l'état du jeu si disponible
                    game_state = result.get('game_state')
                    if game_state and 'board_state' in game_state:
                        board_state = game_state['board_state']
                        print(f"   État: {sum(1 for v in board_state.values() if v)} cases occupées")
                else:
                    error = result.get('error', 'Erreur inconnue')
                    elapsed = time.time() - start_time
                    print(f"❌ Échec | {error} | {elapsed:.2f}s")
            
            except KeyboardInterrupt:
                raise  # Propager pour arrêter proprement
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"⚠️  Exception | {type(e).__name__}: {e} | {elapsed:.2f}s")
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print(f"🛑 Arrêt manuel après {iteration} itérations")
        print("=" * 60)


if __name__ == "__main__":
    main()
