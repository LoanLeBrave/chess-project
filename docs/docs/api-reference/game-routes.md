---
id: game-routes
title: Routes de jeu
sidebar_position: 3
---

# Routes de jeu

## `POST /game/start`

Démarre une nouvelle partie.

**Corps :**
```json
{
  "player_name": "Alice",
  "difficulty": "intermediate",
  "use_vision": true,
  "player_color": "white"
}
```

| Paramètre | Type | Valeurs | Description |
|-----------|------|---------|-------------|
| `player_name` | `string` | — | Prénom du joueur |
| `difficulty` | `string` | `beginner`, `intermediate`, `advanced` | Niveau Stockfish |
| `use_vision` | `bool` | `true/false` | Activer la détection par caméra |
| `player_color` | `string` | `white`, `black` | Couleur du joueur |

**Réponse :**
```json
{
  "status": "ok",
  "message": "Partie démarrée",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
}
```

---

## `POST /game/stop`

Arrête la partie en cours.

**Corps :**
```json
{
  "player_name": "Alice",
  "acpl": 45.3,
  "result": "abandoned"
}
```

**Actions :**
1. `stopScript()` sur le robot
2. `vision_service.game_started = False`
3. Sauvegarde du score si `player_name` fourni

**Réponse :**
```json
{"status": "ok", "message": "Partie arrêtée"}
```

---

## `POST /game/move`

Joue un coup manuellement (sans vision).

**Corps :**
```json
{
  "from": "e2",
  "to": "e4",
  "promotion": null
}
```

**Erreurs possibles :**
- `400` — Coup illégal
- `409` — Ce n'est pas le tour du joueur

**Réponse :**
```json
{
  "status": "ok",
  "fen": "...",
  "acpl": 12
}
```

---

## `POST /game/toggle-pause`

Bascule entre pause et reprise.

**Corps :** aucun

**Réponse :**
```json
{
  "status": "ok",
  "is_paused": true
}
```

---

## `POST /game/confirm-resume`

Confirme que la pièce a été replacée après une reprise interrompue.

**Corps :** aucun

**Réponse :**
```json
{"status": "resumed"}
```

---

## `POST /game/promotion`

Choisit la pièce de promotion.

**Corps :**
```json
{
  "square": "e8",
  "piece": "q"
}
```

| `piece` | Pièce |
|---------|-------|
| `q` | Dame |
| `r` | Tour |
| `b` | Fou |
| `n` | Cavalier |

**Réponse :**
```json
{"status": "ok", "piece": "q"}
```

---

## `GET /game/state`

Retourne l'état complet de la partie.

**Réponse :**
```json
{
  "status": "playing",
  "fen": "...",
  "turn": "human",
  "player_name": "Alice",
  "difficulty": "intermediate",
  "acpl": 23.5,
  "move_count": 10,
  "is_paused": false,
  "is_check": false,
  "is_game_over": false
}
```

---

## `GET /game/legal-moves/{square}`

Retourne les coups légaux depuis une case.

**Exemple :** `GET /game/legal-moves/e2`

**Réponse :**
```json
{
  "square": "e2",
  "moves": ["e3", "e4"]
}
```

---

## `POST /game/replace-pieces`

Déclenche le remplacement physique des pièces déplacées.

**Corps :** aucun

**Réponse :**
```json
{"status": "ok", "message": "Remplacement en cours"}
```

Cette opération est asynchrone. Le frontend doit surveiller le WebSocket pour l'événement `replacement_done`.
