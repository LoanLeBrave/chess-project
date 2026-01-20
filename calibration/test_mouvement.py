#!/usr/bin/env python3
"""
Script de test pour vérifier que le robot bouge correctement.
Test simple: récupère la position, bouge de +1cm en X, vérifie le résultat.
"""

import time
import sys

try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    print("❌ Erreur: rtde_control et rtde_receive non installés")
    print("   Installer avec: pip install ur-rtde")
    sys.exit(1)

# Configuration
ROBOT_IP = "192.168.0.11"
VITESSE = 0.05
ACCELERATION = 0.2

def main():
    print("=" * 60)
    print("🧪 TEST DE MOUVEMENT ROBOT")
    print("=" * 60)
    
    # Connexion au robot
    print(f"\n🤖 Connexion au robot {ROBOT_IP}...")
    try:
        rtde_c = RTDEControlInterface(ROBOT_IP)
        rtde_r = RTDEReceiveInterface(ROBOT_IP)
        print("✅ Robot connecté!")
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return
    
    # Position initiale
    print("\n📍 Position initiale:")
    pos_initial = list(rtde_r.getActualTCPPose())
    print(f"   X={pos_initial[0]*1000:.1f}mm, Y={pos_initial[1]*1000:.1f}mm, Z={pos_initial[2]*1000:.1f}mm")
    
    # Préparer le mouvement: +10mm en X
    print("\n🎯 Déplacement prévu: +10mm en X")
    pos_cible = list(pos_initial)
    pos_cible[0] += 0.010  # +10mm
    
    print(f"   Position cible: X={pos_cible[0]*1000:.1f}mm, Y={pos_cible[1]*1000:.1f}mm, Z={pos_cible[2]*1000:.1f}mm")
    
    # Lancer le mouvement
    print("\n🚀 Lancement du mouvement...")
    try:
        rtde_c.moveL(pos_cible, VITESSE, ACCELERATION)
        print("✅ Commande moveL envoyée")
    except Exception as e:
        print(f"❌ Erreur lors de moveL: {e}")
        rtde_c.disconnect()
        rtde_r.disconnect()
        return
    
    # Attendre que le mouvement soit terminé
    print("\n⏳ Attente fin de mouvement...")
    time.sleep(0.3)  # Petit délai initial
    
    wait_count = 0
    while not rtde_c.isSteady():
        time.sleep(0.1)
        wait_count += 1
        if wait_count % 10 == 0:
            print(f"   Toujours en mouvement... ({wait_count/10:.1f}s)")
        if wait_count > 100:  # Timeout après 10 secondes
            print("⚠️  Timeout - le robot ne s'arrête pas")
            break
    
    print(f"✅ Mouvement terminé (après {wait_count/10:.1f}s)")
    
    # Stabilisation
    time.sleep(0.5)
    
    # Position finale
    print("\n📍 Position finale:")
    pos_finale = list(rtde_r.getActualTCPPose())
    print(f"   X={pos_finale[0]*1000:.1f}mm, Y={pos_finale[1]*1000:.1f}mm, Z={pos_finale[2]*1000:.1f}mm")
    
    # Calcul du déplacement réel
    print("\n📊 Résultat:")
    delta_x = (pos_finale[0] - pos_initial[0]) * 1000
    delta_y = (pos_finale[1] - pos_initial[1]) * 1000
    delta_z = (pos_finale[2] - pos_initial[2]) * 1000
    
    print(f"   Déplacement réel: ΔX={delta_x:.1f}mm, ΔY={delta_y:.1f}mm, ΔZ={delta_z:.1f}mm")
    
    if abs(delta_x - 10.0) < 1.0:
        print("✅ TEST RÉUSSI - Le robot a bien bougé de ~10mm en X")
    else:
        print(f"⚠️  TEST DOUTEUX - Attendu: +10mm, Réel: {delta_x:.1f}mm")
    
    # Déconnexion
    print("\n🔌 Déconnexion...")
    rtde_c.disconnect()
    rtde_r.disconnect()
    print("✅ Test terminé")
    print("=" * 60)

if __name__ == "__main__":
    main()
