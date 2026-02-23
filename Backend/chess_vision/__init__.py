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
            output_dir: Dossier de sortie (si None, utilise 'latest' avec remplacement atomique via symlink)
            
        Returns:
            Dict avec tous les résultats de l'analyse
        """
        import cv2
        import os
        import shutil
        from datetime import datetime
        from .config import OUTPUT_DIR
        
        # Flag pour savoir si on doit faire le remplacement atomique
        use_atomic_replace = False
        latest_symlink = None
        
        # Si output_dir est None, utiliser le système de symlink avec ping-pong data_1/data_2
        if output_dir is None:
            use_atomic_replace = True
            latest_symlink = os.path.join(OUTPUT_DIR, "latest")
            
            # Déterminer quel dossier data utiliser (ping-pong entre data_1 et data_2)
            data_1 = os.path.join(OUTPUT_DIR, "data_1")
            data_2 = os.path.join(OUTPUT_DIR, "data_2")
            
            # Si latest est un symlink, voir vers quoi il pointe
            if os.path.islink(latest_symlink):
                current_target = os.readlink(latest_symlink)
                # Utiliser l'autre dossier
                if "data_1" in current_target:
                    output_dir = data_2
                    old_data_dir = data_1
                else:
                    output_dir = data_1
                    old_data_dir = data_2
            else:
                # Première fois : utiliser data_1
                output_dir = data_1
                old_data_dir = data_2
                # Si latest existe mais n'est pas un symlink, le supprimer
                if os.path.exists(latest_symlink):
                    if os.path.isdir(latest_symlink):
                        shutil.rmtree(latest_symlink)
                    else:
                        os.remove(latest_symlink)
            
            # Nettoyer le dossier de destination
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
        else:
            os.makedirs(output_dir, exist_ok=True)
            old_data_dir = None
        
        # Capturer la photo directement dans le dossier de sortie
        photo_path = take_photo(output_dir=output_dir, filename="0_captured_photo.jpg")
        
        # Charger et analyser
        image = cv2.imread(photo_path)
        if image is None:
            raise ValueError(f"Impossible de charger la photo capturée: {photo_path}")
        
        # Traiter l'image
        result = self._process_image(image, save_outputs, output_dir)
        result['photo_path'] = photo_path
        
        # Remplacement atomique via symlink : si tout s'est bien passé
        if use_atomic_replace and result.get('success'):
            try:
                # Créer un nouveau symlink temporaire pointant vers le nouveau dossier data
                latest_new = os.path.join(OUTPUT_DIR, "latest.new")
                
                # Supprimer latest.new s'il existe
                if os.path.exists(latest_new):
                    os.remove(latest_new)
                
                # Créer le symlink latest.new → data_X (chemin absolu)
                os.symlink(os.path.abspath(output_dir), latest_new)
                
                # Remplacement ATOMIQUE du symlink (os.replace sur symlink = atomique)
                os.replace(latest_new, latest_symlink)
                
                # Mettre à jour le résultat pour pointer vers latest (symlink)
                result['output_dir'] = latest_symlink
                
                # NE PAS supprimer l'ancien dossier data ici.
                # Il sera écrasé au prochain cycle (shutil.rmtree au début).
                # Garder les 2 dossiers permet à l'explorateur de fichiers
                # et aux lecteurs externes de ne pas perdre leur référence.
                    
            except Exception as e:
                result['atomic_replace_error'] = str(e)
                # Pas grave, les données sont dans data_X
        
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
                # Mode standalone : utiliser un dossier temporaire
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(OUTPUT_DIR, f"analysis_{timestamp}.tmp")
                os.makedirs(output_dir, exist_ok=True)
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
            # Recadrage ROI : on ne fait tourner la détection ArUco que sur la zone
            # du plateau (+ marge), pas sur l'image complète haute résolution.
            # Cela réduit la surface analysée et accélère significativement la détection.
            roi_img = image
            roi_offset = (0, 0)
            if board_corners:
                xs = [c[0] for c in board_corners.values()]
                ys = [c[1] for c in board_corners.values()]
                margin = 60  # pixels de marge autour du plateau
                x_min = max(0, int(min(xs)) - margin)
                y_min = max(0, int(min(ys)) - margin)
                x_max = min(image.shape[1], int(max(xs)) + margin)
                y_max = min(image.shape[0], int(max(ys)) + margin)
                roi_img = image[y_min:y_max, x_min:x_max]
                roi_offset = (x_min, y_min)

            pieces = self.analyzer.analyze_pieces(
                board_img,
                transform_matrix=transform_matrix,
                original_img=roi_img,
                roi_offset=roi_offset,
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
    # Désactiver la génération d'images pour maximiser la vitesse
    # Seul le JSON game_state.json sera généré
    pipeline = ChessVisionPipeline(save_visualization_images=False)
    
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
