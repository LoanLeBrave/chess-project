#!/usr/bin/env python3
"""
Script de vérification - Affiche les valeurs de configuration
"""

print("=" * 60)
print("   VÉRIFICATION CONFIGURATION")
print("=" * 60)

# Afficher le chemin du script
import os
import sys

print(f"\n📁 Script exécuté: {os.path.abspath(__file__)}")
print(f"📁 Répertoire actuel: {os.getcwd()}")

# Lister les fichiers Python dans le répertoire
print(f"\n📄 Fichiers Python présents:")
for f in os.listdir('.'):
    if f.endswith('.py'):
        taille = os.path.getsize(f)
        print(f"   - {f} ({taille} bytes)")

# Essayer d'importer les valeurs du script principal
print("\n" + "=" * 60)
print("   VALEURS DE CONFIGURATION")
print("=" * 60)

# Chercher le fichier chess_robot
fichiers_possibles = [
    'chess_robot_final.py',
    'chess_robot_self_play.py',
    'Chess_robot_self_play.py',
    'final_chess.py',
]

for fichier in fichiers_possibles:
    if os.path.exists(fichier):
        print(f"\n📄 Lecture de: {fichier}")
        with open(fichier, 'r') as f:
            contenu = f.read()

        # Chercher les lignes de configuration
        lignes_config = []
        for ligne in contenu.split('\n'):
            if 'DELTA_TRANSIT' in ligne and '=' in ligne and not ligne.strip().startswith('#'):
                lignes_config.append(ligne.strip())
            if 'DELTA_APPROCHE' in ligne and '=' in ligne and not ligne.strip().startswith('#'):
                lignes_config.append(ligne.strip())
            if 'DELTA_RELACHE' in ligne and '=' in ligne and not ligne.strip().startswith('#'):
                lignes_config.append(ligne.strip())
            if 'VITESSE' in ligne and '=' in ligne and not ligne.strip().startswith('#'):
                lignes_config.append(ligne.strip())

        if lignes_config:
            print("   Configuration trouvée:")
            for l in lignes_config[:10]:
                print(f"      {l}")
        else:
            print("   ⚠ Pas de configuration DELTA trouvée!")

print("\n" + "=" * 60)