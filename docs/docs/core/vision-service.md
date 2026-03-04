---
id: vision-service
title: VisionService
sidebar_position: 3
---

# VisionService

**Fichier :** `Backend/manipulation_robot/api.py` + `Backend/chess_vision/`

Le `VisionService` est responsable de la détection des coups humains via la caméra et les marqueurs ArUco.

## Pipeline de vision

```
Caméra (rpicam-still)
    │
    ▼
Capture image (JPEG)
    │
    ▼
chess_vision.process_frame(image)
    │ détection ArUco → grille 10×10
    ▼
compare_with_reference(current, reference)
    │
    ├─ appeared: cases nouvellement occupées
    ├─ disappeared: cases libérées
    └─ changed: cases dont la pièce a changé
    │
    ▼
[Si game_started] sync_with_vision(appeared, disappeared)
    │
    ▼
update reference_board
```

## Grille 10×10

L'échiquier physique est représenté comme une grille **10×10** :
- Cases `a1`–`h8` : les 64 cases d'échecs classiques
- Colonne 0 (`a0`–`j0`) : cimetière des blancs
- Colonne 9 (`a9`–`j9`) : cimetière des noirs
- Lignes 0 et 9 : zones tampon

```
   0  1  2  3  4  5  6  7  8  9
0  ██ ░░ ░░ ░░ ░░ ░░ ░░ ░░ ░░ ██  ← cimetière blancs
1  ██ a1 b1 c1 d1 e1 f1 g1 h1 ██
2  ██ a2 b2 c2 d2 e2 f2 g2 h2 ██
...
8  ██ a8 b8 c8 d8 e8 f8 g8 h8 ██
9  ██ ░░ ░░ ░░ ░░ ░░ ░░ ░░ ░░ ██  ← cimetière noirs
```

## Codes de pièces

Chaque case occupée est identifiée par un code 2 caractères :

| Code | Pièce |
|------|-------|
| `WP` | Pion blanc |
| `WR` | Tour blanche |
| `WN` | Cavalier blanc |
| `WB` | Fou blanc |
| `WQ` | Reine blanche |
| `WK` | Roi blanc |
| `BP` | Pion noir |
| `BR` | Tour noire |
| `BN` | Cavalier noir |
| `BB` | Fou noir |
| `BQ` | Reine noire |
| `BK` | Roi noir |

## Stabilisation

Pour éviter les faux positifs (vibrations, reflets), un **buffer de 3 frames** est utilisé. Un changement n'est validé que s'il est stable sur 3 captures consécutives.

## Configuration ArUco

Les paramètres de détection ArUco sont dans `Backend/chess_vision/config.py` :

```python
aruco_params = cv2.aruco.DetectorParameters()
aruco_params.adaptiveThreshWinSizeMin = 5
aruco_params.adaptiveThreshWinSizeMax = 51
aruco_params.adaptiveThreshWinSizeStep = 6
aruco_params.adaptiveThreshConstant = 15
```

:::warning Valeurs critiques
`adaptiveThreshWinSizeMin` doit être **strictement inférieur** à `adaptiveThreshWinSizeMax`. Si `Min > Max`, OpenCV retourne silencieusement zéro marqueur — aucun coup ne sera jamais détecté.
:::

## Contrôle du service

```python
# Démarrer la boucle de vision
vision_service.game_started = True

# Arrêter la détection (sans arrêter la capture)
vision_service.game_started = False

# Arrêter complètement le service
await vision_service.stop()
```

## `update_reference_after_move(board_state)`

Appelé après chaque coup robot pour mettre à jour l'état de référence. Cela évite que le robot déclenche un nouveau coup en "voyant" sa propre action.

```python
vision_service.update_reference_after_move(current_board_state)
```

## Caméra Raspberry Pi

La caméra est commandée via `rpicam-still` en ligne de commande :

```python
cmd = [
    "rpicam-still",
    "-o", "/tmp/chess_capture.jpg",
    "--width", "2304",
    "--height", "1296",
    "--timeout", "100",
    "--saturation", "1.0",
]
subprocess.run(cmd, capture_output=True)
```

:::note Paramètre saturation
`saturation: None` = saturation par défaut (couleur normale). `saturation: 0` = image en niveaux de gris, ce qui empêche la détection couleur des pièces.
:::
