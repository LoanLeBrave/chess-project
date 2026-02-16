# Chess Vision - Guide d'utilisation dans un programme

Guide pour intégrer le système de vision d'échecs dans votre code.

## 🎯 Deux méthodes d'utilisation

### Méthode 1 : Récupération directe (recommandé)
**Plus rapide** : pas de lecture de fichier, données déjà en mémoire.

### Méthode 2 : Via fichier JSON
**Plus flexible** : permet de réutiliser les résultats plus tard.

---

## 📦 Méthode 1 : Utilisation directe (recommandé)

### Import et initialisation

```python
from chess_vision import ChessVisionPipeline

# Créer le pipeline (une seule fois au début)
pipeline = ChessVisionPipeline()
```

### Analyser une image existante

```python
result = pipeline.analyze_image(
    image_path="photo.jpg",
    save_outputs=False  # False = pas de sauvegarde fichiers
)

if result['success']:
    game_state = result['game_state']
    pieces = game_state['pieces']
    
    # Utiliser les données
    for piece in pieces:
        print(f"{piece['code']}: x={piece['position']['board']['x']}, y={piece['position']['board']['y']}")
else:
    print(f"Erreur: {result['error']}")
```

### Capturer une photo et analyser

```python
result = pipeline.capture_and_analyze(save_outputs=False)

if result['success']:
    game_state = result['game_state']
    # ... utiliser game_state
```

### Structure de `game_state`

```python
{
    'pieces': [
        {
            'id': 0,                    # ID du marqueur ArUco (0-31)
            'code': 'WP1',              # Code pièce (WP1 = White Pawn 1)
            'color': 'white',           # 'white' ou 'black'
            'type': 'Pawn',             # Type: King, Queen, Rook, Bishop, Knight, Pawn
            'symbol': '♙',              # Symbole Unicode
            'initial': 'Pawn_A',        # Position initiale
            'zone': 'board',            # 'board' (plateau) ou 'cemetery' (cimetière)
            'position': {
                'pixel': {               # Coordonnées en pixels du plateau extrait (1000x1000)
                    'x': 100.5,
                    'y': 650.2
                },
                'board': {               # Coordonnées robot (grille étendue -12.5 à +12.5)
                    'x': -7.5,
                    'y': -8.75
                },
                'chess': 'a2',           # Notation échecs (null si en cimetière)
                'grid': 'A2'             # Notation grille (A-H, 1-8 pour plateau, J/K et 0/9 pour cimetière)
            }
        },
        {
            'id': 16,                   # Pièce capturée dans le cimetière
            'code': 'BP1',
            'color': 'black',
            'type': 'Pawn',
            'symbol': '♟',
            'initial': 'Pawn_A',
            'zone': 'cemetery',
            'position': {
                'pixel': {'x': 50.0, 'y': 950.0},
                'board': {'x': -10.0, 'y': -12.5},
                'chess': null,           # Pas de notation échecs en cimetière
                'grid': 'A0',
                'cemetery': 'C1'         # Notation cimetière (C1-C36)
            }
        },
        # ... autres pièces
    ],
    'metadata': {
        'timestamp': '2026-02-13T14:23:45',
        'turn': 'white',
        'move_count': 0,
        'total_detected': 32,
        'white_count': 16,
        'black_count': 16,
        'missing_count': 0,
        'on_board': 31,              # Pièces sur le plateau
        'in_cemetery': 1             # Pièces capturées
    },
    'missing_pieces': []  # Liste des pièces non détectées (si any)
}
```

### Exemple complet : fonction utilitaire

