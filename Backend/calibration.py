#!/usr/bin/env python3
"""
Module de calibration du robot d'échecs
Utilise un trou percé dans l'échiquier pour calibrer précisément la position
"""

import json
import time
import sys
import os
import termios
import tty
import select
from typing import Optional, Dict, List
import math

from config import ROBOT_IP, VITESSE, ACCELERATION, FICHIER_MAPPING


class RobotCalibration:
    """Gestion de la calibration du robot via le trou de référence"""

    def __init__(self):
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.connected = False

        # Position du trou de calibration (connue précisément)
        # Le trou est aligné avec y=0 et à 10mm de la case h1 (coin bas droit)
        self.trou_largeur = 0.012  # 12mm
        self.trou_hauteur = 0.022  # 22mm
        self.trou_distance_h1 = 0.010  # 10mm de la case h1

        # Données de mapping
        self.cases = {}
        self.mapping_data = {}

        # Position de calibration (sera déterminée)
        self.position_calibration = None

        # Vitesses pour descente fine
        self.vitesse_fine = 0.02  # 2cm/s
        self.pas_descente = 0.001  # 1mm par appui

    def init_robot(self):
        """Initialise la connexion au robot"""
        try:
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface
            from robotiq_gripper_control import RobotiqGripper

            print(f"\n🤖 Connexion au robot {ROBOT_IP}...")
            self.rtde_c = RTDEControlInterface(ROBOT_IP)
            self.rtde_r = RTDEReceiveInterface(ROBOT_IP)

            print("🦾 Activation du gripper...")
            self.gripper = RobotiqGripper(self.rtde_c)
            self.gripper.activate()
            self.gripper.set_force(40)
            self.gripper.set_speed(150)

            # Fermer le gripper pour calibration
            print("🤏 Fermeture du gripper...")
            self.gripper.close()
            time.sleep(1)

            self.connected = True
            print("✅ Robot connecté!\n")
            return True

        except Exception as e:
            print(f"❌ Erreur connexion robot: {e}")
            self.connected = False
            return False

    def load_mapping(self):
        """Charge le mapping existant"""
        if not os.path.exists(FICHIER_MAPPING):
            print(f"⚠️  Fichier {FICHIER_MAPPING} non trouvé!")
            return False

        try:
            with open(FICHIER_MAPPING, 'r') as f:
                self.mapping_data = json.load(f)
                self.cases = self.mapping_data.get("cases", {})

            print(f"✅ Mapping chargé: {len(self.cases)} cases")
            return True
        except Exception as e:
            print(f"❌ Erreur chargement mapping: {e}")
            return False

    def calculer_position_trou_theorique(self):
        """
        Calcule la position théorique du trou basée sur la case h1
        Le trou est à 10mm à droite de h1, aligné sur y=0
        """
        if 'h1' not in self.cases:
            print("❌ Case h1 non trouvée dans le mapping!")
            return None

        h1_tcp = self.cases['h1']['tcp']

        # Position théorique du trou
        # h1 est le coin bas droit de l'échiquier
        # Le trou est à 10mm à droite (x positif) et centré sur y=0
        position_trou = list(h1_tcp)
        position_trou[0] += self.trou_distance_h1 + (self.trou_largeur / 2)  # Centré en X
        position_trou[1] = h1_tcp[1]  # Même Y que h1 (devrait être proche de 0)
        position_trou[2] += 0.05  # 5cm au-dessus pour commencer

        return position_trou

    def prepositionnement(self):
        """Positionne le robot au-dessus du trou théorique"""
        position_trou = self.calculer_position_trou_theorique()

        if position_trou is None:
            return False

        print("\n📍 Prépositionnement au-dessus du trou théorique...")
        print(f"   Position: X={position_trou[0]:.4f}, Y={position_trou[1]:.4f}, Z={position_trou[2]:.4f}")

        try:
            self.rtde_c.moveL(position_trou, VITESSE, ACCELERATION)
            time.sleep(0.5)
            print("✅ Prépositionnement terminé\n")
            return True
        except Exception as e:
            print(f"❌ Erreur prépositionnement: {e}")
            return False

    def enable_freedrive_xy(self):
        """Active le mode freedrive uniquement sur X et Y"""
        try:
            # Freedrive avec sélection des axes: [x, y, z, rx, ry, rz]
            # 1 = libre, 0 = bloqué
            selection = [1, 1, 0, 0, 0, 0]  # Libre en X et Y uniquement

            # Activer freedrive
            self.rtde_c.freedriveMode(selection)
            return True
        except Exception as e:
            print(f"❌ Erreur activation freedrive: {e}")
            return False

    def disable_freedrive(self):
        """Désactive le mode freedrive"""
        try:
            self.rtde_c.endFreedriveMode()
            return True
        except Exception as e:
            print(f"❌ Erreur désactivation freedrive: {e}")
            return False

    def get_key(self):
        """Lit une touche du clavier sans bloquer"""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def mode_descente_interactive(self):
        """
        Mode interactif de descente dans le trou
        Touches:
        - Flèche bas / s : Descendre (continu tant que pressé)
        - Flèche haut / w : Remonter (continu tant que pressé)
        - q : Quitter et valider
        - ESC : Annuler
        """
        print("\n" + "=" * 60)
        print("🎮 MODE DESCENTE INTERACTIVE")
        print("=" * 60)
        print("\n📋 Instructions:")
        print("  1. Ajustez la position X/Y manuellement (le robot est en freedrive)")
        print("  2. Utilisez les touches pour descendre dans le trou:")
        print("     ↓ ou S : Descendre (CONTINU tant que pressé)")
        print("     ↑ ou W : Remonter (CONTINU tant que pressé)")
        print("     Q : Valider et enregistrer cette position")
        print("     ESC : Annuler la calibration")
        print("\n⚠️  Dès qu'une touche est relâchée, le mouvement s'arrête et le freedrive X/Y est réactivé")
        print("=" * 60 + "\n")

        # Sauvegarder les paramètres du terminal
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Mode raw pour capturer les touches
            tty.setcbreak(sys.stdin.fileno())

            en_freedrive = True
            en_mouvement = False
            direction_mouvement = None  # 'down' ou 'up'
            self.enable_freedrive_xy()

            # Vitesse de descente continue (m/s)
            vitesse_descente = 0.01  # 1cm/s - fluide et sécurisé

            while True:
                # Lire la position actuelle
                pose = self.rtde_r.getActualTCPPose()

                # Afficher la position
                print(f"\r📍 Position: X={pose[0]:.4f}, Y={pose[1]:.4f}, Z={pose[2]:.4f}  ", end='', flush=True)

                # Lire la touche (non bloquant)
                key = self.get_key()

                if key:
                    # Traiter ESC et flèches
                    if key == '\x1b':
                        next_key = self.get_key()
                        if next_key == '[':
                            arrow_key = self.get_key()
                            if arrow_key == 'B':  # Flèche bas
                                key = 's'
                            elif arrow_key == 'A':  # Flèche haut
                                key = 'w'
                            else:
                                continue
                        else:
                            # ESC seul
                            if en_mouvement:
                                self.rtde_c.speedStop()
                            self.disable_freedrive()
                            print("\n\n❌ Calibration annulée")
                            return None

                    # Touche de descente
                    if key.lower() == 's':
                        if not en_mouvement or direction_mouvement != 'down':
                            # Arrêter le freedrive et démarrer la descente
                            if en_freedrive:
                                self.disable_freedrive()
                                en_freedrive = False

                            # Arrêter tout mouvement précédent
                            if en_mouvement:
                                self.rtde_c.speedStop()

                            # Démarrer descente continue
                            # speedL: [vx, vy, vz, vrx, vry, vrz], acceleration, time
                            self.rtde_c.speedL([0, 0, -vitesse_descente, 0, 0, 0], ACCELERATION, 60)
                            en_mouvement = True
                            direction_mouvement = 'down'
                            print("\n⬇️  Descente continue...")

                    # Touche de montée
                    elif key.lower() == 'w':
                        if not en_mouvement or direction_mouvement != 'up':
                            # Arrêter le freedrive et démarrer la montée
                            if en_freedrive:
                                self.disable_freedrive()
                                en_freedrive = False

                            # Arrêter tout mouvement précédent
                            if en_mouvement:
                                self.rtde_c.speedStop()

                            # Démarrer montée continue
                            self.rtde_c.speedL([0, 0, vitesse_descente, 0, 0, 0], ACCELERATION, 60)
                            en_mouvement = True
                            direction_mouvement = 'up'
                            print("\n⬆️  Montée continue...")

                    # Validation
                    elif key.lower() == 'q':
                        # Arrêter tout mouvement
                        if en_mouvement:
                            self.rtde_c.speedStop()

                        self.disable_freedrive()
                        time.sleep(0.2)  # Attendre stabilisation
                        position_finale = list(self.rtde_r.getActualTCPPose())
                        print("\n\n✅ Position de calibration enregistrée!")
                        return position_finale

                else:
                    # Aucune touche pressée
                    if en_mouvement:
                        # Arrêter le mouvement immédiatement
                        self.rtde_c.speedStop()
                        en_mouvement = False
                        direction_mouvement = None
                        time.sleep(0.1)  # Stabilisation
                        print("\n⏸️  Mouvement arrêté")

                    # Réactiver freedrive si nécessaire
                    if not en_freedrive and not en_mouvement:
                        time.sleep(0.1)
                        self.enable_freedrive_xy()
                        en_freedrive = True

                time.sleep(0.02)  # 20ms entre lectures - très réactif

        finally:
            # Arrêter tout mouvement
            try:
                self.rtde_c.speedStop()
            except:
                pass

            # Restaurer les paramètres du terminal
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.disable_freedrive()

    def calculer_offset(self, position_mesuree):
        """
        Calcule l'offset entre la position théorique et la position mesurée du trou
        """
        position_theorique = self.calculer_position_trou_theorique()

        if position_theorique is None:
            return None

        # Offset = position réelle - position théorique
        offset = [
            position_mesuree[0] - position_theorique[0],
            position_mesuree[1] - position_theorique[1],
            position_mesuree[2] - position_theorique[2],
            0,  # Pas d'offset en rotation
            0,
            0
        ]

        print("\n" + "=" * 60)
        print("📊 ANALYSE DE L'OFFSET")
        print("=" * 60)
        print(
            f"Position théorique: X={position_theorique[0]:.4f}, Y={position_theorique[1]:.4f}, Z={position_theorique[2]:.4f}")
        print(
            f"Position mesurée:   X={position_mesuree[0]:.4f}, Y={position_mesuree[1]:.4f}, Z={position_mesuree[2]:.4f}")
        print(f"\nOffset calculé:")
        print(f"  ΔX = {offset[0] * 1000:+.2f} mm")
        print(f"  ΔY = {offset[1] * 1000:+.2f} mm")
        print(f"  ΔZ = {offset[2] * 1000:+.2f} mm")

        distance_offset = math.sqrt(offset[0] ** 2 + offset[1] ** 2)
        print(f"\n  Distance 2D = {distance_offset * 1000:.2f} mm")
        print("=" * 60 + "\n")

        return offset

    def appliquer_offset_mapping(self, offset):
        """
        Applique l'offset à toutes les positions du mapping
        """
        print("🔧 Application de l'offset à toutes les cases...")

        cases_modifiees = 0

        # Appliquer l'offset aux cases
        for case_name, case_data in self.cases.items():
            tcp_original = case_data['tcp']
            tcp_corrige = [
                tcp_original[0] + offset[0],
                tcp_original[1] + offset[1],
                tcp_original[2] + offset[2],
                tcp_original[3] + offset[3],
                tcp_original[4] + offset[4],
                tcp_original[5] + offset[5],
            ]
            self.cases[case_name]['tcp'] = tcp_corrige
            cases_modifiees += 1

        # Appliquer l'offset aux zones d'élimination si elles existent
        zones_a_corriger = [
            'zone_elimination_blancs_min',
            'zone_elimination_blancs_max',
            'zone_elimination_noirs_min',
            'zone_elimination_noirs_max'
        ]

        for zone_name in zones_a_corriger:
            if zone_name in self.mapping_data and self.mapping_data[zone_name]:
                zone_original = self.mapping_data[zone_name]
                zone_corrigee = [
                    zone_original[0] + offset[0],
                    zone_original[1] + offset[1],
                    zone_original[2] + offset[2],
                    zone_original[3] + offset[3],
                    zone_original[4] + offset[4],
                    zone_original[5] + offset[5],
                ]
                self.mapping_data[zone_name] = zone_corrigee
                print(f"   ✓ Zone {zone_name} corrigée")

        # Mettre à jour le mapping_data avec les cases corrigées
        self.mapping_data['cases'] = self.cases

        print(f"✅ {cases_modifiees} cases corrigées\n")

        return True

    def sauvegarder_mapping(self, backup=True):
        """
        Sauvegarde le mapping corrigé
        """
        # Créer une backup si demandé
        if backup and os.path.exists(FICHIER_MAPPING):
            backup_file = FICHIER_MAPPING.replace('.json', '_backup.json')
            try:
                with open(FICHIER_MAPPING, 'r') as f:
                    backup_data = json.load(f)
                with open(backup_file, 'w') as f:
                    json.dump(backup_data, f, indent=2)
                print(f"💾 Backup créée: {backup_file}")
            except Exception as e:
                print(f"⚠️  Erreur création backup: {e}")

        # Sauvegarder le nouveau mapping
        try:
            with open(FICHIER_MAPPING, 'w') as f:
                json.dump(self.mapping_data, f, indent=2)
            print(f"✅ Mapping corrigé sauvegardé: {FICHIER_MAPPING}\n")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False

    def run(self):
        """
        Exécute le processus complet de calibration
        """
        print("\n" + "=" * 60)
        print("🎯 CALIBRATION DU ROBOT D'ÉCHECS")
        print("=" * 60 + "\n")

        # 1. Connexion robot
        if not self.init_robot():
            return False

        # 2. Charger le mapping
        if not self.load_mapping():
            return False

        # 3. Prépositionnement
        if not self.prepositionnement():
            return False

        # 4. Mode interactif
        print("🎮 Activation du mode freedrive X/Y...")
        print("   Vous pouvez maintenant déplacer le robot manuellement\n")

        position_calibration = self.mode_descente_interactive()

        if position_calibration is None:
            print("❌ Calibration annulée\n")
            return False

        # 5. Calculer l'offset
        offset = self.calculer_offset(position_calibration)

        if offset is None:
            return False

        # 6. Demander confirmation
        print("⚠️  Voulez-vous appliquer cet offset à toutes les positions? (o/n): ", end='')
        reponse = input().strip().lower()

        if reponse != 'o':
            print("❌ Calibration annulée\n")
            return False

        # 7. Appliquer l'offset
        if not self.appliquer_offset_mapping(offset):
            return False

        # 8. Sauvegarder
        if not self.sauvegarder_mapping():
            return False

        print("=" * 60)
        print("✅ CALIBRATION TERMINÉE AVEC SUCCÈS!")
        print("=" * 60 + "\n")

        return True

    def close(self):
        """Ferme les connexions"""
        if self.rtde_c:
            self.disable_freedrive()
            self.rtde_c.stopScript()


def main():
    """Point d'entrée principal"""
    calibration = RobotCalibration()

    try:
        success = calibration.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Calibration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        calibration.close()


if __name__ == "__main__":
    main()