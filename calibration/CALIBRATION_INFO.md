# Calibration - Informations essentielles

## ArUco IDs plateau

```
Côté ROBOT:
  32 (TL) -------- 33 (TR)
     |              |
     |   PLATEAU    |
     |              |
  34 (BL) -------- 35 (BR)
Côté JOUEUR
```

- **32** = Top Left (haut-gauche, côté robot)
- **33** = Top Right (haut-droite, côté robot)
- **34** = Bottom Left (bas-gauche, côté joueur)
- **35** = Bottom Right (bas-droite, côté joueur)
- **36** = ArUco sur robot (end-effector)

## Repère vision (-10/+10)

Extraction plateau → image 800x800 pixels → conversion repère:
```python
x_repere = -10 + (pixel_x / 800) * 20
y_repere = -10 + (pixel_y / 800) * 20
```

**Mapping actuel:**
```
(-10,-10) -------- (+10,-10)
   TL                 TR
    |                  |
    |                  |
   BL                 BR
(-10,+10) -------- (+10,+10)
```

**Centre plateau** = (0, 0) dans le repère

## TODO - Correspondance axes robot ↔ vision

**À déterminer avec `test_axes_correspondance.py`:**

- +X robot (mètres) → ? en (x,y) vision
- +Y robot (mètres) → ? en (x,y) vision

**Une fois connu, formule à corriger dans `calibrate_robot.py`:**
```python
# Ligne ~436-437
delta_x_robot = error_x * SCALE_FACTOR  # À ajuster
delta_y_robot = error_y * SCALE_FACTOR  # À ajuster
```

Peut nécessiter:
- Inversion d'axe (multiplier par -1)
- Permutation (X vision → Y robot)
- Facteur d'échelle différent

## Paramètres actuels

- `SCALE_FACTOR = 0.02` m/unité (1 unité repère = 2cm)
- `TOLERANCE = 0.1` (±0.1 unité autour de 0,0)
- `VITESSE = 0.05` m/s
- `ACCELERATION = 0.2` m/s²
- Robot: UR5e @ 192.168.0.11

## Scripts de test

- **`test_mouvement.py`**: Test basique robot bouge +10mm en X
- **`test_axes_correspondance.py`**: Détermine mapping robot ↔ vision (TODO #3)
- **`calibrate_robot.py`**: Calibration automatique (nécessite mapping correct)
