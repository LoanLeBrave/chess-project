#!/usr/bin/env python3
"""
Run All Tests
=============

Script principal pour exécuter tous les tests ou des tests spécifiques.

Usage:
    python -m chess_vision.tests.run_all_tests --image photo.jpg
    python -m chess_vision.tests.run_all_tests --image photo.jpg --test aruco
    python -m chess_vision.tests.run_all_tests --image photo.jpg --test calibration
    python -m chess_vision.tests.run_all_tests --image photo.jpg --test pieces
    python -m chess_vision.tests.run_all_tests --image photo.jpg --test pipeline
    python -m chess_vision.tests.run_all_tests --list
"""

import sys
import os
import argparse
import time
from datetime import datetime

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chess_vision.tests.test_utils import TestLogger, Colors, find_test_images


# Import des tests
from chess_vision.tests.test_aruco_detection import run_aruco_detection_test
from chess_vision.tests.test_board_calibration import run_board_calibration_test
from chess_vision.tests.test_piece_analysis import run_piece_analysis_test
from chess_vision.tests.test_full_pipeline import run_full_pipeline_test


AVAILABLE_TESTS = {
    'aruco': {
        'name': 'Test Détection ArUco',
        'description': 'Teste la détection des marqueurs ArUco (calibration + pièces)',
        'function': run_aruco_detection_test,
    },
    'calibration': {
        'name': 'Test Calibration Plateau',
        'description': 'Teste la calibration, les offsets et l\'extraction du plateau',
        'function': run_board_calibration_test,
    },
    'pieces': {
        'name': 'Test Analyse Pièces',
        'description': 'Teste l\'analyse des pièces et la conversion de coordonnées',
        'function': run_piece_analysis_test,
    },
    'pipeline': {
        'name': 'Test Pipeline Complet',
        'description': 'Teste le pipeline complet de bout en bout',
        'function': run_full_pipeline_test,
    },
}


def print_banner():
    """Affiche la bannière du programme."""
    print()
    print(f"{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}║           CHESS VISION - SUITE DE TESTS                  ║{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}║                 Debug & Validation                       ║{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    print()


def print_available_tests():
    """Affiche la liste des tests disponibles."""
    print(f"\n{Colors.BOLD}Tests disponibles:{Colors.RESET}\n")
    
    for key, info in AVAILABLE_TESTS.items():
        print(f"  {Colors.GREEN}{key:15}{Colors.RESET} - {info['name']}")
        print(f"  {' '*15}   {Colors.DIM}{info['description']}{Colors.RESET}")
        print()


def run_single_test(test_key: str, image_path: str, verbose: bool) -> bool:
    """
    Exécute un test spécifique.
    
    Args:
        test_key: Clé du test
        image_path: Chemin de l'image
        verbose: Mode verbeux
        
    Returns:
        True si succès
    """
    if test_key not in AVAILABLE_TESTS:
        print(f"{Colors.RED}Test inconnu: {test_key}{Colors.RESET}")
        print_available_tests()
        return False
    
    test_info = AVAILABLE_TESTS[test_key]
    test_func = test_info['function']
    
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}  Exécution: {test_info['name']}{Colors.RESET}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    start_time = time.time()
    
    try:
        success = test_func(image_path, verbose=verbose)
    except Exception as e:
        print(f"{Colors.RED}❌ Exception: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        success = False
    
    elapsed = time.time() - start_time
    
    print(f"\n{Colors.BOLD}Temps d'exécution: {elapsed:.2f}s{Colors.RESET}")
    
    return success


def run_all_tests(image_path: str, verbose: bool) -> dict:
    """
    Exécute tous les tests.
    
    Args:
        image_path: Chemin de l'image
        verbose: Mode verbeux
        
    Returns:
        Dictionnaire des résultats
    """
    results = {}
    total_start = time.time()
    
    for test_key, test_info in AVAILABLE_TESTS.items():
        print(f"\n{'='*70}")
        print(f"  TEST: {test_info['name']}")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        
        try:
            success = test_info['function'](image_path, verbose=verbose)
        except Exception as e:
            print(f"{Colors.RED}❌ Exception: {e}{Colors.RESET}")
            success = False
        
        elapsed = time.time() - start_time
        
        results[test_key] = {
            'success': success,
            'time': elapsed,
            'name': test_info['name']
        }
        
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if success else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"\n  Résultat: {status} ({elapsed:.2f}s)")
    
    total_elapsed = time.time() - total_start
    
    # Résumé final
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}  RÉSUMÉ FINAL{Colors.RESET}")
    print(f"{'='*70}\n")
    
    passed = sum(1 for r in results.values() if r['success'])
    failed = len(results) - passed
    
    print(f"  Tests exécutés: {len(results)}")
    print(f"  {Colors.GREEN}Réussis: {passed}{Colors.RESET}")
    print(f"  {Colors.RED}Échoués: {failed}{Colors.RESET}")
    print(f"  Temps total: {total_elapsed:.2f}s")
    print()
    
    for test_key, result in results.items():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if result['success'] else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {status} {result['name']}: {result['time']:.2f}s")
    
    print()
    
    return results