```python
from chess_vision import ChessVisionPipeline

class ChessPositionTracker:
    def __init__(self):
        self.pipeline = ChessVisionPipeline()
    
    def get_positions(self, zone='board'):
        """
        Récupère les positions actuelles des pièces.
        
        Args:
            zone: 'board', 'cemetery', ou 'all' (par défaut: 'board')
        
        Returns:
            dict: {code: {'x': float, 'y': float, 'zone': str}} ou None si erreur
        """
        result = self.pipeline.capture_and_analyze(save_outputs=False)
        
        if not result['success']:
            print(f"Erreur vision: {result['error']}")
            return None
        
        # Extraire seulement les coordonnées robot
        positions = {}
        for piece in result['game_state']['pieces']:
            # Filtrer par zone si demandé
            if zone != 'all' and piece['zone'] != zone:
                continue
                
            positions[piece['code']] = {
                'x': piece['position']['board']['x'],
                'y': piece['position']['board']['y'],
                'zone': piece['zone']
            }
        
        return positions

# Utilisation
tracker = ChessPositionTracker()

# Récupérer seulement les pièces sur le plateau
board_positions = tracker.get_positions(zone='board')
if board_positions:
    print(f"Pièces sur plateau: {len(board_positions)}")
    print(f"Pion blanc 1: {board_positions['WP1']}")
    # Output: Pion blanc 1: {'x': -7.5, 'y': -8.75, 'zone': 'board'}

# Récupérer seulement les pièces capturées
cemetery_positions = tracker.get_positions(zone='cemetery')
if cemetery_positions:
    print(f"Pièces capturées: {len(cemetery_positions)}")
```

---

## 📄 Méthode 2 : Via fichier JSON

### Activer la sauvegarde

```python
from chess_vision import ChessVisionPipeline

pipeline = ChessVisionPipeline()

# Analyser AVEC sauvegarde des fichiers
result = pipeline.analyze_image(
    image_path="photo.jpg",
    save_outputs=True  # True = sauvegarde dans output/latest/
)

# Les fichiers sont dans output/latest/game_state.json
print(f"Fichiers sauvegardés dans: {result['output_dir']}")
```

### Lire le fichier JSON généré

```python
import json
import os

def load_game_state():
    """
    Charge le dernier état du jeu depuis le fichier JSON.
    
    Returns:
        dict: État du jeu ou None si erreur
    """
    json_path = "chess_vision/output/latest/game_state.json"
    
    if not os.path.exists(json_path):
        print(f"Fichier non trouvé: {json_path}")
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        game_state = json.load(f)
    
    return game_state

# Utilisation
game_state = load_game_state()

if game_state:
    pieces = game_state['pieces']
    for piece in pieces:
        code = piece['code']
        x = piece['position']['board']['x']
        y = piece['position']['board']['y']
        print(f"{code}: ({x}, {y})")
```

### Autres fichiers générés

Quand `save_outputs=True`, plusieurs fichiers sont créés dans `output/latest/` :

- **game_state.json** : État complet avec toutes les coordonnées
- **board_state.json** : État du plateau en notation échecs (a1, b2...)
- **coordinates.json** : Format simplifié pour le robot
- **1_original.jpg** : Image originale
- **2_calibration.jpg** : Visualisation des coins du plateau
- **3_board.jpg** : Plateau extrait et redressé
- **4_board_grid.jpg** : Plateau avec grille 10x10 (8x8 + zone cimetière)
- **5_pieces.jpg** : Pièces détectées avec coordonnées
- **6_aruco.jpg** : ArUcos des pièces détectés

---

## 🔧 Formats alternatifs

### Format simplifié : `robot_coordinates`

Si vous voulez juste les coordonnées robot sans métadonnées :

```python
result = pipeline.capture_and_analyze(save_outputs=False)

if result['success']:
    coords = result['robot_coordinates']
    # Format: liste simplifiée
    for item in coords:
        print(f"{item['id']}: x={item['x']}, y={item['y']}")
```

### Format échecs : `board_state`

État du plateau en notation échecs standard + cimetière :

```python
result = pipeline.capture_and_analyze(save_outputs=False)

if result['success']:
    board_state = result['board_state']
    
    # Plateau d'échecs (a1-h8)
    board = board_state['board']
    print(f"a1: {board.get('a1')}")  # Ex: 'WR' (White Rook)
    print(f"e4: {board.get('e4')}")  # Ex: None (case vide)
    
    # Cimetière (C1-C36)
    cemetery = board_state.get('cemetery', {})
    print(f"Pièces capturées: {len(cemetery)}")
    print(f"C1: {cemetery.get('C1')}")  # Ex: 'BP' (Black Pawn)
```

