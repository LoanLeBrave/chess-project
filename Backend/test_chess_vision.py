#!/usr/bin/env python3
"""
Exemple d'utilisation de la fonction chess_vision().
Fonction ultra-simple : un seul appel pour tout faire.
"""

from chess_vision import chess_vision

# Appel unique : photo + analyse + JSON
result = chess_vision()

# Vérifier le résultat
if result['success']:
    print("✅ Analyse terminée avec succès!")
    print(f"\n📊 Statistiques:")
    print(f"   • Pièces détectées: {len(result['pieces'])}")
    print(f"   • Blanches: {len([p for p in result['pieces'] if p['color'] == 'white'])}")
    print(f"   • Noires: {len([p for p in result['pieces'] if p['color'] == 'black'])}")
    print(f"\n💾 Fichiers générés:")
    print(f"   • Photo: {result['photo_path']}")
    print(f"   • JSON: {result['output_dir']}")
    print(f"\n🎯 Les JSON sont prêts pour le robot!")
else:
    print(f"❌ Erreur: {result['error']}")
