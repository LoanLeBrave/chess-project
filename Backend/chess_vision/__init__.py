#!/usr/bin/env python3
"""
Chess Vision - Module de vision pour jeu d'échecs robotisé.

Ce module fournit toutes les fonctionnalités pour:
- Capturer une image du plateau
- Détecter les marqueurs ArUco de calibration
- Extraire et redresser le plateau
- Analyser les pièces et leurs positions
- Générer l'état du jeu en JSON

Modules:
    - config: Configuration centralisée
    - aruco_detector: Détection des marqueurs ArUco
    - board_extractor: Extraction et transformation du plateau
    - piece_analyzer: Analyse des pièces et coordonnées
    - game_state: Génération des états de jeu JSON
    - camera: Capture photo

Usage basique:
    from chess_vision import ChessVisionPipeline
    
    pipeline = ChessVisionPipeline()
    result = pipeline.analyze_image("photo.jpg")
    print(result['game_state'])
"""

__version__ = "1.0.0"
__author__ = "Chess Robot Project"

# Imports principaux pour une utilisation facile
from .config import (
    OFFSETS,
    FIXED_BOARD_CORNERS,
    CALIBRATION_FILE,
    EXTRACTED_BOARD_SIZE,
    BOARD_COORD_MIN,
    BOARD_COORD_MAX,
    EXTENDED_COORD_MIN,
    EXTENDED_COORD_MAX,
    GRID_SIZE,
    CHESS_GRID_SIZE,
    GRID_COLUMNS,
    GRID_ROWS,
    CEMETERY_FILL_ORDER,
    PIECES,
    CALIBRATION_IDS,
    get_piece_info,
    get_calibration_code,
    load_board_corners,
)

from .modules.aruco_detector import (
    ArucoDetector,
    detect_piece_markers,
    detect_calibration_markers,
    get_detection_summary,
)

from .modules.board_extractor import (
    BoardExtractor,
    draw_chess_grid,
    draw_board_visualization,
    get_cell_bounds,
)

from .modules.piece_analyzer import (
    PieceAnalyzer,
    draw_pieces_on_board,
    draw_pieces_aruco,
    get_pieces_summary,
)

from .modules.game_state import (
    GameStateGenerator,
    load_game_state,
    compare_states,
    format_move,
)

from .modules.camera import (
    take_photo,
    get_camera_mode,
)