def interactive_menu(images: list, verbose: bool):
    """
    Menu interactif pour choisir une image et un test.
    
    Args:
        images: Liste des images disponibles
        verbose: Mode verbeux
    """
    print_banner()
    
    # Sélection de l'image
    print(f"{Colors.BOLD}Images disponibles:{Colors.RESET}\n")
    for i, img_path in enumerate(images[:15]):
        print(f"  {i+1:2}. {os.path.basename(img_path)}")
        print(f"      {Colors.DIM}{img_path}{Colors.RESET}")
    
    print()
    
    try:
        choice = input(f"{Colors.CYAN}Choisir une image (1-{len(images[:15])}): {Colors.RESET}")
        img_index = int(choice) - 1
        
        if 0 <= img_index < len(images):
            image_path = images[img_index]
        else:
            print(f"{Colors.RED}Choix invalide{Colors.RESET}")
            return
    except (ValueError, KeyboardInterrupt):
        print(f"\n{Colors.YELLOW}Annulé{Colors.RESET}")
        return
    
    # Sélection du test
    print(f"\n{Colors.BOLD}Tests disponibles:{Colors.RESET}\n")
    test_keys = list(AVAILABLE_TESTS.keys())
    
    for i, key in enumerate(test_keys):
        info = AVAILABLE_TESTS[key]
        print(f"  {i+1}. {info['name']}")
    
    print(f"  {len(test_keys)+1}. Tous les tests")
    print()
    
    try:
        choice = input(f"{Colors.CYAN}Choisir un test (1-{len(test_keys)+1}): {Colors.RESET}")
        test_index = int(choice) - 1
        
        if test_index == len(test_keys):
            # Tous les tests
            run_all_tests(image_path, verbose)
        elif 0 <= test_index < len(test_keys):
            run_single_test(test_keys[test_index], image_path, verbose)
        else:
            print(f"{Colors.RED}Choix invalide{Colors.RESET}")
            return
    except (ValueError, KeyboardInterrupt):
        print(f"\n{Colors.YELLOW}Annulé{Colors.RESET}")
        return


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Suite de tests pour chess_vision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Lancer tous les tests sur une image
  python -m chess_vision.tests.run_all_tests --image photo.jpg

  # Lancer un test spécifique
  python -m chess_vision.tests.run_all_tests --image photo.jpg --test aruco
  python -m chess_vision.tests.run_all_tests --image photo.jpg --test calibration
  python -m chess_vision.tests.run_all_tests --image photo.jpg --test pieces
  python -m chess_vision.tests.run_all_tests --image photo.jpg --test pipeline

  # Lister les tests disponibles
  python -m chess_vision.tests.run_all_tests --list

  # Mode interactif
  python -m chess_vision.tests.run_all_tests --interactive
        """
    )
    
    parser.add_argument(
        '--image', '-i',
        type=str,
        help='Chemin vers l\'image à tester'
    )
    
    parser.add_argument(
        '--photo', '-p',
        action='store_true',
        help='Prendre une photo en direct avec la caméra'
    )
    
    parser.add_argument(
        '--test', '-t',
        type=str,
        choices=list(AVAILABLE_TESTS.keys()),
        help='Test spécifique à exécuter'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='Lister les tests disponibles'
    )
    
    parser.add_argument(
        '--interactive', '-I',
        action='store_true',
        help='Mode interactif'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=True,
        help='Mode verbeux (par défaut: True)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Mode silencieux'
    )
    
    args = parser.parse_args()
    verbose = not args.quiet
    
    # Afficher la bannière
    print_banner()
    
    # Lister les tests
    if args.list:
        print_available_tests()
        return
    
    # Chercher des images
    search_dirs = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'images_tmp'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'test_extraction_plateau_image_cam_rasp', 'images'),
        os.path.join(os.path.dirname(__file__), '..', 'images'),
        os.path.join(os.path.dirname(__file__), 'images'),
        '.',
    ]
    
    logger = TestLogger("Recherche", verbose=False)
    available_images = find_test_images(search_dirs, logger)
    
    # Mode interactif
    if args.interactive:
        if not available_images:
            print(f"{Colors.RED}Aucune image trouvée dans les dossiers de recherche.{Colors.RESET}")
            return
        interactive_menu(available_images, verbose)
        return
    
    # Capture photo si demandé
    image_to_test = None
    if args.photo:
        from chess_vision.camera import take_photo
        from chess_vision.tests.test_utils import TestLogger
        logger = TestLogger("Capture photo", verbose=verbose)
        logger.info("Capture d'une photo avec la caméra...")
        
        photo_path = take_photo()
        if photo_path:
            logger.success(f"Photo capturée: {photo_path}")
            image_to_test = photo_path
        else:
            print(f"{Colors.RED}Échec de la capture photo{Colors.RESET}")
            return
    elif args.image:
        # Vérifier que l'image existe
        if not os.path.exists(args.image):
            print(f"{Colors.RED}Image non trouvée: {args.image}{Colors.RESET}")
            return
        image_to_test = args.image
    else:
        # Aucune image fournie
        print(f"{Colors.YELLOW}Usage: python -m chess_vision.tests.run_all_tests --image <chemin_image> ou --photo{Colors.RESET}")
        print()
        
        if available_images:
            print(f"{Colors.CYAN}Images disponibles:{Colors.RESET}")
            for img in available_images[:10]:
                print(f"  • {img}")
            print()
            print(f"{Colors.DIM}Conseil: Utilisez --interactive pour un menu interactif{Colors.RESET}")
        else:
            print(f"{Colors.RED}Aucune image trouvée. Spécifiez le chemin avec --image ou utilisez --photo{Colors.RESET}")
        
        return
    
    # Exécuter les tests
    if args.test:
        # Test spécifique
        success = run_single_test(args.test, image_to_test, verbose)
        sys.exit(0 if success else 1)
    else:
        # Tous les tests
        results = run_all_tests(image_to_test, verbose)
        all_passed = all(r['success'] for r in results.values())
        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
