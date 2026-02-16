# Chess Vision 🎯♟️

Module de vision par ordinateur pour jeu d'échecs robotisé.

## 📁 Structure du Module

```
chess_vision/
├── __init__.py          # Module principal avec ChessVisionPipeline
├── config.py            # Configuration centralisée
├── aruco_detector.py    # Détection des marqueurs ArUco
├── board_extractor.py   # Extraction et transformation du plateau
├── piece_analyzer.py    # Analyse des pièces et coordonnées
├── game_state.py        # Génération des états de jeu JSON
├── camera.py            # Capture photo (Raspberry Pi / webcam)
└── main.py              # Script principal
```

## 🚀 Usage Rapide

### En ligne de commande

```bash
# Mode interactif
python -m chess_vision.main

# Prendre une photo et analyser
python -m chess_vision.main --photo

# Analyser une image existante
python -m chess_vision.main --image path/to/photo.jpg
```

### En Python

```python
from chess_vision import ChessVisionPipeline

# Créer le pipeline
pipeline = ChessVisionPipeline()

# Option 1: Analyser une image existante
result = pipeline.analyze_image("photo.jpg")

# Option 2: Capturer et analyser
result = pipeline.capture_and_analyze()

# Accéder aux résultats
if result['success']:
    print(f"Pièces détectées: {len(result['pieces'])}")
    
    # État du jeu complet
    game_state = result['game_state']
    pieces = game_state['pieces']
    
    # Filtrer par zone
    board_pieces = [p for p in pieces if p['zone'] == 'board']
    cemetery_pieces = [p for p in pieces if p['zone'] == 'cemetery']
    
    print(f"Sur plateau: {len(board_pieces)}, En cimetière: {len(cemetery_pieces)}")
    
    # Coordonnées pour le robot
    robot_coords = result['robot_coordinates']
    
    # État du plateau (notation échecs) et cimetière
    board_state = result['board_state']
    print(f"Cases occupées sur plateau: {len(board_state['board'])}")
    print(f"Cases occupées en cimetière: {len(board_state.get('cemetery', {}))}")
```

## 📐 Systèmes de Coordonnées

Le module utilise plusieurs systèmes de coordonnées :

### 1. Pixels (sur l'image du plateau extrait)
- `(0, 0)` = coin haut-gauche
- `(1000, 1000)` = coin bas-droite (grille 10x10)
- Échelle : 100px par case

### 2. Grille Étendue 10x10 (Board -12.5 / +12.5)
- **Plateau d'échecs 8x8** : de `(-10, -10)` à `(+10, +10)`
- **Zone cimetière** : colonnes externes et lignes externes de la grille 10x10
- Centre du plateau = `(0, 0)`
- Échelle : 2.5 unités par case

### 3. Notation Échecs (Plateau uniquement)
- `a1` à `h8` pour les cases du plateau
- Colonnes : a-h (gauche à droite)
- Rangées : 1-8 (bas vers haut)

### 4. Notation Cimetière
- `C1` à `C36` pour les cases du cimetière
- Ordre de remplissage : ligne du bas (gauche → droite), puis ligne du haut, puis colonnes latérales
- Colonnes disponibles : A, B, C, D, E, F, G, H, J, K (J = gauche cimetière, K = droite cimetière)
- Rangées disponibles : 0, 1-8, 9 (0 = bas cimetière, 9 = haut cimetière)

## �️ Architecture de la Grille 10x10

Le système utilise une grille étendue 10x10 qui englobe :

### Plateau d'Échecs (8x8 cases centrales)
- Zone de jeu principale : colonnes **A-H**, rangées **1-8**
- Coordonnées étendues : `(-10, -10)` à `(+10, +10)`
- Notation standard des échecs : `a1` à `h8`

### Zone Cimetière (36 cases périphériques)
- **Ligne du bas (rangée 0)** : A0, B0, C0, D0, E0, F0, G0, H0 → `C1` à `C8`
- **Ligne du haut (rangée 9)** : A9, B9, C9, D9, E9, F9, G9, H9 → `C9` à `C16`
- **Colonne gauche (J)** : J1 à J8 → `C17` à `C24`
- **Colonne droite (K)** : K1 à K8 → `C25` à `C32`
- **Coins** : J0, K0, J9, K9 → `C33` à `C36`

### Visualisation

