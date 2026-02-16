# Chess Vision - Suite de Tests 🧪

Suite de tests complète pour le module `chess_vision` avec génération d'images de debug à chaque étape.

## Structure

```
chess_vision/tests/
├── __init__.py               # Package init
├── test_utils.py             # Utilitaires (logger, saver, helpers)
├── test_aruco_detection.py   # Test détection ArUco
├── test_board_calibration.py # Test calibration plateau
├── test_piece_analysis.py    # Test analyse des pièces
├── test_full_pipeline.py     # Test pipeline complet
├── run_all_tests.py          # Runner principal
├── output/                   # Résultats des tests (auto-généré)
└── images/                   # Images de test (optionnel)
```

## Installation

Les tests utilisent uniquement le code existant de `chess_vision`. Aucune dépendance supplémentaire n'est requise.

## Usage

### Avec une image existante

```bash
# Lancer tous les tests
python -m chess_vision.tests.run_all_tests --image photo.jpg

# Lancer un test spécifique
python -m chess_vision.tests.test_aruco_detection --image photo.jpg
python -m chess_vision.tests.test_board_calibration --image photo.jpg
python -m chess_vision.tests.test_piece_analysis --image photo.jpg
python -m chess_vision.tests.test_full_pipeline --image photo.jpg
```

### Avec capture photo en direct 📸

Sur Raspberry Pi avec la caméra :

```bash
# Lancer tous les tests avec capture photo
python -m chess_vision.tests.run_all_tests --photo

# Lancer un test spécifique avec capture photo
python -m chess_vision.tests.test_aruco_detection --photo
python -m chess_vision.tests.test_board_calibration --photo
python -m chess_vision.tests.test_piece_analysis --photo
python -m chess_vision.tests.test_full_pipeline --photo
```

La photo sera automatiquement capturée avec la caméra (rpicam-still, Picamera2 ou OpenCV selon disponibilité) et sauvegardée dans `chess_vision/images/`.

### Mode interactif

```bash
python -m chess_vision.tests.run_all_tests --interactive
```

### Lister les tests disponibles

```bash
python -m chess_vision.tests.run_all_tests --list
```

## Tests disponibles

### 1. `test_aruco_detection` - Test Détection ArUco
Vérifie la détection de tous les marqueurs ArUco.

**Étapes testées:**
- Chargement de l'image
- Détection de tous les marqueurs
- Détection des marqueurs de calibration (IDs 32-35)
- Détection des marqueurs de pièces (IDs 0-31)
- Analyse des paramètres de détection
- Tests de qualité avec différents prétraitements (grayscale, CLAHE, etc.)

**Images générées:**
- `01_original_input.jpg` - Image source
- `02_all_markers_detected.jpg` - Tous les marqueurs
- `03_calibration_markers_detail.jpg` - Marqueurs de calibration
- `04_piece_markers_annotated.jpg` - Pièces annotées
- `05_detection_parameters.jpg` - Paramètres de détection
- `quality_*.jpg` - Tests de qualité avec différents filtres

### 2. `test_board_calibration` - Test Calibration Plateau
Vérifie le processus complet de calibration.

**Étapes testées:**
- Détection des marqueurs de calibration
- Visualisation des offsets
- Calcul des coins du plateau
- Transformation de perspective
- Extraction du plateau
- Dessin du grillage 8x8
- Système de coordonnées (-10/+10)
- Estimation des coins manquants

**Images générées:**
- `01_original_input.jpg` - Image source
- `02_calibration_markers_detected.jpg` - Marqueurs détectés
- `03_offsets_visualization.jpg` - **Visualisation des offsets**
- `04_calculated_corners.jpg` - Coins calculés
- `05_source_points_for_transform.jpg` - Points source
- `06_warped_result.jpg` - Résultat de la transformation
- `07_extracted_board.jpg` - Plateau extrait
- `08_board_with_simple_grid.jpg` - Grille simple
- `09_board_with_labeled_grid.jpg` - Grille avec labels
- `10_coordinate_system.jpg` - Système de coordonnées
- `11_complete_board_visualization.jpg` - Visualisation complète

### 3. `test_piece_analysis` - Test Analyse Pièces
Vérifie l'analyse des pièces et la conversion de coordonnées.

**Étapes testées:**
- Extraction du plateau
- Détection des pièces sur le plateau extrait
- Conversion pixel → coordonnées plateau (-10/+10)
- Conversion pixel → notation échecs (A1-H8)
- Identification des pièces (nom, couleur)
- Génération du mapping JSON

