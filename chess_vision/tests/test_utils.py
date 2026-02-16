#!/usr/bin/env python3
"""
Utilitaires communs pour les tests du module chess_vision.

Ce module fournit:
- Logger coloré et configurable
- Gestionnaire de sauvegarde d'images avec étapes numérotées
- Utilitaires de comparaison et validation
- Décorateurs pour mesurer les temps d'exécution
"""

import cv2
import numpy as np
import os
import sys
import time
import json
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# CONFIGURATION
# ============================================================

# Couleurs pour le terminal (ANSI codes)
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Couleurs de texte
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Couleurs de fond
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


# ============================================================
# LOGGER COLORÉ
# ============================================================

class TestLogger:
    """
    Logger coloré pour les tests avec différents niveaux de verbosité.
    
    Niveaux:
        - DEBUG: Tout afficher (très verbeux)
        - INFO: Informations importantes
        - SUCCESS: Succès
        - WARNING: Avertissements
        - ERROR: Erreurs
    """
    
    LEVELS = {
        'DEBUG': (Colors.DIM + Colors.WHITE, '🔍'),
        'INFO': (Colors.CYAN, 'ℹ️'),
        'STEP': (Colors.BLUE + Colors.BOLD, '▶️'),
        'SUCCESS': (Colors.GREEN, '✅'),
        'WARNING': (Colors.YELLOW, '⚠️'),
        'ERROR': (Colors.RED + Colors.BOLD, '❌'),
        'HEADER': (Colors.MAGENTA + Colors.BOLD, ''),
        'RESULT': (Colors.GREEN + Colors.BOLD, '📊'),
    }
    
    def __init__(self, name: str, verbose: bool = True):
        """
        Initialise le logger.
        
        Args:
            name: Nom du test/module
            verbose: Afficher les messages DEBUG
        """
        self.name = name
        self.verbose = verbose
        self.start_time = time.time()
        self.step_count = 0
        self.warnings = []
        self.errors = []
    
    def _log(self, level: str, message: str, indent: int = 0):
        """Log un message avec couleur et emoji."""
        color, emoji = self.LEVELS.get(level, (Colors.WHITE, ''))
        prefix = "   " * indent
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if emoji:
            print(f"{Colors.DIM}[{timestamp}]{Colors.RESET} {prefix}{emoji} {color}{message}{Colors.RESET}")
        else:
            print(f"{color}{message}{Colors.RESET}")
    
    def debug(self, message: str, indent: int = 1):
        """Log un message de debug (seulement si verbose)."""
        if self.verbose:
            self._log('DEBUG', message, indent)
    
    def info(self, message: str, indent: int = 1):
        """Log une information."""
        self._log('INFO', message, indent)
    
    def step(self, message: str):
        """Log une étape importante."""
        self.step_count += 1
        self._log('STEP', f"ÉTAPE {self.step_count}: {message}")
    
    def success(self, message: str, indent: int = 1):
        """Log un succès."""
        self._log('SUCCESS', message, indent)
    
    def warning(self, message: str, indent: int = 1):
        """Log un avertissement."""
        self.warnings.append(message)
        self._log('WARNING', message, indent)
    
    def error(self, message: str, indent: int = 1):
        """Log une erreur."""
        self.errors.append(message)
        self._log('ERROR', message, indent)
    
    def header(self, title: str):
        """Affiche un header de section."""
        width = 60
        print()
        print(f"{Colors.MAGENTA}{Colors.BOLD}{'=' * width}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}  {title.upper()}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}{'=' * width}{Colors.RESET}")
    
    def subheader(self, title: str):
        """Affiche un sous-header."""
        print()
        print(f"{Colors.CYAN}{Colors.BOLD}--- {title} ---{Colors.RESET}")
    
    def separator(self):
        """Affiche une ligne de séparation."""
        print(f"{Colors.DIM}{'-' * 50}{Colors.RESET}")
    
    def result(self, key: str, value: Any, indent: int = 1):
        """Affiche un résultat clé-valeur."""
        prefix = "   " * indent
        print(f"{prefix}{Colors.BOLD}{key}:{Colors.RESET} {Colors.GREEN}{value}{Colors.RESET}")
    
    def dict_result(self, data: dict, title: str = None, indent: int = 1):
        """Affiche un dictionnaire de résultats."""
        if title:
            self.subheader(title)
        for key, value in data.items():
            self.result(key, value, indent)
    
    def summary(self):
        """Affiche le résumé du test."""
        elapsed = time.time() - self.start_time
        
        print()
        print(f"{Colors.BOLD}{'=' * 50}{Colors.RESET}")
        print(f"{Colors.BOLD}  RÉSUMÉ - {self.name}{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 50}{Colors.RESET}")
        
        print(f"   ⏱️  Durée totale: {elapsed:.2f}s")
        print(f"   📝 Étapes exécutées: {self.step_count}")
        print(f"   ⚠️  Avertissements: {len(self.warnings)}")
        print(f"   ❌ Erreurs: {len(self.errors)}")
        
        if self.errors:
            print(f"\n   {Colors.RED}ÉCHEC - {len(self.errors)} erreur(s){Colors.RESET}")
            for err in self.errors:
                print(f"      • {err}")
            return False
        elif self.warnings:
            print(f"\n   {Colors.YELLOW}SUCCÈS AVEC AVERTISSEMENTS{Colors.RESET}")
            return True
        else:
            print(f"\n   {Colors.GREEN}SUCCÈS COMPLET{Colors.RESET}")
            return True


