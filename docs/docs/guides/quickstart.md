---
id: quickstart
title: Démarrage rapide
sidebar_position: 1
---

# Démarrage rapide

Ce guide permet de lancer le système Chess Robot en moins de 5 minutes.

## Pré-requis

- Raspberry Pi 4 (ou 5) avec Python 3.11+
- Robot UR5e connecté sur le réseau local
- Caméra Raspberry Pi connectée
- Node.js 18+ pour le frontend

## 1. Cloner le projet

```bash
git clone https://github.com/junia/chess-robot.git
cd chess-robot
```

## 2. Démarrer le backend

```bash
cd Backend
pip install -r requirements.txt

# Installer Stockfish
sudo apt install stockfish

# Lancer le backend
python manipulation_robot/api.py
```

Le backend démarre sur `http://0.0.0.0:8000`.

**Logs attendus :**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     VisionService started
```

## 3. Démarrer le frontend

```bash
cd Frontend
npm install
npm run dev
```

Le frontend est accessible sur `http://localhost:5173`.

## 4. Première utilisation

### Connexion au robot

1. Ouvrir l'interface web
2. Aller dans **Calibration**
3. Cliquer **Connecter le robot**
4. Vérifier que le robot est en mode `Remote Control` sur le teach pendant

### Calibration (si première installation)

1. Activer **FreeDrive**
2. Guider le robot vers le coin a1 de l'échiquier
3. Cliquer **Enregistrer a1**
4. Répéter pour h1, a8, h8
5. Ajuster le Z avec les boutons `Z+` / `Z-`
6. Cliquer **Sauvegarder**

### Lancer une partie

1. Retourner à l'écran d'accueil
2. Saisir votre prénom
3. Choisir la difficulté (Débutant / Intermédiaire / Avancé)
4. Cliquer **Jouer**

## 5. Déroulement d'une partie

1. Les blancs jouent en premier (par défaut)
2. Déplacez physiquement une pièce → la caméra détecte votre coup (~2s)
3. Le robot réfléchit puis joue son coup
4. En cas de promotion, choisissez la pièce dans l'interface
5. La partie se termine par mat, pat ou abandon

## Raccourcis utiles

| Action | Interface |
|--------|-----------|
| Pause | Bouton ⏸ dans GameScreen |
| Arrêt | Bouton ⏹ → confirmation |
| Mode manuel | Cliquer une case de départ + destination |
| Classement | Menu principal → Classement |

## Variables d'environnement

```bash
# Backend/.env (optionnel)
ROBOT_IP=192.168.1.100
STOCKFISH_PATH=/usr/bin/stockfish
LEADERBOARD_FILE=leaderboard.json
```

## Résolution de problèmes rapide

| Symptôme | Solution |
|----------|---------|
| Robot ne répond pas | Vérifier le mode Remote sur teach pendant |
| Vision ne détecte pas | Vérifier l'éclairage, nettoyer les marqueurs |
| ACPL = 0 toujours | Vérifier que Stockfish est installé |
| Frontend vide | Vérifier que le backend tourne sur :8000 |

Voir le [guide de dépannage complet](/guides/troubleshooting).
