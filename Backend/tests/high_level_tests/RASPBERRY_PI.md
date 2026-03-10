# Tests Chess Vision - Guide Rapide Raspberry Pi 🍓

## Installation sur Raspberry Pi

```bash
cd /home/loan/Documents/Junia/AP5/projet_chess/chess-project
```

## Tests avec la caméra en direct

### Test rapide complet
```bash
# Script tout-en-un (capture + tous les tests)
./chess_vision/tests/quick_test.sh
```

### Tests individuels avec capture photo

```bash
# Test détection ArUco
python3 -m chess_vision.tests.test_aruco_detection --photo

# Test calibration plateau
python3 -m chess_vision.tests.test_board_calibration --photo

# Test analyse des pièces
python3 -m chess_vision.tests.test_piece_analysis --photo

# Test pipeline complet
python3 -m chess_vision.tests.test_full_pipeline --photo
```

## Voir les résultats

```bash
# Aller dans le dossier de sortie
cd chess_vision/tests/output/

# Voir les derniers tests
ls -lrt

# Ouvrir le dernier dossier
cd $(ls -t | head -1)

# Lister les images
ls -lh *.jpg
```

## Consulter les images de debug

Les images sont numérotées dans l'ordre du processus :

```bash
# Avec eog (Eye of GNOME) ou autre viewer
eog 01_original_input.jpg
eog 03_offsets_visualization.jpg
eog 09_board_with_labeled_grid.jpg

# Ou toutes d'un coup
eog *.jpg
```

## Mode interactif

```bash
python3 -m chess_vision.tests.run_all_tests --interactive
```

Ce mode vous permet de :
1. Choisir une image existante OU capturer une nouvelle photo
2. Choisir quel test lancer
3. Voir les résultats en temps réel

## Débugger un problème

### Problème: ArUcos non détectés

```bash
# Lancer le test de détection avec analyse de qualité
python3 -m chess_vision.tests.test_aruco_detection --photo

# Consulter les images:
# - quality_comparison_1.jpg : comparaison des méthodes
# - 03_calibration_markers_detail.jpg : marqueurs détectés
```

**Solution :** Vérifier l'éclairage, le focus de la caméra, et les paramètres ArUco dans `config.py`

### Problème: Plateau mal calibré

```bash
# Lancer le test de calibration
python3 -m chess_vision.tests.test_board_calibration --photo

# Consulter:
# - 03_offsets_visualization.jpg : vérifier les offsets
# - 04_calculated_corners.jpg : vérifier le quadrilatère
```

**Solution :** Ajuster les `OFFSETS` dans `chess_vision/config.py`

### Problème: Pièces mal positionnées

```bash
# Lancer le test d'analyse
python3 -m chess_vision.tests.test_piece_analysis --photo

# Consulter:
# - 06_coordinate_conversion_demo.jpg : conversion coordonnées
# - piece_mapping.json : correspondances
```

**Solution :** Vérifier que le plateau est bien extrait et les offsets corrects

## Statistiques des tests

Après chaque test, un fichier `metadata.json` est créé avec :
- Toutes les étapes du test
- Les métriques (temps, compteurs)
- Les résultats de chaque étape

```bash
# Voir les métadonnées du dernier test
cd chess_vision/tests/output/
cat $(ls -t | head -1)/metadata.json | python3 -m json.tool
```

## Tips Raspberry Pi

### Optimiser la caméra

Si les images sont floues ou mal exposées :

```python
# Éditer chess_vision/config.py
CAMERA_CONFIG = {
    'resolution': (1920, 1080),
    'exposure_time': 33000,  # Ajuster selon l'éclairage (µs)
    'analogue_gain': 1.0,
    'awb_mode': 'auto',
    'brightness': 0.0,
    'contrast': 1.0,
    'saturation': 1.0,
    'sharpness': 1.0,
}
```

### Libérer de l'espace

Les tests génèrent beaucoup d'images. Pour nettoyer :

```bash
# Supprimer les anciens tests (garder les 5 derniers)
cd chess_vision/tests/output/
ls -t | tail -n +6 | xargs rm -rf

# Ou tout supprimer
rm -rf chess_vision/tests/output/*
```

### Performance

```bash
# Voir l'utilisation CPU/RAM pendant les tests
htop

# En parallèle dans un autre terminal :
python3 -m chess_vision.tests.test_full_pipeline --photo
```

## Workflow recommandé

1. **Premier test :** Vérifier la détection ArUco
   ```bash
   python3 -m chess_vision.tests.test_aruco_detection --photo
   ```

2. **Ajuster la calibration** si nécessaire (offsets dans `config.py`)

3. **Tester la calibration**
   ```bash
   python3 -m chess_vision.tests.test_board_calibration --photo
   ```

4. **Test complet**
   ```bash
   python3 -m chess_vision.tests.test_full_pipeline --photo
   ```

5. **Utilisation en production**
   ```bash
   python3 -m chess_vision.main --photo
   ```

## Résumé des commandes utiles

| Commande | Description |
|----------|-------------|
| `./chess_vision/tests/quick_test.sh` | Test rapide complet |
| `python3 -m chess_vision.tests.run_all_tests --photo` | Tous les tests + capture |
| `python3 -m chess_vision.tests.test_aruco_detection --photo` | Test ArUco seul |
| `python3 -m chess_vision.tests.test_board_calibration --photo` | Test calibration seul |
| `python3 -m chess_vision.tests.run_all_tests --list` | Liste des tests |
| `python3 -m chess_vision.tests.run_all_tests --interactive` | Mode interactif |

## Support

Pour tout problème :
1. Consulter les images dans `chess_vision/tests/output/`
2. Vérifier `metadata.json` pour les détails
3. Ajuster `chess_vision/config.py` selon les besoins

---

**Fait avec ❤️ pour le projet Chess Robot** 🤖♟️
