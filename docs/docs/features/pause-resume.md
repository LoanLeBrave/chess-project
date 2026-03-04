---
id: pause-resume
title: Pause / Reprise
sidebar_position: 2
---

# Pause et Reprise

Le système supporte la mise en pause à tout moment pendant une partie, y compris au milieu d'un mouvement robot.

## Flux de mise en pause

```
POST /game/toggle-pause (état: playing)
    │
    ▼
chess_manager.toggle_pause()
    │
    ├── robot.rtde_c.stopScript()   [run_in_executor, timeout 5s]
    ├── chess_manager.is_paused = True
    ├── robot.is_paused = True
    └── broadcast: {type: "pause", is_paused: true}
```

Le `stopScript()` arrête immédiatement l'exécution du programme URScript sur le robot.

:::warning
L'arrêt `stopScript()` est instantané mais peut laisser la pince dans un état intermédiaire (partiellement fermée). La reprise gère cet état en rouvrant explicitement la pince.
:::

## Flux de reprise

```
POST /game/toggle-pause (état: paused)
    │
    ▼
chess_manager.toggle_pause()
    │
    └── asyncio.create_task(_resume_process())
            │
            ▼
        robot.reuploadScript()          [run_in_executor]
            │
            ▼
        robot.gripper.open()            [run_in_executor]
            │
            ▼
        chess_manager.is_paused = False
        robot.is_paused = False
            │
            ▼ (si _interrupted_move existe)
        board.push(interrupted_move)    ← validation virtuelle
        vision.update_reference()       ← synchronisation vision
            │
            ▼
        broadcast: resume_confirmation_needed
        {type: "resume_confirmation_needed",
         piece: "Tour", from: "e1", to: "g1"}
            │
            ▼ attente (max 600s)
        _resume_event.wait()
            │ ← POST /game/confirm-resume
            ▼
        _resume_event.set()
            │
            ▼
        [si tour robot] play_robot_move()
```

## Coup interrompu

Quand la pause survient pendant un mouvement robot, le coup est stocké dans `_interrupted_move` :

```python
self._interrupted_move = {
    "from": "e2",
    "to": "e4",
    "move": chess.Move(...),  # objet python-chess
    "is_capture": False,
}
```

Ce dictionnaire est défini **avant** l'appel à `robot.execute_move()` et effacé après la reprise réussie.

## Confirmation de reprise

Lors de la reprise avec un coup interrompu, le frontend affiche une alerte :

```
⚠️  Le robot reprend son coup: Tour e1 → g1
    Veuillez replacer la pièce manuellement si nécessaire.
    [Pièce replacée ✓]
```

L'utilisateur clique "Pièce replacée" → `POST /game/confirm-resume` → le robot reprend son mouvement.

### Endpoint

```http
POST /game/confirm-resume
```

### Réponse
```json
{"status": "resumed"}
```

## Mise en pause pendant un coup humain

Si la pause est activée pendant que le joueur est en train de déplacer une pièce (vision en attente), la vision est simplement désactivée (`game_started=False`). La reprise réactive la vision sans gestion particulière du coup interrompu (le coup n'avait pas encore été validé).

## États internes

| Variable | Type | Valeur pause | Valeur reprise |
|----------|------|-------------|----------------|
| `chess_manager.is_paused` | `bool` | `True` | `False` |
| `robot.is_paused` | `bool` | `True` | `False` |
| `vision_service.game_started` | `bool` | `False` | `True` |
| `_interrupted_move` | `dict\|None` | Défini si coup en cours | `None` |
| `_resume_event` | `asyncio.Event` | — | `.set()` après confirmation |

## Timeout de reprise

Si l'utilisateur ne clique pas sur "Pièce replacée" dans les **600 secondes**, le `_resume_event.wait()` expire et la partie est marquée comme abandonnée.
