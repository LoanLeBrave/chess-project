# Mapping game_state.json → Affichage

## Flux de données

```
game_state.json
    ↓
board_reader.get_board_map()
    ↓
board_display.render_board()
    ↓
Terminal (ASCII)
```

## Étape 1 : Lecture du JSON (`board_reader.py`)

### Structure d'une pièce dans le JSON

```json
{
  "id": 0,
  "code": "WP1",
  "color": "white",
  "type": "Pawn",
  "zone": "board",          ← Seules les pièces avec zone="board" sont affichées
  "position": {
    "grid": "F2",           ← Position grid (non utilisée pour l'affichage)
    "chess": "f2",          ← Position utilisée pour l'affichage (notation algébrique)
    "board": {
      "x": 4.53,            ← Coordonnées caméra (mm)
      "y": -5.09
    },
    "pixel": {
      "x": 681.0,
      "y": 703.5
    }
  }
}
```

### Fonction `get_board_map()`

Construit un dictionnaire `{case: code_pièce}` :

```python
def get_board_map(game_state: dict) -> dict:
    board = {}
    for piece in game_state.get("pieces", []):
        # 1. Filtrer uniquement les pièces sur le plateau
        if piece.get("zone") != "board":
            continue
        
        # 2. Récupérer la position chess (ex: "f2")
        chess_pos = piece.get("position", {}).get("chess")
        if not chess_pos:
            continue
        
        # 3. Construire le code simplifié (ex: "WP" pour White Pawn)
        color_char = "W" if piece.get("color") == "white" else "B"
        type_char = piece.get("type", "Pawn")[0]  # P, K, Q, R, B
        if piece.get("type") == "Knight":
            type_char = "N"
        
        # 4. Stocker dans le dictionnaire
        board[chess_pos.lower()] = f"{color_char}{type_char}"
    
    return board
```

**Exemple de sortie** :
```python
{
    "f2": "WP",   # White Pawn en f2
    "h5": "WP",   # White Pawn en h5
    "c5": "BP",   # Black Pawn en c5
    "g6": "BN",   # Black Knight en g6
    # ...
}
```

## Étape 2 : Rendu ASCII (`board_display.py`)

### Orientation du plateau

```
    a   b   c   d   e   f   g   h
  +---+---+---+---+---+---+---+---+
8 | r | n | b | q | k | b | n | r | 8  ← Rang 8 (côté noir)
  +---+---+---+---+---+---+---+---+
7 | p | p | p | p | p | p | p | p | 7
  +---+---+---+---+---+---+---+---+
6 |   |   |   |   |   |   |   |   | 6
  +---+---+---+---+---+---+---+---+
5 |   |   |   |   |   |   |   |   | 5
  +---+---+---+---+---+---+---+---+
4 |   |   |   |   |   |   |   |   | 4
  +---+---+---+---+---+---+---+---+
3 |   |   |   |   |   |   |   |   | 3
  +---+---+---+---+---+---+---+---+
2 | P | P | P | P | P | P | P | P | 2
  +---+---+---+---+---+---+---+---+
1 | R | N | B | Q | K | B | N | R | 1  ← Rang 1 (côté blanc)
  +---+---+---+---+---+---+---+---+
    a   b   c   d   e   f   g   h
    ↑                           ↑
  colonne a                  colonne h
```

### Mapping des symboles (`config.py`)

```python
DISPLAY_SYMBOLS = {
    "WK": "K",  "WQ": "Q",  "WR": "R",  "WB": "B",  "WN": "N",  "WP": "P",  # Blancs (majuscules)
    "BK": "k",  "BQ": "q",  "BR": "r",  "BB": "b",  "BN": "n",  "BP": "p",  # Noirs (minuscules)
}
```

### Fonction `render_board()`

```python
def render_board(board_map: dict) -> str:
    for rank in range(8, 0, -1):  # De 8 à 1 (top → bottom)
        row = f"{rank} |"
        for col in "abcdefgh":     # De a à h (left → right)
            square = f"{col}{rank}"
            piece_code = board_map.get(square)
            symbol = DISPLAY_SYMBOLS.get(piece_code, " ")
            row += f" {symbol} |"
```

