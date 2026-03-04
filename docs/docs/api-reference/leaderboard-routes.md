---
id: leaderboard-routes
title: Routes classement
sidebar_position: 5
---

# Routes classement

## `GET /leaderboard`

Récupère le classement des joueurs.

**Paramètres de requête :**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `limit` | `int` | `10` | Nombre de joueurs à retourner |

**Exemple :** `GET /leaderboard?limit=10`

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
    {
      "rank": 2,
      "name": "Alice",
      "acpl": 45,
      "games": 3,
      "wins": 1,
      "losses": 2,
      "abandoned": 0
    }
  ]
}
```

Le classement est trié par `acpl` croissant (meilleur score en premier).

---

## `POST /leaderboard/add`

Ajoute ou met à jour un score joueur.

**Corps :**
```json
{
  "name": "Alice",
  "acpl": 45.3,
  "result": "win"
}
```

| Paramètre | Type | Valeurs | Description |
|-----------|------|---------|-------------|
| `name` | `string` | — | Prénom du joueur |
| `acpl` | `float` | ≥ 0 | Score ACPL de la partie |
| `result` | `string` | `win`, `lose`, `abandoned` | Résultat de la partie |

**Comportement :**
- Si le joueur **n'existe pas** → créé avec les stats de cette partie
- Si le joueur **existe déjà** → ACPL moyenné, compteurs incrémentés

**Réponse :**
```json
{
  "status": "ok",
  "player": {
    "name": "Alice",
    "acpl": 42,
    "games": 4,
    "wins": 2,
    "losses": 2,
    "abandoned": 0
  }
}
```

---

## `DELETE /leaderboard/reset`

Réinitialise complètement le classement.

:::danger
Cette opération est irréversible. Toutes les données de classement sont supprimées.
:::

**Réponse :**
```json
{
  "status": "ok",
  "message": "Classement réinitialisé"
}
```

---

## Calcul ACPL

L'**Average Centipawn Loss** est calculé côté backend à chaque coup humain :

```
ACPL = moyenne des CPL sur tous les coups humains de la partie

CPL_i = max(0, eval_avant_coup_i - eval_après_coup_i)
```

Un ACPL de **0** signifie que le joueur a toujours joué le meilleur coup.
Un ACPL de **100+** indique un jeu approximatif.

| ACPL | Niveau indicatif |
|------|-----------------|
| 0–10 | Expert / Maître |
| 10–30 | Joueur avancé |
| 30–60 | Joueur intermédiaire |
| 60–100 | Débutant avancé |
| 100+ | Débutant |
