---
id: castling
title: Roque
sidebar_position: 3
---

# Roque (Castling)

Le système supporte les deux types de roque : petit roque (côté roi) et grand roque (côté dame).

## Représentation UCI

python-chess encode le roque comme un mouvement du roi uniquement :

| Type | Notation UCI | De → Vers |
|------|-------------|-----------|
| Petit roque (blancs) | `e1g1` | Roi e1 → g1 |
| Grand roque (blancs) | `e1c1` | Roi e1 → c1 |
| Petit roque (noirs) | `e8g8` | Roi e8 → g8 |
| Grand roque (noirs) | `e8c8` | Roi e8 → c8 |

La tour est déplacée automatiquement par python-chess lors du `board.push(move)`.

## Roque robot (coup Stockfish)

Quand Stockfish choisit un roque, `play_robot_move()` reçoit le coup UCI (`e1g1`).

Le robot exécute **deux déplacements physiques** :

```python
# Détection du roque via python-chess
if board.is_castling(move):
    # Déterminer le déplacement de la tour
    if chess.square_file(move.to_square) == 6:  # petit roque
        rook_from = "h1"
        rook_to   = "f1"
    else:                                        # grand roque
        rook_from = "a1"
        rook_to   = "d1"

    # 1. Déplacer le roi
    await robot.execute_move(from_sq, to_sq)

    # 2. Déplacer la tour
    robot.piece_courante = chess.ROOK
    await robot.execute_move(rook_from, rook_to)
```

## Roque joueur (détection vision)

La caméra détecte physiquement deux pièces qui bougent simultanément. La méthode `sync_with_vision()` gère ce cas spécial dans le **Case 3** :

```python
# Case 3: Roque
if not detected_move:
    king_from = next(
        (sq for sq, code in disappeared.items() if code == "WK"),
        None
    )
    if king_from:
        for move in self.board.legal_moves:
            if not self.board.is_castling(move):
                continue
            moving_piece = self.board.piece_at(move.from_square)
            if moving_piece is None or moving_piece.color != chess.WHITE:
                continue
            king_to = chess.square_name(move.to_square)
            if appeared.get(king_to) == "WK":
                detected_move = {"from": king_from, "to": king_to}
                break
```

**Principe :** la vision cherche si un roi blanc (`WK`) a disparu ET un roi blanc est apparu en g1 ou c1. Si oui, elle identifie le coup légal correspondant.

:::note
Seul le déplacement du roi est signalé à `play_human_move()`. python-chess comprend automatiquement que c'est un roque et met à jour la position de la tour virtuellement.
:::

## Roque mode manuel

L'interface Frontend gère le roque via la méthode `getLegalMoves()` :

```typescript
// GameScreen.tsx
const moves = await getLegalMoves("e1");
// Retourne: ["g1", "c1"] si les deux roques sont légaux
```

Le joueur clique sur `g1` pour le petit roque ou `c1` pour le grand roque.

## Validation

python-chess vérifie automatiquement les conditions de roque :
- Le roi et la tour n'ont pas encore bougé
- Les cases entre eux sont libres
- Le roi ne passe pas par une case en échec
- Le roi n'est pas actuellement en échec

## Vérification de la prise en charge

| Scenario | Pris en charge |
|----------|---------------|
| Petit roque robot | ✅ |
| Grand roque robot | ✅ |
| Petit roque joueur (vision) | ✅ |
| Grand roque joueur (vision) | ✅ |
| Petit roque joueur (manuel) | ✅ |
| Grand roque joueur (manuel) | ✅ |
| Roque lors d'une reprise de pause | ✅ |
