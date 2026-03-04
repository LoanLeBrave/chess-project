---
id: aruco
title: Marqueurs ArUco
sidebar_position: 1
---

# Marqueurs ArUco

Les marqueurs ArUco sont des codes QR visuels utilisés pour identifier les pièces d'échecs et calibrer l'échiquier.

## Principe

Chaque pièce d'échecs porte un marqueur ArUco unique collé sur le dessus. La caméra détecte ces marqueurs et associe chaque ID de marqueur à un type de pièce.

```
┌─────────────────────┐
│   ID=1  → WP (pion blanc)
│   ID=2  → WP (pion blanc)
│   ...
│   ID=17 → BK (roi noir)
└─────────────────────┘
```

## Configuration de détection

**Fichier :** `Backend/chess_vision/config.py`

```python
import cv2

ARUCO_DICT = cv2.aruco.DICT_4X4_50  # dictionnaire 4x4, 50 marqueurs

aruco_params = cv2.aruco.DetectorParameters()
aruco_params.adaptiveThreshWinSizeMin = 5
aruco_params.adaptiveThreshWinSizeMax = 51
aruco_params.adaptiveThreshWinSizeStep = 6
aruco_params.adaptiveThreshConstant = 15
```

### Paramètres critiques

| Paramètre | Valeur | Rôle |
|-----------|--------|------|
| `adaptiveThreshWinSizeMin` | 5 | Taille minimale de fenêtre de seuillage adaptatif |
| `adaptiveThreshWinSizeMax` | 51 | Taille maximale |
| `adaptiveThreshWinSizeStep` | 6 | Pas d'incrémentation |
| `adaptiveThreshConstant` | 15 | Constante de seuillage |

:::danger Contrainte absolue
`adaptiveThreshWinSizeMin` **doit être strictement inférieur** à `adaptiveThreshWinSizeMax`. Si `Min ≥ Max`, OpenCV retourne silencieusement **zéro marqueur**. La vision semble fonctionner mais ne détecte rien.

Valeurs invalides : `Min=24, Max=10` → 0 marqueurs
Valeurs valides : `Min=5, Max=51` → détection normale
:::

## Détection

```python
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
corners, ids, rejected = detector.detectMarkers(gray_image)
```

**Résultat :**
- `corners` : liste de tableaux 4×2 (coins de chaque marqueur)
- `ids` : identifiants des marqueurs détectés
- `rejected` : marqueurs candidats rejetés

## Table de correspondance ID → pièce

```python
ID_TO_PIECE = {
    1:  "WP",   2:  "WP",   3:  "WP",   4:  "WP",
    5:  "WP",   6:  "WP",   7:  "WP",   8:  "WP",
    9:  "WR",   10: "WN",   11: "WB",   12: "WQ",
    13: "WK",   14: "WB",   15: "WN",   16: "WR",
    17: "BP",   18: "BP",   19: "BP",   20: "BP",
    21: "BP",   22: "BP",   23: "BP",   24: "BP",
    25: "BR",   26: "BN",   27: "BB",   28: "BQ",
    29: "BK",   30: "BB",   31: "BN",   32: "BR",
}
```

## Localisation sur la grille

Après détection, les centres des marqueurs sont mappés sur la grille 10×10 :

```python
def marker_to_square(cx, cy, grid_corners):
    # Transformation perspective depuis les 4 coins de l'échiquier
    M = cv2.getPerspectiveTransform(grid_corners, normalized_corners)
    col, row = apply_transform(M, cx, cy)
    return grid_to_square_name(col, row)
```

## Caméra

La caméra est montée en hauteur, perpendiculairement à l'échiquier. Les paramètres de capture :

```python
# rpicam-still
--width 2304 --height 1296
--timeout 100ms
```

La haute résolution est nécessaire pour détecter les marqueurs sur les petites pièces (pions).
