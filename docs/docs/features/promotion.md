---
id: promotion
title: Promotion
sidebar_position: 4
---

# Promotion de pion

La promotion survient quand un pion atteint la dernière rangée (rang 8 pour les blancs, rang 1 pour les noirs).

## Promotion joueur humain

### Mode vision

Quand la vision détecte un pion sur la dernière rangée, le backend broadcast un événement :

```json
{
  "type": "promotion",
  "square": "e8",
  "color": "white"
}
```

Le frontend affiche un dialogue de choix :

```
Choisissez la pièce de promotion :
[♛ Dame]  [♖ Tour]  [♗ Fou]  [♘ Cavalier]
```

### Confirmation

```http
POST /game/promotion
Content-Type: application/json

{
  "square": "e8",
  "piece": "q"   // q=dame, r=tour, b=fou, n=cavalier
}
```

Le backend récupère le coup interrompu, applique la promotion et continue la partie.

### Pattern asyncio.Event

La promotion utilise le même pattern que la pause/reprise :

```python
# Dans play_human_move()
if move.promotion:
    self._promotion_event = asyncio.Event()
    broadcast({"type": "promotion", "square": to_sq})
    await asyncio.wait_for(self._promotion_event.wait(), timeout=300)
    # ← POST /promotion arrive ici
    move = chess.Move(..., promotion=self._promotion_choice)

# Dans l'endpoint /game/promotion
chess_manager._promotion_choice = chess.QUEEN
chess_manager._promotion_event.set()
```

## Promotion robot

Quand Stockfish choisit une promotion, le coup UCI inclut la pièce :
- `e7e8q` — promotion en dame
- `e7e8r` — promotion en tour

Le robot déplace le pion en e8, puis la tour doit être remplacée physiquement par la nouvelle pièce. Une instruction est affichée à l'opérateur.

:::info
La promotion robot nécessite une intervention humaine pour échanger physiquement la pièce sur l'échiquier.
:::

## Timeout

Si aucune promotion n'est choisie dans les **300 secondes**, la partie est marquée comme abandonnée.