```
     J  A  B  C  D  E  F  G  H  K
  9  C16 C9 C10 C11 C12 C13 C14 C15 C32
  8  C24 a8 b8 c8 d8 e8 f8 g8 h8 K8
  7  C23 a7 ...                  K7
  6  C22                          K6
  5  C21                          K5
  4  C20                          K4
  3  C19                          K3
  2  C18                          K2
  1  C17 a1 b1 c1 d1 e1 f1 g1 h1 K1
  0  C33 C1 C2 C3 C4 C5 C6 C7 C8 C34
```

### Paramètres Clés (config.py)

```python
EXTRACTED_BOARD_SIZE = 1000      # Taille du plateau extrait (pixels)
GRID_SIZE = 10                   # Grille totale 10x10
CHESS_GRID_SIZE = 8              # Grille d'échecs 8x8 (central)
CELL_SIZE = 100                  # Pixels par case (1000/10)

# Limites des coordonnées étendues
EXTENDED_GRID_MIN = -12.5        # Limite min (incluant cimetière)
EXTENDED_GRID_MAX = 12.5         # Limite max (incluant cimetière)
CHESS_COORD_MIN = -10.0          # Limite min du plateau d'échecs
CHESS_COORD_MAX = 10.0           # Limite max du plateau d'échecs
```

## �🎯 Marqueurs ArUco

### IDs de Calibration (32-35)
- **32** : TL (Top-Left / Haut-Gauche)
- **33** : TR (Top-Right / Haut-Droite)
- **34** : BL (Bottom-Left / Bas-Gauche)
- **35** : BR (Bottom-Right / Bas-Droite)

### IDs des Pièces (0-31)
- **0-15** : Pièces blanches
- **16-31** : Pièces noires

## ⚙️ Configuration

### Offsets de Calibration

Les ArUcos de calibration sont placés à l'extérieur du plateau. Les offsets définissent la distance entre le centre de l'ArUco et le coin réel de la grille 10x10 (incluant le cimetière).

