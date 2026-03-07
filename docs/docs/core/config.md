---
id: config
title: Configuration
sidebar_position: 4
---

# Configuration

**Fichier :** `Backend/manipulation_robot/config.py`

Ce fichier centralise tous les paramètres du système : positions robot, dimensions échiquier, hauteurs des pièces, niveaux de difficulté.

## Positions du robot

### Position HOME

```python
HOME_POSITION = [x, y, z, rx, ry, rz]  # coordonnées en m, angles en rad
```

Position de repos entre deux coups. Le robot revient toujours ici après avoir posé ou pris une pièce.

### Origine de l'échiquier

```python
BOARD_ORIGIN = [x, y, z, rx, ry, rz]  # coin a1 de l'échiquier
CASE_SIZE = 0.055  # taille d'une case en mètres (55mm)
```

### Hauteurs Z

```python
Z_APPROCHE = -0.080   # hauteur de déplacement au-dessus de l'échiquier
Z_DEPOSE   = -0.150   # hauteur de pose (posée sur le plateau)
```

### Hauteurs par type de pièce

```python
HAUTEUR_PIECES = {
    chess.PAWN:   -0.150,
    chess.ROOK:   -0.145,
    chess.KNIGHT: -0.148,
    chess.BISHOP: -0.148,
    chess.QUEEN:  -0.140,
    chess.KING:   -0.140,
}
```

Ces hauteurs compensent la taille physique de chaque pièce pour que la pince saisisse toujours au même endroit relatif.

## Cimetière

```python
CIMETIERE_BLANCS = ["a0", "b0", "c0", "d0", "e0", "f0", "g0", "h0"]
CIMETIERE_NOIRS  = ["a9", "b9", "c9", "d9", "e9", "f9", "g9", "h9"]
```

Zones où sont déposées les pièces capturées. La première case libre est utilisée en priorité.

## Niveaux de difficulté

```python
DIFFICULTY_PRESETS = {
    "beginner": {
        "skill_level": 5,    # Stockfish skill level (0-20)
        "depth": 5,          # profondeur de recherche
        "time_limit": 0.5,   # temps max en secondes
    },
    "intermediate": {
        "skill_level": 12,
        "depth": 12,
        "time_limit": 1.0,
    },
    "advanced": {
        "skill_level": 20,
        "depth": 20,
        "time_limit": 2.0,
    },
}
```

| Paramètre | Plage | Effet |
|-----------|-------|-------|
| `skill_level` | 0–20 | Qualité des coups Stockfish (0=aléatoire, 20=meilleur) |
| `depth` | 1–∞ | Nombre de demi-coups analysés |
| `time_limit` | >0 | Temps maximum de calcul (s) |

## Pince Robotiq

```python
GRIPPER_OPEN_POSITION  = 0    # complètement ouvert
GRIPPER_CLOSE_PAWN     = 180  # fermeture pour un pion
GRIPPER_CLOSE_ROOK     = 200  # fermeture pour une tour
GRIPPER_CLOSE_DEFAULT  = 190  # fermeture par défaut

GRIPPER_SPEED = 150
GRIPPER_FORCE = 50
```

## Vitesses robot

```python
ROBOT_SPEED        = 0.3   # m/s — vitesse de déplacement
ROBOT_ACCELERATION = 0.5   # m/s² — accélération
ROBOT_SPEED_SLOW   = 0.1   # m/s — vitesse lente (approche d'une pièce)
```

## Paramètres de connexion

```python
ROBOT_IP = "192.168.1.100"   # adresse IP du UR5e sur le réseau local
```

## Fichier de données leaderboard

```python
LEADERBOARD_FILE = "leaderboard.json"   # chemin relatif au répertoire backend
```
