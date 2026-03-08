# Chess Robot API - Structure Modulaire

## 📁 Structure des Fichiers

```
.
├── config.py              # Configuration et constantes
├── models.py              # Modèles Pydantic et classes de données
├── robot_controller.py    # Contrôle du robot UR5e et gripper
├── chess_manager.py       # Logique du jeu d'échecs et Stockfish
├── api.py                 # Routes FastAPI et WebSocket
└── main.py                # Point d'entrée de l'application
```

## 📄 Description des Modules

### `config.py`
Contient toutes les constantes et configurations :
- Configuration du robot (IP, vitesses, hauteurs)
- Fichiers de données (mapping, positions)
- Hauteurs par type de pièce
- Niveaux de difficulté
- Position initiale des pièces
- Chemins Stockfish

### `models.py`
Définit les structures de données :
- `MoveRequest` : Requête de mouvement
- `GameConfig` : Configuration de partie
- `RobotPosition` : Position du robot
- `PieceEliminee` : Pièce capturée avec sa position de stockage

### `robot_controller.py`
Gère le contrôle physique du robot :
- Connexion RTDE au robot UR7e
- Contrôle du gripper Robotiq
- Mouvements de prise/pose de pièces
- Gestion des zones d'élimination
- Suivi des pièces capturées
- Reset du plateau

### `chess_manager.py`
Gère la logique du jeu :
- Plateau d'échecs virtuel
- Moteur Stockfish
- Validation des coups
- Calcul des meilleurs coups
- Gestion des parties
- Détection de fin de partie

### `api.py`
Définit l'API REST et WebSocket :
- Routes HTTP pour les actions
- WebSocket pour les mises à jour temps réel
- Gestion des clients connectés
- Orchestration entre robot et logique de jeu

### `main.py`
Point d'entrée de l'application :
- Démarrage du serveur uvicorn
- Affichage des informations de connexion

## 🔄 Flux de Données

```
Frontend (React)
    ↓ HTTP/WebSocket
api.py (ApplicationManager)
    ↓
chess_manager.py (ChessManager) ←→ robot_controller.py (RobotController)
    ↓                                        ↓
Stockfish                              Robot UR5e + Gripper
```

## 🚀 Utilisation

### Démarrage
```bash
python main.py
```

### Import dans d'autres modules
```python
from config import ROBOT_IP, VITESSE
from models import MoveRequest, PieceEliminee
from robot_controller import RobotController
from chess_manager import ChessManager
```

## 🔗 Dépendances Entre Modules

- `config.py` : Aucune dépendance (module de base)
- `models.py` : Dépend de `chess`
- `robot_controller.py` : Dépend de `config`, `models`, `chess`
- `chess_manager.py` : Dépend de `config`, `robot_controller`, `chess`
- `api.py` : Dépend de `models`, `robot_controller`, `chess_manager`
- `main.py` : Dépend de `api`

## ⚙️ Callbacks et Communication

Les modules communiquent via des callbacks :

```python
# Dans api.py (ApplicationManager)
self.robot.set_log_callback(self.log)
self.chess.set_broadcast_callback(self.broadcast)
self.chess.set_log_callback(self.log)
self.chess.set_status_callback(self.set_status)
```

Cela permet :
- Logging centralisé
- Broadcast WebSocket unifié
- Gestion d'état cohérente

## 📝 Notes

- **Code strictement identique** : Aucune modification de la logique
- **Séparation des responsabilités** : Chaque module a un rôle précis
- **Facilité de maintenance** : Modifications isolées par module
- **Testabilité** : Chaque module peut être testé indépendamment
- **Réutilisabilité** : Les modules peuvent être importés ailleurs

## 🔧 Fichiers de Configuration Requis

- `chess_board_positions.json` : Mapping des cases et zones d'élimination
- `position_depart_robot.json` : Position de repos du robot