**Important** : Les 4 coins de calibration doivent englober toute la zone 10x10 (plateau d'échecs 8x8 + zone cimetière périphérique).

```python
# Dans config.py
OFFSETS = {
    "TL": {"x": -70, "y": -155},
    "TR": {"x": -96, "y": 47},
    "BL": {"x": 111, "y": -128},
    "BR": {"x": 87, "y": 57}
}
```

**Pour ajuster :**
- `x` positif → décale vers la droite
- `x` négatif → décale vers la gauche
- `y` positif → décale vers le bas
- `y` négatif → décale vers le haut

**Note** : Si vous migrez depuis un système 8x8, recalibrez les 4 coins pour couvrir la zone étendue incluant les marges du cimetière.

### Paramètres Caméra

```python
# Dans config.py
CAMERA_CONFIG = {
    'timeout': 2000,              # Stabilisation (ms)
    'autofocus_mode': 'manual',   # 'auto', 'manual', 'continuous'
    'lens_position': 7.0,         # Focus manuel (0.0-10.0)
    # ...
}
```

## 📄 Fichiers de Sortie

Après une analyse, le dossier `output/analysis_YYYYMMDD_HHMMSS/` contient :

| Fichier | Description |
|---------|-------------|
| `1_original.jpg` | Image originale |
| `2_calibration.jpg` | Visualisation des coins |
| `3_board.jpg` | Plateau extrait et redressé |
| `4_board_grid.jpg` | Plateau avec grille 10x10 (8x8 + cimetière) |
| `5_pieces.jpg` | Pièces avec coordonnées |
| `6_aruco.jpg` | ArUcos des pièces |
| `game_state.json` | État complet du jeu |
| `board_state.json` | État du plateau (A1-H8) |
| `coordinates.json` | Coordonnées robot |

### Format game_state.json

```json
{
  "pieces": [
    {
      "id": 0,
      "code": "WP1",
      "color": "white",
      "type": "Pawn",
      "zone": "board",
      "position": {
        "chess": "e2",
        "grid": "E2",
        "board": {"x": 2.5, "y": -7.5},
        "pixel": {"x": 450, "y": 700}
      }
    },
    {
      "id": 16,
      "code": "BP1",
      "color": "black",
      "type": "Pawn",
      "zone": "cemetery",
      "position": {
        "chess": null,
        "grid": "C5",
        "cemetery": "C5",
        "board": {"x": -10.0, "y": -12.5},
        "pixel": {"x": 100, "y": 900}
      }
    }
  ],
  "metadata": {
    "timestamp": "2026-02-13T...",
    "total_detected": 32,
    "white_count": 16,
    "black_count": 16,
    "on_board": 31,
    "in_cemetery": 1
  }
}
```

### Format board_state.json

```json
{
  "board": {
    "a8": "BR",
    "b8": "BN",
    "c8": "BB",
    "d8": "BQ",
    "e8": "BK",
    ...
    "e1": "WK",
    "h1": "WR"
  },
  "cemetery": {
    "C5": "BP",
    "C6": "WN"
  },
  "metadata": {
    "board_pieces": 30,
    "cemetery_pieces": 2
  }
}
```

### Format coordinates.json

```json
{
  "coordinates": [
    {"id": 0, "color": "white", "type": "Pawn", "x": 2.5, "y": -7.5, "chess": "e2", "zone": "board"},
    {"id": 15, "color": "white", "type": "King", "x": 2.5, "y": -10.0, "chess": "e1", "zone": "board"},
    {"id": 16, "color": "black", "type": "Pawn", "x": -10.0, "y": -12.5, "cemetery": "C5", "zone": "cemetery"}
  ],
  "metadata": {
    "coord_system": "extended_grid_-12.5_+12.5",
    "count": 32,
    "board_pieces": 31,
    "cemetery_pieces": 1
  }
}
```

## 🔧 Utilisation Modulaire

### Détection ArUco seule

```python
from chess_vision import ArucoDetector, detect_calibration_markers
import cv2

image = cv2.imread("photo.jpg")
detector = ArucoDetector()

# Tous les marqueurs
all_markers = detector.detect(image)

# Seulement calibration
calib_markers = detect_calibration_markers(image)
```

### Extraction du plateau seule

```python
from chess_vision import BoardExtractor

extractor = BoardExtractor()
board_corners, offset_lines = extractor.calculate_corners(calib_markers)
board_img, matrix = extractor.extract(image, board_corners)
```

### Analyse des pièces seule

```python
from chess_vision import PieceAnalyzer

analyzer = PieceAnalyzer()
pieces = analyzer.analyze_pieces(board_img)

# Conversion de coordonnées
pixel_pos = (450, 700)
board_pos = analyzer.pixel_to_board(pixel_pos)          # Ex: (2.5, -7.5)
chess_square = analyzer.pixel_to_chess_square(pixel_pos) # Ex: "e2"
grid_square = analyzer.pixel_to_grid(pixel_pos)          # Ex: "E2"

# Tester les zones
is_on_board = analyzer.is_on_board(board_pos)            # True si sur plateau 8x8
is_in_cemetery = analyzer.is_in_cemetery(board_pos)      # True si dans cimetière

# Obtenir la zone d'une position
zone = analyzer.get_zone(board_pos)                      # "board" ou "cemetery"

# Conversion inverse
board_to_pixel = analyzer.board_to_pixel(2.5, -7.5)      # Retour aux pixels
```

### Génération JSON seule

```python
from chess_vision import GameStateGenerator

generator = GameStateGenerator()
game_state = generator.generate_full_state(pieces)
board_state = generator.generate_board_state(pieces)
robot_coords = generator.generate_robot_coordinates(pieces)
```

## 🧪 Tests

```bash
# Tester la détection sur une image
python -m chess_vision.main --image test_image.jpg

# Vérifier le mode caméra disponible
python -c "from chess_vision import get_camera_mode; print(get_camera_mode())"
```

## 📦 Dépendances

- `opencv-python` (cv2)
- `numpy`

Pour Raspberry Pi :
- `rpicam-still` ou `libcamera-still` (recommandé)
- ou `picamera2` (alternative Python)

## 🔄 Migration depuis l'ancien code

| Ancien fichier | Nouveau module |
|----------------|----------------|
| `photo_analyse.py` | `aruco_detector.py` + `game_state.py` |
| `detect_board_corners.py` | `board_extractor.py` + `piece_analyzer.py` |
| `simple_detection.py` | Remplacé par `ChessVisionPipeline` |

Les offsets de `detect_board_corners.py` ont été conservés dans `config.py`.
