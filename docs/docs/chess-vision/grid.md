---
id: grid
title: Détection de la grille
sidebar_position: 2
---

# Détection de la grille

La grille 10×10 est définie par une calibration manuelle : l'utilisateur clique sur les quatre coins du plateau depuis l'interface de calibration. Ces coordonnées sont ensuite utilisées pour calculer une transformation de perspective appliquée à chaque frame de la caméra.

## Calibration manuelle des coins

### Processus

1. **Capture d'une photo** — l'utilisateur déclenche `POST /camera/capture` depuis l'écran de calibration, qui retourne l'image en base64.
2. **Clic sur les 4 coins** — l'utilisateur clique sur le canvas dans l'ordre suivant :

```
TL (A8)    TR (H8)
   ┌─────────────┐
   │             │
   │   échiquier │
   │             │
   └─────────────┘
BL (A1)    BR (H1)
```

3. **Aperçu temps réel** — dès que les 4 coins sont placés, le frontend superpose la grille 10×10 sur l'image via interpolation bilinéaire.
4. **Sauvegarde** — `POST /camera/calibrate/save` envoie les coordonnées au backend.

### Coordonnées transmises

```json
{
  "corners": {
    "TL": { "x": 312, "y": 148 },
    "TR": { "x": 987, "y": 152 },
    "BR": { "x": 991, "y": 831 },
    "BL": { "x": 308, "y": 827 }
  },
  "source_image": "/tmp/capture_xxx.jpg"
}
```

Les coordonnées sont en pixels dans l'image originale (avant mise à l'échelle d'affichage).

## Transformation perspective

À partir des 4 coins cliqués, le backend calcule une matrice d'homographie qui redresse le plateau en une image carrée de 1000×1000 px :

```python
size = EXTRACTED_BOARD_SIZE   # 1000 px
inner = size // GRID_SIZE     # 100 px (1 cellule = 100 px)

src_points = np.float32([
    [TL.x, TL.y],  # coin haut-gauche (a8)
    [TR.x, TR.y],  # coin haut-droit  (h8)
    [BR.x, BR.y],  # coin bas-droit   (h1)
    [BL.x, BL.y],  # coin bas-gauche  (a1)
])

# L'échiquier 8×8 occupe les cellules 1-8 de la grille 10×10.
# La cellule 0 et la cellule 9 forment la bordure cimetière.
dst_points = np.float32([
    [inner,            inner           ],   # → A8
    [size - 1 - inner, inner           ],   # → H8
    [size - 1 - inner, size - 1 - inner],   # → H1
    [inner,            size - 1 - inner],   # → A1
])

M = cv2.getPerspectiveTransform(src_points, dst_points)
board_img = cv2.warpPerspective(image, M, (size, size))
```

La matrice `M` est calculée une seule fois lors de la calibration et réutilisée pour toutes les frames suivantes.

### Persistance

Les coins sont sauvegardés dans `board_calibration.json` et rechargés au démarrage du backend via `FIXED_BOARD_CORNERS = load_board_corners()`. Après une nouvelle calibration, le pipeline de vision est réinitialisé automatiquement.

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

La détection ArUco des pièces est sensible aux conditions d'éclairage. Paramètres recommandés :

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
- La grille 10×10 superposée sur le plateau redressé
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
