#!/usr/bin/env python3
"""
Script de DIAGNOSTIC v2 - Test du robot étape par étape
"""

import json
import time
import os

ROBOT_IP = "192.168.0.11"
MAPPING_FILE = "chess_board_positions.json"

print("=" * 60)
print("   DIAGNOSTIC ROBOT UR5e - CHESS")
print("=" * 60)

# =========================================
# TEST 1: Import des modules
# =========================================
print("\n[TEST 1] Import des modules...")
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
    from robotiq_gripper_control import RobotiqGripper

    print("✅ Modules importés OK")
except Exception as e:
    print(f"❌ Erreur import: {e}")
    exit(1)

# =========================================
# TEST 2: Connexion RTDE Control
# =========================================
print(f"\n[TEST 2] Connexion RTDE Control à {ROBOT_IP}...")
try:
    rtde_c = RTDEControlInterface(ROBOT_IP)
    if rtde_c is None:
        print("❌ rtde_c est None!")
        exit(1)
    print(f"✅ RTDE Control connecté")
    print(f"   isConnected: {rtde_c.isConnected()}")
except Exception as e:
    print(f"❌ Erreur connexion Control: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# =========================================
# TEST 3: Connexion RTDE Receive
# =========================================
print(f"\n[TEST 3] Connexion RTDE Receive à {ROBOT_IP}...")
try:
    rtde_r = RTDEReceiveInterface(ROBOT_IP)
    if rtde_r is None:
        print("❌ rtde_r est None!")
        exit(1)
    print(f"✅ RTDE Receive connecté")
except Exception as e:
    print(f"❌ Erreur connexion Receive: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# =========================================
# TEST 4: Lecture position actuelle
# =========================================
print("\n[TEST 4] Lecture position TCP...")
try:
    pose = rtde_r.getActualTCPPose()
    print(f"✅ Position TCP actuelle:")
    print(f"   X={pose[0]:.4f}  Y={pose[1]:.4f}  Z={pose[2]:.4f}")
    print(f"   RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
except Exception as e:
    print(f"❌ Erreur lecture position: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# =========================================
# TEST 5: Mode robot
# =========================================
print("\n[TEST 5] Vérification mode robot...")
try:
    mode = rtde_r.getRobotMode()
    safety = rtde_r.getSafetyMode()

    modes = {0: "DISCONNECTED", 1: "CONFIRM_SAFETY", 2: "BOOTING",
             3: "POWER_OFF", 4: "POWER_ON", 5: "IDLE", 6: "BACKDRIVE",
             7: "RUNNING"}

    safety_modes = {0: "NORMAL", 1: "REDUCED", 2: "PROTECTIVE_STOP",
                    3: "RECOVERY", 4: "SAFEGUARD_STOP", 5: "SYSTEM_EMERGENCY_STOP",
                    6: "ROBOT_EMERGENCY_STOP", 7: "VIOLATION", 8: "FAULT"}

    print(f"   Robot Mode: {mode} ({modes.get(mode, 'UNKNOWN')})")
    print(f"   Safety Mode: {safety} ({safety_modes.get(safety, 'UNKNOWN')})")

    if mode != 7:
        print(f"   ⚠️ Robot PAS en mode RUNNING!")
    else:
        print(f"   ✅ Robot en mode RUNNING")

    if safety != 0:
        print(f"   ⚠️ Safety PAS en mode NORMAL!")
    else:
        print(f"   ✅ Safety en mode NORMAL")

except Exception as e:
    print(f"❌ Erreur mode robot: {e}")

# =========================================
# TEST 6: Vérifier isProgramRunning
# =========================================
print("\n[TEST 6] État du programme...")
try:
    is_connected = rtde_c.isConnected()
    is_running = rtde_c.isProgramRunning()
    print(f"   isConnected: {is_connected}")
    print(f"   isProgramRunning: {is_running}")

    if is_running:
        print("   ⚠️ Un programme tourne! Cela peut bloquer les commandes externes.")
except Exception as e:
    print(f"❌ Erreur: {e}")

# =========================================
# TEST 7: Charger le mapping
# =========================================
print(f"\n[TEST 7] Chargement mapping ({MAPPING_FILE})...")
try:
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ Fichier {MAPPING_FILE} non trouvé!")
        print(f"   Répertoire actuel: {os.getcwd()}")
        print(f"   Fichiers présents: {os.listdir('.')}")
    else:
        with open(MAPPING_FILE, 'r') as f:
            mapping_data = json.load(f)

        cases = mapping_data.get("cases", {})
        print(f"✅ Mapping chargé: {len(cases)} cases")

        if "e2" in cases:
            tcp = cases["e2"]["tcp"]
            print(f"   Position e2: X={tcp[0]:.4f} Y={tcp[1]:.4f} Z={tcp[2]:.4f}")
except Exception as e:
    print(f"❌ Erreur mapping: {e}")

# =========================================
# TEST 8: Test mouvement réel
# =========================================
print("\n[TEST 8] Test mouvement réel...")
print("   ⚠️ Le robot va monter de 2cm!")
reponse = input("   Continuer? (o/n): ").strip().lower()

if reponse in ['o', 'oui', 'y', 'yes']:
    try:
        # Position actuelle
        pose_avant = rtde_r.getActualTCPPose()
        print(f"   Position AVANT: Z={pose_avant[2]:.4f}")

        # Nouvelle position (+2cm en Z)
        nouvelle_pose = list(pose_avant)
        nouvelle_pose[2] += 0.02  # +2cm

        print(f"   Envoi commande moveL vers Z={nouvelle_pose[2]:.4f}...")
        print(f"   Vitesse: 0.1 m/s, Accélération: 0.3 m/s²")

        # Exécuter le mouvement
        result = rtde_c.moveL(nouvelle_pose, 0.1, 0.3)
        print(f"   Retour moveL: {result}")

        # Attendre
        print("   Attente 2 secondes...")
        time.sleep(2)

        # Vérifier
        pose_apres = rtde_r.getActualTCPPose()
        print(f"   Position APRÈS: Z={pose_apres[2]:.4f}")

        delta = (pose_apres[2] - pose_avant[2]) * 1000  # en mm
        print(f"   Déplacement réel: {delta:.2f} mm")

        if abs(delta) < 1:
            print("\n   ❌ LE ROBOT N'A PAS BOUGÉ!")
            print("\n   Vérifications sur le PENDANT:")
            print("   1. Remote Control activé? (Menu → Settings → System → Remote Control)")
            print("   2. Freedrive désactivé?")
            print("   3. Pas de Protective Stop?")
            print("   4. Pas de programme en cours?")
        else:
            print(f"\n   ✅ LE ROBOT A BOUGÉ DE {delta:.1f} mm!")

            # Revenir
            print("\n   Retour à la position initiale...")
            rtde_c.moveL(pose_avant, 0.1, 0.3)
            time.sleep(2)
            print("   ✅ Retour effectué")

    except Exception as e:
        print(f"❌ Erreur mouvement: {e}")
        import traceback

        traceback.print_exc()
else:
    print("   Test mouvement annulé")

# =========================================
# RÉSUMÉ
# =========================================
print("\n" + "=" * 60)
print("   FIN DU DIAGNOSTIC")
print("=" * 60)

# Fermeture
print("\nFermeture des connexions...")
try:
    rtde_c.stopScript()
    print("✅ Connexions fermées")
except:
    pass