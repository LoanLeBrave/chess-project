---
id: index
title: Introduction
sidebar_position: 1
---

# Documentation du projet Chess Robot
Bienvenue dans la documentation du **Chess Robot**, un projet intégrant un bras robotique UR7e capable de jouer aux échecs de manière autonome contre un joueur humain. 
Avant de vous plonger dans les détails techniques du projet, nous vous invitons à parcourir la fiche des **concepts clés** pour comprendre les notions de base qui y sont abordées : **[Concepts clés](/concepts)**.

## Présentation du projet

Le Chess Robot combine :
- Un **bras robotique UR7e** (Universal Robots) pour manipuler les pièces d'échecs
- Un moteur **Stockfish** pour calculer les meilleurs coups
- Une **caméra Raspberry Pi** et des marqueurs **ArUco** pour détecter les mouvements du joueur
- Une **interface web React** pour configurer la partie et suivre le jeu en temps réel

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11, FastAPI, asyncio |
| Logique échecs | python-chess, Stockfish |
| Robot | RTDE (Real-Time Data Exchange), Robotiq gripper |
| Vision | OpenCV, ArUco markers, rpicam |
| Frontend | React 18, TypeScript, TailwindCSS |
| Communication | WebSocket (temps réel) + REST API |

## Structure du projet

```
chess-project/
├── Backend/
│   ├── manipulation_robot/     ← Cerveau du système
│   │   ├── api.py              ← FastAPI + VisionService + ApplicationManager
│   │   ├── chess_manager.py    ← Logique de jeu + Stockfish
│   │   ├── robot_controller.py ← Commandes robot UR7e
│   │   ├── leaderboard_manager.py ← Classement des joueurs
│   │   └── config.py           ← Configuration globale
│   └── chess_vision/           ← Pipeline de vision
│       ├── chess_vision.py     ← Détection ArUco + état échiquier
│       └── config.py           ← Paramètres caméra/ArUco
├── Frontend/
│   └── src/
│       ├── components/         ← Écrans UI
│       └── hooks/              ← useChessRobot.ts (WebSocket)
└── docs/                       ← Cette documentation
```

## Démarrage rapide

Consultez le [guide de démarrage rapide](/guides/quickstart) pour lancer le système en quelques minutes.

## Navigation

- **[Concepts clés](/concepts)** — Stockfish, niveaux de difficulté, ACPL, ArUco... les notions importantes expliquées simplement
- **[Architecture](/architecture/overview)** — Vue d'ensemble des composants et de leurs interactions
- **[Modules principaux](/core/chess-manager)** — Documentation détaillée de chaque module Python
- **[Fonctionnalités](/features/game-flow)** — Flux de jeu, pause/reprise, roque, promotion...
- **[Robot UR7e](/robot/movements)** — Mouvements, pince, calibration
- **[Vision](/chess-vision/aruco)** — Détection ArUco et synchronisation échiquier
- **[Référence API](/api-reference/endpoints)** — Tous les endpoints REST et WebSocket
- **[Guides](/guides/quickstart)** — Tutoriels pratiques et dépannage
