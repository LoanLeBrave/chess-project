#!/usr/bin/env python3
"""
Test de lecture haute fréquence de latest/game_state.json.
Simule un programme externe qui lit le JSON en continu pendant que
chess_vision() met à jour le dossier latest.

Usage:
    python3 chess_vision/test_read_latest.py

Ce script lit game_state.json aussi vite que possible et
vérifie qu'il ne crash jamais (fichier manquant, JSON corrompu, etc.)
"""

import os
import sys
import json
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LATEST_DIR = os.path.join(SCRIPT_DIR, "output", "latest")
JSON_FILE = os.path.join(LATEST_DIR, "game_state.json")

def main():
    print("=" * 60)
    print("🔍 TEST LECTURE HAUTE FREQUENCE - latest/game_state.json")
    print("=" * 60)
    print(f"\nFichier surveillé: {JSON_FILE}")
    print("⚡ Lecture toutes les 50ms")
    print("🛑 Arrêt: Ctrl+C\n")

    reads = 0
    errors = 0
    missing = 0
    success = 0

    try:
        while True:
            reads += 1
            try:
                if not os.path.exists(JSON_FILE):
                    missing += 1
                    status = "❌ MANQUANT"
                    info = ""
                else:
                    with open(JSON_FILE, 'r') as f:
                        data = json.load(f)
                    success += 1
                    # Vérifier structure minimale
                    if 'board_state' not in data and 'pieces' not in data:
                        status = "⚠️  JSON INCOMPLET"
                        info = ""
                        errors += 1
                    else:
                        status = "✅"
                        # Compter les pièces sur le plateau
                        board = data.get('board_state', {})
                        occupied = {k: v for k, v in board.items() if v}
                        info = f"| {len(occupied)} pièces sur le plateau"
            except json.JSONDecodeError:
                errors += 1
                status = "❌ JSON CORROMPU"
                info = ""
            except FileNotFoundError:
                missing += 1
                status = "❌ DISPARU EN COURS DE LECTURE"
                info = ""
            except Exception as e:
                errors += 1
                status = f"❌ {type(e).__name__}: {e}"
                info = ""

            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] #{reads:>6d} {status} {info} (ok={success} err={errors} miss={missing})")

            time.sleep(0.05)  # 50ms = 20 lectures/sec

    except KeyboardInterrupt:
        print(f"\n{'=' * 60}")
        print(f"📊 RESULTATS APRES {reads} LECTURES:")
        print(f"   ✅ Succès:   {success}")
        print(f"   ❌ Erreurs:  {errors}")
        print(f"   ❌ Manquant: {missing}")
        rate = (success / reads * 100) if reads > 0 else 0
        print(f"   📈 Taux:     {rate:.2f}%")
        print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