# ============================================================
# GESTIONNAIRE D'IMAGES DE DEBUG
# ============================================================

class DebugImageSaver:
    """
    Gestionnaire pour sauvegarder les images de debug avec numérotation.
    
    Sauvegarde automatiquement les images avec:
    - Numérotation séquentielle
    - Noms descriptifs
    - Métadonnées JSON optionnelles
    
    Usage:
        saver = DebugImageSaver("test_calibration")
        saver.save(image, "original")
        saver.save(processed, "after_detection", metadata={'count': 5})
    """
    
    def __init__(self, test_name: str, base_dir: str = None, logger: TestLogger = None):
        """
        Initialise le gestionnaire.
        
        Args:
            test_name: Nom du test (utilisé pour le dossier)
            base_dir: Dossier de base (par défaut: tests/output)
            logger: Logger pour les messages
        """
        self.test_name = test_name
        self.logger = logger
        self.step_counter = 0
        
        # Créer le dossier de sortie
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "output")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(base_dir, f"{test_name}_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Fichier de log JSON pour les métadonnées
        self.metadata_file = os.path.join(self.output_dir, "metadata.json")
        self.metadata = {
            'test_name': test_name,
            'timestamp': timestamp,
            'steps': []
        }
        
        if self.logger:
            self.logger.info(f"Dossier de debug: {self.output_dir}")
    
    def save(
        self, 
        image: np.ndarray, 
        name: str, 
        metadata: dict = None,
        add_text: str = None
    ) -> str:
        """
        Sauvegarde une image avec numérotation.
        
        Args:
            image: Image numpy (BGR)
            name: Nom descriptif (ex: "after_detection")
            metadata: Métadonnées optionnelles
            add_text: Texte à ajouter sur l'image
            
        Returns:
            Chemin du fichier sauvegardé
        """
        if image is None:
            if self.logger:
                self.logger.warning(f"Image None pour '{name}' - pas de sauvegarde")
            return None
        
        self.step_counter += 1
        
        # Nom du fichier
        filename = f"{self.step_counter:02d}_{name}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        
        # Copier l'image pour ne pas modifier l'originale
        img_to_save = image.copy()
        
        # Ajouter du texte si demandé
        if add_text:
            img_to_save = self._add_text_overlay(img_to_save, add_text)
        
        # Sauvegarder
        cv2.imwrite(filepath, img_to_save)
        
        # Enregistrer les métadonnées
        step_meta = {
            'step': self.step_counter,
            'name': name,
            'filename': filename,
            'shape': list(image.shape),
        }
        if metadata:
            step_meta['data'] = metadata
        
        self.metadata['steps'].append(step_meta)
        self._save_metadata()
        
        if self.logger:
            size_str = f"{image.shape[1]}x{image.shape[0]}"
            self.logger.debug(f"💾 Sauvegardé: {filename} ({size_str})")
        
        return filepath
    
    def save_comparison(
        self, 
        images: List[np.ndarray], 
        labels: List[str], 
        name: str,
        cols: int = 2
    ) -> str:
        """
        Sauvegarde une comparaison côte à côte de plusieurs images.
        
        Args:
            images: Liste d'images
            labels: Labels pour chaque image
            name: Nom du fichier
            cols: Nombre de colonnes
            
        Returns:
            Chemin du fichier
        """
        if not images:
            return None
        
        # Filtrer les images None
        valid = [(img, lbl) for img, lbl in zip(images, labels) if img is not None]
        if not valid:
            return None
        
        images, labels = zip(*valid)
        
        # Redimensionner toutes les images à la même taille
        max_h = max(img.shape[0] for img in images)
        max_w = max(img.shape[1] for img in images)
        
        resized = []
        for img, label in zip(images, labels):
            # Redimensionner
            h, w = img.shape[:2]
            scale = min(max_w / w, max_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            img_resized = cv2.resize(img, (new_w, new_h))
            
            # Ajouter du padding pour avoir la même taille
            padded = np.zeros((max_h, max_w, 3), dtype=np.uint8)
            y_off = (max_h - new_h) // 2
            x_off = (max_w - new_w) // 2
            padded[y_off:y_off+new_h, x_off:x_off+new_w] = img_resized
            
            # Ajouter le label
            cv2.putText(padded, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       1, (0, 255, 0), 2)
            
            resized.append(padded)
        
        # Créer la grille
        rows = (len(resized) + cols - 1) // cols
        grid_h = rows * max_h
        grid_w = cols * max_w
        grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
        
        for i, img in enumerate(resized):
            row = i // cols
            col = i % cols
            y = row * max_h
            x = col * max_w
            grid[y:y+max_h, x:x+max_w] = img
        
        return self.save(grid, name)
    
    def _add_text_overlay(self, image: np.ndarray, text: str) -> np.ndarray:
        """Ajoute un texte en overlay sur l'image."""
        img = image.copy()
        
        # Fond semi-transparent pour le texte
        overlay = img.copy()
        cv2.rectangle(overlay, (5, 5), (len(text) * 12 + 15, 35), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)
        
        # Texte
        cv2.putText(img, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (255, 255, 255), 2)
        
        return img
    
    def _save_metadata(self):
        """Sauvegarde les métadonnées JSON."""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def add_custom_metadata(self, key: str, value: Any):
        """Ajoute des métadonnées personnalisées."""
        self.metadata[key] = value
        self._save_metadata()
    
    def get_output_dir(self) -> str:
        """Retourne le chemin du dossier de sortie."""
        return self.output_dir


# ============================================================
# DÉCORATEURS UTILITAIRES
# ============================================================

def timed(logger: TestLogger = None):
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction.
    
    Usage:
        @timed(logger)
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            
            if logger:
                logger.debug(f"⏱️  {func.__name__}: {elapsed*1000:.1f}ms")
            
            return result
        return wrapper
    return decorator


def catch_errors(logger: TestLogger):
    """
    Décorateur pour capturer et logger les erreurs.
    
    Usage:
        @catch_errors(logger)
        def risky_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception dans {func.__name__}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return None
        return wrapper
    return decorator


# ============================================================
# UTILITAIRES DE VALIDATION
# ============================================================

def validate_image(image: np.ndarray, name: str, logger: TestLogger) -> bool:
    """
    Valide qu'une image est correcte.
    
    Args:
        image: Image à valider
        name: Nom pour les logs
        logger: Logger
        
    Returns:
        True si valide
    """
    if image is None:
        logger.error(f"Image '{name}' est None")
        return False
    
    if not isinstance(image, np.ndarray):
        logger.error(f"Image '{name}' n'est pas un numpy array")
        return False
    
    if len(image.shape) < 2:
        logger.error(f"Image '{name}' a une forme invalide: {image.shape}")
        return False
    
    if image.size == 0:
        logger.error(f"Image '{name}' est vide")
        return False
    
    logger.debug(f"Image '{name}' valide: {image.shape}")
    return True


def validate_markers(markers: dict, expected_count: int, name: str, logger: TestLogger) -> bool:
    """
    Valide un dictionnaire de marqueurs.
    
    Args:
        markers: Dict des marqueurs détectés
        expected_count: Nombre attendu
        name: Nom pour les logs
        logger: Logger
        
    Returns:
        True si valide
    """
    if markers is None:
        logger.error(f"Marqueurs '{name}' est None")
        return False
    
    if not isinstance(markers, dict):
        logger.error(f"Marqueurs '{name}' n'est pas un dictionnaire")
        return False
    
    count = len(markers)
    if count < expected_count:
        logger.warning(f"Marqueurs '{name}': {count}/{expected_count} détectés")
        return False
    
    logger.success(f"Marqueurs '{name}': {count} détectés")
    return True


# ============================================================
# UTILITAIRES D'IMAGE
# ============================================================

def load_test_image(path: str, logger: TestLogger) -> Optional[np.ndarray]:
    """
    Charge une image de test.
    
    Args:
        path: Chemin de l'image
        logger: Logger
        
    Returns:
        Image numpy ou None
    """
    if not os.path.exists(path):
        logger.error(f"Fichier non trouvé: {path}")
        return None
    
    image = cv2.imread(path)
    
    if image is None:
        logger.error(f"Impossible de charger: {path}")
        return None
    
    logger.info(f"Image chargée: {os.path.basename(path)} ({image.shape[1]}x{image.shape[0]})")
    return image


def find_test_images(search_dirs: List[str], logger: TestLogger) -> List[str]:
    """
    Trouve les images de test disponibles.
    
    Args:
        search_dirs: Liste de dossiers à chercher
        logger: Logger
        
    Returns:
        Liste des chemins d'images trouvées
    """
    import glob
    
    images = []
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                images.extend(glob.glob(os.path.join(search_dir, ext)))
    
    images = sorted(set(images))
    logger.info(f"Trouvé {len(images)} image(s) de test")
    
    return images


def draw_debug_info(
    image: np.ndarray,
    info: Dict[str, Any],
    position: str = 'top'
) -> np.ndarray:
    """
    Ajoute des informations de debug sur une image.
    
    Args:
        image: Image
        info: Dict d'informations à afficher
        position: 'top' ou 'bottom'
        
    Returns:
        Image avec infos
    """
    img = image.copy()
    
    y_start = 30 if position == 'top' else img.shape[0] - 30 * len(info)
    y_step = 25
    
    for i, (key, value) in enumerate(info.items()):
        y = y_start + i * y_step
        text = f"{key}: {value}"
        
        # Fond
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (5, y - h - 5), (w + 15, y + 5), (0, 0, 0), -1)
        
        # Texte
        cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (0, 255, 0), 2)
    
    return img
