---
id: data-flow
title: Flux de données
sidebar_position: 3
---

# Architecture — Flux de données

## Flux d'un coup humain (mode vision)

```
Joueur déplace une pièce
        │
        ▼
VisionService (boucle ~2s)
  compare grille actuelle vs référence
  détecte: appeared={e4: WP}, disappeared={e2: WP}
        │
        ▼
chess_manager.sync_with_vision(appeared, disappeared)
  Case 1: simple déplacement  → detected_move = {from: e2, to: e4}
  Case 2: capture             → pièce disparue + cimetière
  Case 3: roque               → 2 pièces disparues (roi + tour)
        │
        ▼
chess_manager.play_human_move(from, to)
  valide le coup (python-chess)
  calcule ACPL (Stockfish pre-éval)
  board.push(move)
  broadcast: {type: "move", from, to, acpl, fen, ...}
        │
        ▼
chess_manager.play_robot_move()
  Stockfish calcule le meilleur coup
  broadcast: {type: "robot_thinking"}
  robot.execute_move(from, to, is_capture)
        │
        ▼
RobotController.execute_move()
  séquence: home → prendre pièce → (cimetière si capture) → poser → home
        │
        ▼
broadcast: {type: "move", from, to, fen, ...}
vision.update_reference_after_move()
```

## Flux d'un coup humain (mode manuel)

Le joueur saisit le coup directement dans l'UI (mode de secours sans vision) :

```
Frontend: bouton "Jouer" + case de/vers
        │
        ▼
POST /game/move  {from, to}
        │
        ▼
chess_manager.play_human_move(from, to)
  (identique au flux vision à partir de là)
```

## Flux WebSocket

Le backend diffuse des messages JSON structurés :

| `type` | Données | Déclencheur |
|--------|---------|-------------|
| `game_state` | `{fen, status, turn, acpl, ...}` | Connexion initiale |
| `move` | `{from, to, fen, acpl, promotion}` | Coup joué |
| `robot_thinking` | `{status}` | Stockfish calcule |
| `robot_moving` | `{status}` | Robot en mouvement |
| `check` | `{fen}` | Roi en échec |
| `game_over` | `{result, winner}` | Fin de partie |
| `pause` | `{is_paused}` | Pause/reprise |
| `resume_confirmation_needed` | `{piece, from, to}` | Reprise interrompue |
| `promotion` | `{square, color}` | Promotion d'un pion |
| `error` | `{message}` | Erreur backend |

## Flux de pause/reprise

```
Utilisateur → POST /game/toggle-pause
        │
        ▼ (si mise en pause)
chess_manager.toggle_pause()
  robot.rtde_c.stopScript() [run_in_executor]
  chess_manager.is_paused = True
  robot.is_paused = True
  broadcast: {type: "pause", is_paused: true}
        │
        ▼ (si reprise)
chess_manager.toggle_pause()
  asyncio.create_task(_resume_process())
        │
        ▼
_resume_process():
  robot.reuploadScript() [run_in_executor]
  robot.gripper.open() [run_in_executor]
  chess_manager.is_paused = False
  robot.is_paused = False
  si _interrupted_move:
    board.push(move)
    broadcast: resume_confirmation_needed
    _resume_event.wait(600s)
    ← utilisateur clique "Pièce replacée"
    POST /game/confirm-resume → _resume_event.set()
    play_robot_move() ou rien selon tour
```

## Flux de sauvegarde du score

```
Fin de partie (game_over WS)
        │ frontend
        ▼
POST /leaderboard/add
  {name, acpl, result}
        │
        ▼
LeaderboardManager.add_game()
  charge leaderboard.json
  agrège stats joueur
  sauvegarde leaderboard.json
        │
        ▼
200 OK
        │ frontend
        ▼
setShowScoreSaved(true) → notification 4s
```
