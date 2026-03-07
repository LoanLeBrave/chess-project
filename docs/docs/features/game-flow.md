---
id: game-flow
title: Flux de jeu
sidebar_position: 1
---

# Flux de jeu

## Cycle de vie d'une partie

```
IDLE
 │ POST /game/start
 ▼
PLAYING (tour humain)
 │ Coup humain (vision ou manuel)
 ▼
PLAYING (tour robot)
 │ Stockfish + Robot execute_move()
 ▼
PLAYING (tour humain)
 │ ... répétition ...
 │ Fin de partie (mat / pat / abandon)
 ▼
GAME_OVER
 │ Sauvegarde score (POST /leaderboard/add)
 ▼
IDLE
```

## Démarrage d'une partie

### Pré-requis
- Robot calibré et connecté
- Caméra active (si mode vision)
- Joueur enregistré (prénom)

### Appel API
```http
POST /game/start
Content-Type: application/json

{
  "player_name": "Alice",
  "difficulty": "intermediate",
  "use_vision": true,
  "player_color": "white"
}
```

### Actions backend
1. `chess_manager.reset()` — réinitialise le board python-chess
2. `vision_service.game_started = True` — active la détection
3. `vision_service.capture_reference()` — capture l'état initial
4. Broadcast `game_state` avec FEN initiale

## Tour du joueur humain

### Mode vision (par défaut)
Le joueur déplace physiquement une pièce. La caméra détecte le changement sous ~2 secondes.

```
Joueur déplace une pièce
    ↓ ~2s
VisionService détecte le changement
    ↓
sync_with_vision() → play_human_move()
    ↓
Broadcast "move"
    ↓
Tour robot déclenché automatiquement
```

### Mode manuel (secours)
L'opérateur saisit le coup dans l'interface web.

```
Opérateur saisit: e2 → e4
    ↓
POST /game/move {"from": "e2", "to": "e4"}
    ↓
play_human_move()
    ↓
Tour robot déclenché automatiquement
```

## Tour du robot

```
play_robot_move()
    │
    ▼ Broadcast: robot_thinking
Stockfish analyse (depth, time_limit)
    │
    ▼ Broadcast: robot_moving
RobotController.execute_move()
    │ ~10-30 secondes de mouvement physique
    ▼ Broadcast: move + fen
vision.update_reference_after_move()
    │
    ▼
Tour humain (attente coup)
```

## Fin de partie

La partie se termine quand `board.is_game_over()` retourne `True`.

**Causes possibles :**
- `board.is_checkmate()` — échec et mat
- `board.is_stalemate()` — pat
- `board.is_insufficient_material()` — matériel insuffisant
- `board.is_fifty_moves()` — règle des 50 coups
- Abandon (bouton STOP dans l'UI)

**Broadcast `game_over` :**
```json
{
  "type": "game_over",
  "result": "checkmate",
  "winner": "robot",
  "final_acpl": 42.5
}
```

## Statuts de la partie

| Statut | Description |
|--------|-------------|
| `idle` | Aucune partie en cours |
| `playing` | Partie active |
| `paused` | Partie en pause |
| `game_over` | Partie terminée |
| `robot_thinking` | Stockfish calcule |
| `robot_moving` | Robot en mouvement |
| `waiting_promotion` | Attente choix de promotion |
| `waiting_resume` | Attente confirmation reprise |

## Gestion des couleurs

Par défaut, le joueur humain joue les **blancs** (commence). Si `player_color = "black"`, le robot joue le premier coup automatiquement.

Les codes de pièces vision (`WP`, `BP`, etc.) sont toujours en référence à la couleur absolue (W=blanc, B=noir), indépendamment du camp du joueur.
