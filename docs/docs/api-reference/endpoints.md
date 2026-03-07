---
id: endpoints
title: Vue d'ensemble des endpoints
sidebar_position: 1
---

# Référence API — Vue d'ensemble

Le backend expose une API REST sur le port **8000** et un WebSocket sur `/ws`.

## URL de base

```
http://<raspberry-pi-ip>:8000
```

## Endpoints par catégorie

### Jeu

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/game/start` | Démarrer une nouvelle partie |
| `POST` | `/game/stop` | Arrêter la partie |
| `POST` | `/game/move` | Jouer un coup manuel |
| `POST` | `/game/toggle-pause` | Mettre en pause / reprendre |
| `POST` | `/game/confirm-resume` | Confirmer la reprise (pièce replacée) |
| `POST` | `/game/promotion` | Choisir la pièce de promotion |
| `GET` | `/game/state` | État actuel de la partie |
| `GET` | `/game/legal-moves/{square}` | Coups légaux depuis une case |
| `POST` | `/game/replace-pieces` | Remettre les pièces en position initiale |

### Robot

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/robot/connect` | Connecter le robot |
| `POST` | `/robot/disconnect` | Déconnecter le robot |
| `POST` | `/robot/freedrive` | Activer/désactiver FreeDrive |
| `POST` | `/robot/move-z` | Déplacer l'axe Z |
| `GET` | `/robot/position` | Lire la position TCP |
| `POST` | `/robot/save-calibration` | Sauvegarder la calibration |

### Vision

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/vision/board-state` | État actuel de la grille |
| `GET` | `/vision/debug-frame` | Frame avec annotations |
| `POST` | `/vision/capture-reference` | Capturer un état de référence |

### Leaderboard

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/leaderboard` | Obtenir le classement |
| `POST` | `/leaderboard/add` | Ajouter un score |
| `DELETE` | `/leaderboard/reset` | Réinitialiser le classement |

### Système

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Vérification de santé |
| `GET` | `/status` | État global du système |

## Formats de réponse

### Succès

```json
{
  "status": "ok",
  "data": { ... }
}
```

### Erreur

```json
{
  "status": "error",
  "message": "Description de l'erreur"
}
```

## CORS

L'API autorise les requêtes depuis toutes les origines (développement) :

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## WebSocket

```
ws://<raspberry-pi-ip>:8000/ws
```

Voir [WebSocket](/api-reference/websocket) pour le détail des messages.
