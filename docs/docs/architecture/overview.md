---
id: overview
title: Vue d'ensemble
sidebar_position: 1
---

# Architecture — Vue d'ensemble

## Diagramme général

![Architecture générale du Chess Robot](/img/architecture_overview.svg)

## Couches logicielles

### 1. Couche présentation (Frontend)
L'interface utilisateur React communique avec le backend via :
- **WebSocket** `/ws` — état du jeu en temps réel (coups, status, ACPL)
- **REST API** — actions ponctuelles (démarrer, pause, arrêt, calibration)

### 2. Couche application (api.py)

`api.py` est le point d'entrée du backend. Il instancie et orchestre :
- `ApplicationManager` — gère le cycle de vie de l'application et les connexions WebSocket
- `VisionService` — thread de vision en arrière-plan, capture + analyse l'échiquier
- `ChessManager` — logique de jeu
- `RobotController` — commandes hardware

### 3. Couche métier

| Module | Responsabilité |
|--------|---------------|
| `ChessManager` | Arbitre des règles, Stockfish, gestion des tours |
| `RobotController` | Séquences de mouvement, prise/pose de pièces |
| `LeaderboardManager` | Persistance et agrégation des scores |

### 4. Couche matérielle

- **UR5e** via RTDE (`rtde_control`, `rtde_receive`) — commandes de mouvement
- **Robotiq gripper** — prise/release des pièces
- **Caméra Raspberry Pi** — capture vidéo continue

## Principes de conception

### Asynchronisme
Tout le backend est `async` (FastAPI + asyncio). Les appels bloquants RTDE sont wrappés dans `asyncio.run_in_executor` pour ne pas bloquer la boucle d'événements.

### Communication temps réel
Le WebSocket diffuse (`broadcast`) tous les événements de jeu aux clients connectés. Cela permet à l'UI de réagir immédiatement sans polling.

### Résilience
- Reconnexion robot : 8 tentatives avec délai de 3s
- Timeout par tentative : 12s
- Pattern `asyncio.Event` pour les opérations longues (pause, promotion)

## Pages suivantes

- [Composants détaillés](/architecture/components)
- [Flux de données](/architecture/data-flow)
