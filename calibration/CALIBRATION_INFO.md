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
y_repere = +10 - (pixel_y / 800) * 20  # Inversion Y pour repère math
```

**Mapping validé (tests réels):**
```
        Y+ (vers robot)
              ^
              |
TL(-10,+10) -------- TR(+10,+10)
    |                  |
    |      (0,0)       |
    |     centre       |
BL(-10,-10) -------- BR(+10,-10)
              |
              v
        Y- (vers joueur)
```

**Convention:** Repère mathématique standard
- X augmente vers la droite
- Y augmente vers le robot (haut)
- Centre plateau = (0, 0)

## Correspondance axes robot ↔ vision (VALIDÉ)

**Tests effectués avec `test_axes_observation.py`:**

- +X robot → X- plateau (gauche) → **axes X inversés**
- +Y robot → Y- plateau (vers joueur) → **axes Y inversés**

**Formule de correction dans `calibrate_robot.py`:**
```python
# Pour aller de (x,y) vers (0,0)
error_x = 0 - x
error_y = 0 - y

# Conversion vers commandes robot (axes inversés)
delta_x_robot = -error_x * SCALE_FACTOR
delta_y_robot = -error_y * SCALE_FACTOR
```

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
