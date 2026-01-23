# 📐 Traduction de Coordonnées Robot ↔ Plateau

Module de conversion entre les coordonnées robot (en mètres) et les coordonnées plateau (repère -10/+10).

## 🎯 Pourquoi ce module ?

**Problème :** Plusieurs personnes travaillent sur le robot avec des systèmes de coordonnées différents :
- **Robot** : coordonnées en mètres (x, y) depuis la base du robot
- **Plateau** : repère -10 à +10 avec centre (0,0) au milieu de l'échiquier

**Solution :** Ce module permet de convertir entre ces deux repères pour qu'**on parle tous de la même position**.

## 📋 Prérequis

1. **Calibration effectuée** : Vous devez avoir lancé la calibration du robot au moins une fois
   ```bash
   cd ../calibration
   python3 calibrate_robot_v2.py
   ```
   Cela crée le fichier `robot_calibration.json` nécessaire.

2. **Fichier de calibration** : `calibration/robot_calibration.json` doit exister

## 🚀 Utilisation rapide

### Exemple 1 : Convertir une position robot → plateau

```python
from coordinate_converter import CoordinateConverter

# Charger la calibration
converter = CoordinateConverter("../calibration/robot_calibration.json")

# Position du robot en mètres
x_robot, y_robot = 0.450, 0.320

# Convertir en coordonnées plateau (-10/+10)
x_plateau, y_plateau = converter.robot_to_plateau(x_robot, y_robot)

print(f"Robot ({x_robot}, {y_robot}) → Plateau ({x_plateau:.2f}, {y_plateau:.2f})")
# Sortie : Robot (0.450, 0.320) → Plateau (5.20, -3.10)
```

### Exemple 2 : Convertir une position plateau → robot

```python
# Vous détectez un pion sur le plateau à (5.2, -3.1)
x_plateau, y_plateau = 5.2, -3.1

# Convertir en coordonnées robot pour déplacer le bras
x_robot, y_robot = converter.plateau_to_robot(x_plateau, y_plateau)

print(f"Plateau ({x_plateau}, {y_plateau}) → Robot ({x_robot:.4f}, {y_robot:.4f})")
# Sortie : Plateau (5.2, -3.1) → Robot (0.4500, 0.3200)

# Maintenant on peut envoyer le robot à cette position
```

### Exemple 3 : Convertir un JSON complet

Si quelqu'un vous donne un fichier JSON avec des positions robot :

```python
import json
from coordinate_converter import CoordinateConverter

# Charger le JSON d'une autre personne
with open("positions_ami.json", "r") as f:
    positions_robot = json.load(f)
# Format : {"E2": {"x": 0.450, "y": 0.320}, "E4": {"x": 0.450, "y": 0.240}, ...}

# Convertir toutes les positions en coordonnées plateau
converter = CoordinateConverter("../calibration/robot_calibration.json")
positions_plateau = converter.convert_positions_dict(positions_robot)

# Sauvegarder dans votre format
with open("positions_plateau.json", "w") as f:
    json.dump(positions_plateau, f, indent=2)

print("✅ Conversion terminée ! Vous avez maintenant les positions dans votre repère.")
```

## 📊 Test du module

Lancez le script d'exemple pour voir des conversions :

```bash
python3 coordinate_converter.py
```

Cela affiche :
- Test Robot → Plateau
- Test Plateau → Robot
- Conversion d'un JSON exemple

## 🧮 Formules utilisées

### Robot → Plateau
```python
x_plateau = -(x_robot - center_x) / SCALE_FACTOR
y_plateau = -(y_robot - center_y) / SCALE_FACTOR
```

### Plateau → Robot
```python
x_robot = center_x - (x_plateau * SCALE_FACTOR)
y_robot = center_y - (y_plateau * SCALE_FACTOR)
```

**Note :** Les axes sont **inversés** entre robot et plateau (validé par tests).

## 📌 Repère plateau (-10/+10)

```
        Y+ (vers robot)
        ↑
        |
   (-10,+10)──────(+10,+10)
        |            |
        |   (0,0)    |
        |     ●      |
        |            |
   (-10,-10)──────(+10,-10)
        |
        ↓
        Y- (vers joueur)
    ────────────────────→ X+
```

- **Centre (0,0)** : milieu de l'échiquier
- **Limites** : -10 à +10 dans chaque direction
- **Y+** : vers le robot
- **Y-** : vers le joueur

## 🔧 Cas d'usage pratiques

### Cas 1 : Recevoir des positions d'un collègue

Votre collègue vous envoie : *"Le cavalier blanc est à robot(0.482, 0.315)"*

```python
x_plateau, y_plateau = converter.robot_to_plateau(0.482, 0.315)
print(f"Le cavalier est à plateau({x_plateau:.1f}, {y_plateau:.1f}) dans notre repère")
```

### Cas 2 : Déplacer le robot vers une pièce détectée

Vous détectez une pièce sur votre caméra à plateau(7.5, -4.2) :

```python
x_robot, y_robot = converter.plateau_to_robot(7.5, -4.2)
# Envoyer le robot à (x_robot, y_robot)
robot.moveL([x_robot, y_robot, z, rx, ry, rz])
```

### Cas 3 : Synchroniser deux systèmes

Système A (détection caméra) → coordonnées plateau  
Système B (robot) → coordonnées robot  

Ce module fait le pont entre les deux ! 🌉

## ⚠️ Points importants

1. **Calibration obligatoire** : Sans `robot_calibration.json`, le module ne peut pas fonctionner
2. **SCALE_FACTOR** : Actuellement 0.02 m/unité (2cm par unité plateau). Ajuster si besoin après tests réels
3. **Axes inversés** : Ne pas oublier que X robot+ = X plateau-, Y robot+ = Y plateau-
4. **Zone de travail** : Le robot ne peut atteindre que les positions dans sa zone accessible

## 📁 Fichiers du module

```
Traduction_coordonnes/
├── README.md                    ← Vous êtes ici
├── coordinate_converter.py      ← Module principal
├── calibration.py               ← Calibration image (non lié)
└── traduction.py                ← Ancien module (non lié)
```

## 🤝 Collaboration

Pour partager des positions entre plusieurs personnes :

1. **Une personne calibre** le robot et crée `robot_calibration.json`
2. **Tout le monde utilise ce fichier** comme référence commune
3. **On peut échanger** des positions dans n'importe quel repère
4. **Le module fait la conversion** automatiquement

## 📞 Questions fréquentes

**Q : Le fichier de calibration doit-il être régénéré régulièrement ?**  
R : Seulement si le robot ou la caméra sont déplacés physiquement.

**Q : Puis-je avoir plusieurs fichiers de calibration ?**  
R : Oui, passez le chemin en paramètre : `CoordinateConverter("calibration_test.json")`

**Q : Les conversions sont-elles précises ?**  
R : Oui, tant que le SCALE_FACTOR est correct et que le robot est bien perpendiculaire au plateau.

**Q : Que se passe-t-il si j'essaie de convertir une position hors plateau ?**  
R : La conversion mathématique fonctionne, mais le robot pourrait ne pas pouvoir y aller physiquement.

## 🎓 Pour aller plus loin

Voir aussi :
- [calibration/CALIBRATION_INFO.md](../calibration/CALIBRATION_INFO.md) : Documentation complète sur le système de calibration
- [calibration/calibrate_robot_v2.py](../calibration/calibrate_robot_v2.py) : Script de calibration automatique
