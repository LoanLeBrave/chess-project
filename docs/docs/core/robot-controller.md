---
id: robot-controller
title: RobotController
sidebar_position: 2
---

# RobotController

**Fichier :** `Backend/manipulation_robot/robot_controller.py`

Le `RobotController` encapsule toutes les interactions avec le bras robotique UR7e et la pince Robotiq.

## Connexion

```python
robot = RobotController(ip="192.168.1.100")
await robot.connect()      # établit la connexion RTDE
await robot.disconnect()   # ferme proprement
```

La connexion utilise un mécanisme de retry : **8 tentatives** avec un délai de **3 secondes** entre chaque, et un **timeout de 12 secondes** par tentative.

## Exécution d'un coup

### `execute_move(from_sq, to_sq, is_capture, piece_type)`

Point d'entrée principal pour déplacer une pièce.

```python
await robot.execute_move(
    from_sq="e2",
    to_sq="e4",
    is_capture=False,
    piece_type=chess.PAWN
)
```

**Séquence complète :**

```
Position HOME
    │
    ▼
_move_tcp(HOME_POSITION)
    │
    ▼
[Si capture] _prendre_piece(to_sq)  ← prise de la pièce adverse
             _poser_piece(CIMETIERE) ← pose au cimetière
    │
    ▼
_prendre_piece(from_sq)   ← prise de notre pièce
    │
    ▼
_poser_piece(to_sq)       ← pose à destination
    │
    ▼
_move_tcp(HOME_POSITION)
```

### `_prendre_piece(square)`

Séquence de prise d'une pièce :
1. Déplacement XY vers la case (Z haute)
2. Ouverture pince
3. Descente Z (selon hauteur de la pièce)
4. Fermeture pince
5. Remontée Z

```python
success = await robot._prendre_piece("e4")
if not success:
    # gestion erreur
```

### `_poser_piece(square)`

Séquence de pose :
1. Déplacement XY vers la case (Z haute)
2. Descente Z
3. Ouverture pince (libération)
4. Remontée Z

```python
success = await robot._poser_piece("e6")
```

## Conversion de coordonnées

Les cases d'échecs sont converties en coordonnées cartésiennes par la méthode `_square_to_position(square)`.

```python
# Exemple: e4 → [x_mm, y_mm, Z_APPROCHE, Rx, Ry, Rz]
position = robot._square_to_position("e4")
```

**Calcul :**
- L'échiquier physique est mappé sur une grille
- `BOARD_ORIGIN` (config.py) = coin a1 en coordonnées robot
- `CASE_SIZE` = taille d'une case en mm
- Les coordonnées X/Y sont calculées par interpolation sur la grille 8×8

## Hauteurs Z

Les hauteurs de descente varient selon le type de pièce pour s'adapter à leur taille physique :

```python
# config.py
HAUTEUR_PIECES = {
    chess.PAWN:   -150,   # Pion (plus petit)
    chess.ROOK:   -145,
    chess.KNIGHT: -148,
    chess.BISHOP: -148,
    chess.QUEEN:  -140,
    chess.KING:   -140,   # Roi (plus grand)
}
```

La hauteur est récupérée depuis `robot.piece_courante` qui doit être défini avant `_prendre_piece()`.

## Position HOME

Le robot retourne à la position HOME entre chaque coup. Cette position est définie dans `config.py` :

```python
HOME_POSITION = [x, y, z, rx, ry, rz]  # en mm et radians
```

## Gestion du cimetière

Quand une pièce est capturée, elle est envoyée dans une zone de cimetière adjacente à l'échiquier. Le cimetière est une grille de cases supplémentaires.

**Logique d'occupation :**
- Le vision service détecte quelles cases du cimetière sont déjà occupées
- `_find_free_cemetery_cell(color)` sélectionne la première case libre
- Convention : cimetière blanc en `A0`-`J0`, cimetière noir en `A9`-`J9`

:::warning
La vision utilise des cases en majuscules (`'A0'`), le robot utilise des minuscules (`'a0'`). La conversion `.lower()` est appliquée avant tout appel robot.
:::

## Non-blocage de la boucle asyncio

Toutes les commandes RTDE (`moveL`, `stopScript`, `reuploadScript`, `gripper`) sont synchrones (bloquantes). Elles sont wrappées avec `run_in_executor` :

```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, self.rtde_c.moveL, position, speed, accel)
```

Cela permet au serveur FastAPI de continuer à traiter d'autres requêtes (ex: pause) pendant un mouvement robot.

## États internes

| Attribut | Type | Description |
|----------|------|-------------|
| `is_paused` | `bool` | True si le robot est en pause |
| `piece_courante` | `chess.PieceType` | Type de pièce en cours de manipulation |
| `rtde_c` | `RTDEControlInterface` | Interface de contrôle RTDE |
| `rtde_r` | `RTDEReceiveInterface` | Interface de lecture RTDE |
| `gripper` | `RobotiqGripper` | Contrôleur de pince |
