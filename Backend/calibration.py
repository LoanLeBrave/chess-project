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
        self.pas_descente = 0.05  # 1mm par appui

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

        ATTENTION: Cette fonction retourne le Z de h1 (hauteur basse de prise de pièce)
        Le prepositionnement() doit REMPLACER ce Z par le Z actuel du robot!
        """
        if 'h1' not in self.cases:
            print("❌ Case h1 non trouvée dans le mapping!")
            return None

        h1_tcp = self.cases['h1']['tcp']

        # Position théorique du trou (X, Y corrects, mais Z de h1 = BAS)
        # h1 est le coin bas droit de l'échiquier
        # Le trou est à 10mm à droite (x positif) et centré sur y=0
        position_trou = list(h1_tcp)
        position_trou[0] += self.trou_distance_h1 + (self.trou_largeur / 2)  # Centré en X
        position_trou[1] = h1_tcp[1]  # Même Y que h1 (devrait être proche de 0)
        # position_trou[2] = h1_tcp[2]  ← Reste au Z de h1 (ATTENTION: position BASSE!)

        return position_trou

    def prepositionnement(self):
        """
        Positionne le robot au-dessus du trou théorique EN X ET Y UNIQUEMENT
        GARDE LE Z ACTUEL - NE DESCEND JAMAIS automatiquement
        """
        position_trou = self.calculer_position_trou_theorique()

        if position_trou is None:
            return False

        # RÉCUPÉRER LA POSITION ACTUELLE DU ROBOT
        pose_actuelle = list(self.rtde_r.getActualTCPPose())

        # Créer la position cible: X et Y du trou, Z ACTUEL du robot
        position_cible = list(position_trou)
        position_cible[2] = pose_actuelle[2]  # 🔒 GARDER LE Z ACTUEL!

        print("\n📍 Prépositionnement au-dessus du trou théorique...")
        print(f"   Position actuelle: X={pose_actuelle[0]:.4f}, Y={pose_actuelle[1]:.4f}, Z={pose_actuelle[2]:.4f}")
        print(f"   Position cible:    X={position_cible[0]:.4f}, Y={position_cible[1]:.4f}, Z={position_cible[2]:.4f}")
        print("   ⚠️  SÉCURITÉ: Mouvement en X/Y uniquement - Z reste INCHANGÉ")

        try:
            self.rtde_c.moveL(position_cible, VITESSE, ACCELERATION)
            time.sleep(0.5)

            # Vérifier que Z n'a pas changé
            pose_finale = list(self.rtde_r.getActualTCPPose())
            delta_z = abs(pose_finale[2] - pose_actuelle[2])

            if delta_z > 0.001:  # Plus de 1mm de changement en Z
                print(f"   ⚠️  ATTENTION: Z a changé de {delta_z * 1000:.1f}mm!")
            else:
                print(f"   ✅ Prépositionnement terminé (Z inchangé: {pose_finale[2]:.4f})\n")

            # VÉRIFICATION DE SÉCURITÉ
            print("🔍 VÉRIFICATION DE SÉCURITÉ")
            print("   Regardez le robot et vérifiez visuellement:")
            print("   ✓ Le gripper est-il approximativement au-dessus du trou?")
            print("   ✓ Le gripper est-il bien fermé?")
            print("   ✓ Rien ne bloque le passage vers le bas?")
            print("")
            print("   Si tout est OK, vous pourrez ajuster précisément en X/Y")
            print("   avec le freedrive avant de descendre.")
            print("")
            input("   Appuyez sur ENTRÉE pour continuer...")
            print("")

            return True
        except Exception as e:
            print(f"❌ Erreur prépositionnement: {e}")
            return False
            print("")

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
        - f : Activer/Désactiver freedrive X/Y (toggle)
        - q : Valider et enregistrer
        - ESC : Annuler
        """
        print("\n" + "=" * 60)
        print("🎮 MODE DESCENTE INTERACTIVE")
        print("=" * 60)
        print("\n⚠️  SÉCURITÉ CRITIQUE ⚠️")
        print("  Le robot est actuellement EN HAUTEUR au-dessus du trou.")
        print("  Il ne descendra QUE lorsque vous appuierez sur ↓ ou S.")
        print("  Vérifiez visuellement qu'il est bien centré sur le trou")
        print("  AVANT de commencer la descente!")
        print("")
        print("📋 Instructions:")
        print("  DESCENTE/MONTÉE:")
        print("     ↓ ou S : Descendre (CONTINU tant que pressé)")
        print("     ↑ ou W : Remonter (CONTINU tant que pressé)")
        print("")
        print("  AJUSTEMENT X/Y:")
        print("     F : Activer/Désactiver le freedrive X/Y (bouton toggle)")
        print("     → Freedrive actif = vous pouvez déplacer le robot manuellement en X/Y")
        print("     → Freedrive inactif = robot bloqué (pour descente stable)")
        print("")
        print("  VALIDATION:")
        print("     Q : Valider et enregistrer cette position")
        print("     ESC : Annuler la calibration")
        print("")
        print("💡 ASTUCE: Descendez avec freedrive DÉSACTIVÉ pour plus de stabilité")
        print("=" * 60 + "\n")

        # Sauvegarder les paramètres du terminal
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Mode raw pour capturer les touches
            tty.setcbreak(sys.stdin.fileno())

            freedrive_actif = False  # Commence SANS freedrive
            en_mouvement = False

            # Vitesse de descente continue (m/s)
            vitesse_descente = 0.05  # 5cm/s - plus rapide pour calibration

            print("🔒 Freedrive: DÉSACTIVÉ (appuyez sur F pour activer)")

            while True:
                # Lire la position actuelle
                pose = self.rtde_r.getActualTCPPose()

                # Afficher la position et l'état du freedrive
                freedrive_status = "🟢 ACTIF" if freedrive_actif else "🔒 DÉSACTIVÉ"
                print(
                    f"\r📍 Position: X={pose[0]:.4f}, Y={pose[1]:.4f}, Z={pose[2]:.4f} | Freedrive: {freedrive_status}  ",
                    end='', flush=True)

                # Lire la touche (non bloquant)
                key = self.get_key()

                # Nouvelle vitesse à appliquer (par défaut = 0)
                vz = 0

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
                            if freedrive_actif:
                                self.disable_freedrive()
                            print("\n\n❌ Calibration annulée")
                            return None

                    # Toggle Freedrive
                    if key.lower() == 'f':
                        if freedrive_actif:
                            self.disable_freedrive()
                            freedrive_actif = False
                            print("\n🔒 Freedrive DÉSACTIVÉ")
                        else:
                            # Arrêter tout mouvement avant d'activer freedrive
                            if en_mouvement:
                                self.rtde_c.speedStop()
                                en_mouvement = False
                                time.sleep(0.05)

                            self.enable_freedrive_xy()
                            freedrive_actif = True
                            print("\n🟢 Freedrive ACTIVÉ (déplacez le robot manuellement en X/Y)")
                        continue

                    # Descente
                    if key.lower() == 's':
                        # Si freedrive actif, le désactiver automatiquement
                        if freedrive_actif:
                            self.disable_freedrive()
                            freedrive_actif = False
                            print("\n🔒 Freedrive auto-désactivé pour descente")
                            time.sleep(0.05)

                        vz = -vitesse_descente  # Descendre
                        if not en_mouvement:
                            print("\n⬇️  Descente...")
                            en_mouvement = True

                    # Montée
                    elif key.lower() == 'w':
                        # Si freedrive actif, le désactiver automatiquement
                        if freedrive_actif:
                            self.disable_freedrive()
                            freedrive_actif = False
                            print("\n🔒 Freedrive auto-désactivé pour montée")
                            time.sleep(0.05)

                        vz = vitesse_descente  # Monter
                        if not en_mouvement:
                            print("\n⬆️  Montée...")
                            en_mouvement = True

                    # Validation
                    elif key.lower() == 'q':
                        # Arrêter tout mouvement
                        if en_mouvement:
                            self.rtde_c.speedStop()

                        if freedrive_actif:
                            self.disable_freedrive()

                        time.sleep(0.2)  # Attendre stabilisation
                        position_finale = list(self.rtde_r.getActualTCPPose())
                        print("\n\n✅ Position de calibration enregistrée!")
                        return position_finale

                # Appliquer la vitesse
                if vz != 0:
                    # Mouvement demandé - appliquer speedL
                    self.rtde_c.speedL([0, 0, vz, 0, 0, 0], ACCELERATION, 60)
                    en_mouvement = True
                else:
                    # Aucun mouvement demandé - arrêter si en mouvement
                    if en_mouvement:
                        self.rtde_c.speedStop()
                        en_mouvement = False
                        print("\n⏸️  Arrêt")

                time.sleep(0.01)  # 10ms entre lectures - 100 Hz

        finally:
            # Arrêter tout mouvement
            try:
                self.rtde_c.speedStop()
            except:
                pass

            # Désactiver freedrive
            try:
                if freedrive_actif:
                    self.disable_freedrive()
            except:
                pass

            # Restaurer les paramètres du terminal
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def sortir_du_trou_et_centrer(self):
        """
        Remonte le robot du trou et le positionne au centre de l'échiquier
        pour éviter de bloquer le gripper
        """
        print("\n🔼 Remontée et positionnement au centre de l'échiquier...")

        try:
            # 1. Remonter verticalement de 10cm
            pose_actuelle = list(self.rtde_r.getActualTCPPose())
            pose_haute = list(pose_actuelle)
            pose_haute[2] += 0.10  # Monter de 10cm

            print("   📍 Remontée verticale de 10cm...")
            self.rtde_c.moveL(pose_haute, VITESSE * 0.5, ACCELERATION)
            time.sleep(0.5)

            # 2. Calculer le centre de l'échiquier (moyenne des 4 cases centrales)
            # Le vrai centre est entre d4, e4, d5, e5
            if all(c in self.cases for c in ['d4', 'e4', 'd5', 'e5']):
                d4_tcp = self.cases['d4']['tcp']
                e4_tcp = self.cases['e4']['tcp']
                d5_tcp = self.cases['d5']['tcp']
                e5_tcp = self.cases['e5']['tcp']

                position_centre = [
                    (d4_tcp[0] + e4_tcp[0] + d5_tcp[0] + e5_tcp[0]) / 4,
                    (d4_tcp[1] + e4_tcp[1] + d5_tcp[1] + e5_tcp[1]) / 4,
                    pose_haute[2],  # Garder la hauteur actuelle
                    d4_tcp[3],  # Orientation de d4
                    d4_tcp[4],
                    d4_tcp[5]
                ]

                print("   📍 Déplacement au centre de l'échiquier (d4-e4-d5-e5)...")
                self.rtde_c.moveL(position_centre, VITESSE, ACCELERATION)
                time.sleep(0.5)

                print("   ✅ Robot positionné au centre à 10cm de hauteur")

            elif 'd5' in self.cases and 'e5' in self.cases:
                # Fallback sur d5-e5 si les 4 cases ne sont pas dispo
                d5_tcp = self.cases['d5']['tcp']
                e5_tcp = self.cases['e5']['tcp']

                position_centre = [
                    (d5_tcp[0] + e5_tcp[0]) / 2,
                    (d5_tcp[1] + e5_tcp[1]) / 2,
                    pose_haute[2],
                    d5_tcp[3],
                    d5_tcp[4],
                    d5_tcp[5]
                ]

                print("   📍 Déplacement au centre de l'échiquier (d5-e5)...")
                self.rtde_c.moveL(position_centre, VITESSE, ACCELERATION)
                time.sleep(0.5)

                print("   ✅ Robot positionné au centre à 10cm de hauteur")

            else:
                print("   ⚠️  Cases centrales non trouvées, robot reste en position haute")

            return True

        except Exception as e:
            print(f"   ❌ Erreur lors du repositionnement: {e}")
            return False

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

        # 5. Sortir du trou et repositionner au centre
        if not self.sortir_du_trou_et_centrer():
            print("⚠️  Repositionnement impossible, continuez manuellement")

        # 6. Calculer l'offset
        offset = self.calculer_offset(position_calibration)

        if offset is None:
            return False

        # 7. Demander confirmation
        print("⚠️  Voulez-vous appliquer cet offset à toutes les positions? (o/n): ", end='')
        reponse = input().strip().lower()

        if reponse != 'o':
            print("❌ Calibration annulée\n")
            return False

        # 8. Appliquer l'offset
        if not self.appliquer_offset_mapping(offset):
            return False

        # 9. Sauvegarder
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