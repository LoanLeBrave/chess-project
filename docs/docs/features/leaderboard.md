---
id: leaderboard
title: Classement
sidebar_position: 6
---

# Classement (Leaderboard)

Le classement affiche les 10 meilleurs joueurs triés par leur score **ACPL** (Average Centipawn Loss). Un score plus bas indique un meilleur joueur.

## Structure des données

Chaque joueur est représenté par un objet agrégé :

```typescript
interface PlayerScore {
  rank: number;      // Position dans le classement
  name: string;      // Prénom du joueur
  acpl: number;      // ACPL moyen (arrondi)
  games: number;     // Nombre total de parties
  wins: number;      // Victoires
  losses: number;    // Défaites
  abandoned: number; // Parties abandonnées
}
```

## Sauvegarde d'un score

À la fin d'une partie, le frontend appelle :

```http
POST /leaderboard/add
Content-Type: application/json

{
  "name": "Alice",
  "acpl": 45.3,
  "result": "win"   // "win" | "lose" | "abandoned"
}
```

**Résultats possibles :**

| `result` | Condition |
|----------|-----------|
| `"win"` | Le joueur humain a gagné (mat du robot) |
| `"lose"` | Le robot a gagné (mat du joueur) |
| `"abandoned"` | Partie arrêtée par l'opérateur |

### Agrégation

Si le joueur existe déjà, son ACPL est **moyenné** avec ses parties précédentes :

```python
new_acpl = (old_acpl * old_games + new_acpl) / (old_games + 1)
```

Les compteurs `wins`, `losses`, `abandoned` sont incrémentés.

## Récupération du classement

```http
GET /leaderboard?limit=10
```

**Réponse :**
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "name": "Bob",
      "acpl": 23,
      "games": 5,
      "wins": 3,
      "losses": 1,
      "abandoned": 1
    },
    ...
  ]
}
```

Le classement est trié par ACPL croissant (meilleur en premier).

## Interface utilisateur

L'écran leaderboard (`LeaderboardScreen.tsx`) :
- Se rafraîchit automatiquement toutes les **5 secondes**
- Affiche une icône tournante pendant le rafraîchissement
- Affiche les 3 premières places avec des icônes spéciales (🏆 or, 🥈 argent, 🥉 bronze)
- Fallback sur le localStorage si l'API est inaccessible

### Fallback localStorage

Si le backend est hors ligne, le frontend calcule le classement depuis les données locales :

```typescript
const leaderboardData = localStorage.getItem('chessLeaderboard');
// Aggrège les parties par joueur
// Trie par ACPL croissant
// Garde les 10 premiers
```

## Persistance

Les données sont stockées dans `leaderboard.json` (côté backend) :

```json
{
  "players": {
    "Alice": {
      "name": "Alice",
      "acpl": 45.3,
      "games": 3,
      "wins": 1,
      "losses": 2,
      "abandoned": 0,
      "date": "2025-03-04T10:30:00"
    }
  }
}
```

## Migration

Le `LeaderboardManager` inclut une migration automatique depuis l'ancien format (liste de parties individuelles) vers le nouveau format agrégé par joueur. La migration se déclenche au démarrage si l'ancien format est détecté.
