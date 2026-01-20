#!/usr/bin/env python3
"""
Script de test pour trouver la meilleure position de focus.
Prend des photos avec différentes valeurs de lens-position.
"""

import subprocess
import os
import time

OUTPUT_DIR = "focus_tests"

def test_focus(lens_position, filename):
    """Prend une photo avec une position de focus spécifique."""
    print(f"\n📸 Test focus: lens-position = {lens_position}")
    
    cmd = [
        "rpicam-still",
        "-n",  # No preview
        "-o", filename,
        "--timeout", "2000",
        "--autofocus-mode", "manual",
        "--lens-position", str(lens_position)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Photo sauvegardée: {filename}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e}")
        return False
    except FileNotFoundError:
        print("❌ rpicam-still non trouvé")
        return False

def test_autofocus(filename):
    """Prend une photo avec autofocus."""
    print(f"\n📸 Test AUTOFOCUS")
    
    cmd = [
        "rpicam-still",
        "-n",
        "-o", filename,
        "--timeout", "2000",
        "--autofocus-on-capture"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Photo sauvegardée: {filename}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print("=" * 60)
    print("🔬 TEST DE FOCUS - Recherche de la meilleure position")
    print("=" * 60)
    
    # Créer le dossier de sortie
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Test avec autofocus
    print("\n" + "=" * 60)
    print("1. TEST AUTOFOCUS")
    print("=" * 60)
    test_autofocus(f"{OUTPUT_DIR}/focus_auto.jpg")
    time.sleep(1)
    
    # Tests avec focus manuel
    print("\n" + "=" * 60)
    print("2. TESTS FOCUS MANUEL")
    print("=" * 60)
    
    # Positions à tester (0.0 = très proche, 10.0 = infini)
    test_positions = [
        0.0,   # Focus très proche
        2.0,   # Proche
        3.5,   # Moyen-proche
        5.0,   # Moyen
        7.0,   # Loin
        10.0   # Infini
    ]
    
    for pos in test_positions:
        test_focus(pos, f"{OUTPUT_DIR}/focus_{pos:.1f}.jpg")
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("✅ TESTS TERMINÉS")
    print("=" * 60)
    print(f"\n📁 Photos sauvegardées dans: {OUTPUT_DIR}/")
    print("\nRegarde les photos et note quelle position donne la meilleure netteté!")
    print("Positions testées:")
    print("  - focus_auto.jpg = Autofocus automatique")
    print("  - focus_0.0.jpg  = Focus très proche")
    print("  - focus_2.0.jpg  = Focus proche")
    print("  - focus_3.5.jpg  = Focus moyen-proche")
    print("  - focus_5.0.jpg  = Focus moyen")
    print("  - focus_7.0.jpg  = Focus loin")
    print("  - focus_10.0.jpg = Focus infini")

if __name__ == "__main__":
    main()
