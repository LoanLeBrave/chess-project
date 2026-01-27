# Architecture du Projet Chess Robot

## 📁 Structure complète des dossiers

```
chess-robot-project/
│
├── 📁 Backend/                          # Côté Raspberry Pi / PC avec robot
│   ├── chess_robot_api.py               # API FastAPI (serveur principal)
│   ├── chess_robot_final.py             # Script autonome (optionnel)
│   ├── robotiq_gripper_control.py       # Contrôle du gripper
│   ├── chess_board_positions.json       # Mapping des cases
│   ├── position_depart_robot.json       # Position de départ (auto-généré)
│   ├── zone_defausse_robot.json         # Zone défausse (auto-généré)
│   └── requirements.txt                 # Dépendances Python
│
├── 📁 Frontend/                         # Application React
│   ├── index.html                       # Point d'entrée HTML
│   ├── package.json                     # Dépendances npm
│   ├── vite.config.ts                   # Config Vite (si utilisé)
│   ├── tsconfig.json                    # Config TypeScript
│   ├── tailwind.config.js               # Config Tailwind CSS
│   │
│   └── 📁 src/
│       ├── App.tsx                      # Composant principal
│       ├── main.tsx                     # Point d'entrée React
│       ├── index.css                    # Styles globaux
│       │
│       ├── 📁 components/               # Composants React
│       │   ├── ChessBoard.tsx           # ⭐ Plateau (MODIFIÉ)
│       │   ├── GameScreen.tsx           # ⭐ Écran de jeu (MODIFIÉ)
│       │   ├── StartScreen.tsx          # Écran d'accueil
│       │   ├── ControlPanel.tsx         # Boutons de contrôle
│       │   ├── MoveHistory.tsx          # Historique des coups
│       │   ├── RobotStatus.tsx          # Statut du robot
│       │   └── PlayerTurnStatus.tsx     # Indicateur de tour
│       │
│       ├── 📁 hooks/                    # ⭐ NOUVEAU DOSSIER
│       │   └── useChessRobot.ts         # Hook de connexion à l'API
│       │
│       └── 📁 types/                    # Types TypeScript (optionnel)
│           └── index.ts                 # Types partagés
│
└── README.md                            # Documentation
```

---

## 🔧 Installation pas à pas

### 1. Créer la structure

```bash
# Créer le dossier principal
mkdir chess-robot-project
cd chess-robot-project

# Créer les sous-dossiers
mkdir Backend
mkdir -p Frontend/src/components
mkdir -p Frontend/src/hooks
```

### 2. Backend (Raspberry Pi)

```bash
cd Backend

# Copier les fichiers
# - chess_robot_api.py
# - robotiq_gripper_control.py
# - chess_board_positions.json

# Créer requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
python-chess==1.999
EOF

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Frontend (ton PC ou même machine)

```bash
cd ../Frontend

# Si tu n'as pas encore de projet React, créer avec Vite
npm create vite@latest . -- --template react-ts

# Installer les dépendances
npm install

# Installer Tailwind CSS (si pas déjà fait)
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

## 📄 Fichiers à placer

### Frontend/src/hooks/useChessRobot.ts
```
Copier le fichier useChessRobot.ts dans ce dossier
```

### Frontend/src/components/
```
Remplacer ChessBoard.tsx et GameScreen.tsx par les nouvelles versions
Garder les autres fichiers (StartScreen, ControlPanel, etc.)
```

---

## ⚙️ Configuration de l'API URL

Dans `Frontend/src/hooks/useChessRobot.ts`, modifier les URLs selon ton réseau :

```typescript
// Si le robot est sur le même PC (développement)
const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// Si le robot est sur un Raspberry Pi
const API_URL = 'http://192.168.0.11:8000';  // IP du Raspberry Pi
const WS_URL = 'ws://192.168.0.11:8000/ws';
```

---

## 🚀 Lancement

### Terminal 1 - Backend (sur le Raspberry Pi ou PC avec robot)
```bash
cd chess-robot-project/Backend
python chess_robot_api.py

# Tu verras:
# ============================================================
#      ♔ CHESS ROBOT API ♚
# ============================================================
# Démarrage du serveur...
# Interface: http://localhost:8000
# Documentation: http://localhost:8000/docs
# WebSocket: ws://localhost:8000/ws
```

### Terminal 2 - Frontend
```bash
cd chess-robot-project/Frontend
npm run dev

# Tu verras:
#   VITE v5.x.x  ready in xxx ms
#   ➜  Local:   http://localhost:5173/
```

### Ouvrir dans le navigateur
```
http://localhost:5173
```

---

## 📋 Checklist des fichiers

### Backend/ (7 fichiers)
- [ ] `chess_robot_api.py` - API FastAPI
- [ ] `robotiq_gripper_control.py` - Contrôle gripper
- [ ] `chess_board_positions.json` - Mapping cases
- [ ] `requirements.txt` - Dépendances Python
- [ ] `position_depart_robot.json` - (auto-généré au premier lancement)
- [ ] `zone_defausse_robot.json` - (auto-généré au premier lancement)

### Frontend/src/hooks/ (1 fichier)
- [ ] `useChessRobot.ts` - ⭐ NOUVEAU

### Frontend/src/components/ (7 fichiers)
- [ ] `ChessBoard.tsx` - ⭐ NOUVELLE VERSION
- [ ] `GameScreen.tsx` - ⭐ NOUVELLE VERSION
- [ ] `StartScreen.tsx` - Inchangé
- [ ] `ControlPanel.tsx` - Inchangé
- [ ] `MoveHistory.tsx` - Inchangé
- [ ] `RobotStatus.tsx` - Inchangé
- [ ] `PlayerTurnStatus.tsx` - Inchangé

---

## 🔍 Vérification

### Tester l'API seule
```bash
# Ouvrir dans le navigateur
http://localhost:8000/docs

# Tu verras la documentation Swagger avec tous les endpoints
```

### Tester la connexion
```bash
# Dans un terminal
curl http://localhost:8000/status

# Devrait retourner:
# {"connected":true,"status":"idle","difficulty":"intermediate",...}
```

---

## 🐛 Problèmes courants

### "WebSocket connection failed"
→ L'API n'est pas lancée ou l'URL est incorrecte

### "CORS error"
→ Vérifier que l'API autorise les requêtes cross-origin (déjà configuré)

### "Robot non connecté"
→ Le robot n'est pas accessible, l'API fonctionne en mode simulation

### "Module not found: useChessRobot"
→ Vérifier que le fichier est dans `src/hooks/useChessRobot.ts`
→ Vérifier l'import: `import { useChessRobot } from '../hooks/useChessRobot'`