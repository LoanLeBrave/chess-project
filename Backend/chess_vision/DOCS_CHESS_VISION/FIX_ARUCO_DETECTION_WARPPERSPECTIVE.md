# Problème de détection ArUco après transformation perspective

**Date**: 6 février 2026  
**Status**: ✅ RÉSOLU  
**Impact**: Critique - empêchait la détection des pièces

---

## 🔍 Problème identifié

### Symptômes
- **Image originale (4608×2592)** : 5 pièces détectées ✅
- **Plateau extrait (800×800)** : 0 pièce détectée ❌
- OpenCV trouve 665 candidats ArUco mais **les rejette tous**

### Cause racine

`cv2.warpPerspective()` utilise une **interpolation bilinéaire** par défaut qui crée des pixels intermédiaires gris entre les zones noires et blanches des marqueurs ArUco.

```
Image originale:     ████████     (bords nets, bits clairs)
                     ████████
                     
Après warpPerspective: ▓▓██████▓▓   (pixels gris aux bords)
                      ▓▓██████▓▓   (bits ambigus → rejeté)
```

Les marqueurs ArUco encodent des informations binaires (noir/blanc). L'interpolation dégrade cette information → OpenCV ne peut plus décoder l'ID → rejet.

---

## 🧪 Tests effectués

| Test | Méthode | Résultat | Candidats rejetés |
|------|---------|----------|-------------------|
| 1 | Image originale 4608×2592 | ✅ 5 pièces | 494 |
| 2 | warpPerspective 800×800 INTER_LINEAR | ❌ 0 pièce | **665** |
| 3 | warpPerspective 800×800 INTER_NEAREST | ❌ 0 pièce | 420 |
| 4 | warpPerspective 2000×2000 INTER_NEAREST | ❌ 0 pièce | 81 |
| 5 | warpPerspective 2000×2000 INTER_LINEAR | ❌ 0 pièce | 158 |
| 6 | **Détection sur original + projection** | ✅ **5 pièces** | N/A |

**Conclusion** : Aucune méthode d'interpolation ou augmentation de résolution ne résout le problème. La transformation perspective **détruit** l'information des ArUcos.

---

## ✅ Solution adoptée

### Principe
**Détecter sur l'image originale, projeter les coordonnées vers le plateau extrait.**

1. Détection ArUco sur l'image **originale** (haute résolution, pixels nets)
2. Transformation des coordonnées via la matrice de perspective
3. Projection dans le repère du plateau extrait (800×800)

### Avantages
- ✅ **Précision maximale** : haute résolution + pas de dégradation
- ✅ **Mathématiquement exact** : projection linéaire via matrice
- ✅ **Robuste** : exploite la meilleure qualité disponible
- ✅ **Performance** : détection unique sur l'original

### Code implémenté

#### piece_analyzer.py
```python
def analyze_pieces(
    self, 
    board_img: np.ndarray,
    transform_matrix: np.ndarray = None,
    original_img: np.ndarray = None
) -> List[Dict[str, Any]]:
    """
    Stratégie de détection :
        - Si original_img + transform_matrix fournis : détecte sur l'image
          originale (haute résolution, ArUcos nets) puis projette les
          coordonnées vers le repère du plateau extrait.
        - Sinon : détecte directement sur board_img (fallback).
    """
    if original_img is not None and transform_matrix is not None:
        return self.analyze_from_original(original_img, transform_matrix)
    
    # Fallback : détection sur le plateau extrait
    piece_markers = detect_piece_markers(board_img, self.detector)
    # ...
```

