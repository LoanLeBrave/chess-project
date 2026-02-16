# 🚀 Guide de Démarrage Rapide

## Installation

### Prérequis
```bash
pip install fastapi uvicorn python-chess
pip install rtde_control rtde_receive
# Installer robotiq_gripper_control selon la documentation Robotiq
```

## Workflow Complet

### 1️⃣ Première Installation

```bash
# 1. Calibration initiale du robot
python calibration.py

# 2. Tester la précision de la calibration
python test_calibration.py

# 3. Démarrer l'API
python main.py
```

### 2️⃣ Utilisation Quotidienne

```bash
# Démarrer directement l'API
python main.py
```

### 3️⃣ Re-calibration

Si les prises deviennent imprécises ou après avoir déplacé l'échiquier :
```bash
python calibration.py
```

## 📁 Fichiers Nécessaires

### Fichiers à Créer/Configurer
- `chess_board_positions.json` - Mapping des positions (créé lors du mapping initial)
- `position_depart_robot.json` - Position de repos du robot

### Fichiers Générés Automatiquement
- `chess_board_positions_backup.json` - Backup automatique lors de la calibration

## 🎯 Structure du Mapping JSON

### chess_board_positions.json
```json
{
  "cases": {
    "a1": {
      "tcp": [x, y, z, rx, ry, rz],
      "pixel": [px, py]
    },
    // ... 64 cases ...
    "h8": {
      "tcp": [x, y, z, rx, ry, rz],
      "pixel": [px, py]
    }
  },
  "zone_elimination_blancs_min": [x, y, z, rx, ry, rz],
  "zone_elimination_blancs_max": [x, y, z, rx, ry, rz],
  "zone_elimination_noirs_min": [x, y, z, rx, ry, rz],
  "zone_elimination_noirs_max": [x, y, z, rx, ry, rz],
  "espacement_elimination": 0.02
}
```

### position_depart_robot.json
```json
{
  "position_depart": [x, y, z, rx, ry, rz]
}
```

## 🔧 Configuration

### config.py
Modifiez les paramètres selon votre setup :

```python
ROBOT_IP = "192.168.0.11"  # IP de votre robot UR5e
VITESSE = 0.1              # Vitesse de mouvement (m/s)
ACCELERATION = 0.3         # Accélération (m/s²)
GRIPPER_OUVERTURE = 25     # Ouverture du gripper (mm)
```

### Hauteurs par Type de Pièce
Ajustez dans `config.py` si nécessaire :
```python
HAUTEUR_PIECES = {
    chess.PAWN: 0.005,    # 5mm
    chess.KNIGHT: 0.010,  # 10mm
    chess.BISHOP: 0.012,  # 12mm
    chess.ROOK: 0.008,    # 8mm
    chess.QUEEN: 0.015,   # 15mm
    chess.KING: 0.018,    # 18mm
}
```

## 🎮 Utilisation de l'API

### Endpoints Principaux

#### Statut
```http
GET /status
```

#### Nouvelle Partie
```http
POST /game/new
{
  "difficulty": "intermediate"  // beginner, intermediate, advanced
}
```

#### Coup Humain
```http
POST /game/move/human
{
  "from_square": "e2",
  "to_square": "e4"
}
```

#### Coup Robot
```http
POST /game/move/robot
```

#### Reset Plateau
```http
POST /game/reset-plateau
```

### WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'move':
      // Mise à jour du plateau
      break;
    case 'status':
      // Mise à jour du statut
      break;
    case 'log':
      // Log du robot
      break;
  }
};
```

## 🐛 Dépannage

### Robot ne se connecte pas
```bash
# Vérifier l'IP du robot
ping 192.168.0.11

# Vérifier que le robot est allumé et en mode distant
```

### Calibration imprécise
```bash
# Re-faire la calibration
python calibration.py

# Vérifier avec le test
python test_calibration.py
```

### Gripper ne fonctionne pas
```bash
# Vérifier l'activation du gripper dans les logs
# Réinitialiser le gripper depuis PolyScope si nécessaire
```

### Erreur de mapping
```bash
# Restaurer la backup
cp chess_board_positions_backup.json chess_board_positions.json
```

## 📊 Niveaux de Difficulté

| Niveau | Skill Level | Depth | Time Limit |
|--------|-------------|-------|------------|
| Beginner | 3 | 8 | 0.5s |
| Intermediate | 10 | 12 | 1.0s |
| Advanced | 18 | 18 | 2.0s |

## 🔒 Sécurité

### Limites de Vitesse
- **Normale**: 0.1 m/s
- **Fine** (calibration): 0.02 m/s

### Zones Sûres
- **Delta Transit**: 12cm au-dessus du plateau (évite les collisions)
- **Delta Approche**: 3cm au-dessus de la pièce
- **Delta Relâche**: 1mm au-dessus de la surface

### Arrêt d'Urgence
- **Bouton d'arrêt d'urgence** sur le robot
- **Ctrl+C** dans le terminal pour arrêter l'API
- **ESC** durant la calibration pour annuler

## 📞 Support

### Logs
Les logs sont affichés en temps réel via WebSocket :
- `info` - Informations générales
- `robot` - Actions du robot
- `error` - Erreurs
- `warning` - Avertissements

### Debug
Activer le mode verbose dans l'API :
```python
# Dans main.py
uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
```

## 📚 Documentation Complète

- [README.md](README.md) - Architecture et modules
- [CALIBRATION.md](CALIBRATION.md) - Guide de calibration détaillé

## ✅ Checklist de Démarrage

- [ ] Robot UR5e allumé et en mode distant
- [ ] Gripper Robotiq activé
- [ ] Fichier `chess_board_positions.json` présent
- [ ] Fichier `position_depart_robot.json` présent
- [ ] Échiquier en place avec le trou de calibration
- [ ] Calibration effectuée (`python calibration.py`)
- [ ] Test de calibration OK (`python test_calibration.py`)
- [ ] API démarrée (`python main.py`)
- [ ] Frontend connecté au WebSocket
