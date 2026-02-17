#!/usr/bin/env python3
"""
Script de capture et analyse en boucle infinie — VERSION OPTIMISÉE.

Optimisations par rapport à la version originale:
  1. Pipeline créé UNE SEULE FOIS (au lieu de recréer ArucoDetector etc. à chaque itération)
  2. Caméra persistante (PersistentCamera) — init/start une seule fois
  3. Capture directe en mémoire (numpy array, pas d'écriture/lecture disque pour la photo)
  4. Détection de changement — le JSON n'est écrit QUE si le plateau a changé
  5. Seul game_state.json est écrit (board_state.json et coordinates.json ignorés)
  6. Écriture atomique via fichier temporaire + os.replace
  7. Throttle configurable (intervalle minimum entre itérations)
  8. Priorité OS réduite via os.nice() pour laisser de la marge au backend/frontend

Usage:
    python3 -m chess_vision.infinite_chess_vision [OPTIONS]

Options:
    --interval SECONDS   Intervalle minimum entre itérations (défaut: 0.5)
    --nice VALUE         Valeur nice OS, 0-19 (défaut: 10)
    --no-nice            Désactiver os.nice()
    --no-change-detect   Écrire le JSON à chaque itération (même sans changement)
    --verbose            Affichage détaillé

Arrêt: Ctrl+C
"""

import sys
import os
import json
import time
import argparse
import tempfile
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_vision import ChessVisionPipeline
from chess_vision.modules.camera import PersistentCamera
from chess_vision.config import OUTPUT_DIR


def _parse_args():
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Analyse continue du plateau d'échecs (optimisée)"
    )
    parser.add_argument(
        '--interval', type=float, default=0.5,
        help='Intervalle minimum entre itérations en secondes (défaut: 0.5)'
    )
    parser.add_argument(
        '--nice', type=int, default=10,
        help='Valeur nice OS, 0-19 (défaut: 10). Plus haut = moins prioritaire'
    )
    parser.add_argument(
        '--no-nice', action='store_true',
        help='Désactiver os.nice()'
    )
    parser.add_argument(
        '--no-change-detect', action='store_true',
        help="Écrire le JSON à chaque itération même si le plateau n'a pas changé"
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Affichage détaillé'
    )
    return parser.parse_args()


def _extract_board_fingerprint(pieces):
    """
    Crée une empreinte compacte de l'état du plateau pour détection de changement.
    Retourne un tuple trié (immuable, hashable, comparable rapidement).
    
    Seuls les champs pertinents sont inclus : ID + case (grid notation).
    On utilise grid (et non chess) pour couvrir aussi le cimetière.
    """
    if not pieces:
        return ()
    return tuple(sorted(
        (p['id'], p['position'].get('grid', '??'))
        for p in pieces
    ))


def _write_game_state_atomic(game_state, output_path):
    """
    Écrit game_state.json de manière atomique.
    
    Stratégie:
      1. Écrire dans un fichier temporaire dans le même répertoire
      2. os.replace() atomique vers le chemin final
    
    Cela garantit que le lecteur ne verra jamais un fichier tronqué.
    """
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Sérialiser le JSON de manière compacte (moins d'I/O, plus rapide)
    json_bytes = json.dumps(game_state, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    
    # Écriture atomique: fichier temporaire + rename
    fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix='.tmp', prefix='.gs_')
    try:
        os.write(fd, json_bytes)
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, output_path)
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _setup_output_dir():
    """
    Prépare les répertoires de sortie.
    Crée output/data_1 et le symlink output/latest → data_1 si nécessaire.
    
    Returns:
        Tuple (data_dir, game_state_path)
    """
    data_dir = os.path.join(OUTPUT_DIR, "data_1")
    latest_link = os.path.join(OUTPUT_DIR, "latest")
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Créer le symlink latest si inexistant
    if not os.path.exists(latest_link):
        try:
            os.symlink(os.path.abspath(data_dir), latest_link)
        except OSError:
            pass  # Pas grave, on écrit directement dans data_1
    
    # Le game_state.json est écrit dans le répertoire pointé par latest
    if os.path.islink(latest_link):
        actual_dir = os.path.realpath(latest_link)
    else:
        actual_dir = data_dir
    
    game_state_path = os.path.join(actual_dir, "game_state.json")
    return actual_dir, game_state_path