---

## ⚠️ Prérequis : Calibration

Avant la première utilisation, calibrer le plateau :

```bash
python -m chess_vision.calibrate_board
```

La calibration est sauvegardée dans `board_calibration.json` et chargée automatiquement.

---

## 🚀 Exemple complet : intégration robot

```python
from chess_vision import ChessVisionPipeline
import time

class RobotChessController:
    def __init__(self):
        self.vision = ChessVisionPipeline()
        self.last_positions = {}
    
    def update_positions(self):
        """Met à jour les positions des pièces."""
        result = self.vision.capture_and_analyze(save_outputs=False)
        
        if not result['success']:
            print(f"Erreur vision: {result['error']}")
            return False
        
        # Stocker les nouvelles positions (avec zone)
        new_positions = {}
        for piece in result['game_state']['pieces']:
            new_positions[piece['code']] = {
                'x': piece['position']['board']['x'],
                'y': piece['position']['board']['y'],
                'zone': piece['zone']
            }
        
        # Détecter les pièces qui ont bougé
        moved_pieces = []
        captured_pieces = []
        
        for code, new_pos in new_positions.items():
            if code in self.last_positions:
                old_pos = self.last_positions[code]
                
                # Vérifier déplacement
                if (old_pos['x'] != new_pos['x'] or 
                    old_pos['y'] != new_pos['y'] or
                    old_pos['zone'] != new_pos['zone']):
                    
                    move_info = {
                        'code': code,
                        'from': old_pos,
                        'to': new_pos
                    }
                    
                    # Pièce capturée (déplacée au cimetière)
                    if old_pos['zone'] == 'board' and new_pos['zone'] == 'cemetery':
                        captured_pieces.append(move_info)
                    else:
                        moved_pieces.append(move_info)
        
        self.last_positions = new_positions
        return {'moved': moved_pieces, 'captured': captured_pieces}
    
    def main_loop(self):
        """Boucle principale de surveillance."""
        print("Robot Chess Controller - Démarré")
        
        while True:
            changes = self.update_positions()
            
            if not changes:
                time.sleep(1)
                continue
            
            # Gérer les pièces déplacées
            if changes['moved']:
                print(f"{len(changes['moved'])} pièce(s) déplacée(s):")
                for move in changes['moved']:
                    print(f"  {move['code']}: "
                          f"({move['from']['x']:.1f}, {move['from']['y']:.1f}) "
                          f"→ ({move['to']['x']:.1f}, {move['to']['y']:.1f})")
                    
                    # Ici: envoyer commande au robot pour déplacer
                    # self.robot.move_piece(move['to']['x'], move['to']['y'])
            
            # Gérer les pièces capturées
            if changes['captured']:
                print(f"{len(changes['captured'])} pièce(s) capturée(s):")
                for capture in changes['captured']:
                    print(f"  {capture['code']}: plateau → cimetière "
                          f"({capture['to']['x']:.1f}, {capture['to']['y']:.1f})")
                    
                    # Ici: envoyer commande au robot pour capturer
                    # self.robot.capture_piece(capture['to']['x'], capture['to']['y'])
            
            time.sleep(1)  # Vérifier chaque seconde

# Lancement
if __name__ == "__main__":
    controller = RobotChessController()
    controller.main_loop()
```

---

## 📚 Résumé : Quelle méthode choisir ?

| Critère | Méthode 1 (directe) | Méthode 2 (JSON) |
|---------|---------------------|------------------|
| **Vitesse** | ⚡ Rapide (pas d'I/O) | 🐢 Plus lent (lecture fichier) |
| **Usage** | ✅ Temps réel, intégration robot | ✅ Analyse différée, debug |
| **Simplicité** | ✅ Une ligne de code | ⚠️ Lire fichier manuellement |
| **Persistance** | ❌ Perdu après exécution | ✅ Sauvegardé sur disque |

**Recommandation** : Méthode 1 (directe) pour votre cas d'usage robot.
