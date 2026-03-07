---
id: grid
title: Détection de la grille
sidebar_position: 2
---

# Détection de la grille

La grille 10×10 est détectée à partir des marqueurs ArUco placés aux coins de l'échiquier.

## Marqueurs de coin

Quatre marqueurs ArUco spéciaux (IDs 40-43 par convention) sont placés aux coins de l'échiquier physique :

```
ID=40  ID=41
   ┌─────────┐
   │         │
   │         │
   └─────────┘
ID=43  ID=42
```

Ces marqueurs permettent de calculer la transformation de perspective.

## Transformation perspective

```python
# Coordonnées des marqueurs de coin dans l'image
src_points = np.float32([
    corner_tl,   # coin haut-gauche (a8)
    corner_tr,   # coin haut-droit (h8)
    corner_br,   # coin bas-droit (h1)
    corner_bl,   # coin bas-gauche (a1)
])

# Coordonnées normalisées de destination
dst_points = np.float32([
    [0, 0],
    [GRID_SIZE, 0],
    [GRID_SIZE, GRID_SIZE],
    [0, GRID_SIZE],
])

M = cv2.getPerspectiveTransform(src_points, dst_points)
```

Une fois la matrice `M` calculée, chaque marqueur de pièce peut être localisé sur la grille normalisée.

## Mapping grille → case

```python
def grid_pos_to_square(col: int, row: int) -> str:
    """
    Grille 10x10:
    - col 1-8 → colonnes a-h
    - row 1-8 → rangées 1-8
    - col 0, row 0 → cimetière
    """
    if col == 0 or col == 9 or row == 0 or row == 9:
        # Case de cimetière
        return f"{chr(ord('A') + col)}{row}"  # ex: "A0", "B9"
    else:
        # Case d'échecs
        file = chr(ord('a') + col - 1)  # 1→a, 2→b, ...
        rank = row                        # 1→1, 2→2, ...
        return f"{file}{rank}"            # ex: "e4"
```

## Tolérance et robustesse

### Marqueurs partiellement visibles

Si un marqueur est partiellement hors-champ ou obscurci, le pipeline peut quand même fonctionner avec 3 coins sur 4 en utilisant une homographie partielle.

### Stabilisation temporelle

L'état de la grille est moyenné sur plusieurs frames pour réduire le bruit :

```python
# Buffer de stabilisation
STABILITY_FRAMES = 3

# Un changement n'est validé que s'il est stable sur N frames consécutives
if all(frame[square] == new_state for frame in recent_frames[-STABILITY_FRAMES:]):
    validated_state[square] = new_state
```

## Contraste et éclairage

La détection ArUco est sensible aux conditions d'éclairage. Paramètres recommandés :

```python
# chess_vision/config.py
CAMERA_CONTRAST = None       # Contraste par défaut
CAMERA_SATURATION = None     # Saturation par défaut (pas 0 = pas niveaux de gris)
CAMERA_BRIGHTNESS = None     # Luminosité par défaut
```

:::warning Saturation
Ne pas définir `saturation = 0` : cela rend l'image en niveaux de gris, ce qui empêche la distinction des pièces blanches et noires.
:::

## Debugging

Pour visualiser la grille détectée en temps réel :

```http
GET /vision/debug-frame
```

Retourne une image JPEG avec :
- Les marqueurs ArUco encadrés
- La grille 10×10 superposée
- Les IDs des pièces détectées sur chaque case

```http
GET /vision/board-state
```

Retourne l'état JSON actuel de la grille :
```json
{
  "e2": "WP",
  "e4": "WP",
  "d7": "BP",
  ...
}
```
