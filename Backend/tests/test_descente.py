#!/usr/bin/env python3
"""
Script de diagnostic pour tester la descente du robot
"""

from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
import time
import sys
import tty
import termios
import select

# Configuration
ROBOT_IP = "192.168.0.11"
ACCELERATION = 0.3

print("\n" + "=" * 60)
print("🔬 TEST DE DESCENTE - DIAGNOSTIC")
print("=" * 60)

# Connexion
print("\n📡 Connexion au robot...")
rtde_c = RTDEControlInterface(ROBOT_IP)
rtde_r = RTDEReceiveInterface(ROBOT_IP)
print("✓ Connecté")


def get_key():
    """Lit une touche sans bloquer"""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


# Position initiale
pose_init = rtde_r.getActualTCPPose()
print(f"\n📍 Position initiale:")
print(f"   X={pose_init[0]:.4f}, Y={pose_init[1]:.4f}, Z={pose_init[2]:.4f}")

# Test des unités
print("\n" + "=" * 60)
print("TEST 1: Vérification des unités")
print("=" * 60)
print("\nLes unités RTDE sont:")
print("  - Position: mètres (m)")
print("  - Vitesse: mètres/seconde (m/s)")
print("  - Accélération: mètres/seconde² (m/s²)")
print("")
print("Conversions:")
print("  - 0.05 m/s = 50 mm/s = 5 cm/s")
print("  - 0.01 m/s = 10 mm/s = 1 cm/s")
print("  - 0.001 m/s = 1 mm/s = 0.1 cm/s")

input("\nAppuyez sur ENTRÉE pour continuer...")

# Test de mouvement programmé
print("\n" + "=" * 60)
print("TEST 2: Mouvement programmé (descente de 1cm)")
print("=" * 60)
print("\nLe robot va descendre de 1cm (0.01m) à 5cm/s")
print("Durée attendue: 0.2 secondes")

input("Appuyez sur ENTRÉE pour démarrer...")

pose_avant = list(rtde_r.getActualTCPPose())
print(f"Position avant: Z={pose_avant[2]:.4f}")

# Descente de 1cm
pose_cible = list(pose_avant)
pose_cible[2] -= 0.01  # -1cm

print("⬇️  Descente...")
rtde_c.moveL(pose_cible, 0.05, ACCELERATION)

pose_apres = rtde_r.getActualTCPPose()
print(f"Position après: Z={pose_apres[2]:.4f}")

delta_z = abs(pose_apres[2] - pose_avant[2])
print(f"Distance parcourue: {delta_z * 1000:.2f} mm")

if delta_z >= 0.009 and delta_z <= 0.011:  # 9-11mm
    print("✓ Test réussi - mouvement correct")
else:
    print(f"❌ PROBLÈME - Distance attendue: 10mm, obtenue: {delta_z * 1000:.2f}mm")

input("\nAppuyez sur ENTRÉE pour continuer...")

# Test speedL
print("\n" + "=" * 60)
print("TEST 3: speedL (mouvement continu)")
print("=" * 60)
print("\nTest avec speedL pendant 2 secondes à 0.05 m/s (5cm/s)")
print("Distance attendue: 10cm")

input("Appuyez sur ENTRÉE pour démarrer...")

pose_avant = list(rtde_r.getActualTCPPose())
print(f"Position avant: Z={pose_avant[2]:.4f}")

print("⬇️  Descente speedL pendant 2s...")
rtde_c.speedL([0, 0, -0.05, 0, 0, 0], ACCELERATION, 60)
time.sleep(2.0)
rtde_c.speedStop()

pose_apres = rtde_r.getActualTCPPose()
print(f"Position après: Z={pose_apres[2]:.4f}")

delta_z = abs(pose_apres[2] - pose_avant[2])
print(f"Distance parcourue: {delta_z * 1000:.2f} mm")

if delta_z >= 95 and delta_z <= 105:  # 95-105mm
    print("✓ Test réussi - speedL fonctionne correctement")
else:
    print(f"⚠️  Distance attendue: ~100mm, obtenue: {delta_z * 1000:.2f}mm")

input("\nAppuyez sur ENTRÉE pour continuer...")

# Test interactif avec touche S
print("\n" + "=" * 60)
print("TEST 4: Test interactif avec touche S")
print("=" * 60)
print("\nTest du contrôle clavier:")
print("  S : Descendre (MAINTENIR)")
print("  W : Remonter (MAINTENIR)")
print("  Q : Quitter")
print("")
print("⚠️  Le robot descend TANT QUE vous maintenez 'S' pressé")
print("")

input("Appuyez sur ENTRÉE pour démarrer le test interactif...")

# Configuration terminal
old_settings = termios.tcgetattr(sys.stdin)

try:
    tty.setcbreak(sys.stdin.fileno())

    vitesse = 0.05  # 5cm/s
    en_mouvement = False

    print("\n🎮 Mode interactif actif")
    print("Maintenez 'S' pour descendre, 'W' pour monter, 'Q' pour quitter\n")

    while True:
        # Position actuelle
        pose = rtde_r.getActualTCPPose()
        print(f"\r📍 Z={pose[2]:.4f} | Mouvement: {'⬇️ OUI' if en_mouvement else '⏸️  NON'}  ", end='', flush=True)

        # Lire touche
        key = get_key()

        vz = 0

        if key:
            if key.lower() == 's':
                vz = -vitesse
                if not en_mouvement:
                    print("\n⬇️  DESCENTE ACTIVÉE (touche S détectée)")
                    en_mouvement = True
            elif key.lower() == 'w':
                vz = vitesse
                if not en_mouvement:
                    print("\n⬆️  MONTÉE ACTIVÉE (touche W détectée)")
                    en_mouvement = True
            elif key.lower() == 'q':
                print("\n\n✓ Test terminé")
                break

        # Appliquer vitesse
        if vz != 0:
            rtde_c.speedL([0, 0, vz, 0, 0, 0], ACCELERATION, 60)
            en_mouvement = True
        else:
            if en_mouvement:
                rtde_c.speedStop()
                en_mouvement = False
                print("\n⏸️  ARRÊT (touche relâchée)")

        time.sleep(0.01)

finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    rtde_c.speedStop()

# Résumé
print("\n" + "=" * 60)
print("RÉSUMÉ DES TESTS")
print("=" * 60)

pose_finale = rtde_r.getActualTCPPose()
delta_total = pose_init[2] - pose_finale[2]

print(f"\nPosition initiale: Z={pose_init[2]:.4f}")
print(f"Position finale:   Z={pose_finale[2]:.4f}")
print(f"Déplacement total: {delta_total * 1000:+.2f} mm (négatif = descendu)")

print("\n📋 Vérifications:")
if delta_total > 0.001:
    print(f"✓ Le robot A BIEN DESCENDU de {delta_total * 1000:.2f}mm")
else:
    print(f"❌ PROBLÈME: Le robot n'a pas bougé ou a monté")

print("\n🔧 Si le robot ne descend pas avec 'S':")
print("  1. Vérifiez que vous MAINTENEZ la touche S (pas juste un appui)")
print("  2. Vérifiez les logs - voyez-vous 'DESCENTE ACTIVÉE' ?")
print("  3. Vérifiez que le freedrive n'est pas actif")
print("  4. Vérifiez qu'il n'y a pas de limite logicielle en Z")

print("\n" + "=" * 60)

rtde_c.stopScript()
print("\n✓ Déconnecté\n")