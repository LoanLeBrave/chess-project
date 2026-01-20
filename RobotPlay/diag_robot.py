#!/usr/bin/env python3
"""
Test simple : déplacer UNE pièce de e2 à e4
Pour vérifier que le script de jeu fonctionne
"""

import json
import time
import os

ROBOT_IP = "192.168.0.11"
MAPPING_FILE = "chess_board_positions.json"

# Paramètres de mouvement
VITESSE = 0.1
ACCELERATION = 0.3
GRIPPER_OUVERTURE = 25

# Hauteurs
DELTA_APPROCHE = 0.03  # 3cm au-dessus
DELTA_RELACHE = 0.002  # 2mm au-dessus pour poser

print("="*60)
print("   TEST: Déplacer une pièce de e2 à e4")
print("="*60)

# Import
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper

# Connexion
print("\n[1] Connexion au robot...")
rtde_c = RTDEControlInterface(ROBOT_IP)
rtde_r = RTDEReceiveInterface(ROBOT_IP)
print(f"    ✅ Connecté")

# Gripper
print("\n[2] Activation gripper...")
gripper = RobotiqGripper(rtde_c)
gripper.activate()
gripper.set_force(40)
gripper.set_speed(150)
gripper.move(GRIPPER_OUVERTURE)
print(f"    ✅ Gripper ouvert à {GRIPPER_OUVERTURE}mm")

# Charger mapping
print(f"\n[3] Chargement mapping...")
with open(MAPPING_FILE, 'r') as f:
    data = json.load(f)
cases = data["cases"]
print(f"    ✅ {len(cases)} cases chargées")

# Vérifier e2 et e4
if "e2" not in cases:
    print("    ❌ Case e2 non mappée!")
    exit(1)
if "e4" not in cases:
    print("    ❌ Case e4 non mappée!")
    exit(1)

tcp_e2 = cases["e2"]["tcp"]
tcp_e4 = cases["e4"]["tcp"]

print(f"    e2: X={tcp_e2[0]:.4f} Y={tcp_e2[1]:.4f} Z={tcp_e2[2]:.4f}")
print(f"    e4: X={tcp_e4[0]:.4f} Y={tcp_e4[1]:.4f} Z={tcp_e4[2]:.4f}")

# Confirmation
print("\n" + "="*60)
print("   ⚠️  Le robot va déplacer une pièce de e2 à e4")
print("   Assurez-vous qu'il y a une pièce sur e2!")
print("="*60)
reponse = input("\nContinuer? (o/n): ").strip().lower()
if reponse not in ['o', 'oui', 'y']:
    print("Annulé")
    exit(0)

# Fonction helper
def position_avec_delta_z(tcp, delta):
    pos = list(tcp)
    pos[2] += delta
    return pos

# =============================================
# SÉQUENCE DE MOUVEMENT
# =============================================

print("\n" + "-"*60)
print("ÉTAPE 1: Aller au-dessus de e2 (approche)")
print("-"*60)
pos_e2_approche = position_avec_delta_z(tcp_e2, DELTA_APPROCHE)
print(f"  Destination: Z={pos_e2_approche[2]:.4f}")
input("  [ENTRÉE pour exécuter...]")
result = rtde_c.moveL(pos_e2_approche, VITESSE, ACCELERATION)
print(f"  moveL retour: {result}")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 2: Descendre sur e2 (prise)")
print("-"*60)
print(f"  Destination: Z={tcp_e2[2]:.4f}")
input("  [ENTRÉE pour exécuter...]")
result = rtde_c.moveL(tcp_e2, VITESSE, ACCELERATION)
print(f"  moveL retour: {result}")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 3: Fermer le gripper")
print("-"*60)
input("  [ENTRÉE pour exécuter...]")
gripper.close()
print("  ✅ Gripper fermé")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 4: Remonter (avec la pièce)")
print("-"*60)
print(f"  Destination: Z={pos_e2_approche[2]:.4f}")
input("  [ENTRÉE pour exécuter...]")
result = rtde_c.moveL(pos_e2_approche, VITESSE, ACCELERATION)
print(f"  moveL retour: {result}")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 5: Aller au-dessus de e4")
print("-"*60)
pos_e4_approche = position_avec_delta_z(tcp_e4, DELTA_APPROCHE)
print(f"  Destination: X={pos_e4_approche[0]:.4f} Y={pos_e4_approche[1]:.4f} Z={pos_e4_approche[2]:.4f}")
input("  [ENTRÉE pour exécuter...]")
result = rtde_c.moveL(pos_e4_approche, VITESSE, ACCELERATION)
print(f"  moveL retour: {result}")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 6: Descendre sur e4 (relâche)")
print("-"*60)
pos_e4_relache = position_avec_delta_z(tcp_e4, DELTA_RELACHE)
print(f"  Destination: Z={pos_e4_relache[2]:.4f}")
input("  [ENTRÉE pour exécuter...]")
result = rtde_c.moveL(pos_e4_relache, VITESSE, ACCELERATION)
print(f"  moveL retour: {result}")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 7: Ouvrir le gripper")
print("-"*60)
input("  [ENTRÉE pour exécuter...]")
gripper.move(GRIPPER_OUVERTURE)
print(f"  ✅ Gripper ouvert à {GRIPPER_OUVERTURE}mm")
time.sleep(0.5)

print("\n" + "-"*60)
print("ÉTAPE 8: Remonter")
print("-"*60)
print(f"  Destination: Z={pos_e4_approche[2]:.4f}")
input("  [ENTRÉE pour exécuter...]")
result = rtde_c.moveL(pos_e4_approche, VITESSE, ACCELERATION)
print(f"  moveL retour: {result}")
time.sleep(0.5)

# =============================================
# FIN
# =============================================
print("\n" + "="*60)
print("   ✅ MOUVEMENT e2 → e4 TERMINÉ!")
print("="*60)

# Vérifier position finale
pose_finale = rtde_r.getActualTCPPose()
print(f"\nPosition finale: X={pose_finale[0]:.4f} Y={pose_finale[1]:.4f} Z={pose_finale[2]:.4f}")

# Fermeture
print("\nFermeture...")
rtde_c.stopScript()
print("✅ Terminé")