# Classe de haut niveau pour une utilisation simplifiée
class ChessVisionPipeline:
    """
    Pipeline complet de vision d'échecs.
    Combine tous les modules pour une utilisation simple.
    
    Usage:
        pipeline = ChessVisionPipeline()
        
        # Analyser une image existante
        result = pipeline.analyze_image("photo.jpg")
        
        # Ou prendre une photo et analyser
        result = pipeline.capture_and_analyze()
        
        # Accéder aux résultats
        print(result['pieces'])  # Liste des pièces détectées
        print(result['game_state'])  # État du jeu complet
    """
    
    def __init__(self, board_corners=None, board_size=None, save_visualization_images=True):
        """
        Initialise le pipeline.
        
        Args:
            board_corners: Coins fixes personnalisés {code: (x, y)} (sinon chargés depuis calibration)
            board_size: Taille de l'image du plateau extrait
            save_visualization_images: Sauvegarder les images de visualisation (False = uniquement JSON)
        """
        self.detector = ArucoDetector()
        self.extractor = BoardExtractor(board_corners=board_corners, board_size=board_size)
        self.analyzer = PieceAnalyzer(board_size=board_size)
        self.state_generator = GameStateGenerator()
        self.save_visualization_images = save_visualization_images
    
    def analyze_image(
        self,
        image_path: str,
        save_outputs: bool = True,
        output_dir=None
    ) -> dict:
        """
        Analyse une image et retourne l'état du jeu.
        
        Args:
            image_path: Chemin vers l'image à analyser
            save_outputs: Sauvegarder les images et JSONs intermédiaires
            output_dir: Dossier de sortie (auto-généré si None)
            
        Returns:
            Dict avec tous les résultats de l'analyse
        """
        import cv2
        import os
        from datetime import datetime
        
        # Charger l'image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Impossible de charger: {image_path}")
        
        return self._process_image(image, save_outputs, output_dir)
    
    def capture_and_analyze(
        self,
        save_outputs: bool = True,
        output_dir=None
    ) -> dict:
        """
        Capture une photo et l'analyse.
        
        Args:
            save_outputs: Sauvegarder les images et JSONs intermédiaires
            output_dir: Dossier de sortie (auto-généré si None)
            
        Returns:
            Dict avec tous les résultats de l'analyse
        """
        import cv2
        import os
        from datetime import datetime
        
        # Créer le dossier de sortie si nécessaire
        if output_dir is None:
            from .config import OUTPUT_DIR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(OUTPUT_DIR, f"analysis_{timestamp}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Capturer la photo directement dans le dossier de sortie
        photo_path = take_photo(output_dir=output_dir, filename="0_captured_photo.jpg")
        
        # Charger et analyser
        image = cv2.imread(photo_path)
        if image is None:
            raise ValueError(f"Impossible de charger la photo capturée: {photo_path}")
        
        result = self._process_image(image, save_outputs, output_dir)
        result['photo_path'] = photo_path
        
        return result
    
    def _process_image(
        self,
        image,
        save_outputs: bool,
        output_dir: str
    ) -> dict:
        """Traite une image numpy."""
        import cv2
        import os
        from datetime import datetime
        
        result = {
            'success': False,
            'board_corners': {},
            'pieces': [],
            'game_state': None,
            'board_image': None,
            'error': None,
        }
        
        # Créer le dossier de sortie si nécessaire
        if save_outputs:
            if output_dir is None:
                from .config import OUTPUT_DIR
                import shutil
                # Utiliser un dossier fixe 'latest' qui est écrasé à chaque fois
                output_dir = os.path.join(OUTPUT_DIR, "latest")
                # Créer le dossier s'il n'existe pas
                os.makedirs(output_dir, exist_ok=True)
                # Nettoyer le contenu (mais garder le dossier pour éviter crash explorateur)
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception:
                        pass  # Ignorer les erreurs de suppression
            else:
                os.makedirs(output_dir, exist_ok=True)
            result['output_dir'] = output_dir
        
        try:
            # 1. Vérifier la calibration
            if not self.extractor.is_calibrated:
                result['error'] = (
                    "Pas de calibration disponible!\n"
                    "Lancez: python -m chess_vision.calibrate_board"
                )
                return result
            
            # 2. Récupérer les coins fixes du plateau
            board_corners = self.extractor.get_corners()
            result['board_corners'] = board_corners
            
            # 3. Extraire le plateau (transformation perspective)
            board_img, transform_matrix = self.extractor.extract(image)
            
            if board_img is None:
                result['error'] = "Échec de l'extraction du plateau"
                return result
            
            result['board_image'] = board_img
            result['transform_matrix'] = transform_matrix
            
            # 4. Analyser les pièces
            # Détection sur l'image originale (ArUcos nets) + projection des coordonnées
            pieces = self.analyzer.analyze_pieces(
                board_img,
                transform_matrix=transform_matrix,
                original_img=image
            )
            result['pieces'] = pieces
            
            # 5. Générer l'état du jeu
            game_state = self.state_generator.generate_full_state(pieces)
            result['game_state'] = game_state
            
            result['board_state'] = self.state_generator.generate_board_state(pieces)
            result['robot_coordinates'] = self.state_generator.generate_robot_coordinates(pieces)
            
            # 6. Sauvegarder les JSONs en priorité (pour rapidité)
            if save_outputs and output_dir:
                # Sauvegarder d'abord les JSONs (essentiel)
                self.state_generator.save_all(pieces, output_dir)
                result['files_saved'] = True
            
            result['success'] = True
            
            # 7. Générer et sauvegarder les images de visualisation APRÈS le succès
            # (non-bloquant pour les performances)
            if save_outputs and output_dir and self.save_visualization_images:
                try:
                    # Image originale
                    cv2.imwrite(os.path.join(output_dir, "1_original.jpg"), image)
                    
                    # Visualisation des coins du plateau
                    viz = draw_board_visualization(image, board_corners)
                    cv2.imwrite(os.path.join(output_dir, "2_calibration.jpg"), viz)
                    
                    # Plateau extrait
                    cv2.imwrite(os.path.join(output_dir, "3_board.jpg"), board_img)
                    
                    # Plateau avec grille
                    board_grid = draw_chess_grid(board_img)
                    cv2.imwrite(os.path.join(output_dir, "4_board_grid.jpg"), board_grid)
                    
                    # Pièces détectées
                    if pieces:
                        pieces_img = draw_pieces_on_board(board_grid, pieces)
                        cv2.imwrite(os.path.join(output_dir, "5_pieces.jpg"), pieces_img)
                        
                        aruco_img = draw_pieces_aruco(board_img, pieces)
                        cv2.imwrite(os.path.join(output_dir, "6_aruco.jpg"), aruco_img)
                except Exception as e:
                    # Ne pas bloquer si les visualisations échouent
                    print(f"⚠️  Avertissement: échec génération images ({e})")
            
        except Exception as e:
            result['error'] = str(e)
            import traceback
            result['traceback'] = traceback.format_exc()
        
        return result


# Fonction simplifiée tout-en-un
def chess_vision():
    """
    Fonction tout-en-un : photo → analyse → JSON.
    Aucune interaction utilisateur requise.
    
    Prend une photo en direct, l'analyse et génère tous les JSON.
    Vérifie automatiquement la présence du fichier board_calibration.json.
    
    Returns:
        dict avec:
            - success (bool): True si réussi
            - error (str): Message d'erreur si échec
            - pieces (list): Liste des pièces détectées
            - game_state (dict): État complet du jeu
            - board_state (dict): État du plateau (a1-h8)
            - robot_coordinates (dict): Coordonnées pour le robot
            - output_dir (str): Dossier où sont sauvegardés les fichiers
            - photo_path (str): Chemin de la photo capturée
    
    Usage:
        from chess_vision import chess_vision
        
        result = chess_vision()
        
        if result['success']:
            print("✅ Analyse terminée")
            print(f"Pièces: {len(result['pieces'])}")
        else:
            print(f"❌ {result['error']}")
    """
    pipeline = ChessVisionPipeline()
    
    # Vérifier la calibration AVANT de prendre la photo
    if not pipeline.extractor.is_calibrated:
        return {
            'success': False,
            'error': (
                "❌ Fichier board_calibration.json manquant!\n"
                "Lancez: python -m chess_vision.modules.calibrate_board"
            ),
            'pieces': [],
            'game_state': None,
        }
    
    # Tout automatique : photo + analyse + JSON
    result = pipeline.capture_and_analyze()
    
    return result


__all__ = [
    # Config
    'OFFSETS',
    'FIXED_BOARD_CORNERS',
    'CALIBRATION_FILE',
    'EXTRACTED_BOARD_SIZE',
    'BOARD_COORD_MIN',
    'BOARD_COORD_MAX',
    'EXTENDED_COORD_MIN',
    'EXTENDED_COORD_MAX',
    'GRID_SIZE',
    'CHESS_GRID_SIZE',
    'GRID_COLUMNS',
    'GRID_ROWS',
    'CEMETERY_FILL_ORDER',
    'PIECES',
    'CALIBRATION_IDS',
    'get_piece_info',
    'get_calibration_code',
    'load_board_corners',
    
    # ArUco
    'ArucoDetector',
    'detect_piece_markers',
    'get_detection_summary',
    
    # Board
    'BoardExtractor',
    'draw_chess_grid',
    'draw_board_visualization',
    'get_cell_bounds',
    
    # Pieces
    'PieceAnalyzer',
    'draw_pieces_on_board',
    'draw_pieces_aruco',
    'get_pieces_summary',
    
    # Game State
    'GameStateGenerator',
    'load_game_state',
    'compare_states',
    'format_move',
    
    # Camera
    'take_photo',
    'get_camera_mode',
    
    # Pipeline
    'ChessVisionPipeline',
    
    # Fonction simplifiée
    'chess_vision',
]
