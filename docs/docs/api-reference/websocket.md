---
id: websocket
title: WebSocket
sidebar_position: 2
---

# WebSocket

Le WebSocket permet une communication bidirectionnelle en temps réel entre le backend et le frontend.

## Connexion

```javascript
const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};
```

## Messages du serveur → client

### `game_state` — État initial

Envoyé lors de la connexion ou d'un changement d'état majeur.

```json
{
  "type": "game_state",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "status": "idle",
  "turn": "human",
  "player_name": "Alice",
  "difficulty": "intermediate",
  "acpl": 0,
  "move_count": 0,
  "is_paused": false
}
```

### `move` — Coup joué

```json
{
  "type": "move",
  "from": "e2",
  "to": "e4",
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "turn": "robot",
  "acpl": 15,
  "promotion": null,
  "is_capture": false
}
```

### `robot_thinking` — Robot réfléchit

```json
{
  "type": "robot_thinking",
  "status": "calculating"
}
```

### `robot_moving` — Robot se déplace

```json
{
  "type": "robot_moving",
  "from": "d2",
  "to": "d4",
  "status": "moving"
}
```

### `check` — Échec

```json
{
  "type": "check",
  "fen": "...",
  "turn": "human"
}
```

### `game_over` — Fin de partie

```json
{
  "type": "game_over",
  "result": "checkmate",
  "winner": "robot",
  "final_acpl": 42.5,
  "fen": "..."
}
```

**Valeurs de `result` :**
- `"checkmate"` — Échec et mat
- `"stalemate"` — Pat
- `"insufficient_material"` — Matériel insuffisant
- `"fifty_moves"` — Règle des 50 coups
- `"abandoned"` — Abandon

### `pause` — Pause/Reprise

```json
{
  "type": "pause",
  "is_paused": true
}
```

### `resume_confirmation_needed` — Reprise avec coup interrompu

```json
{
  "type": "resume_confirmation_needed",
  "piece": "Tour",
  "from": "h1",
  "to": "f1"
}
```

### `promotion` — Choix de promotion requis

```json
{
  "type": "promotion",
  "square": "e8",
  "color": "white"
}
```

### `error` — Erreur

```json
{
  "type": "error",
  "message": "Coup illégal: e2 → e5",
  "code": "ILLEGAL_MOVE"
}
```

## Messages client → serveur

Le client peut envoyer des messages JSON au serveur via le WebSocket (optionnel, la plupart des actions passent par REST) :

```json
{
  "type": "ping"
}
```

## Reconnexion automatique

Le frontend (`useChessRobot.ts`) implémente une reconnexion automatique :

```typescript
ws.onclose = () => {
    setTimeout(() => {
        connect();  // tentative de reconnexion après 3s
    }, 3000);
};
```

## Broadcast multi-clients

Le backend maintient une liste de toutes les connexions WebSocket actives et diffuse chaque événement à tous :

```python
async def broadcast(data: dict):
    message = json.dumps(data)
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception:
            active_connections.remove(connection)
```

Plusieurs clients peuvent être connectés simultanément (ex: l'interface principale + un écran d'affichage secondaire).
