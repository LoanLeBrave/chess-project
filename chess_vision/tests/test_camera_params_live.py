#!/usr/bin/env python3
"""
TEST: Prise de photos avec différents paramètres de caméra
============================================================

Ce script prend des photos en rafale avec différents paramètres de caméra
et détecte les ArUco pour trouver les meilleurs réglages.

Usage:
    python test_camera_params_live.py
    
Le script va prendre ~20 photos avec différents paramètres et afficher
combien d'ArUco sont détectés dans chacune.
"""

import sys
import os
import cv2
import time
from datetime import datetime
from picamera2 import Picamera2, Preview

# Ajouter le chemin parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.aruco_detector import ArucoDetector


def detect_arucos_in_image(image_path):
    """Détecte les ArUco dans une image."""
    img = cv2.imread(image_path)
    if img is None:
        return 0, []
    
    detector = ArucoDetector()
    markers = detector.detect(img)
    return len(markers), sorted(markers.keys())


def take_photo_with_params(picam2, output_dir, config_name, params_dict, fixed_exposure=None):
    """Prend une photo avec des paramètres spécifiques."""
    
    # Appliquer les paramètres
    controls = {}
    
    # Si exposition fixe fournie, l'utiliser
    if fixed_exposure is not None:
        controls['ExposureTime'] = fixed_exposure['exposure_time']
        controls['AnalogueGain'] = fixed_exposure['gain']
        controls['AeEnable'] = False  # Désactiver l'auto-exposition
    
    if 'brightness' in params_dict:
        controls['Brightness'] = params_dict['brightness']
    if 'contrast' in params_dict:
        controls['Contrast'] = params_dict['contrast']
    if 'saturation' in params_dict:
        controls['Saturation'] = params_dict['saturation']
    if 'sharpness' in params_dict:
        controls['Sharpness'] = params_dict['sharpness']
    if 'focus_mode' in params_dict:
        controls['AfMode'] = params_dict['focus_mode']
    if 'lens_position' in params_dict:
        controls['LensPosition'] = params_dict['lens_position']
    
    if controls:
        picam2.set_controls(controls)
    
    # Attendre la stabilisation (plus long pour le focus)
    time.sleep(1.0 if 'lens_position' in params_dict else 0.5)
    
    # Prendre la photo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{config_name}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    
    picam2.capture_file(filepath)
    
    return filepath