def main():
    """Boucle infinie d'analyse du plateau — version optimisée."""
    args = _parse_args()
    
    print("=" * 60)
    print("♟️  INFINITE CHESS VISION — Mode optimisé")
    print("=" * 60)
    print(f"\n⚙️  Intervalle min: {args.interval}s")
    print(f"⚙️  Détection changement: {'NON' if args.no_change_detect else 'OUI'}")
    print(f"⚙️  Nice: {'désactivé' if args.no_nice else args.nice}")
    
    # ── Réduire la priorité OS ──────────────────────────────
    if not args.no_nice and args.nice > 0:
        try:
            actual = os.nice(args.nice)
            print(f"⚙️  Priorité OS réduite (nice={actual})")
        except PermissionError:
            print("⚠️  os.nice() refusé (droits insuffisants)")
    
    # ── Créer le pipeline UNE SEULE FOIS ────────────────────
    print("\n🔧 Initialisation du pipeline (une seule fois)...")
    pipeline = ChessVisionPipeline(save_visualization_images=False)
    
    if not pipeline.extractor.is_calibrated:
        print("❌ Fichier board_calibration.json manquant!")
        print("   Lancez: python -m chess_vision.modules.calibrate_board")
        sys.exit(1)
    
    # ── Ouvrir la caméra UNE SEULE FOIS ─────────────────────
    print("📷 Initialisation de la caméra persistante...")
    camera = PersistentCamera(prefer_picamera2=True)
    camera.start()
    
    # ── Préparer le répertoire de sortie ────────────────────
    _, game_state_path = _setup_output_dir()
    print(f"📂 Sortie: {game_state_path}")
    
    print("\n🛑 Arrêt: Ctrl+C\n")
    
    # ── État pour la détection de changement ────────────────
    previous_fingerprint = None
    iteration = 0
    writes = 0
    errors = 0
    
    try:
        while True:
            iteration += 1
            t_start = time.monotonic()
            
            try:
                # 1. Capture en mémoire (pas d'écriture disque)
                image = camera.capture_array()
                if image is None:
                    if args.verbose:
                        print(f"  [{iteration}] ⚠️  Capture vide, skip")
                    errors += 1
                    time.sleep(args.interval)
                    continue
                
                # 2. Analyse (pipeline réutilisé, pas de sauvegarde auto)
                result = pipeline._process_image(
                    image,
                    save_outputs=False,
                    output_dir=None
                )
                
                if not result.get('success'):
                    if args.verbose:
                        print(f"  [{iteration}] ❌ {result.get('error', '?')}")
                    errors += 1
                    time.sleep(args.interval)
                    continue
                
                pieces = result.get('pieces', [])
                
                # 3. Détection de changement
                current_fingerprint = _extract_board_fingerprint(pieces)
                state_changed = (
                    args.no_change_detect
                    or previous_fingerprint is None
                    or current_fingerprint != previous_fingerprint
                )
                
                # 4. Écriture JSON uniquement si changement
                if state_changed:
                    game_state = result.get('game_state')
                    if game_state:
                        _write_game_state_atomic(game_state, game_state_path)
                        writes += 1
                        previous_fingerprint = current_fingerprint
                
                # 5. Affichage
                elapsed = time.monotonic() - t_start
                board_count = sum(1 for p in pieces if p.get('zone') == 'board')
                
                if args.verbose or state_changed:
                    status = "📝 MÀJ" if state_changed else "⏸️  idem"
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(
                        f"  [{ts}] #{iteration} | {board_count} pièces "
                        f"| {elapsed:.2f}s | {status} "
                        f"| écritures: {writes}"
                    )
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                errors += 1
                if args.verbose:
                    print(f"  [{iteration}] ⚠️  {type(e).__name__}: {e}")
            
            # 6. Throttle — attendre au minimum `interval` entre itérations
            elapsed = time.monotonic() - t_start
            sleep_time = args.interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        pass
    finally:
        # Nettoyage propre
        camera.stop()
        print(f"\n{'=' * 60}")
        print(f"🛑 Arrêt après {iteration} itérations")
        print(f"   📝 {writes} écritures JSON | ⚠️  {errors} erreurs")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
