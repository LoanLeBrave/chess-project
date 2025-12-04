# ♔ Robot Échecs Autonome - UR5e + Stockfish

Système complet permettant à un robot UR5e équipé d'un gripper Robotiq Hand-E de jouer aux échecs contre lui-même, avec analyse Stockfish et visualisations en temps réel.

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture du système](#architecture-du-système)
3. [Prérequis](#prérequis)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Utilisation](#utilisation)
7. [Niveaux de difficulté](#niveaux-de-difficulté)
8. [Visualisations](#visualisations)
9. [Structure des fichiers](#structure-des-fichiers)
10. [Dépannage](#dépannage)

---

## Vue d'ensemble

Ce projet permet à un bras robotique UR5e de jouer une partie d'échecs complète contre lui-même. Le système utilise :

- **Stockfish** : Moteur d'échecs pour calculer les coups des deux joueurs
- **Niveaux configurables** : Chaque joueur (Blancs/Noirs) peut avoir un niveau différent
- **Contrôle robot** : Déplacement physique des pièces via RTDE
- **Visualisations SVG** : Génération automatique d'images de chaque position

```
┌─────────────────────────────────────────────────────────────────┐
│                      FLUX DE FONCTIONNEMENT                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │ Position │───▶│ Stockfish│───▶│  Robot   │───▶│   SVG    │ │
│   │ actuelle │    │ (analyse)│    │ (déplace)│    │ (visuel) │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│        │                                               │        │
│        └───────────────────────────────────────────────┘        │
│                        Boucle de jeu                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture du système

### Composants matériels

| Composant | Modèle | Rôle |
|-----------|--------|------|
| Bras robotique | Universal Robots UR5e | Manipulation des pièces |
| Gripper | Robotiq Hand-E | Préhension des pièces |
| Ordinateur | Raspberry Pi 5 | Exécution du code |
| Échiquier | Plateau transparent | Surface de jeu |

### Composants logiciels

```
chess_robot_self_play.py          # Script principal
├── StockfishPlayer               # Gestion des joueurs IA
├── ChessGameVisualizer           # Génération des SVG/HTML
└── ChessRobotSelfPlay            # Contrôleur de partie

chess_robot_control.py            # Contrôle robot (existant)
├── ChessRobotPlayer              # Interface robot
└── Mouvements (prendre/poser)    # Actions physiques

chess_board_positions.json        # Mapping des cases (existant)
└── Positions TCP de a1 à h8      # Coordonnées robot
```

---

## Prérequis

### Matériel
- Robot UR5e connecté au réseau (IP par défaut : `192.168.0.11`)
- Gripper Robotiq Hand-E installé et calibré
- Échiquier avec mapping des cases effectué

### Logiciel
- Python 3.8+
- Stockfish installé sur le système
- Bibliothèques Python requises

---

## Installation

### 1. Installer Stockfish

```bash
# Ubuntu/Debian
sudo apt-get install stockfish

# macOS
brew install stockfish

# Vérifier l'installation
stockfish --version
```

### 2. Installer les dépendances Python

```bash
pip install python-chess
pip install ur_rtde          # Pour le contrôle robot
```

### 3. Copier les scripts

Placez les fichiers suivants dans le même répertoire :
- `chess_robot_self_play.py`
- `chess_robot_control.py` (votre script existant)
- `chess_board_positions.json` (mapping des cases)

---

## Configuration

### Fichier de mapping requis

Le fichier `chess_board_positions.json` doit contenir les positions TCP de chaque case. Ce fichier est généré par le script `chess_board_mapping.py`.

Structure attendue :
```json
{
  "cases": {
    "a1": {"tcp": [x, y, z, rx, ry, rz], "joints": [...]},
    "a2": {"tcp": [...], "joints": [...]},
    ...
    "h8": {"tcp": [...], "joints": [...]}
  },
  "position_securite_globale": [x, y, z, rx, ry, rz],
  "delta_hauteur_securite": 0.08,
  "delta_hauteur_approche": 0.03,
  "delta_hauteur_relache": 0.002
}
```

### Configuration réseau robot

Par défaut, le robot est attendu à l'IP `192.168.0.11`. Modifiable via l'argument `--robot-ip`.

---

## Utilisation

### Commandes de base

```bash
# Afficher l'aide complète
python chess_robot_self_play.py --help

# Afficher les niveaux disponibles
python chess_robot_self_play.py --list-levels
```

### Lancer une partie

```bash
# Partie avec niveaux prédéfinis
python chess_robot_self_play.py --blanc facile --noir expert

# Partie avec niveaux personnalisés (skill 0-20)
python chess_robot_self_play.py --blanc-skill 5 --noir-skill 18

# Mode simulation (sans robot physique)
python chess_robot_self_play.py --simulate --blanc debutant --noir maitre
```

### Options avancées

| Option | Description | Défaut |
|--------|-------------|--------|
| `--blanc <niveau>` | Niveau du joueur blanc | `intermediaire` |
| `--noir <niveau>` | Niveau du joueur noir | `intermediaire` |
| `--blanc-skill <0-20>` | Skill personnalisé blancs | - |
| `--noir-skill <0-20>` | Skill personnalisé noirs | - |
| `--max-coups <n>` | Limite de coups | `100` |
| `--delai <s>` | Délai entre coups | `0.5` |
| `--simulate` | Mode simulation | `false` |
| `--stockfish <path>` | Chemin vers Stockfish | Auto-détection |
| `--mapping <file>` | Fichier de mapping | `chess_board_positions.json` |
| `--robot-ip <ip>` | IP du robot | `192.168.0.11` |
| `--output-dir <dir>` | Dossier des visualisations | `game_visualizations` |

### Exemples de parties

```bash
# 🎮 Partie débutant vs débutant (partie équilibrée, niveau faible)
python chess_robot_self_play.py --blanc debutant --noir debutant

# 🏆 Partie déséquilibrée (le joueur fort devrait gagner)
python chess_robot_self_play.py --blanc debutant --noir maitre

# ⚔️ Combat de titans (deux joueurs très forts)
python chess_robot_self_play.py --blanc expert --noir maitre --delai 2

# 🧪 Test rapide en simulation
python chess_robot_self_play.py --simulate --blanc facile --noir avance --max-coups 20

# 🤖 Partie réelle sur le robot avec pause entre chaque coup
python chess_robot_self_play_complete.py --blanc intermediaire --noir avance --pause
```

---

## Niveaux de difficulté

Le système propose 6 niveaux prédéfinis correspondant à différentes forces de jeu :

| Niveau | Skill Level | Profondeur | Temps | Elo estimé | Description |
|--------|-------------|------------|-------|------------|-------------|
| `debutant` | 3 | 8 | 0.5s | 800-1000 | Joue comme un débutant, fait des erreurs |
| `facile` | 6 | 10 | 0.8s | 1000-1200 | Joueur occasionnel |
| `intermediaire` | 10 | 12 | 1.0s | 1400-1600 | Joueur de club amateur |
| `avance` | 15 | 15 | 1.5s | 1800-2000 | Joueur de club confirmé |
| `expert` | 18 | 18 | 2.0s | 2000-2200 | Niveau candidat maître |
| `maitre` | 20 | 22 | 3.0s | 2200+ | Force maximale |

### Personnalisation fine

Vous pouvez définir des niveaux personnalisés avec `--blanc-skill` et `--noir-skill` :

```bash
# Blancs skill 7, Noirs skill 14
python chess_robot_self_play.py --blanc-skill 7 --noir-skill 14
```

Le **Skill Level** de Stockfish (0-20) influence directement la qualité des coups :
- **0-5** : Fait régulièrement des erreurs tactiques
- **6-10** : Joue de façon raisonnable mais rate des opportunités
- **11-15** : Jeu solide, peu d'erreurs graves
- **16-20** : Jeu quasi-optimal

---

## Visualisations

### Fichiers générés

Pour chaque partie, le système génère :

```
game_visualizations/
├── move_001_start.svg       # Position initiale
├── move_001_start.html      # Version HTML enrichie
├── move_002_e2e4.svg        # Coup 1 des blancs
├── move_002_e2e4.html
├── move_003_e7e5.svg        # Coup 1 des noirs
├── move_003_e7e5.html
├── ...
└── game_summary.html        # Résumé de la partie
```

### Contenu des visualisations

**Fichiers SVG** : Image pure du plateau avec :
- Position des pièces
- Flèche verte indiquant le dernier coup
- Coordonnées du plateau

**Fichiers HTML** : Vue enrichie avec :
- Numéro du coup
- Notation du coup (ex: "E2E4")
- Évaluation Stockfish
- Informations des deux joueurs (nom, niveau, Elo estimé)
- Indicateur du joueur au trait

### Exemple de visualisation HTML

```
┌────────────────────────────────────┐
│           COUP 15                  │
│          F6H7                      │
│        Eval: +1.25                 │
├────────────────────────────────────┤
│                                    │
│    [  Plateau d'échecs SVG  ]      │
│    [  avec flèche du coup   ]      │
│                                    │
├────────────────────────────────────┤
│  ♔ Blancs          ♚ Noirs        │
│  Robot Blancs      Robot Noirs     │
│  Skill 6 • ~1100   Skill 15 • ~1900│
├────────────────────────────────────┤
│      Au tour des Blancs            │
└────────────────────────────────────┘
```

---

## Structure des fichiers

```
projet/
│
├── 📄 chess_robot_self_play.py        # Script principal (ce README)
├── 📄 chess_robot_self_play_complete.py # Version avec intégration robot complète
│
├── 📄 chess_robot_control.py          # Contrôle robot pour les mouvements
├── 📄 chess_board_mapping.py          # Mapping des cases (à exécuter d'abord)
├── 📄 robotiq_gripper_control.py      # Contrôle du gripper
│
├── 📄 chess_board_positions.json      # Positions TCP des 64 cases
│
├── 📄 chess_analysis.py               # Analyse Stockfish (optionnel)
├── 📁 positions/                      # Positions JSON pour tests
│
└── 📁 game_visualizations/            # Dossier de sortie (créé automatiquement)
    ├── move_001_start.svg
    ├── move_001_start.html
    ├── ...
    └── game_summary.html
```

---

## Dépannage

### Stockfish non trouvé

```
⚠ Stockfish non trouvé - Mode simulation activé
```

**Solutions :**
1. Installer Stockfish : `sudo apt-get install stockfish`
2. Spécifier le chemin : `--stockfish /chemin/vers/stockfish`
3. Vérifier que Stockfish est dans le PATH : `which stockfish`

### Robot non connecté

```
⚠ Robot non disponible - Simulation activée
```

**Solutions :**
1. Vérifier que le robot est allumé et connecté au réseau
2. Vérifier l'IP : `ping 192.168.0.11`
3. Vérifier que le robot est en mode Remote Control
4. Utiliser `--robot-ip` si l'IP est différente

### Fichier de mapping non trouvé

```
⚠ Fichier de mapping non trouvé: chess_board_positions.json
```

**Solutions :**
1. Exécuter d'abord le script de mapping : `python chess_board_mapping.py`
2. Spécifier le bon chemin : `--mapping /chemin/vers/mapping.json`

### Erreur lors d'un mouvement robot

```
⚠ Erreur robot: [détails]
```

**Solutions :**
1. Vérifier que toutes les cases utilisées sont mappées
2. Vérifier que le robot n'est pas en arrêt d'urgence
3. Vérifier que le gripper est activé
4. Relancer le mapping si les positions ont changé

---

## Exemples de sorties console

### Démarrage d'une partie

```
======================================================================
     ♔ ROBOT ÉCHECS - MODE JEU AUTONOME ♚
======================================================================

Configuration des joueurs:
  ♔ Robot Blancs (Blancs) - Skill=6, Depth=10, Elo≈~1100
  ♚ Robot Noirs (Noirs) - Skill=15, Depth=15, Elo≈~1900

✓ Stockfish chargé: /usr/games/stockfish
✓ Mapping chargé: 64 cases

======================================================================
                    ♔ PARTIE D'ÉCHECS ROBOT ♚
======================================================================
```

### Pendant la partie

```
──────────────────────────────────────────────────
  Coup 12 - Robot Noirs (Noirs)
──────────────────────────────────────────────────
   📍 Coup: d7d5 (d5)
   📊 Évaluation: -0.35
   🤖 Déplacement: d7 → d5
   📊 Visualisation: move_013_d7d5.svg
```

### Fin de partie

```
======================================================================
                    FIN DE PARTIE: Échec et mat! Noirs gagnent
======================================================================

📋 Résumé de la partie: game_visualizations/game_summary.html

✓ Partie terminée!
  Résultat: Échec et mat! Noirs gagnent
  Visualisations: game_visualizations/
```

---

## Licence

Ce projet est développé dans le cadre d'un projet robotique personnel.

---

## Contact

Pour toute question ou amélioration, n'hésitez pas à contribuer au projet.

---

*Dernière mise à jour : Décembre 2025*