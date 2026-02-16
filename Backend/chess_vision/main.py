#!/usr/bin/env python3
"""
Script principal de vision d'échecs.
Orchestre le pipeline complet: capture → détection → analyse → JSON

Usage:
    python main.py                     # Mode interactif
    python main.py --photo             # Prendre une photo et analyser
    python main.py --image path.jpg    # Analyser une image existante
    python main.py --help              # Aide

Outputs:
    - 1_original.jpg: Image originale
    - 2_calibration.jpg: Visualisation des coins de calibration
    - 3_board.jpg: Plateau extrait et redressé
    - 4_board_grid.jpg: Plateau avec grille 8x8
    - 5_pieces.jpg: Pièces détectées avec coordonnées
    - 6_aruco.jpg: ArUcos des pièces détectés
    - game_state.json: État complet du jeu
    - board_state.json: État du plateau (A1, B2...)
    - coordinates.json: Coordonnées robot (-10/+10)
"""

import cv2
import os
import sys
import argparse
import glob
import time
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_vision import (
    ChessVisionPipeline,
    take_photo,
    get_camera_mode,
    FIXED_BOARD_CORNERS,
    CALIBRATION_FILE,
    EXTRACTED_BOARD_SIZE,
)
from chess_vision.config import OUTPUT_DIR, IMAGES_DIR


def print_header():
    """Affiche l'en-tête du programme."""
    print("\n" + "=" * 60)
    print("♟️  CHESS VISION - Système de vision pour échecs robotisé")
    print("=" * 60)


def print_calibration_status(result: dict):
    """Affiche le statut de la calibration."""
    print("\n🎯 CALIBRATION (coins fixes)")
    print("-" * 40)
    
    corners = result.get('board_corners', {})
    
    if not corners:
        print("   ❌ Pas de calibration!")
        print(f"   Lancez: python -m chess_vision.calibrate_board")
        return
    
    print(f"   ✅ Calibration chargée ({len(corners)}/4 coins)")
    for code in ['TL', 'TR', 'BR', 'BL']:
        if code in corners:
            corner = corners[code]
            print(f"      ✅ {code}: ({corner[0]:.1f}, {corner[1]:.1f})")
        else:
            print(f"      ❌ {code}: manquant")


def print_pieces_summary(result: dict):
    """Affiche le résumé des pièces détectées."""
    pieces = result.get('pieces', [])
    
    print("\n-- PIECES DETECTEES")
    print("-" * 40)
    
    if not pieces:
        print("   Aucune piece detectee")
        return
    
    board_pieces = [p for p in pieces if p.get('zone') == 'board']
    cemetery_pieces = [p for p in pieces if p.get('zone') == 'cemetery']
    white_pieces = [p for p in pieces if p['color'] == 'white']
    black_pieces = [p for p in pieces if p['color'] == 'black']
    
    print(f"   Total: {len(pieces)} pieces")
    print(f"   Blanches: {len(white_pieces)} | Noires: {len(black_pieces)}")
    print(f"   Sur plateau: {len(board_pieces)} | Cimetiere: {len(cemetery_pieces)}")
    
    if board_pieces:
        print("\n   [Plateau]")
        for p in sorted(board_pieces, key=lambda x: x['id']):
            pos = p['position']
            chess = pos.get('chess', '??')
            print(f"      ID {p['id']:2d} {p['symbol']} {p['code']:4s}  "
                  f"{chess} / {pos.get('grid', '??')}  "
                  f"({pos['board']['x']:+6.2f}, {pos['board']['y']:+6.2f})")
    
    if cemetery_pieces:
        print("\n   [Cimetiere]")
        for p in sorted(cemetery_pieces, key=lambda x: x['id']):
            pos = p['position']
            print(f"      ID {p['id']:2d} {p['symbol']} {p['code']:4s}  "
                  f"{pos.get('grid', '??')}  "
                  f"({pos['board']['x']:+6.2f}, {pos['board']['y']:+6.2f})")


