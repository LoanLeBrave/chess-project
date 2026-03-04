---
id: calibration
title: Calibration
sidebar_position: 3
---

# Calibration du robot

La calibration permet d'aligner les coordonnées robot avec les cases de l'échiquier physique. Elle se fait via l'interface **CalibrationScreen** dans le frontend.

## Procédure de calibration

### 1. Mode FreeDrive

Le FreeDrive permet de guider le robot manuellement sans résistance.

```http
POST /robot/freedrive
Content-Type: application/json

{"enable": true}
```

:::warning
En mode FreeDrive, les boutons de déplacement Z sont désactivés pour éviter les mouvements involontaires.
:::

### 2. Calibration XY

Le robot est guidé manuellement vers les 4 coins de l'échiquier pour définir l'origine et l'orientation.

Points de calibration :
- **a1** — coin bas-gauche
- **h1** — coin bas-droit
- **a8** — coin haut-gauche
- **h8** — coin haut-droit

### 3. Calibration Z

La hauteur Z est ajustée via les boutons `Z+` / `Z-` dans l'interface.

```http
POST /robot/move-z
Content-Type: application/json

{"direction": "up", "step": 5}   // déplacement de 5mm vers le haut
```

Les boutons Z sont **désactivés pendant le FreeDrive** :

```tsx
// CalibrationScreen.tsx
<button
  onClick={() => moveZ('up')}
  disabled={isFreeDriveActive}
  className={isFreeDriveActive ? 'opacity-50 cursor-not-allowed' : ''}
>
  Z+
</button>
```

### 4. Sauvegarde

Les coordonnées calibrées sont sauvegardées dans `config.py` et rechargées au prochain démarrage.

```http
POST /robot/save-calibration
Content-Type: application/json

{
  "board_origin": [x, y, z, rx, ry, rz],
  "case_size": 0.055
}
```

## Points de calibration critiques

| Point | Description | Impact |
|-------|-------------|--------|
| `BOARD_ORIGIN` | Coin a1 de l'échiquier | Décalage de toutes les cases |
| `CASE_SIZE` | Taille d'une case en m | Espacement entre cases |
| `Z_APPROCHE` | Hauteur de transit | Collision avec pièces voisines |
| `HAUTEUR_PIECES[type]` | Z de prise par type | Mauvaise prise de pièce |

## Vérification

Après calibration, il est recommandé de :
1. Tester avec une pièce sur a1 (coin)
2. Tester avec une pièce sur h8 (coin opposé)
3. Tester une capture (cimetière)
4. Vérifier que le robot ne heurte pas les pièces voisines

## Recalibration partielle

Si seule la hauteur Z a changé (ex: plateau légèrement différent), il suffit de recalibrer le Z sans refaire les XY :

```http
POST /robot/update-z
Content-Type: application/json

{"z_approach": -0.080, "z_depose": -0.150}
```

## Endpoints de calibration

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/robot/freedrive` | POST | Activer/désactiver FreeDrive |
| `/robot/move-z` | POST | Déplacer Z d'un step |
| `/robot/move-joint` | POST | Déplacer un joint |
| `/robot/save-calibration` | POST | Sauvegarder la calibration |
| `/robot/get-position` | GET | Lire la position TCP actuelle |
