# ⚠️ OBSOLÈTE - NE PAS UTILISER

Ce fichier `game_state.json` à la racine du projet est **obsolète** et n'est **pas** utilisé par le système.

## Fichier correct à utiliser

Le vrai fichier de state mis à jour en temps réel est :

```
Backend/chess_vision/output/latest/game_state.json
```

où `latest` est un **symlink** qui pointe vers `data_1` ou `data_2` en ping-pong pour éviter les corruptions lors de la lecture/écriture simultanée.

## Pourquoi ce fichier existe-t-il ?

Résidu d'anciennes versions du code. Il peut être supprimé sans impact.

## Systèmes utilisant le bon chemin

- `test_camera_robot` : lit depuis `output/latest/game_state.json`
- `infinite_chess_vision` : écrit dans `output/data_X/game_state.json` puis met à jour le symlink `latest`
- Frontend (si applicable) : doit lire depuis `output/latest/game_state.json`

## Migration

Si vous utilisez encore ce fichier quelque part, changez le chemin vers :

```python
GAME_STATE_PATH = os.path.join(BACKEND_DIR, "chess_vision", "output", "latest", "game_state.json")
```
