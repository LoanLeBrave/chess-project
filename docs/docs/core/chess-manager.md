---
id: chess-manager
title: ChessManager
sidebar_position: 1
---

# ChessManager

**Fichier :** `Backend/manipulation_robot/chess_manager.py`

Le `ChessManager` est le module central de la logique de jeu. Il gère l'état de la partie, valide les coups, interagit avec Stockfish et coordonne les actions du robot.

## Initialisation

```python
chess_manager = ChessManager(
    robot=robot_controller,
    broadcast_func=app_manager.broadcast,
    vision_service=vision_service,
    difficulty="intermediate"  # "beginner" | "intermediate" | "advanced"
)
await chess_manager.initialize()  # charge Stockfish
```

## État de la partie

```python
chess_manager.board          # chess.Board — état virtuel de l'échiquier
chess_manager.status         # "idle" | "playing" | "paused" | "game_over"
chess_manager.current_turn   # "human" | "robot"
chess_manager.acpl           # float — ACPL courant du joueur
chess_manager.is_paused      # bool
```

## Méthodes principales

### `play_human_move(from_sq, to_sq, promotion=None)`

Joue un coup humain et déclenche la réponse du robot.

```python
await chess_manager.play_human_move("e2", "e4")
await chess_manager.play_human_move("e7", "e8", promotion="q")  # avec promotion
```

**Séquence interne :**
1. Valide le coup avec `board.is_legal(move)`
2. Évalue la position avant coup (Stockfish) → score pré-coup
3. `board.push(move)`
4. Évalue après coup → calcul CPL = max(0, pre - post)
5. Met à jour l'ACPL moyen
6. Broadcast `move`
7. Vérifie fin de partie (`board.is_game_over()`)
8. Lance `play_robot_move()` si la partie continue

### `play_robot_move()`

Calcule et exécute le coup du robot.

```python
await chess_manager.play_robot_move()
```

**Séquence interne :**
1. Broadcast `robot_thinking`
2. Demande à Stockfish le meilleur coup (selon niveau)
3. Stockfish retourne un coup UCI (ex: `e2e4`, `e1g1` pour roque)
4. Stocke `_interrupted_move` avant exécution (pour pause/reprise)
5. `robot.execute_move(from_sq, to_sq, is_capture)` — déplacement physique
6. `board.push(move)`
7. Broadcast `move`
8. Vérifie fin de partie

### `sync_with_vision(appeared, disappeared, changed)`

Synchronise l'état virtuel avec l'état physique détecté par la caméra.

```python
await chess_manager.sync_with_vision(
    appeared={"e4": "WP"},
    disappeared={"e2": "WP"},
    changed={}
)
```

**3 cas détectés :**

| Cas | Condition | Action |
|-----|-----------|--------|
| Déplacement simple | 1 pièce disparue + 1 apparue, même type | `play_human_move(from, to)` |
| Capture | 1 pièce disparue + 1 apparue au cimetière | `play_human_move(from, to)` |
| Roque | Roi disparu + Roi apparu en g1/c1 | `play_human_move(e1, g1/c1)` |

### `toggle_pause()`

Basculer l'état pause/reprise.

```python
await chess_manager.toggle_pause()
```

Voir [Pause/Reprise](/features/pause-resume) pour le détail du flux.

## Calcul de l'ACPL

L'**Average Centipawn Loss** (ACPL) mesure la qualité de jeu du joueur humain. Un score plus bas = meilleur joueur.

```python
# Avant chaque coup humain
pre_score = engine.analyse(board, limit)["score"].white().score(mate_score=10000)

# Après le coup
post_score = engine.analyse(board, limit)["score"].white().score(mate_score=10000)

# CPL (toujours >= 0)
cpl = max(0, pre_score - post_score)  # pour les blancs
# ou
cpl = max(0, post_score - pre_score)  # pour les noirs

# Mise à jour ACPL
self.acpl = (self.acpl * (self.move_count - 1) + cpl) / self.move_count
```

:::note
L'ACPL est calculé uniquement sur les coups humains, pas sur les coups robot.
:::

## Niveaux de difficulté

Voir [config.py](/core/config) pour les paramètres `DIFFICULTY_PRESETS`.

| Niveau | Skill Level | Profondeur | ELO approximatif |
|--------|------------|------------|-----------------|
| Débutant | 5 | 5 | ~1100-1200 |
| Intermédiaire | 12 | 12 | ~1600-1800 |
| Avancé | 20 | 20 | ~2300-2500 |

## Remplacement des pièces

La méthode `_replacer_pieces_deplacees()` est appelée lorsque l'utilisateur demande à remettre les pièces en position initiale après un arrêt de partie.

```python
await chess_manager._replacer_pieces_deplacees()
```

Voir [Remplacement des pièces](/features/replacement) pour le détail.