## Exemple concret

### JSON d'entrée

```json
{
  "pieces": [
    {"code": "WP1", "color": "white", "type": "Pawn", "zone": "board", "position": {"chess": "f2"}},
    {"code": "WP2", "color": "white", "type": "Pawn", "zone": "board", "position": {"chess": "h5"}},
    {"code": "BP3", "color": "black", "type": "Pawn", "zone": "board", "position": {"chess": "c5"}},
    {"code": "BN2", "color": "black", "type": "Knight", "zone": "board", "position": {"chess": "g6"}},
    {"code": "WP7", "zone": "cemetery", "position": {"chess": null}}
  ]
}
```

### Board map construit

```python
{
    "f2": "WP",
    "h5": "WP",
    "c5": "BP",
    "g6": "BN"
}
```

### Affichage résultant

```
    a   b   c   d   e   f   g   h
  +---+---+---+---+---+---+---+---+
8 |   |   |   |   |   |   |   |   | 8
  +---+---+---+---+---+---+---+---+
7 |   |   |   |   |   |   |   |   | 7
  +---+---+---+---+---+---+---+---+
6 |   |   |   |   |   |   | n |   | 6  ← BN en g6
  +---+---+---+---+---+---+---+---+
5 |   |   | p |   |   |   |   | P | 5  ← BP en c5, WP en h5
  +---+---+---+---+---+---+---+---+
4 |   |   |   |   |   |   |   |   | 4
  +---+---+---+---+---+---+---+---+
3 |   |   |   |   |   |   |   |   | 3
  +---+---+---+---+---+---+---+---+
2 |   |   |   |   |   | P |   |   | 2  ← WP en f2
  +---+---+---+---+---+---+---+---+
1 |   |   |   |   |   |   |   |   | 1
  +---+---+---+---+---+---+---+---+
    a   b   c   d   e   f   g   h
```

## Debugging : Pourquoi je ne vois pas la réalité ?

### Problème 1 : Calibration caméra incorrecte

**Symptôme** : Les pièces sont détectées aux mauvaises positions.

**Solution** : Recalibrer la caméra
```bash
cd Backend/chess_vision/
# Vérifier board_calibration.json
# Relancer la calibration si nécessaire
```

### Problème 2 : Orientation physique du plateau

**Symptôme** : Le plateau physique est tourné par rapport à ce qu'attend la vision.

**Vérification** : 
- La case **a1** doit être en bas à gauche (vue des blancs)
- La case **h8** doit être en haut à droite (vue des blancs)
- Les blancs sont en rang 1-2
- Les noirs sont en rang 7-8

### Problème 3 : Délai de mise à jour

**Symptôme** : L'affichage est en retard par rapport à la réalité.

**Cause** : `infinite_chess_vision.py` met à jour le JSON toutes les ~2 secondes.

**Vérification** : Regarder le `timestamp` dans les métadonnées.

### Outil de debug

Lancer le script de debug pour analyser en détail :

```bash
cd Backend/test_camera_robot/
python3 debug_display.py
```

Cela affichera :
- ✅ Toutes les pièces détectées avec leurs positions
- ✅ Le board_map construit
- ✅ L'affichage ASCII final
- ✅ Les pièces au cimetière
- ✅ Les pièces manquantes

## Checklist de vérification

```
□ infinite_chess_vision.py tourne en arrière-plan
□ game_state.json existe et est récent (timestamp < 5s)
□ Les positions "chess" dans le JSON correspondent à la réalité
□ L'orientation du plateau physique est correcte (a1 = bas-gauche)
□ La calibration caméra est à jour (board_calibration.json)
□ Le nombre de pièces détectées correspond au nombre réel
```

## Zones du JSON

```json
{
  "zone": "board"       → Affiché sur le plateau
  "zone": "cemetery"    → Affiché dans la zone des pièces éliminées (non visible dans ASCII)
  "zone": null          → Pièce non détectée
}
```

**Important** : Seules les pièces avec `zone="board"` sont affichées dans le rendu ASCII !
