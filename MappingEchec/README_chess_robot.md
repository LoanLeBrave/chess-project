# Système de Mapping et Contrôle Robot pour Échecs

Ce système permet de mapper toutes les cases d'un échiquier avec un robot UR5e équipé d'un gripper Robotiq Hand-E, puis d'utiliser ce mapping pour déplacer automatiquement les pièces.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. MAPPING (chess_board_mapping.py)                           │
│      ┌──────────┐     ┌──────────┐     ┌──────────────────┐    │
│      │ Freedrive │ ──▶ │ Position │ ──▶ │ chess_board_     │    │
│      │ manuel    │     │ + ESPACE │     │ positions.json   │    │
│      └──────────┘     └──────────┘     └──────────────────┘    │
│                                                                  │
│   2. JEU (chess_robot_player.py)                                │
│      ┌──────────────────┐     ┌────────────┐     ┌─────────┐   │
│      │ chess_board_     │ ──▶ │ Commande   │ ──▶ │ Robot   │   │
│      │ positions.json   │     │ (ex: e2e4) │     │ exécute │   │
│      └──────────────────┘     └────────────┘     └─────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Fichiers

| Fichier | Description |
|---------|-------------|
| `chess_board_mapping.py` | Script de mapping en mode freedrive |
| `chess_robot_player.py` | Script de contrôle pour jouer |
| `chess_board_positions.json` | Données de mapping (généré) |
| `robotiq_gripper_control.py` | Module de contrôle du gripper (existant) |

## 1. Mapping de l'échiquier

### Lancement

```bash
python chess_board_mapping.py
```

### Procédure recommandée

1. **Position initiale** : Place le robot dans une position de sécurité au-dessus de l'échiquier
2. **Enregistre la position d'approche** : Appuie sur `p` - c'est la position de sécurité
3. **Active le freedrive** : Appuie sur `f`
4. **Pour chaque case** :
   - Déplace manuellement le robot vers le centre de la case
   - Descends jusqu'à la hauteur de prise d'une pièce
   - Appuie sur `ESPACE` pour enregistrer et passer à la case suivante
   - Teste le gripper avec `t` si nécessaire

### Commandes de mapping

| Touche | Action |
|--------|--------|
| `f` | Activer/désactiver freedrive |
| `ESPACE` | Enregistrer case + passer à la suivante |
| `ENTRÉE` | Enregistrer case sans avancer |
| `n` | Saisir une case spécifique (ex: e4) |
| `p` | Enregistrer position d'approche |
| `→/←` | Case suivante/précédente |
| `↑/↓` | Rangée suivante/précédente |
| `g` | Toggle gripper |
| `t` | Test de préhension |
| `m` | Afficher grille de progression |
| `i` | Position TCP actuelle |
| `s` | Sauvegarder le mapping |
| `h` | Aide |
| `ESC/q` | Quitter (sauvegarde auto) |

### Ordre de mapping suggéré

```
a1 → b1 → c1 → d1 → e1 → f1 → g1 → h1
a2 → b2 → c2 → d2 → e2 → f2 → g2 → h2
...
a8 → b8 → c8 → d8 → e8 → f8 → g8 → h8
```

Le script avance automatiquement dans cet ordre après chaque `ESPACE`.

## 2. Contrôle pour jouer

### Lancement

```bash
# Mode interactif (défaut)
python chess_robot_player.py

# Exécuter un coup directement
python chess_robot_player.py -c e2e4

# Tester une case
python chess_robot_player.py -t e4

# Utiliser un autre fichier de mapping
python chess_robot_player.py -f mon_mapping.json
```

### Mode interactif - Commandes

| Commande | Description | Exemple |
|----------|-------------|---------|
| `<coup>` | Exécuter un coup | `e2e4`, `e4xd5` |
| `go <case>` | Aller à une case | `go e4` |
| `test <case>` | Tester une case | `test d4` |
| `take <case>` | Prendre pièce | `take e2` |
| `drop <case>` | Poser pièce | `drop e4` |
| `open` | Ouvrir gripper | |
| `close` | Fermer gripper | |
| `home` | Position sécurité | |
| `map` | Afficher cases | |
| `pos` | Position actuelle | |
| `quit` | Quitter | |

### Format des coups

```
e2e4      # Déplacement simple
e2-e4     # Avec tiret (équivalent)
e4xd5     # Capture (retire d5, déplace e4→d5)
```

## Structure du fichier JSON

```json
{
  "cases": {
    "e4": {
      "tcp": [x, y, z, rx, ry, rz],
      "joints": [j1, j2, j3, j4, j5, j6],
      "timestamp": "2024-01-01T12:00:00"
    }
  },
  "position_approche": [x, y, z, rx, ry, rz],
  "hauteur_securite": 0.08,
  "hauteur_approche": 0.03,
  "hauteur_prise": 0.0,
  "metadata": {
    "date_creation": "...",
    "robot_ip": "192.168.0.11",
    "nb_cases": 64
  }
}
```

## Séquence de mouvement pour prise de pièce

```
Position initiale
        │
        ▼
┌───────────────────┐
│ 1. Approche case  │  (hauteur_approche au-dessus)
│    (moveL)        │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 2. Descente       │  (hauteur_prise)
│    (moveL)        │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 3. Fermer gripper │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 4. Remontée       │  (hauteur_approche)
│    (moveL)        │
└───────────────────┘
        │
        ▼
    Pièce prise ✓
```

## Paramètres ajustables

Dans `chess_robot_player.py` :

```python
VITESSE_JOINTS = 0.5       # rad/s
ACCELERATION_JOINTS = 0.3  # rad/s²
VITESSE_LINEAIRE = 0.1     # m/s
ACCELERATION_LINEAIRE = 0.3  # m/s²

HAUTEUR_SECURITE = 0.08    # 8cm au-dessus
HAUTEUR_APPROCHE = 0.03    # 3cm au-dessus
HAUTEUR_PRISE = 0.0        # Position de prise
```

## Conseils

### Pour un bon mapping

1. **Cohérence** : Garde la même orientation du gripper pour toutes les cases
2. **Hauteur** : Enregistre les positions à la hauteur de prise (pas au-dessus)
3. **Centre** : Vise bien le centre de chaque case
4. **Test** : Utilise `t` pour vérifier que le gripper peut saisir une pièce

### Calibration

- La position d'approche doit être assez haute pour passer au-dessus de toutes les pièces
- `hauteur_approche` (3cm) doit permettre d'éviter les collisions avec les pièces voisines
- `hauteur_prise` (0) correspond au point où le gripper peut saisir les pièces

## Intégration avec Stockfish

Pour une partie complète, tu peux combiner avec ton analyse Stockfish :

```python
from chess_robot_player import ChessRobotPlayer

robot = ChessRobotPlayer()

# Recevoir un coup de Stockfish
coup_stockfish = "e2e4"  # Format UCI

# Exécuter le coup
robot.executer_coup(coup_stockfish)
```

## Dépannage

| Problème | Solution |
|----------|----------|
| Case non mappée | Utiliser le script de mapping pour ajouter la case |
| Gripper ne saisit pas | Ajuster `hauteur_prise` ou la force du gripper |
| Collision avec pièces | Augmenter `hauteur_approche` |
| Robot trop lent | Augmenter `VITESSE_LINEAIRE` |
