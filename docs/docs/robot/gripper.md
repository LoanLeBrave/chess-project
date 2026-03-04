---
id: gripper
title: Pince Robotiq
sidebar_position: 2
---

# Pince Robotiq

Le robot UR5e est équipé d'une **pince Robotiq Hand-E**  pour saisir les pièces d'échecs.

## Interface

```python
from robotiq_gripper import RobotiqGripper

gripper = RobotiqGripper()
gripper.connect(ROBOT_IP, 63352)  # port Robotiq par défaut
gripper.activate()
```

## Commandes de base

```python
# Ouverture complète
gripper.move(position=0, speed=150, force=50)

# Fermeture adaptée selon le type de pièce
gripper.move(position=180, speed=150, force=50)  # pion
gripper.move(position=200, speed=150, force=50)  # tour/roi
```

## Paramètres

| Paramètre | Plage | Description |
|-----------|-------|-------------|
| `position` | 0–255 | 0 = ouvert, 255 = fermé |
| `speed` | 0–255 | Vitesse de fermeture |
| `force` | 0–255 | Force de serrage |

## Fermeture adaptative

Chaque type de pièce a un diamètre différent. La position de fermeture est adaptée :

```python
GRIPPER_POSITIONS = {
    chess.PAWN:   180,  # pion: plus petit
    chess.ROOK:   200,  # tour: base carrée large
    chess.KNIGHT: 190,  # cavalier
    chess.BISHOP: 185,  # fou
    chess.QUEEN:  195,  # reine
    chess.KING:   200,  # roi: plus grand
}
```

La pièce courante est définie dans `robot.piece_courante` avant chaque opération de prise. Cette valeur est utilisée pour sélectionner la bonne position de fermeture.

## Non-blocage asyncio

Les commandes pince sont synchrones. Elles sont wrappées avec `run_in_executor` :

```python
loop = asyncio.get_event_loop()

# Ouverture
await loop.run_in_executor(
    None,
    gripper.move,
    GRIPPER_OPEN_POSITION,
    GRIPPER_SPEED,
    GRIPPER_FORCE
)

# Fermeture
close_pos = GRIPPER_POSITIONS.get(robot.piece_courante, GRIPPER_CLOSE_DEFAULT)
await loop.run_in_executor(
    None,
    gripper.move,
    close_pos,
    GRIPPER_SPEED,
    GRIPPER_FORCE
)
```

## État après pause

Lors d'un `stopScript()`, la pince conserve son état (ouverte ou fermée). La routine de reprise commence toujours par `gripper.open()` pour s'assurer d'un état connu :

```python
# _resume_process() dans chess_manager.py
await loop.run_in_executor(None, robot.gripper.move, 0, 150, 50)
```

## Détection de prise échouée

Si la pince ne rencontre pas de résistance suffisante (pièce manquante), `_prendre_piece()` peut détecter un échec via la position réelle de fermeture :

```python
actual_position = gripper.get_current_position()
if actual_position > expected_position + TOLERANCE:
    # La pince s'est refermée trop fort → aucune pièce saisie
    return False
```

:::note
Cette détection n'est pas toujours implémentée et dépend du modèle exact de pince.
:::
