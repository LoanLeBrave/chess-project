#!/usr/bin/env python3
"""
Script simple pour déterminer la correspondance axes robot ↔ repère plateau.
Le robot bouge dans des directions connues, l'utilisateur observe visuellement.

Procédure:
1. Place le robot au-dessus du plateau (visible par la caméra)
2. Lance le script
3. Le robot va bouger dans 4 directions : +X, -X, +Y, -Y
4. À chaque mouvement, observe visuellement dans quelle direction il va
5. Note les résultats
"""

import sys
import time

try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    print("❌ rtde_control non installé")
    sys.exit(1)

# Configuration
ROBOT_IP = "192.168.0.11"
VITESSE = 0.05
ACCELERATION = 0.2
DEPLACEMENT = 0.05  # 5cm de déplacement pour chaque test

def attendre_mouvement(rtde_c):
    """Attend que le robot finisse son mouvement."""
    time.sleep(0.3)
    while not rtde_c.isSteady():
        time.sleep(0.1)
    time.sleep(0.5)

def main():
    print("=" * 70)
    print("🧪 TEST CORRESPONDANCE AXES ROBOT ↔ REPÈRE PLATEAU")
    print("=" * 70)
    print("\n📋 Instructions:")
    print("   1. Assure-toi que le robot est au-dessus du plateau")
    print("   2. La caméra doit voir le robot")
    print("   3. Observe visuellement chaque mouvement")
    print("   4. Note la direction sur le plateau pour chaque test")
    print("\n⚠️  Le robot va bouger de 5cm dans 4 directions différentes")
    print()
    
    # Connexion robot
    print(f"🤖 Connexion au robot {ROBOT_IP}...")
    try:
        rtde_c = RTDEControlInterface(ROBOT_IP)
        rtde_r = RTDEReceiveInterface(ROBOT_IP)
        print("✅ Connecté!")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    # Position initiale
    print("\n" + "=" * 70)
    print("📍 POSITION INITIALE")
    print("=" * 70)
    pos_init = list(rtde_r.getActualTCPPose())
    print(f"Position: X={pos_init[0]*1000:.1f}mm, Y={pos_init[1]*1000:.1f}mm, Z={pos_init[2]*1000:.1f}mm")
    
    input("\n⏸️  Appuie sur ENTER pour commencer les tests...")
    
    # ========== TEST 1: +X robot ==========
    print("\n" + "=" * 70)
    print("TEST 1/4 : MOUVEMENT +5cm EN X ROBOT")
    print("=" * 70)
    print("🚀 Déplacement en cours...")
    
    pos_test1 = list(pos_init)
    pos_test1[0] += DEPLACEMENT  # +5cm en X
    rtde_c.moveL(pos_test1, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    
    print("✅ Mouvement terminé!")
    print("\n👀 OBSERVE le robot sur le plateau:")
    print("   ❓ Dans quelle direction a-t-il bougé?")
    print("      A) Vers la droite (X+)")
    print("      B) Vers la gauche (X-)")
    print("      C) Vers le robot (Y+)")
    print("      D) Vers le joueur (Y-)")
    
    input("\n⏸️  Note ta réponse, puis appuie sur ENTER pour revenir...")
    
    # Retour position initiale
    rtde_c.moveL(pos_init, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    print("🔙 Retour position initiale")
    time.sleep(1)
    
    # ========== TEST 2: -X robot ==========
    print("\n" + "=" * 70)
    print("TEST 2/4 : MOUVEMENT -5cm EN X ROBOT")
    print("=" * 70)
    print("🚀 Déplacement en cours...")
    
    pos_test2 = list(pos_init)
    pos_test2[0] -= DEPLACEMENT  # -5cm en X
    rtde_c.moveL(pos_test2, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    
    print("✅ Mouvement terminé!")
    print("\n👀 OBSERVE le robot sur le plateau:")
    print("   ❓ Dans quelle direction a-t-il bougé?")
    print("      (Devrait être l'opposé du test 1)")
    
    input("\n⏸️  Note ta réponse, puis appuie sur ENTER pour revenir...")
    
    rtde_c.moveL(pos_init, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    print("🔙 Retour position initiale")
    time.sleep(1)
    
    # ========== TEST 3: +Y robot ==========
    print("\n" + "=" * 70)
    print("TEST 3/4 : MOUVEMENT +5cm EN Y ROBOT")
    print("=" * 70)
    print("🚀 Déplacement en cours...")
    
    pos_test3 = list(pos_init)
    pos_test3[1] += DEPLACEMENT  # +5cm en Y
    rtde_c.moveL(pos_test3, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    
    print("✅ Mouvement terminé!")
    print("\n👀 OBSERVE le robot sur le plateau:")
    print("   ❓ Dans quelle direction a-t-il bougé?")
    
    input("\n⏸️  Note ta réponse, puis appuie sur ENTER pour revenir...")
    
    rtde_c.moveL(pos_init, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    print("🔙 Retour position initiale")
    time.sleep(1)
    
    # ========== TEST 4: -Y robot ==========
    print("\n" + "=" * 70)
    print("TEST 4/4 : MOUVEMENT -5cm EN Y ROBOT")
    print("=" * 70)
    print("🚀 Déplacement en cours...")
    
    pos_test4 = list(pos_init)
    pos_test4[1] -= DEPLACEMENT  # -5cm en Y
    rtde_c.moveL(pos_test4, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    
    print("✅ Mouvement terminé!")
    print("\n👀 OBSERVE le robot sur le plateau:")
    print("   ❓ Dans quelle direction a-t-il bougé?")
    print("      (Devrait être l'opposé du test 3)")
    
    input("\n⏸️  Note ta réponse, puis appuie sur ENTER pour terminer...")
    
    # Retour final
    rtde_c.moveL(pos_init, VITESSE, ACCELERATION)
    attendre_mouvement(rtde_c)
    print("🔙 Retour position initiale")
    
    # Déconnexion
    rtde_c.disconnect()
    rtde_r.disconnect()
    
    # Résumé
    print("\n" + "=" * 70)
    print("📝 RÉSUMÉ DES TESTS")
    print("=" * 70)
    print("TEST 1: +5cm X robot → Direction observée: _____")
    print("TEST 2: -5cm X robot → Direction observée: _____")
    print("TEST 3: +5cm Y robot → Direction observée: _____")
    print("TEST 4: -5cm Y robot → Direction observée: _____")
    print()
    print("Repère plateau:")
    print("  - Droite = X+")
    print("  - Gauche = X-")
    print("  - Vers robot = Y+")
    print("  - Vers joueur = Y-")
    print()
    print("Donne-moi ces 4 directions pour calculer la transformation!")
    print("=" * 70)

if __name__ == "__main__":
    main()
