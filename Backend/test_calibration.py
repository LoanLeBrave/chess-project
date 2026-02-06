#!/usr/bin/env python3
"""
Script de test pour vérifier la précision de la calibration
Teste quelques positions après calibration
"""

import json
import time
import sys

from config import ROBOT_IP, VITESSE, ACCELERATION, FICHIER_MAPPING


def test_calibration():
    """Teste la précision de la calibration en visitant quelques cases"""
    
    print("\n" + "="*60)
    print("🧪 TEST DE CALIBRATION")
    print("="*60 + "\n")
    
    # Charger le mapping
    try:
        with open(FICHIER_MAPPING, 'r') as f:
            data = json.load(f)
            cases = data.get("cases", {})
        print(f"✅ Mapping chargé: {len(cases)} cases\n")
    except Exception as e:
        print(f"❌ Erreur chargement mapping: {e}")
        return False
    
    # Connexion robot
    try:
        from rtde_control import RTDEControlInterface
        from rtde_receive import RTDEReceiveInterface
        from robotiq_gripper_control import RobotiqGripper
        
        print(f"🤖 Connexion au robot {ROBOT_IP}...")
        rtde_c = RTDEControlInterface(ROBOT_IP)
        rtde_r = RTDEReceiveInterface(ROBOT_IP)
        
        print("🦾 Activation du gripper...")
        gripper = RobotiqGripper(rtde_c)
        gripper.activate()
        gripper.set_force(40)
        gripper.set_speed(150)
        gripper.move(25)
        
        print("✅ Robot connecté!\n")
    except Exception as e:
        print(f"❌ Erreur connexion robot: {e}")
        return False
    
    # Cases à tester (coins + centre)
    cases_test = ['a1', 'a8', 'h1', 'h8', 'd4', 'e4', 'd5', 'e5']
    
    print("📍 Test de positionnement sur les cases clés:\n")
    
    try:
        for case in cases_test:
            if case not in cases:
                print(f"⚠️  Case {case} non trouvée")
                continue
            
            tcp = cases[case]['tcp']
            
            # Position au-dessus de la case
            tcp_haute = list(tcp)
            tcp_haute[2] += 0.05  # 5cm au-dessus
            
            print(f"   → {case.upper()}: ", end='', flush=True)
            rtde_c.moveL(tcp_haute, VITESSE, ACCELERATION)
            time.sleep(0.3)
            
            # Descendre à la case
            rtde_c.moveL(tcp, VITESSE * 0.5, ACCELERATION)
            time.sleep(0.5)
            
            # Remonter
            rtde_c.moveL(tcp_haute, VITESSE, ACCELERATION)
            time.sleep(0.3)
            
            print("✓")
        
        print("\n✅ Test de positionnement terminé!")
        print("\n💡 Vérifiez visuellement que le gripper était bien centré sur chaque case")
        
        # Retour position haute
        print("\n📍 Retour position haute...")
        pose = rtde_r.getActualTCPPose()
        pose_haute = list(pose)
        pose_haute[2] += 0.1
        rtde_c.moveL(pose_haute, VITESSE, ACCELERATION)
        
    except Exception as e:
        print(f"\n❌ Erreur durant le test: {e}")
        return False
    finally:
        rtde_c.stopScript()
    
    print("\n" + "="*60)
    print("✅ TEST TERMINÉ")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_calibration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
