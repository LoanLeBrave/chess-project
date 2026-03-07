---
id: components
title: Composants
sidebar_position: 2
---

# Architecture — Composants

## ApplicationManager (`api.py`)

Classe centrale qui orchestre tous les composants.

```python
class ApplicationManager:
    chess_manager: ChessManager
    robot: RobotController
    vision_service: VisionService
    leaderboard: LeaderboardManager
    active_connections: list[WebSocket]
```

**Responsabilités :**
- Gestion des connexions WebSocket (liste `active_connections`)
- Méthode `broadcast(data)` — diffuse un message JSON à tous les clients
- Initialisation et liaison des composants (le chess_manager reçoit une référence au robot et au broadcast)
- Démarrage du thread vision au démarrage de l'application

## VisionService (`api.py`)

Service de vision exécuté en tâche de fond asyncio.

```python
class VisionService:
    chess_vision: ChessVision       # pipeline ArUco
    game_started: bool              # active la détection de coups
    reference_board: dict           # état de référence après le dernier coup
```

**Cycle de fonctionnement :**
1. Capture image (rpicam-still ou simulation)
2. Détecte les marqueurs ArUco → grille 10×10
3. Compare avec `reference_board` → calcule `appeared/disappeared/changed`
4. Si `game_started=True` et mouvement détecté → appelle `chess_manager.sync_with_vision()`
5. Met à jour `reference_board`

**Méthodes clés :**
- `start()` — démarre la boucle infinie
- `stop()` — arrête proprement
- `update_reference_after_move(board_state)` — met à jour la référence après un coup robot

## ChessManager (`chess_manager.py`)

Le cerveau de la logique de jeu.

```python
class ChessManager:
    board: chess.Board              # état virtuel de l'échiquier
    engine: chess.engine.SimpleEngine  # Stockfish
    robot: RobotController
    broadcast_func: Callable
    is_paused: bool
    _interrupted_move: dict | None  # coup en cours au moment de la pause
    _resume_event: asyncio.Event    # signal de reprise
```

**Responsabilités :**
- Validation des coups (règles python-chess)
- Calcul des coups Stockfish selon le niveau de difficulté
- Gestion des tours (humain/robot)
- Calcul de l'ACPL (Average Centipawn Loss)
- Coordination pause/reprise
- Remplacement des pièces déplacées

## RobotController (`robot_controller.py`)

Interface avec le hardware robot.

```python
class RobotController:
    rtde_c: RTDEControlInterface
    rtde_r: RTDEReceiveInterface
    gripper: RobotiqGripper
    piece_courante: chess.PieceType  # type de pièce en cours de manipulation
    is_paused: bool
```

**Responsabilités :**
- Séquences de mouvement (approche → descente → prise → montée → déplacement → pose)
- Gestion de la pince Robotiq (ouverture/fermeture adaptée au type de pièce)
- Conversion coordonnées échecs (a1-h8) → coordonnées cartésiennes robot
- Calcul de hauteur Z selon le type de pièce (`HAUTEUR_PIECES`)

## LeaderboardManager (`leaderboard_manager.py`)

Persistance des scores par joueur.

```python
class LeaderboardManager:
    filepath: str                   # chemin vers leaderboard.json
    players: dict[str, PlayerData]  # stats agrégées par joueur
```

**Structure des données :**
```json
{
  "players": {
    "Alice": {
      "name": "Alice",
      "acpl": 45,
      "games": 3,
      "wins": 1,
      "losses": 2,
      "abandoned": 0,
      "date": "2025-03-04T10:30:00"
    }
  }
}
```

**Méthodes :**
- `add_game(name, acpl, result)` — ajoute/met à jour un joueur (ACPL moyenné)
- `get_leaderboard(limit)` — retourne les N meilleurs joueurs triés par ACPL
