---
id: movements
title: Mouvements
sidebar_position: 1
---

# Mouvements du robot UR7e

## Types de mouvements

Le robot UR7e utilise des mouvements **cartésiens linéaires** (`moveL`) pour tous ses déplacements. Cela garantit des trajectoires prévisibles au-dessus de l'échiquier.

### `moveL(position, speed, acceleration)`

```python
# Exemple: déplacement vers une position cartésienne
await loop.run_in_executor(
    None,
    self.rtde_c.moveL,
    [x, y, z, rx, ry, rz],  # pose (m + rad)
    ROBOT_SPEED,
    ROBOT_ACCELERATION
)
```

## Séquence de prise d'une pièce

```
Position HOME
    │
    ▼ moveL(case, z=Z_APPROCHE)   ← au-dessus de la pièce
    │
    ▼ gripper.open()               ← ouverture pince
    │
    ▼ moveL(case, z=HAUTEUR_PIECE) ← descente vers la pièce
    │
    ▼ gripper.close(force)         ← fermeture selon type pièce
    │
    ▼ moveL(case, z=Z_APPROCHE)   ← remontée
    │
    ▼ (déplacement vers destination)
```

## Séquence de pose d'une pièce

```
Au-dessus de la source
    │
    ▼ moveL(dest, z=Z_APPROCHE)    ← déplacement XY vers destination
    │
    ▼ moveL(dest, z=Z_DEPOSE)      ← descente
    │
    ▼ gripper.open()               ← relâchement
    │
    ▼ moveL(dest, z=Z_APPROCHE)    ← remontée
    │
    ▼ moveL(HOME_POSITION)         ← retour HOME
```

## Conversion cases → coordonnées

Les cases d'échecs (a1-h8) sont converties en coordonnées cartésiennes par interpolation linéaire :

```python
def _square_to_position(self, square: str) -> list:
    col = ord(square[0]) - ord('a')  # 0-7 pour a-h
    row = int(square[1]) - 1         # 0-7 pour 1-8

    x = BOARD_ORIGIN[0] + col * CASE_SIZE
    y = BOARD_ORIGIN[1] + row * CASE_SIZE
    z = Z_APPROCHE

    return [x, y, z, Rx, Ry, Rz]
```

## Paramètres de vitesse

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `ROBOT_SPEED` | 0.3 m/s | Vitesse déplacement XY |
| `ROBOT_SPEED_SLOW` | 0.1 m/s | Vitesse approche pièce |
| `ROBOT_ACCELERATION` | 0.5 m/s² | Accélération |

:::tip Performance
La vitesse est délibérément limitée pour les approches de pièces afin d'éviter de renverser les pièces voisines lors de l'approche.
:::

## Gestion de la collision Z

Pour éviter de frapper les pièces en déplacement horizontal, le robot monte toujours à `Z_APPROCHE` avant tout déplacement XY :

```
Hauteur Z pendant un coup:

Z_APPROCHE ─────┐         ┌──────────┐
                │         │          │
                └─────────┘          └──── Z_PIECE
                départ    destination  retour
```

## Position HOME

La position HOME est définie pour maximiser la visibilité de la caméra et être hors de la zone de jeu. Le robot revient à HOME :
- Avant chaque coup
- Après chaque coup
- Après le dépôt au cimetière

## Arrêt d'urgence

En cas d'urgence, le script URScript peut être arrêté via :

```python
await loop.run_in_executor(None, self.rtde_c.stopScript)
```

Cela arrête immédiatement tout mouvement en cours. La reprise nécessite un `reuploadScript()` pour relancer le programme URScript.
