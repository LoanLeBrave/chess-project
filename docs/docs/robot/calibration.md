---
id: calibration
title: Calibration
sidebar_position: 3
---

# Calibration du robot

La calibration permet d'aligner les coordonnées robot avec les cases de l'échiquier physique. Elle se fait via l'interface **CalibrationScreen** dans le frontend.

## Procédure de calibration

u### 1. Déverrouillage et mise en position initiale

Avant d'accéder à la calibration, un code PIN est demandé. Une fois déverrouillé, l'API exécute automatiquement un **auto-level** : la pince se verticalise et se ferme pour entrer dans les trous de calibration.

```http
POST /robot/calibrate/auto-level
```

### 2. Mode FreeDrive

Le FreeDrive permet de guider le robot manuellement sans résistance.

```http
POST /robot/calibrate/freedrive
Content-Type: application/json

{"enable": true}
```

Le FreeDrive libère les 6 degrés de liberté en translation (X, Y, Z) tout en bloquant les rotations, ce qui maintient la pince verticale pendant le guidage manuel.

:::warning
En mode FreeDrive, les boutons de déplacement Z de l'interface sont désactivés pour éviter les conflits de commande.
:::

### 3. Calibration du point A1

L'échiquier possède un **trou physique** positionné à environ 1 cm de la case A1 (coin bas-gauche). La pince doit y être insérée :

1. Activer le FreeDrive
2. Guider manuellement la pince dans le trou près de A1
3. Cliquer **Valider position A1**

```http
POST /robot/calibrate/point
Content-Type: application/json

{"point": "a1", "freedrive_active": true}
```

Le robot enregistre la position TCP, **remonte de 10 cm** automatiquement, et reste en FreeDrive.

### 4. Calibration du point H8

L'échiquier possède un second **trou physique** positionné à environ 1 cm de la case H8 (coin haut-droit) :

1. Guider manuellement la pince dans le trou près de H8 (FreeDrive toujours actif)
2. Cliquer **Calibrer** (enregistre H8 et déclenche la sauvegarde)

```http
POST /robot/calibrate/point
Content-Type: application/json

{"point": "h8", "freedrive_active": true}
```

Ces deux points permettent de calculer l'origine, l'orientation et l'échelle de l'échiquier par un algorithme à 2 points.

### 5. Calibration de la hauteur Z (surface du plateau)

Toujours en FreeDrive, la hauteur minimale du plateau est calibrée :

1. Descendre manuellement la pince jusqu'à environ **1 cm au-dessus de la surface du plateau**
2. Cliquer **Enregistrer Z**

```http
POST /robot/calibrate/point
Content-Type: application/json

{"point": "z"}
```

:::tip
Cette hauteur est utilisée comme référence absolue. Les hauteurs par type de pièce (`HAUTEUR_PIECES` dans `config.py`) s'ajoutent ensuite à cette valeur de base.
:::

### 6. Sauvegarde

La sauvegarde est déclenchée automatiquement après l'enregistrement de H8 ou manuellement via :

```http
POST /robot/calibrate/save
```

L'algorithme calcule :
- **Origine** : centre géométrique entre A1 et H8
- **Rotation** : angle de l'échiquier par rapport au repère robot
- **Échelle** : taille réelle des cases à partir de la distance mesurée
- **Hauteur Z** : surface du plateau

Les résultats sont sauvegardés dans `robot_calibration.json` et rechargés au prochain démarrage. Le robot remonte de 10 cm puis retourne en position d'attente.

## Points de calibration critiques

| Point | Description | Impact |
|-------|-------------|--------|
| `origin` | Centre de l'échiquier (mi-chemin A1-H8) | Décalage de toutes les cases |
| `rotation` | Angle d'orientation de l'échiquier | Toutes les cases mal orientées |
| `board_size` | Taille totale du plateau (calculée) | Espacement entre cases |
| `HAUTEUR_PIECES[type]` | Offset Z par type de pièce | Mauvaise prise de pièce |

## Vérification

Après calibration, il est recommandé de :
1. Tester avec une pièce sur a1 (coin)
2. Tester avec une pièce sur h8 (coin opposé)
3. Tester une capture (cimetière)
4. Vérifier que le robot ne heurte pas les pièces voisines

## Recalibration partielle

Si seule la hauteur Z a changé (ex: plateau légèrement décalé), relancer uniquement l'étape Z sans refaire A1 et H8. Les points A1/H8 existants dans `robot_calibration.json` sont conservés.

## Endpoints de calibration

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/robot/calibrate/freedrive` | POST | Activer/désactiver FreeDrive |
| `/robot/calibrate/auto-level` | POST | Verticaliser la pince et la fermer |
| `/robot/calibrate/point` | POST | Enregistrer un point (a1, h8, z) |
| `/robot/calibrate/save` | POST | Calculer la géométrie et sauvegarder |
| `/robot/calibrate/move-z/start` | POST | Démarrer un déplacement Z continu |
| `/robot/calibrate/move-z/stop` | POST | Stopper le déplacement Z |