#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'orientation de l'échiquier
"""

import json
import os
from config import FICHIER_MAPPING


def diagnostiquer_orientation():
    """Analyse l'orientation du mapping pour détecter les inversions"""

    print("\n" + "=" * 60)
    print(" DIAGNOSTIC D'ORIENTATION DE L'ÉCHIQUIER")
    print("=" * 60 + "\n")

    # Charger le mapping
    if not os.path.exists(FICHIER_MAPPING):
        print(f" Fichier {FICHIER_MAPPING} non trouvé!")
        return

    with open(FICHIER_MAPPING, 'r') as f:
        data = json.load(f)
        cases = data.get("cases", {})

    print(f"✓ Mapping chargé: {len(cases)} cases\n")

    # Analyser les coins
    coins = ['a1', 'a8', 'h1', 'h8']

    print("=" * 60)
    print("POSITIONS DES 4 COINS")
    print("=" * 60)
    for coin in coins:
        if coin in cases:
            tcp = cases[coin]['tcp']
            print(f"{coin.upper()}: X={tcp[0]:.4f}, Y={tcp[1]:.4f}, Z={tcp[2]:.4f}")
        else:
            print(f"{coin.upper()}:  Non trouvé")

    # Vérifier l'orientation
    if all(c in cases for c in coins):
        a1 = cases['a1']['tcp']
        a8 = cases['a8']['tcp']
        h1 = cases['h1']['tcp']
        h8 = cases['h8']['tcp']

        print("\n" + "=" * 60)
        print("ANALYSE DE L'ORIENTATION")
        print("=" * 60)

        # Axe X (a vers h)
        delta_x_ligne1 = h1[0] - a1[0]  # a1 -> h1
        delta_x_ligne8 = h8[0] - a8[0]  # a8 -> h8

        print(f"\n AXE X (colonnes a → h):")
        print(f"   Ligne 1: a1→h1 = {delta_x_ligne1:+.4f} m ({delta_x_ligne1 * 1000:+.1f} mm)")
        print(f"   Ligne 8: a8→h8 = {delta_x_ligne8:+.4f} m ({delta_x_ligne8 * 1000:+.1f} mm)")

        if delta_x_ligne1 > 0 and delta_x_ligne8 > 0:
            print("   ✓ X augmente de a vers h (normal)")
        elif delta_x_ligne1 < 0 and delta_x_ligne8 < 0:
            print("     X DIMINUE de a vers h (INVERSÉ!)")
        else:
            print("    Orientation incohérente!")

        # Axe Y (1 vers 8)
        delta_y_col_a = a8[1] - a1[1]  # a1 -> a8
        delta_y_col_h = h8[1] - h1[1]  # h1 -> h8

        print(f"\n AXE Y (rangées 1 → 8):")
        print(f"   Colonne a: a1→a8 = {delta_y_col_a:+.4f} m ({delta_y_col_a * 1000:+.1f} mm)")
        print(f"   Colonne h: h1→h8 = {delta_y_col_h:+.4f} m ({delta_y_col_h * 1000:+.1f} mm)")

        if delta_y_col_a > 0 and delta_y_col_h > 0:
            print("   ✓ Y augmente de 1 vers 8 (normal)")
        elif delta_y_col_a < 0 and delta_y_col_h < 0:
            print("     Y DIMINUE de 1 vers 8 (INVERSÉ!)")
        else:
            print("    Orientation incohérente!")

        # Distance entre cases
        taille_case_x = abs(delta_x_ligne1) / 7  # 8 cases = 7 intervalles
        taille_case_y = abs(delta_y_col_a) / 7

        print(f"\n TAILLE DES CASES:")
        print(f"   Largeur (X): {taille_case_x * 1000:.1f} mm")
        print(f"   Hauteur (Y): {taille_case_y * 1000:.1f} mm")

        if abs(taille_case_x - taille_case_y) > 0.002:  # >2mm de différence
            print("     Cases non carrées! Vérifier le mapping")
        else:
            print("   ✓ Cases carrées")

    # Vérifier le centre
    print("\n" + "=" * 60)
    print("POSITION DU CENTRE (d4-e4-d5-e5)")
    print("=" * 60)

    cases_centre = ['d4', 'e4', 'd5', 'e5']
    for case in cases_centre:
        if case in cases:
            tcp = cases[case]['tcp']
            print(f"{case.upper()}: X={tcp[0]:.4f}, Y={tcp[1]:.4f}")
        else:
            print(f"{case.upper()}:  Non trouvé")

    if all(c in cases for c in cases_centre):
        d4 = cases['d4']['tcp']
        e4 = cases['e4']['tcp']
        d5 = cases['d5']['tcp']
        e5 = cases['e5']['tcp']

        centre_x = (d4[0] + e4[0] + d5[0] + e5[0]) / 4
        centre_y = (d4[1] + e4[1] + d5[1] + e5[1]) / 4

        print(f"\nCentre calculé: X={centre_x:.4f}, Y={centre_y:.4f}")

        # Comparer avec h1
        if 'h1' in cases:
            h1 = cases['h1']['tcp']
            distance_x = centre_x - h1[0]
            distance_y = centre_y - h1[1]

            print(f"\nDistance du centre par rapport à h1:")
            print(f"   ΔX = {distance_x * 1000:+.1f} mm")
            print(f"   ΔY = {distance_y * 1000:+.1f} mm")

            # Le centre devrait être à ~3.5 cases de h1 en X et Y
            # Échiquier 280mm = 8 cases de 35mm
            # Centre à 4.5 cases du bord = 157.5mm
            # h1 est au bord, donc centre devrait être à ~140mm de h1

            expected_offset = -140  # mm (négatif car centre est à gauche de h1)

            if abs(distance_x * 1000 - expected_offset) > 20:  # >20mm d'erreur
                print(f"     ATTENTION: Expected ~{expected_offset}mm, got {distance_x * 1000:.1f}mm")

    # Vérifier la position du trou
    print("\n" + "=" * 60)
    print("POSITION THÉORIQUE DU TROU DE CALIBRATION")
    print("=" * 60)

    if 'h1' in cases:
        h1 = cases['h1']['tcp']

        # Position théorique du trou (comme dans le code)
        trou_x = h1[0] + 0.010 + 0.006  # 10mm + 6mm (centre)
        trou_y = h1[1] + 0.011  # 11mm (centre en Y)

        print(f"\nh1: X={h1[0]:.4f}, Y={h1[1]:.4f}")
        print(f"Trou théorique: X={trou_x:.4f}, Y={trou_y:.4f}")
        print(f"Offset du trou: ΔX=+16mm, ΔY=+11mm par rapport à h1")

        print("\n  REMARQUE:")
        print("   Si le trou est physiquement À DROITE de h1 (X+),")
        print("   mais que h1[X] est PLUS GRAND que a1[X],")
        print("   alors l'orientation X est peut-être inversée!")

    print("\n" + "=" * 60)
    print("FIN DU DIAGNOSTIC")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    diagnostiquer_orientation()