#### analyze_from_original()
```python
def analyze_from_original(
    self,
    original_img: np.ndarray,
    transform_matrix: np.ndarray
) -> List[Dict[str, Any]]:
    """Détecte sur l'original et projette les coordonnées."""
    
    # 1. Détecter sur l'image originale
    piece_markers = detect_piece_markers(original_img, self.detector)
    
    for marker_id, data in piece_markers.items():
        cx_orig, cy_orig = data['center']
        
        # 2. Projeter via la matrice de transformation
        point_orig = np.array([[[cx_orig, cy_orig]]], dtype=np.float32)
        point_board = cv2.perspectiveTransform(point_orig, transform_matrix)[0][0]
        px, py = float(point_board[0]), float(point_board[1])
        
        # 3. Vérifier les limites
        if not (0 <= px < self.board_size and 0 <= py < self.board_size):
            continue
        
        # 4. Convertir en coordonnées board (-10/+10) et chess (a1-h8)
        board_x, board_y = self.pixel_to_board_coords(px, py)
        chess_square = self.pixel_to_chess_square(px, py)
        # ...
```

---

## 🔬 Pourquoi l'œil humain voit les marqueurs mais pas OpenCV ?

### Perception humaine
- Tolère le flou et les dégradés
- Reconstruit mentalement les formes
- Insensible aux variations d'intensité locale

### Décodage ArUco
1. **Seuillage adaptatif** : déterminer noir vs blanc par zone
2. **Extraction de bits** : lire la matrice 4×4 interne
3. **Vérification code correcteur** : valider l'ID
4. **Rejet si incertain** : pixels gris → bits ambigus → rejet

Les pixels gris créés par l'interpolation tombent dans une zone d'ambiguïté où le seuillage adaptatif ne peut pas trancher → bits illisibles → ID invalide.

---

## 📊 Données de validation

### Test sur photo réelle (6 février 2026)
```
Image originale : 4608x2592
Plateau extrait : 800x800

Détection sur IMAGE ORIGINALE:
  Total: 9 marqueurs
  Pièces: 5/32 (IDs: 1, 7, 20, 28, 30)
  Calibration: 4/4 (IDs: 32, 33, 34, 35)

Détection sur PLATEAU EXTRAIT 800x800:
  Total: 0 marqueur
  Candidats rejetés: 665 ❌

Détection sur ORIGINAL + PROJECTION:
  ID  1 : original(2700,1190) → board(198,399) ✅
  ID  7 : original(1834,1809) → board(582,617) ✅
  ID 20 : original(2722,978)  → board(181,310) ✅
  ID 28 : original(2722,1537) → board(203,546) ✅
  ID 30 : original(2749,1343) → board(183,465) ✅
```

---

## 🎯 Impact sur le pipeline

### Avant (détection échouait)
```
Image → warpPerspective(800×800) → detect_piece_markers() → ❌ 0 pièce
```

### Après (détection fonctionne)
```
Image → detect_piece_markers(original) → perspectiveTransform(coords) → ✅ 5 pièces
     ↘                                    ↗
       warpPerspective(800×800, visualisation)
```

Le plateau extrait sert **uniquement pour la visualisation** (grille, annotations). La détection se fait toujours sur l'original.

---

## 📝 Modules modifiés

| Fichier | Changement | Ligne |
|---------|-----------|-------|
| `piece_analyzer.py` | `analyze_pieces()` utilise `analyze_from_original()` si possible | 184 |
| `__init__.py` | Passe `original_img` et `transform_matrix` à `analyze_pieces()` | 234 |
| `test_piece_analysis.py` | Détecte sur original, projette pour visualisation | 433 |

---

## 🔗 Références

- **Script de diagnostic** : `chess_vision/tests/test_compare_detection.py`
- **Issue** : Détection ArUco échoue après extraction plateau
- **Solution** : Détection sur image haute résolution + projection mathématique

---

## 💡 Recommandations futures

### Ne PAS
- ❌ Détecter sur une image transformée par `warpPerspective`
- ❌ Upscaler une image déjà interpolée (information perdue)
- ❌ Utiliser INTER_NEAREST (crée des artefacts, ne résout pas le problème)

### FAIRE
- ✅ Toujours détecter sur l'image source haute résolution
- ✅ Utiliser `cv2.perspectiveTransform()` pour projeter les coordonnées
- ✅ Garder le plateau extrait pour la visualisation uniquement
- ✅ Optimiser le focus caméra (lens_position=10.0 pour Raspberry Pi)

---

**Auteur**: Système de vision chess_vision  
**Validation**: Tests réels sur Raspberry Pi avec caméra HQ