def print_output_files(result: dict):
    """Affiche les fichiers générés."""
    output_dir = result.get('output_dir')
    
    if not output_dir:
        return
    
    print("\n📁 FICHIERS GÉNÉRÉS")
    print("-" * 40)
    print(f"   Dossier: {output_dir}")
    
    files = [
        ("1_original.jpg", "Image originale"),
        ("2_calibration.jpg", "Visualisation calibration"),
        ("3_board.jpg", "Plateau extrait"),
        ("4_board_grid.jpg", "Plateau avec grille"),
        ("5_pieces.jpg", "Pièces détectées"),
        ("6_aruco.jpg", "ArUcos des pièces"),
        ("game_state.json", "État complet du jeu"),
        ("board_state.json", "État du plateau (A1, B2...)"),
        ("coordinates.json", "Coordonnées robot"),
    ]
    
    for filename, description in files:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"      ✅ {filename} - {description} ({size} bytes)")


def select_image_interactive():
    """Sélection interactive d'une image."""
    # Chercher les images dans les dossiers habituels
    search_dirs = [
        IMAGES_DIR,
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "analyse", "images"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_extraction_plateau_image_cam_rasp", "images"),
        os.path.dirname(__file__),
    ]
    
    images = []
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                images.extend(glob.glob(os.path.join(search_dir, ext)))
    
    images = sorted(set(images))
    
    if not images:
        print("❌ Aucune image trouvée dans les dossiers habituels.")
        return None
    
    print("\n📷 Images disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"   {i}. {os.path.basename(img_path)}")
        print(f"      {os.path.dirname(img_path)}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("\nNuméro de l'image (ou 'q' pour quitter): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(images):
                return images[idx]
            
            print("   ⚠️ Numéro invalide")
        except ValueError:
            print("   ⚠️ Entrez un numéro valide")


def interactive_menu():
    """Menu interactif."""
    print("\n📋 OPTIONS")
    print("-" * 40)
    print("   1. Prendre une photo et analyser")
    print("   2. Analyser une image existante")
    print("   3. Calibrer le plateau (cliquer les 4 coins)")
    print("   4. Afficher la configuration actuelle")
    print("   q. Quitter")
    print("-" * 40)
    
    while True:
        choice = input("\nChoix: ").strip().lower()
        
        if choice == '1':
            return 'photo'
        elif choice == '2':
            return 'image'
        elif choice == '3':
            return 'calibrate'
        elif choice == '4':
            return 'config'
        elif choice == 'q':
            return 'quit'
        else:
            print("   ⚠️ Choix invalide")


def show_config():
    """Affiche la configuration actuelle."""
    print("\n-- CONFIGURATION ACTUELLE")
    print("-" * 40)
    
    print(f"\n   Mode camera: {get_camera_mode()}")
    print(f"   Image extraite: {EXTRACTED_BOARD_SIZE}x{EXTRACTED_BOARD_SIZE} pixels")
    print(f"   Grille: 10x10 (plateau 8x8 + cimetiere)")
    print(f"   Repere etendu: -12.5 a +12.5 (plateau: -10 a +10)")
    
    print(f"\n   Calibration (coins fixes):")
    if FIXED_BOARD_CORNERS:
        print(f"   [OK] Fichier: {CALIBRATION_FILE}")
        for code in ['TL', 'TR', 'BR', 'BL']:
            if code in FIXED_BOARD_CORNERS:
                c = FIXED_BOARD_CORNERS[code]
                print(f"      {code}: ({c[0]}, {c[1]})")
    else:
        print(f"   [!!] Pas de calibration!")
        print(f"   Lancez: python -m chess_vision.calibrate_board")
    
    print(f"\n   Dossier images: {IMAGES_DIR}")
    print(f"   Dossier output: {OUTPUT_DIR}")


def analyze_and_display(pipeline: ChessVisionPipeline, image_path=None, take_new_photo: bool = False):
    """Analyse une image et affiche les résultats."""
    
    # Démarrer le chronomètre
    start_time = time.time()
    
    try:
        if take_new_photo:
            print("\n📸 CAPTURE PHOTO")
            print("-" * 40)
            result = pipeline.capture_and_analyze()
            print(f"   ✅ Photo capturée: {result.get('photo_path', 'N/A')}")
        else:
            if image_path is None:
                print("❌ Pas de chemin d'image spécifié")
                return
            
            print(f"\n📷 ANALYSE IMAGE")
            print("-" * 40)
            print(f"   Fichier: {image_path}")
            result = pipeline.analyze_image(image_path)
        
        # Calculer le temps de traitement
        processing_time = time.time() - start_time
        
        # Afficher les résultats
        print_calibration_status(result)
        
        if result.get('success'):
            print_pieces_summary(result)
            print_output_files(result)
            
            # Afficher le temps de traitement
            print(f"\n⏱️  TEMPS DE TRAITEMENT: {processing_time:.2f} secondes")
            
            print("\n" + "=" * 60)
            print("✅ ANALYSE TERMINÉE AVEC SUCCÈS")
            print("=" * 60)
        else:
            print(f"\n❌ ERREUR: {result.get('error', 'Erreur inconnue')}")
            if result.get('traceback'):
                print(f"\n   Détails:\n{result['traceback']}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_calibration(pipeline):
    """Exécute la calibration et met à jour le pipeline."""
    from chess_vision.calibrate_board import main as calibrate_main
    calibrate_main()
    # Recharger la calibration
    from chess_vision.config import load_board_corners
    new_corners = load_board_corners()
    if new_corners:
        pipeline.extractor.board_corners = new_corners
        print("   ✅ Calibration rechargée dans le pipeline")


def handle_cli_mode(args, pipeline):
    """Gère le mode ligne de commande. Retourne True si une action a été traitée."""
    if args.photo:
        analyze_and_display(pipeline, take_new_photo=True)
        return True
    
    if args.image:
        if not os.path.exists(args.image):
            print(f"❌ Fichier non trouvé: {args.image}")
            return True
        analyze_and_display(pipeline, image_path=args.image)
        return True
    
    return False


def run_interactive_loop(pipeline):
    """Boucle principale du mode interactif."""
    while True:
        action = interactive_menu()
        
        if action == 'quit':
            print("\n👋 Au revoir!")
            break
        
        elif action == 'config':
            show_config()
        
        elif action == 'calibrate':
            run_calibration(pipeline)
        
        elif action == 'photo':
            analyze_and_display(pipeline, take_new_photo=True)
        
        elif action == 'image':
            image_path = select_image_interactive()
            if image_path:
                analyze_and_display(pipeline, image_path=image_path)


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Chess Vision - Système de vision pour échecs robotisé",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
    python main.py                     # Mode interactif
    python main.py --photo             # Prendre une photo et analyser
    python main.py --image photo.jpg   # Analyser une image existante
    python main.py --no-save           # Analyser sans sauvegarder les fichiers
        """
    )
    
    parser.add_argument('--photo', '-p', action='store_true',
                       help='Prendre une photo et analyser')
    parser.add_argument('--image', '-i', type=str,
                       help='Chemin vers une image à analyser')
    parser.add_argument('--output', '-o', type=str,
                       help='Dossier de sortie personnalisé')
    parser.add_argument('--no-save', action='store_true',
                       help='Ne pas sauvegarder les fichiers intermédiaires')
    parser.add_argument('--board-size', type=int, default=EXTRACTED_BOARD_SIZE,
                       help=f'Taille du plateau extrait (default: {EXTRACTED_BOARD_SIZE})')
    
    args = parser.parse_args()
    
    print_header()
    
    # Créer le pipeline
    pipeline = ChessVisionPipeline(board_size=args.board_size)
    
    # Mode direct avec arguments
    if handle_cli_mode(args, pipeline):
        return
    
    # Mode interactif
    run_interactive_loop(pipeline)


if __name__ == "__main__":
    main()
