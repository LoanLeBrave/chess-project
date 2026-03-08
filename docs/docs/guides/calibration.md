---
id: calibration
title: Guide de calibration
sidebar_position: 2
---

# Guide de calibration

La calibration est une étape critique pour que le robot dépose les pièces précisément sur les bonnes cases.

## Quand recalibrer ?

- Première installation
- Déplacement de l'échiquier ou du robot
- Changement des pièces (hauteurs différentes)
- Le robot rate systématiquement les cases (décalage constant)

## Outils nécessaires

- Interface web ChessRobot ouverte
- Accès physique au robot
- L'échiquier physique avec ses **deux trous de calibration** (près de A1 et H8)

## Étape 1 : Connexion

1. Ouvrir l'interface → **Calibration**
2. Cliquer **Connecter le robot**
3. Le statut passe à "Connecté ✓"
4. Entrer le **code PIN** de calibration
5. La pince se verticalise et se ferme automatiquement (prête à entrer dans les trous)

## Étape 2 : Calibration du point A1

### Activer FreeDrive

```
[Activer FreeDrive]
```

Le robot peut maintenant être guidé à la main. Les rotations restent bloquées : la pince reste verticale.

### Positionner sur le trou A1

1. Guider le bras jusqu'au **trou de calibration situé près de la case A1** (coin bas-gauche de l'échiquier)
2. Insérer la pince dans le trou — elle doit s'y loger sans forcer
3. Cliquer **Valider position A1**

Le robot enregistre la position, **remonte automatiquement de 10 cm**, et reste en FreeDrive.

:::tip
L'échiquier possède deux trous physiques usinés dans le plateau, l'un près de A1 et l'autre près de H8. Ce sont ces trous — et non le centre des cases — qui servent de références de calibration.
:::

## Étape 3 : Calibration du point H8

Sans désactiver le FreeDrive :

1. Guider le bras jusqu'au **trou de calibration situé près de la case H8** (coin haut-droit de l'échiquier)
2. Insérer la pince dans le trou
3. Cliquer **Calibrer**

Le système enregistre les deux points A1 et H8 et calcule automatiquement :
- L'**origine** de l'échiquier (centre géométrique)
- L'**orientation** (angle du plateau par rapport au robot)
- L'**échelle** (taille réelle des cases)

## Étape 4 : Calibration de la hauteur du plateau (Z)

Toujours en FreeDrive, calibrer la hauteur minimale :

1. Descendre manuellement la pince jusqu'à environ **1 cm au-dessus de la surface du plateau**
2. Cliquer **Enregistrer Z**

:::warning
Ne pas poser la pince directement sur le plateau. Une position à ~1 cm de la surface suffit comme référence de hauteur minimale.
:::

La calibration est alors sauvegardée. Le robot remonte automatiquement et retourne en position d'attente.

### Hauteurs par pièce

La hauteur Z calibrée est la hauteur de référence du plateau. Les hauteurs de prise sont ensuite ajustées par type de pièce dans `config.py` :

```python
HAUTEUR_PIECES = {
    chess.PAWN:   0.005,   # +5mm au-dessus du plateau
    chess.ROOK:   0.008,   # +8mm
    chess.KNIGHT: 0.010,   # +10mm
    chess.BISHOP: 0.012,   # +12mm
    chess.QUEEN:  0.015,   # +15mm
    chess.KING:   0.018,   # +18mm
}
```

## Étape 5 : Test de calibration

### Test simple

1. Placer un pion en **e4**
2. Lancer un déplacement e4 → e5 via l'interface
3. Vérifier que le pion est bien en e5

### Test complet

Lancer une partie courte et observer :
- Le robot prend-il les pièces au centre ?
- La pièce ne tombe-t-elle pas à côté ?
- Les captures fonctionnent-elles ?

## Problèmes courants

### Décalage constant dans une direction

Le robot rate toutes les cases avec un décalage fixe (ex: 5mm à gauche).

**Solution :** Refaire la calibration A1 et H8. Si le problème persiste, vérifier que les trous de calibration sont bien propres et que la pince s'insère correctement.

### Cases au bord rateées, centre OK

L'échelle calculée est légèrement incorrecte — la distance mesurée entre les deux trous ne correspond pas à la distance théorique.

**Solution :** Vérifier que la pince est bien centrée dans chaque trou lors de la calibration, puis recalibrer.

### Pince ne saisit pas la pièce

La hauteur Z de référence est trop haute, ou l'offset de la pièce dans `HAUTEUR_PIECES` est trop grand.

**Solution :** Recalibrer le Z en descendant légèrement plus bas, ou réduire la valeur dans `HAUTEUR_PIECES` pour ce type de pièce.

### Pièce renversée lors de la prise

La hauteur Z est trop basse, la pince pousse la pièce.

**Solution :** Augmenter la valeur dans `HAUTEUR_PIECES` pour ce type de pièce de 2-3mm.