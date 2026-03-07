---
id: troubleshooting
title: Dépannage
sidebar_position: 3
---

# Dépannage

## Problèmes de connexion robot

### Symptôme : "Impossible de se connecter au robot"

**Causes possibles :**
1. Robot pas en mode Remote Control
2. Mauvaise adresse IP dans `config.py`
3. Robot éteint ou en erreur

**Diagnostic :**
```bash
# Vérifier que le robot est joignable
ping 192.168.1.100

# Vérifier le port RTDE
nc -zv 192.168.1.100 30004
```

**Solution :**
1. Sur le teach pendant UR : Settings → Network → Remote control → Enable
2. Vérifier `ROBOT_IP = "192.168.1.100"` dans `config.py`

---

### Symptôme : Robot se déconnecte pendant la partie

**Cause :** Timeout RTDE ou perte réseau temporaire.

**Solution :** Le système tente automatiquement 8 reconnexions. Si ça échoue, relancer le backend :
```bash
# Redémarrer le backend
pkill -f "python manipulation_robot/api.py"
python manipulation_robot/api.py
```

---

## Problèmes de vision

### Symptôme : La caméra ne détecte aucun mouvement

**Vérification 1 : Paramètres ArUco**

Vérifier dans `Backend/chess_vision/config.py` :
```python
# INVALIDE — Min doit être < Max
adaptiveThreshWinSizeMin = 24
adaptiveThreshWinSizeMax = 10

# CORRECT
adaptiveThreshWinSizeMin = 5
adaptiveThreshWinSizeMax = 51
```

**Vérification 2 : Saturation**

```python
# INVALIDE — image en niveaux de gris
CAMERA_SATURATION = 0

# CORRECT
CAMERA_SATURATION = None  # valeur par défaut
```

**Vérification 3 : game_started**

```bash
curl http://localhost:8000/game/state
# Vérifier "status": "playing" et non "idle"
```

---

### Symptôme : Faux coups détectés

**Cause :** Vibrations, reflets ou ombres.

**Solutions :**
- Améliorer l'éclairage (lumière diffuse, sans reflets)
- Augmenter `STABILITY_FRAMES` de 3 à 5
- Vérifier que les marqueurs ArUco ne sont pas endommagés

---

### Symptôme : Coups détectés en double

**Cause :** Le délai anti-rebond est trop court.

**Solution :** Augmenter le délai dans `chess_vision.py` :
```python
DEBOUNCE_DELAY = 2.0  # secondes (au lieu de 1.0)
```

---

## Problèmes de jeu

### Symptôme : "Coup illégal" au moment d'un roque

**Cause :** La vision a détecté le déplacement de la tour avant celui du roi.

**Solution :** Le Case 3 de `sync_with_vision()` gère ce cas. Vérifier que la version à jour de `chess_manager.py` est utilisée.

---

### Symptôme : ACPL toujours à 0

**Causes possibles :**
1. Stockfish n'est pas installé
2. Stockfish est à un chemin non standard

**Diagnostic :**
```bash
which stockfish
stockfish
# Doit afficher "Stockfish 16..." et attendre des commandes UCI
```

**Solution :**
```bash
sudo apt install stockfish
# ou télécharger depuis https://stockfishchess.org/download/
```

---

### Symptôme : Le classement n'affiche pas les scores

**Cause :** `showScoreSaved` n'est pas mis à jour, ou l'API retourne un format incorrect.

**Vérification :**
```bash
curl http://localhost:8000/leaderboard?limit=10
# Doit retourner: {"leaderboard": [...]}
# et NON: [...]
```

---

## Problèmes de pause/reprise

### Symptôme : Le robot ne reprend pas après une pause

**Cause :** Le `_resume_event` n'est jamais déclenché.

**Vérification :**
1. Vérifier si le WS a envoyé `resume_confirmation_needed`
2. Vérifier que `POST /game/confirm-resume` est appelé

```bash
curl -X POST http://localhost:8000/game/confirm-resume
```

---

### Symptôme : La pince reste fermée après reprise

**Cause :** `gripper.open()` dans `_resume_process()` a échoué silencieusement.

**Solution :**
```bash
# Tester la pince directement
curl -X POST http://localhost:8000/robot/gripper/open
```

---

## Problèmes frontend

### Symptôme : Page blanche au démarrage

**Cause :** Backend non démarré ou mauvais port.

**Solution :**
```bash
# Vérifier que le backend répond
curl http://localhost:8000/health
# Doit retourner: {"status": "ok"}
```

---

### Symptôme : WebSocket se déconnecte en boucle

**Cause :** Erreur backend qui ferme la connexion.

**Solution :** Vérifier les logs backend pour trouver l'exception.

```bash
python manipulation_robot/api.py 2>&1 | tee chess.log
```

---

## Logs utiles

### Niveau de log

```python
# api.py — augmenter la verbosité
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Endpoints de diagnostic

```bash
# État complet
curl http://localhost:8000/status

# État vision
curl http://localhost:8000/vision/board-state

# Image annotée
curl http://localhost:8000/vision/debug-frame -o debug.jpg
```