**Images générées:**
- `01_original_input.jpg` - Image source
- `02_extracted_board.jpg` - Plateau extrait
- `03_board_with_grid.jpg` - Plateau avec grille
- `04_piece_markers_raw.jpg` - Marqueurs bruts
- `05_pieces_analyzed_detailed.jpg` - **Pièces analysées en détail**
- `06_coordinate_conversion_demo.jpg` - **Démo conversion coordonnées**
- `07_pieces_by_color.jpg` - Pièces par couleur
- `08_chess_board_state.jpg` - État échiquier style classique
- `09_comparison.jpg` - Comparaison

### 4. `test_full_pipeline` - Test Pipeline Complet
Vérifie le pipeline complet de bout en bout.

**Étapes testées:**
- Initialisation du `ChessVisionPipeline`
- Analyse complète de l'image
- Vérification de la structure du résultat
- Génération du JSON final
- Métriques de performance

**Images générées:**
- `01_input_image.jpg` - Image source
- `02_board_extracted.jpg` - Plateau extrait
- `03_board_with_pieces_annotated.jpg` - Pièces annotées
- `04_full_debug_composite.jpg` - **Vue composite debug**
- `05_comparison.jpg` - Comparaison
- `game_state_full.json` - État de jeu complet

## Résultats des tests

Chaque test génère un dossier dans `chess_vision/tests/output/` avec:
- Un horodatage unique: `{test_name}_{YYYYMMDD_HHMMSS}/`
- Toutes les images de debug numérotées
- Un fichier `metadata.json` avec les métadonnées de chaque étape

### Exemple de sortie

```
output/
└── aruco_detection_20260206_143022/
    ├── 01_original_input.jpg
    ├── 02_all_markers_detected.jpg
    ├── 03_calibration_markers_detail.jpg
    ├── ...
    └── metadata.json
```

## Logger Coloré

Le système de log utilise des couleurs et emojis pour faciliter la lecture:

| Niveau | Emoji | Couleur | Usage |
|--------|-------|---------|-------|
| DEBUG | 🔍 | Gris | Détails techniques |
| INFO | ℹ️ | Cyan | Informations générales |
| STEP | ▶️ | Bleu | Étapes principales |
| SUCCESS | ✅ | Vert | Succès |
| WARNING | ⚠️ | Jaune | Avertissements |
| ERROR | ❌ | Rouge | Erreurs |
| RESULT | 📊 | Vert gras | Résultats clés |

## Débugger un problème

### Calibration échoue

1. Lancer le test de calibration:
```bash
python -m chess_vision.tests.test_board_calibration --image photo.jpg
```

2. Ouvrir le dossier `output/board_calibration_*/`

3. Vérifier dans l'ordre:
   - `02_calibration_markers_detected.jpg` → Les 4 marqueurs sont-ils détectés?
   - `03_offsets_visualization.jpg` → Les offsets sont-ils corrects?
   - `04_calculated_corners.jpg` → Les coins forment-ils un quadrilatère correct?

4. Si les offsets sont incorrects, modifier `chess_vision/config.py`:
```python
OFFSETS = {
    "TL": {"x": -70, "y": -155},  # Ajuster ces valeurs
    "TR": {"x": -96, "y": 47},
    "BL": {"x": 111, "y": -128},
    "BR": {"x": 87, "y": 57}
}
```

### Pièces mal positionnées

1. Lancer le test d'analyse des pièces:
```bash
python -m chess_vision.tests.test_piece_analysis --image photo.jpg
```

2. Vérifier:
   - `06_coordinate_conversion_demo.jpg` → Les conversions sont-elles logiques?
   - `piece_mapping.json` → Les cases correspondent-elles à la réalité?

### ArUcos non détectés

1. Lancer le test de détection avec tests de qualité:
```bash
python -m chess_vision.tests.test_aruco_detection --image photo.jpg
```

2. Comparer les images `quality_*.jpg` pour voir quelle méthode fonctionne le mieux

3. Ajuster les paramètres dans `chess_vision/config.py`:
```python
ARUCO_PARAMS = {
    'adaptiveThreshWinSizeMin': 3,
    'adaptiveThreshWinSizeMax': 23,
    # ... ajuster selon les résultats des tests
}
```

## Intégration avec le code principal

Les tests utilisent **exactement le même code** que le module principal. Si un test échoue:
1. Identifiez le problème avec les images de debug
2. Corrigez le code dans `chess_vision/`
3. Relancez le test pour valider

## Contributions

Pour ajouter un nouveau test:
1. Créer `test_mon_test.py` dans `chess_vision/tests/`
2. Implémenter une fonction `run_mon_test_test(image_path, verbose)`
3. Ajouter au dictionnaire `AVAILABLE_TESTS` dans `run_all_tests.py`

## Licence

Fait avec ❤️ pour le projet Chess Robot
