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

## Documentation Interactive (Swagger & OpenAPI)

L'API utilise **FastAPI**, ce qui permet de générer automatiquement une documentation interactive et testable. C'est l'outil idéal pour explorer tous les points d'entrée (endpoints) disponibles, voir les schémas de données requis (JSON) et tester les requêtes en direct sans passer par le frontend.

Deux interfaces sont disponibles :

- **Swagger UI** : `http://<raspberry-pi-ip>:8000/docs`
  - Permet de tester les endpoints directement ("Try it out").
  - Affiche les exemples de requêtes et les modèles Pydantic.
  - Regroupe les endpoints par catégorie (Game, Robot, Vision, etc.).
- **ReDoc** : `http://<raspberry-pi-ip>:8000/redoc`
  - Documentation plus épurée et orientée lecture seule.

Le schéma complet au format OpenAPI est disponible sur `http://<raspberry-pi-ip>:8000/openapi.json`.

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
| `POST` | `/robot/calibrate/freedrive` | Activer/désactiver FreeDrive |
| `POST` | `/robot/calibrate/auto-level` | Verticaliser et fermer la pince |
| `POST` | `/robot/calibrate/point` | Enregistrer un point de calibration (a1, h8, z) |
| `POST` | `/robot/calibrate/save` | Calculer la géométrie et sauvegarder |
| `POST` | `/robot/calibrate/move-z/start` | Démarrer déplacement Z continu |
| `POST` | `/robot/calibrate/move-z/stop` | Stopper déplacement Z |
| `GET` | `/robot/position` | Lire la position TCP |

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
