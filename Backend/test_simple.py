#!/usr/bin/env python3
"""
Test simple de la fonction chess_vision()
"""

import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chess_vision import chess_vision

print("🚀 Lancement du test chess_vision()...")
print("=" * 60)

# Appel unique
result = chess_vision()

print("\n" + "=" * 60)
print("📊 RÉSULTATS:")
print("=" * 60)

if result['success']:
    print("✅ SUCCESS!")
    print(f"\n📷 Photo: {result.get('photo_path', 'N/A')}")
    print(f"💾 Output: {result.get('output_dir', 'N/A')}")
    print(f"\n🎯 Pièces détectées: {len(result['pieces'])}")
    
    white = [p for p in result['pieces'] if p['color'] == 'white']
    black = [p for p in result['pieces'] if p['color'] == 'black']
    
    print(f"   • Blanches: {len(white)}")
    print(f"   • Noires: {len(black)}")
    
    board_pieces = [p for p in result['pieces'] if p.get('zone') == 'board']
    cemetery = [p for p in result['pieces'] if p.get('zone') == 'cemetery']
    
    print(f"   • Sur plateau: {board_pieces}")
    print(f"   • Au cimetière: {len(cemetery)}")
    
    print("\n📋 Premiers JSON générés avec succès:")
    print("   • game_state.json")
    print("   • board_state.json")
    print("   • coordinates.json")
    
else:
    print("❌ ÉCHEC")
    print(f"\n⚠️  Erreur: {result.get('error', 'Erreur inconnue')}")

print("\n" + "=" * 60)
