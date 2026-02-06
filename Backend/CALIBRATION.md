# 🎯 Guide de Calibration du Robot d'Échecs

## Vue d'ensemble

Le système de calibration utilise un **trou percé dans l'échiquier** comme point de référence précis pour corriger automatiquement toutes les positions du robot.

## 📏 Caractéristiques du Trou de Calibration

- **Largeur**: 12 mm (taille de la pince fermée)
- **Hauteur**: 22 mm
- **Position**: Aligné avec y=0 (ligne du bas de l'échiquier)
- **Distance**: 10 mm à droite de la case h1 (coin bas droit)

```
┌─────────────────────────────┐
│  Échiquier (28×28 cm)      │
│                             │
│  a8 ... h8                 │
│   :      :                 │
│  a1 ... h1 ▓ ← Trou        │
└─────────────┘ │             
                └─ 10mm
```

## 🚀 Utilisation

### Lancement
```bash
python calibration.py
```

### Processus de Calibration

#### 1️⃣ **Initialisation** (Automatique)
- Connexion au robot UR5e
- Activation et fermeture du gripper
- Chargement du mapping existant

#### 2️⃣ **Prépositionnement** (Automatique)
- Le robot se positionne au-dessus du trou théorique
- Position calculée à partir de la case h1 + 10mm

#### 3️⃣ **Ajustement Manuel X/Y** (Interactif)
- Le robot passe en **mode freedrive** sur les axes X et Y
- Déplacez manuellement le robot pour aligner le gripper avec le trou
- Les axes Z, RX, RY, RZ restent bloqués pour la sécurité

#### 4️⃣ **Descente dans le Trou** (Contrôle Clavier)

**Touches disponibles:**

| Touche | Action |
|--------|--------|
| `↓` ou `S` | Descendre de 1mm |
| `↑` ou `W` | Remonter de 1mm |
| `Q` | Valider et enregistrer |
| `ESC` | Annuler la calibration |

**Fonctionnement:**
- Tant qu'une touche est **pressée** → Mouvement contrôlé (freedrive désactivé)
- Dès que la touche est **relâchée** → Freedrive X/Y réactivé automatiquement
- Cela permet d'alterner rapidement entre ajustement fin et repositionnement manuel

#### 5️⃣ **Calcul de l'Offset** (Automatique)
- Compare la position mesurée vs position théorique
- Affiche l'offset en X, Y, Z (en mm)
- Affiche la distance 2D totale

#### 6️⃣ **Application de l'Offset** (Après confirmation)
- Applique l'offset à **toutes les 64 cases** de l'échiquier
- Applique l'offset aux **zones d'élimination** (blancs et noirs)
- Crée une **backup** du fichier original

#### 7️⃣ **Sauvegarde** (Automatique)
- Sauvegarde le mapping corrigé dans `chess_board_positions.json`
- La backup est dans `chess_board_positions_backup.json`

## 📊 Exemple de Sortie

```
====================================================
🎯 CALIBRATION DU ROBOT D'ÉCHECS
====================================================

🤖 Connexion au robot 192.168.0.11...
🦾 Activation du gripper...
🤏 Fermeture du gripper...
✅ Robot connecté!

✅ Mapping chargé: 64 cases

📍 Prépositionnement au-dessus du trou théorique...
   Position: X=0.4523, Y=0.0012, Z=0.0823
✅ Prépositionnement terminé

====================================================
🎮 MODE DESCENTE INTERACTIVE
====================================================

📋 Instructions:
  1. Ajustez la position X/Y manuellement (le robot est en freedrive)
  2. Utilisez les touches pour descendre dans le trou:
     ↓ ou S : Descendre de 1mm
     ↑ ou W : Remonter de 1mm
     Q : Valider et enregistrer cette position
     ESC : Annuler la calibration

⚠️  Dès qu'une touche est relâchée, le freedrive X/Y est réactivé
====================================================

📍 Position: X=0.4528, Y=0.0015, Z=0.0234

⬇️  Descente de 1.0mm
⬇️  Descente de 1.0mm

✅ Position de calibration enregistrée!

====================================================
📊 ANALYSE DE L'OFFSET
====================================================
Position théorique: X=0.4520, Y=0.0010, Z=0.0300
Position mesurée:   X=0.4528, Y=0.0015, Z=0.0234

Offset calculé:
  ΔX = +0.80 mm
  ΔY = +0.50 mm
  ΔZ = -6.60 mm

  Distance 2D = 0.94 mm
====================================================

⚠️  Voulez-vous appliquer cet offset à toutes les positions? (o/n): o

🔧 Application de l'offset à toutes les cases...
   ✓ Zone zone_elimination_blancs_min corrigée
   ✓ Zone zone_elimination_blancs_max corrigée
   ✓ Zone zone_elimination_noirs_min corrigée
   ✓ Zone zone_elimination_noirs_max corrigée
✅ 64 cases corrigées

💾 Backup créée: chess_board_positions_backup.json
✅ Mapping corrigé sauvegardé: chess_board_positions.json

====================================================
✅ CALIBRATION TERMINÉE AVEC SUCCÈS!
====================================================
```

## 🔧 Détails Techniques

### Mode Freedrive Sélectif
```python
# Axes: [x, y, z, rx, ry, rz]
# 1 = libre, 0 = bloqué
selection = [1, 1, 0, 0, 0, 0]  # Libre en X et Y uniquement
```

### Calcul de la Position Théorique du Trou
```python
position_trou[X] = h1[X] + 10mm + (12mm / 2)  # Centré sur le trou
position_trou[Y] = h1[Y]  # Aligné avec la ligne du bas
position_trou[Z] = h1[Z] + 50mm  # 5cm au-dessus pour commencer
```

### Calcul de l'Offset
```python
offset[X] = position_mesurée[X] - position_théorique[X]
offset[Y] = position_mesurée[Y] - position_théorique[Y]
offset[Z] = position_mesurée[Z] - position_théorique[Z]
```

### Application aux Cases
```python
for case in cases:
    case.tcp[X] += offset[X]
    case.tcp[Y] += offset[Y]
    case.tcp[Z] += offset[Z]
```

## ⚠️ Précautions

1. **Gripper fermé**: Le gripper doit être fermé pour entrer dans le trou
2. **Descente progressive**: Descendre lentement (1mm par appui) pour éviter les chocs
3. **Backup automatique**: Une sauvegarde est toujours créée avant modification
4. **Vérification visuelle**: Assurez-vous que le gripper est bien centré dans le trou

## 🔄 Quand Re-calibrer?

- Après avoir déplacé l'échiquier
- Si les prises de pièces deviennent imprécises
- Après toute modification mécanique du setup
- Recommandé: 1 fois par semaine pour précision optimale

## 📝 Fichiers Modifiés

- `chess_board_positions.json` - Mapping corrigé avec offset appliqué
- `chess_board_positions_backup.json` - Backup de l'ancien mapping

## 🐛 Dépannage

**Le robot ne bouge pas en freedrive:**
- Vérifiez que le mode enseigner (Teach) n'est pas activé
- Redémarrez le module de calibration

**Le gripper ne rentre pas dans le trou:**
- Vérifiez que le gripper est bien fermé
- Utilisez les touches ↑/↓ pour ajuster finement la hauteur
- Repositionnez en X/Y avec le freedrive

**L'offset semble trop grand (>5mm):**
- Vérifiez la position de la case h1 dans le mapping
- Vérifiez que les dimensions du trou sont correctes
- Re-mesurez la distance trou ↔ h1

## 🎓 Conseils d'Utilisation

1. **Première fois**: Prenez votre temps pour bien centrer le gripper
2. **Descente**: Descendez par petits paliers et vérifiez l'alignement
3. **Validation**: Une fois dans le trou, bougez légèrement en X/Y pour vérifier que c'est bien centré
4. **Offset**: Un offset de 0.5-2mm est normal, >5mm indique un problème
