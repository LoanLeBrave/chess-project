---
id: replacement
title: Remplacement des pièces
sidebar_position: 5
---

# Remplacement des pièces

Quand une partie est arrêtée (bouton STOP), l'opérateur peut demander au robot de **remettre toutes les pièces déplacées à leur position initiale**.

## Déclenchement

Via la modal de confirmation d'arrêt dans le Frontend :

```
Arrêter la partie ?
[x] Remettre les pièces en position initiale
[Annuler]  [Arrêter]
```

Si la case est cochée, le frontend appelle d'abord `/game/stop`, puis `/game/replace-pieces`.

```http
POST /game/replace-pieces
```

## Algorithme de remplacement

La méthode `_replacer_pieces_deplacees()` dans `chess_manager.py` compare l'état actuel de l'échiquier avec la position initiale et déplace chaque pièce hors-place.

### Étapes

```python
async def _replacer_pieces_deplacees(self):
    initial_board = chess.Board()  # position de départ standard

    # Trouver toutes les pièces déplacées
    for sq in chess.SQUARES:
        current_piece = self.board.piece_at(sq)
        initial_piece = initial_board.piece_at(sq)

        if current_piece == initial_piece:
            continue  # pièce déjà en bonne position

        # Cas 1: pièce manquante à sa case initiale
        if initial_piece and not current_piece:
            # Chercher où est cette pièce actuellement
            case_actuelle = find_piece_on_board(initial_piece)
            if case_actuelle:
                # Définir hauteur AVANT de prendre
                self.robot.piece_courante = initial_piece.piece_type

                # Prendre la pièce
                success = await self.robot._prendre_piece(case_actuelle)
                if not success or self.is_paused:
                    return

                # Poser à la case initiale
                success = await self.robot._poser_piece(case_initiale)
                if not success or self.is_paused:
                    return

                # Mettre à jour le board virtuel
                piece_obj = self.board.piece_at(parse_square(case_actuelle))
                self.board.remove_piece_at(parse_square(case_actuelle))
                self.board.set_piece_at(parse_square(case_initiale), piece_obj)
```

### Points clés

**Ordre des opérations :**
1. `piece_courante` doit être défini **avant** `_prendre_piece()` — sinon la mauvaise hauteur Z est utilisée
2. Le board virtuel est mis à jour **après** chaque déplacement — sinon la même pièce peut être trouvée deux fois
3. Les valeurs de retour de `_prendre_piece()` et `_poser_piece()` sont vérifiées — en cas d'échec, le remplacement s'arrête proprement

### Gestion de la pause

Si une pause est déclenchée pendant le remplacement, la méthode s'arrête proprement (`if self.is_paused: return`). L'opérateur devra relancer le remplacement manuellement.

## Limitations connues

| Limitation | Description |
|------------|-------------|
| Pions promus | Un pion promu en dame ne peut pas être automatiquement replacé comme pion |
| Pièces capturées | Les pièces dans le cimetière ne sont pas replacées automatiquement |
| Ordre de remplacement | Si l'échiquier est très désorganisé, des collisions peuvent survenir |

## Sécurité

- Si le robot ne peut pas attraper une pièce (`_prendre_piece()` retourne `False`), il s'arrête
- L'opérateur peut toujours remettre manuellement les pièces restantes
- Un message d'état est broadcasté à chaque fin de remplacement
