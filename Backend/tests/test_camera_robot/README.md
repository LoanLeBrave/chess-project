# Test Camera-Robot

Interface de test pour le système vision-robot avec rafraîchissement automatique.

## Architecture

```
test_camera_robot/
├── __init__.py        # Package marker
├── __main__.py        # Point d'entrée
├── config.py          # Constantes et mappings
├── board_reader.py    # Lecture de game_state.json
├── board_display.py   # Rendu ASCII du plateau
├── robot_bridge.py    # Interface vers RobotController
├── terminal_ui.py     # Gestion affichage terminal (ANSI)
└── cli.py             # Boucle interactive + commandes
```

## Fonctionnement

Le système utilise deux tâches asynchrones :

1. **Rafraîchissement automatique** (1 Hz)
   - Lit `game_state.json` toutes les secondes
   - Met à jour l'affichage du plateau en temps réel
   - Affiche les métadonnées (nombre de pièces, fraîcheur des données)

2. **Gestion des commandes**
   - Zone de saisie stable en bas de l'écran
   - Permet de taper sans perturber l'affichage du plateau
   - Traite les commandes utilisateur

## Prérequis

- `infinite_chess_vision.py` doit tourner en parallèle pour mettre à jour `game_state.json`
- Robot UR5e allumé et calibré
- Fichier `robot_calibration.json` présent dans `manipulation_robot/`

## Lancement

### Méthode 1 : Script automatique (recommandé)

```bash
cd Backend/
./start_test_camera_robot.sh
```

Ce script lance automatiquement :
1. `infinite_chess_vision.py` en arrière-plan (mise à jour du JSON)
2. `test_camera_robot` au premier plan (interface interactive)

À l'arrêt (Ctrl+C ou `quit`), les deux processus sont terminés proprement.

### Méthode 2 : Manuel (deux terminaux)

Terminal 1 - Vision :
```bash
cd Backend/
python3 -m chess_vision.infinite_chess_vision
```

Terminal 2 - Robot :
```bash
cd Backend/
python -m test_camera_robot
```

## Commandes

| Commande | Alias | Description |
|----------|-------|-------------|
| `e2 e4` ou `e2e4` | - | Déplacer une pièce (notation algébrique) |
| `refresh` | `r`, `p`, `photo`, `capture` | Forcer la lecture du JSON |
| `status` | `s`, `info` | Afficher métadonnées détaillées |
| `help` | `h`, `?` | Afficher l'aide |
| `quit` | `q`, `exit` | Quitter le programme |

## Interface

```
    a   b   c   d   e   f   g   h
  +---+---+---+---+---+---+---+---+
8 | r | n | b | q | k | b | n | r | 8
  +---+---+---+---+---+---+---+---+
7 | p | p | p | p | p | p | p | p | 7
  +---+---+---+---+---+---+---+---+
[...]
  +---+---+---+---+---+---+---+---+
    a   b   c   d   e   f   g   h

  13 pieces | Données à jour

  ------------------------------------------------------
> _
```

- **Zone supérieure** : Plateau (mis à jour automatiquement)
- **Ligne status** : Métadonnées
- **Ligne de commande** : Saisie stable (ne bouge jamais)

## Détails techniques

### Codes ANSI utilisés

- `\033[s` / `\033[u` : Sauvegarde/restauration position curseur
- `\033[H` : Retour en haut de l'écran
- `\033[2K` : Effacement de ligne
- `\033[{line};{col}H` : Positionnement absolu

### Gestion de l'input non-bloquant

Utilise `asyncio.run_in_executor()` pour lire stdin sans bloquer la tâche de rafraîchissement.

### Lecture du JSON

Contrairement à l'ancien script :
- ❌ **Avant** : Appel synchrone `chess_vision()` (capture photo + analyse)
- ✅ **Maintenant** : Lecture instantanée de `game_state.json` (mise à jour par `infinite_chess_vision.py`)

Avantages :
- Pas de temps d'attente pour la capture
- Affichage en temps réel des mouvements détectés
- Séparation des responsabilités (vision / contrôle robot)

## Évolutions possibles

- [ ] Historique des coups dans une zone dédiée
- [ ] Highlighting des pièces qui viennent de bouger
- [ ] Mode debug avec coordonnées caméra affichées
- [ ] Suggestions de coups (intégration moteur d'échecs)
- [ ] Replay des parties avec navigation temporelle