def main():
    print("=" * 60)
    print("  TEST PARAMÈTRES CAMÉRA - PRISE DE PHOTOS EN RAFALE")
    print("=" * 60)
    print()
    
    # Créer le dossier de sortie
    output_dir = f"camera_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Dossier de sortie: {output_dir}")
    print()
    
    # Initialiser la caméra
    print("📸 Initialisation de la caméra...")
    picam2 = Picamera2()
    
    # Configuration haute résolution
    config = picam2.create_still_configuration(
        main={"size": (4608, 2592)},
        buffer_count=2
    )
    picam2.configure(config)
    picam2.start()
    
    print("✅ Caméra prête")
    print()
    
    # Prendre une première photo de référence pour obtenir l'exposition
    print("📸 Photo de référence pour obtenir l'exposition...")
    ref_path = take_photo_with_params(picam2, output_dir, "00_reference", {})
    
    # Récupérer les métadonnées de la photo de référence
    metadata = picam2.capture_metadata()
    fixed_exposure = {
        'exposure_time': metadata.get('ExposureTime', 10000),
        'gain': metadata.get('AnalogueGain', 1.0)
    }
    print(f"   Exposition fixée: {fixed_exposure['exposure_time']}µs, Gain: {fixed_exposure['gain']:.2f}")
    print()
    
    # Définir les configurations à tester - FOCUS PRINCIPAL
    test_configs = [
        ("01_baseline", {}),
        
        # Test de différentes positions de lentille (focus manuel)
        # 0.0 = infini, valeurs plus hautes = plus proche
        ("02_focus_0.0_infini", {'focus_mode': 0, 'lens_position': 0.0}),
        ("03_focus_0.5", {'focus_mode': 0, 'lens_position': 0.5}),
        ("04_focus_1.0", {'focus_mode': 0, 'lens_position': 1.0}),
        ("05_focus_1.5", {'focus_mode': 0, 'lens_position': 1.5}),
        ("06_focus_2.0", {'focus_mode': 0, 'lens_position': 2.0}),
        ("07_focus_2.5", {'focus_mode': 0, 'lens_position': 2.5}),
        ("08_focus_3.0", {'focus_mode': 0, 'lens_position': 3.0}),
        ("09_focus_3.5", {'focus_mode': 0, 'lens_position': 3.5}),
        ("10_focus_4.0", {'focus_mode': 0, 'lens_position': 4.0}),
        ("11_focus_5.0", {'focus_mode': 0, 'lens_position': 5.0}),
        ("12_focus_6.0", {'focus_mode': 0, 'lens_position': 6.0}),
        ("13_focus_7.0", {'focus_mode': 0, 'lens_position': 7.0}),
        ("14_focus_8.0", {'focus_mode': 0, 'lens_position': 8.0}),
        ("15_focus_10.0_proche", {'focus_mode': 0, 'lens_position': 10.0}),
        
        # Autofocus modes
        ("16_autofocus_auto", {'focus_mode': 1}),
        ("17_autofocus_continuous", {'focus_mode': 2}),
        
        # Focus + ajustements légers
        ("18_focus_2.0+sharp", {'focus_mode': 0, 'lens_position': 2.0, 'sharpness': 1.5}),
        ("19_focus_3.0+sharp", {'focus_mode': 0, 'lens_position': 3.0, 'sharpness': 1.5}),
        ("20_focus_4.0+sharp", {'focus_mode': 0, 'lens_position': 4.0, 'sharpness': 1.5}),
        
        # Focus + contraste
        ("21_focus_2.0+contrast", {'focus_mode': 0, 'lens_position': 2.0, 'contrast': 1.3}),
        ("22_focus_3.0+contrast", {'focus_mode': 0, 'lens_position': 3.0, 'contrast': 1.3}),
        ("23_focus_4.0+contrast", {'focus_mode': 0, 'lens_position': 4.0, 'contrast': 1.3}),
        
        # Meilleures combinaisons focus + netteté + contraste
        ("24_combo_focus_2.0", {'focus_mode': 0, 'lens_position': 2.0, 'sharpness': 1.5, 'contrast': 1.3}),
        ("25_combo_focus_3.0", {'focus_mode': 0, 'lens_position': 3.0, 'sharpness': 1.5, 'contrast': 1.3}),
        ("26_combo_focus_4.0", {'focus_mode': 0, 'lens_position': 4.0, 'sharpness': 1.5, 'contrast': 1.3}),
    ]
    
    print(f"🎯 {len(test_configs)} configurations à tester")
    print()
    
    results = []
    
    # Prendre les photos
    for i, (config_name, params) in enumerate(test_configs, 1):
        print(f"[{i}/{len(test_configs)}] 📸 {config_name}")
        
        # Afficher les paramètres
        if params:
            params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            print(f"    Paramètres: {params_str}")
        else:
            print(f"    Paramètres: par défaut")
        
        # Prendre la photo avec exposition fixe
        filepath = take_photo_with_params(picam2, output_dir, config_name, params, fixed_exposure)
        
        # Détecter les ArUco
        count, ids = detect_arucos_in_image(filepath)
        results.append({
            'config': config_name,
            'params': params,
            'count': count,
            'ids': ids,
            'file': os.path.basename(filepath)
        })
        
        if count > 0:
            print(f"    ✅ {count} ArUco détectés: {ids}")
        else:
            print(f"    ❌ Aucun ArUco détecté")
        print()
    
    # Arrêter la caméra
    picam2.stop()
    picam2.close()
    
    # Trier par nombre de détections
    results.sort(key=lambda x: x['count'], reverse=True)
    
    # Afficher le résumé
    print("=" * 60)
    print("  RÉSUMÉ - CLASSEMENT PAR NOMBRE D'ARUCO DÉTECTÉS")
    print("=" * 60)
    print()
    
    for i, result in enumerate(results, 1):
        status = "✅" if result['count'] > 0 else "❌"
        print(f"{i:2d}. {status} {result['config']:20s} → {result['count']} ArUco {result['ids']}")
        if result['params']:
            params_str = ", ".join([f"{k}={v}" for k, v in result['params'].items()])
            print(f"    📋 {params_str}")
    
    print()
    
    # Sauvegarder le rapport
    report_path = os.path.join(output_dir, "RAPPORT.txt")
    with open(report_path, 'w') as f:
        f.write("RAPPORT DE TEST DES PARAMÈTRES CAMÉRA\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Configurations testées: {len(test_configs)}\n\n")
        
        f.write("RÉSULTATS CLASSÉS PAR NOMBRE D'ARUCO DÉTECTÉS:\n")
        f.write("-" * 60 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"{i}. {result['config']}\n")
            f.write(f"   Fichier: {result['file']}\n")
            f.write(f"   ArUco détectés: {result['count']}\n")
            f.write(f"   IDs: {result['ids']}\n")
            if result['params']:
                f.write(f"   Paramètres:\n")
                for k, v in result['params'].items():
                    f.write(f"     - {k}: {v}\n")
            else:
                f.write(f"   Paramètres: par défaut\n")
            f.write("\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("RECOMMANDATION:\n")
        f.write("-" * 60 + "\n\n")
        
        if results[0]['count'] > 0:
            best = results[0]
            f.write(f"✅ Meilleure configuration: {best['config']}\n")
            f.write(f"   ArUco détectés: {best['count']}\n")
            if best['params']:
                f.write(f"   Paramètres à utiliser:\n")
                for k, v in best['params'].items():
                    f.write(f"     - {k} = {v}\n")
        else:
            f.write("❌ Aucune configuration n'a détecté d'ArUco.\n")
            f.write("   Suggestions:\n")
            f.write("   - Vérifier l'éclairage\n")
            f.write("   - Vérifier la mise au point\n")
            f.write("   - Vérifier que les ArUco sont visibles\n")
    
    print(f"💾 Rapport sauvegardé: {report_path}")
    print()
    print("=" * 60)
    print("  TEST TERMINÉ")
    print("=" * 60)
    
    # Afficher les meilleures configs
    if results[0]['count'] > 0:
        print()
        print("🏆 TOP 3 CONFIGURATIONS:")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result['config']} → {result['count']} ArUco")
            if result['params']:
                params_str = ", ".join([f"{k}={v}" for k, v in result['params'].items()])
                print(f"     {params_str}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Arrêt par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
