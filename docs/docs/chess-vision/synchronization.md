---
id: synchronization
title: Synchronisation
sidebar_position: 3
---

# Synchronisation vision ↔ échiquier virtuel

La synchronisation est le processus qui transforme les changements visuels détectés par la caméra en coups légaux python-chess.

## Principe général

```
État vision actuel
        │
        ▼
compare_with_reference(current, reference)
        │
        ├── appeared:    {"e4": "WP"}      (pièces nouvellement visibles)
        ├── disappeared: {"e2": "WP"}      (pièces qui ont disparu)
        └── changed:     {"e4": "WP→BP"}   (pièce remplacée par une autre)
        │
        ▼
sync_with_vision(appeared, disappeared, changed)
        │
        ├── Case 1: Simple déplacement
        ├── Case 2: Capture
        └── Case 3: Roque
        │
        ▼
play_human_move(from, to)
```

## Case 1 — Déplacement simple

**Condition :** 1 pièce disparue + 1 apparue, même type de pièce

```python
if len(disappeared) == 1 and len(appeared) == 1:
    from_sq, piece_code = list(disappeared.items())[0]
    to_sq, new_code = list(appeared.items())[0]

    if piece_code == new_code:  # même type de pièce
        detected_move = {"from": from_sq, "to": to_sq}
```

**Exemple :**
- `disappeared = {"e2": "WP"}`
- `appeared = {"e4": "WP"}`
- → Mouvement e2 → e4

## Case 2 — Capture

**Condition :** 1 pièce disparue sur l'échiquier + 1 pièce apparue dans le cimetière adverse

```python
if not detected_move:
    for from_sq, piece_code in disappeared.items():
        if is_board_square(from_sq):
            for to_sq, captured_code in appeared.items():
                if is_cemetery_square(to_sq, color_of(piece_code)):
                    # La case de destination est la case d'où vient la pièce capturée
                    detected_move = {"from": from_sq, "to": captured_original_sq}
```

## Case 3 — Roque

**Condition :** Un roi a disparu ET un roi est apparu sur g1/c1 (ou g8/c8), ET le coup est légal

```python
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

:::note
Seul le mouvement du roi est transmis à `play_human_move()`. python-chess déduit automatiquement que la tour doit aussi bouger.
:::

## Gestion des faux positifs

### Stabilisation temporelle

Un changement doit persister sur **3 frames consécutives** avant d'être validé comme coup :

```python
if stability_counter[square] >= STABILITY_THRESHOLD:
    # Valider le changement
```

### Filtrage par légalité

Avant de déclencher un coup, `sync_with_vision()` vérifie que le coup détecté est légal selon python-chess :

```python
move = chess.Move.from_uci(f"{from_sq}{to_sq}")
if move not in self.board.legal_moves:
    # Ignorer — peut être un artéfact visuel
    logger.warning(f"Coup illégal détecté par vision: {from_sq}{to_sq}")
    return
```

### Délai anti-rebond

Un délai minimal de **1 seconde** est imposé entre deux détections de coups pour éviter les doubles-déclenchements.

## Mise à jour de la référence

Après chaque coup (humain ou robot), la référence est mise à jour :

```python
# Après un coup robot
vision_service.update_reference_after_move(new_board_state)

# Après un coup humain (via play_human_move)
vision_service.reference_board = current_board_state
```

Cela évite que le robot "voit" son propre mouvement comme un coup humain.

## États de la vision

| `game_started` | `is_paused` | Comportement |
|---------------|-------------|--------------|
| `False` | — | Capture continue, pas de détection de coup |
| `True` | `False` | Détection active |
| `True` | `True` | Capture suspendue |
