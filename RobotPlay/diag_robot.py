#!/usr/bin/env python3
"""
Script de DIAGNOSTIC - Test du robot étape par étape
Pour identifier pourquoi le robot ne bouge pas
"""

import json
import time
import os

ROBOT_IP = "192.168.0.11"
MAPPING_FILE = "chess_board_positions.json"


def test_etape(nom, fonction):
    """Exécute une étape de test"""
    print(f"\n{'=' * 60}")
    print(f"TEST: {nom}")
    print(f"{'=' * 60}")
    try:
        result = fonction()
        print(f"✅ {nom} - OK")
        return result
    except Exception as e:
        print(f"❌ {nom} - ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=" * 60)
    print("   DIAGNOSTIC ROBOT UR5e - CHESS")
    print("=" * 60)

    # =========================================
    # TEST 1: Import des modules
    # =========================================
    def test_imports():
        global RTDEControlInterface, RTDEReceiveInterface, RobotiqGripper
        from rtde_control import RTDEControlInterface
        from rtde_receive import RTDEReceiveInterface
        from robotiq_gripper_control import RobotiqGripper
        print("   Modules importés: rtde_control, rtde_receive, robotiq_gripper_control")
        return True

    if not test_etape("Import des modules", test_imports):
        return

    # =========================================
    # TEST 2: Connexion RTDE Control
    # =========================================
    rtde_c = None

    def test_rtde_control():
        global rtde_c
        rtde_c = RTDEControlInterface(ROBOT_IP)
        print(f"   Connecté à {ROBOT_IP} (Control)")
        return rtde_c

    if not test_etape("Connexion RTDE Control", test_rtde_control):
        return

    # =========================================
    # TEST 3: Connexion RTDE Receive
    # =========================================
    rtde_r = None

    def test_rtde_receive():
        global rtde_r
        rtde_r = RTDEReceiveInterface(ROBOT_IP)
        print(f"   Connecté à {ROBOT_IP} (Receive)")
        return rtde_r

    if not test_etape("Connexion RTDE Receive", test_rtde_receive):
        return

    # =========================================
    # TEST 4: Lecture position actuelle
    # =========================================
    def test_lecture_position():
        pose = rtde_r.getActualTCPPose()
        print(f"   Position TCP actuelle:")
        print(f"   X={pose[0]:.4f}  Y={pose[1]:.4f}  Z={pose[2]:.4f}")
        print(f"   RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
        return pose

    pose_actuelle = test_etape("Lecture position TCP", test_lecture_position)
    if pose_actuelle is None:
        return

    # =========================================
    # TEST 5: Vérifier mode robot
    # =========================================
    def test_mode_robot():
        mode = rtde_r.getRobotMode()
        status = rtde_r.getRobotStatus()
        safety = rtde_r.getSafetyMode()

        modes = {0: "DISCONNECTED", 1: "CONFIRM_SAFETY", 2: "BOOTING",
                 3: "POWER_OFF", 4: "POWER_ON", 5: "IDLE", 6: "BACKDRIVE",
                 7: "RUNNING"}

        safety_modes = {0: "NORMAL", 1: "REDUCED", 2: "PROTECTIVE_STOP",
                        3: "RECOVERY", 4: "SAFEGUARD_STOP", 5: "SYSTEM_EMERGENCY_STOP",
                        6: "ROBOT_EMERGENCY_STOP", 7: "VIOLATION", 8: "FAULT"}

        print(f"   Robot Mode: {mode} ({modes.get(mode, 'UNKNOWN')})")
        print(f"   Robot Status: {status}")
        print(f"   Safety Mode: {safety} ({safety_modes.get(safety, 'UNKNOWN')})")

        if mode != 7:
            print(f"   ⚠️ Le robot n'est PAS en mode RUNNING!")
            print(f"   → Vérifiez que le robot est démarré et en mode Remote Control")

        if safety != 0:
            print(f"   ⚠️ Le robot n'est PAS en mode NORMAL!")
            print(f"   → Vérifiez les arrêts d'urgence")

        return mode == 7 and safety == 0

    robot_ok = test_etape("Vérification mode robot", test_mode_robot)

    # =========================================
    # TEST 6: Charger le mapping
    # =========================================
    mapping_data = None

    def test_mapping():
        global mapping_data
        if not os.path.exists(MAPPING_FILE):
            print(f"   ❌ Fichier {MAPPING_FILE} non trouvé!")
            return None

        with open(MAPPING_FILE, 'r') as f:
            mapping_data = json.load(f)

        cases = mapping_data.get("cases", {})
        print(f"   Cases mappées: {len(cases)}")
        print(f"   Exemples: {list(cases.keys())[:5]}...")

        if "e2" in cases:
            tcp = cases["e2"]["tcp"]
            print(f"   Position e2: X={tcp[0]:.4f} Y={tcp[1]:.4f} Z={tcp[2]:.4f}")

        return mapping_data

    mapping_data = test_etape("Chargement mapping", test_mapping)
    if mapping_data is None:
        return

    # =========================================
    # TEST 7: Test mouvement simple (CRITIQUE)
    # =========================================
    def test_mouvement_simple():
        print("\n   ⚠️ Le robot va bouger de 1cm vers le HAUT!")
        print("   Assurez-vous que la zone est dégagée.")
        reponse = input("   Continuer? (o/n): ").strip().lower()

        if reponse not in ['o', 'oui', 'y']:
            print("   Test annulé")
            return False

        # Position actuelle
        pose = rtde_r.getActualTCPPose()
        print(f"   Position avant: Z={pose[2]:.4f}")

        # Monter de 1cm
        nouvelle_pose = list(pose)
        nouvelle_pose[2] += 0.01  # +1cm en Z

        print(f"   Commande moveL vers Z={nouvelle_pose[2]:.4f}...")

        # Essayer moveL
        vitesse = 0.1
        acceleration = 0.3

        result = rtde_c.moveL(nouvelle_pose, vitesse, acceleration)
        print(f"   Retour moveL: {result}")

        time.sleep(1)

        # Vérifier nouvelle position
        pose_apres = rtde_r.getActualTCPPose()
        print(f"   Position après: Z={pose_apres[2]:.4f}")

        delta = pose_apres[2] - pose[2]
        print(f"   Déplacement réel: {delta * 1000:.2f} mm")

        if abs(delta) < 0.001:
            print("   ❌ Le robot N'A PAS BOUGÉ!")
            print("\n   Causes possibles:")
            print("   1. Robot pas en mode Remote Control (vérifier le pendant)")
            print("   2. Programme en cours sur le pendant")
            print("   3. Protective stop actif")
            print("   4. Limites de sécurité atteintes")
            return False
        else:
            print("   ✅ Le robot a bougé!")

            # Revenir à la position initiale
            print("   Retour position initiale...")
            rtde_c.moveL(pose, vitesse, acceleration)
            return True

    mouvement_ok = test_etape("Test mouvement simple (+1cm Z)", test_mouvement_simple)

    # =========================================
    # TEST 8: Test moveL avec async
    # =========================================
    if not mouvement_ok:
        def test_mouvement_async():
            print("\n   Essai avec moveL asynchrone...")

            pose = rtde_r.getActualTCPPose()
            nouvelle_pose = list(pose)
            nouvelle_pose[2] += 0.01

            # Essayer avec asynchrone=False explicitement
            print("   Commande moveL (synchrone)...")
            result = rtde_c.moveL(nouvelle_pose, 0.1, 0.3, False)
            print(f"   Retour: {result}")

            time.sleep(2)

            pose_apres = rtde_r.getActualTCPPose()
            delta = pose_apres[2] - pose[2]
            print(f"   Déplacement: {delta * 1000:.2f} mm")

            return abs(delta) > 0.001

        test_etape("Test moveL synchrone", test_mouvement_async)

    # =========================================
    # TEST 9: Vérifier isConnected et autres états
    # =========================================
    def test_etats():
        print("   États RTDE:")
        print(f"   - isConnected: {rtde_c.isConnected()}")
        print(f"   - isProgramRunning: {rtde_c.isProgramRunning()}")

        # Vérifier si un programme tourne sur le pendant
        if rtde_c.isProgramRunning():
            print("   ⚠️ Un programme est en cours sur le robot!")
            print("   → Arrêtez le programme sur le pendant")

        return True

    test_etape("Vérification états RTDE", test_etats)

    # =========================================
    # RÉSUMÉ
    # =========================================
    print("\n" + "=" * 60)
    print("   RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 60)

    print(f"""
   Connexion RTDE:     {'✅' if rtde_c else '❌'}
   Lecture position:   {'✅' if pose_actuelle else '❌'}
   Mode robot OK:      {'✅' if robot_ok else '❌'}
   Mapping chargé:     {'✅' if mapping_data else '❌'}
   Mouvement robot:    {'✅' if mouvement_ok else '❌'}
    """)

    if not mouvement_ok:
        print("""
   ⚠️ PROBLÈME IDENTIFIÉ: Le robot ne bouge pas

   Vérifications à faire sur le PENDANT:

   1. Mode Remote Control activé?
      → Menu hamburger → Settings → System → Remote Control → Enable

   2. Programme en cours?
      → Arrêter tout programme actif

   3. Protective Stop?
      → Vérifier les voyants et messages d'erreur

   4. Freedrive actif?
      → Désactiver le freedrive

   5. Installation correcte?
      → Vérifier que l'installation est chargée
        """)

    # Fermeture
    print("\nFermeture des connexions...")
    try:
        rtde_c.stopScript()
    except:
        pass


if __name__ == "__main__":
    main()