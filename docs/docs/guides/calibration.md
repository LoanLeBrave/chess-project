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
- Une pièce test (idéalement un pion)

## Étape 1 : Connexion

1. Ouvrir l'interface → **Calibration**
2. Cliquer **Connecter le robot**
3. Le statut passe à "Connecté ✓"

## Étape 2 : Calibration XY (origine de l'échiquier)

### Activer FreeDrive

```
[Activer FreeDrive]
```

Le robot peut maintenant être guidé à la main.

### Positionner sur a1

1. Guider le bras jusqu'au **centre de la case a1** (coin bas-gauche)
2. La pince doit être au-dessus de la case, orientée vers le bas
3. Cliquer **Enregistrer position a1**

### Optionnel : vérifier h8

Pour s'assurer que l'orientation est correcte :
1. Guider jusqu'au centre de **h8** (coin haut-droit)
2. Vérifier que le système calcule correctement

:::tip
Si le robot va dans la mauvaise direction lors d'un déplacement, l'axe X ou Y est inversé dans `config.py`. Modifier le signe du vecteur BOARD_ORIGIN.
:::

### Désactiver FreeDrive

```
[Désactiver FreeDrive]
```

## Étape 3 : Calibration Z

La hauteur Z doit être ajustée pour que la pince saisisse les pièces correctement.

### Procédure

1. Placer un **pion** sur la case a1
2. Utiliser **Z-** pour descendre le robot jusqu'à la pince
3. Arrêter quand la pince est à **5mm au-dessus** de la tête du pion
4. Cliquer **Enregistrer Z**

:::warning
Les boutons Z sont désactivés quand FreeDrive est actif. Désactivez d'abord FreeDrive.
:::

### Hauteurs par pièce

Si vous avez des pièces de tailles différentes, ajustez les hauteurs dans `config.py` :

```python
HAUTEUR_PIECES = {
    chess.PAWN:   -0.150,  # ajuster selon vos pièces
    chess.ROOK:   -0.145,
    chess.KNIGHT: -0.148,
    chess.BISHOP: -0.148,
    chess.QUEEN:  -0.140,
    chess.KING:   -0.140,
}
```

## Étape 4 : Test de calibration

### Test simple

1. Placer un pion en **e4**
2. Dans le terminal backend :
```python
await robot._prendre_piece("e4")
await robot._poser_piece("e5")
```
3. Vérifier que le pion est bien en e5

### Test complet

Lancer une partie courte et observer :
- Le robot prend-il les pièces au centre ?
- La pièce ne tombe-t-elle pas à côté ?
- Les captures fonctionnent-elles ?

## Étape 5 : Sauvegarder

```
[Sauvegarder la calibration]
```

La calibration est écrite dans `config.py` et sera rechargée au prochain démarrage.

## Problèmes courants

### Décalage constant dans une direction

Le robot rate toutes les cases avec un décalage fixe (ex: 5mm à gauche).

**Solution :** Ajuster `BOARD_ORIGIN` dans `config.py` :
```python
BOARD_ORIGIN[0] += 0.005  # +5mm en X
```

### Cases au bord rateées, centre OK

Le `CASE_SIZE` est légèrement incorrect.

**Solution :** Mesurer physiquement la taille d'une case et mettre à jour :
```python
CASE_SIZE = 0.057  # au lieu de 0.055
```

### Pince ne saisit pas la pièce

La hauteur Z est trop haute.

**Solution :** Descendre Z de quelques mm dans les `HAUTEUR_PIECES`.

### Pièce renversée lors de la prise

La hauteur Z est trop basse, la pince pousse la pièce.

**Solution :** Monter Z de 2-3mm.
