# test_aruco_detection

Test simple de détection des marqueurs ArUco sur les pièces d'échecs.

## Ce que fait ce test

1. Prend une photo via la caméra (Raspberry Pi ou webcam)
2. Détecte tous les marqueurs ArUco présents (dictionnaire `DICT_4X4_50`)
3. Identifie chaque marqueur :
   - **IDs 0–15** → pièces blanches (WP1…WK)
   - **IDs 16–31** → pièces noires (BP1…BK)
   - **IDs 32–35** → coins de calibration du plateau (TL/TR/BL/BR)
4. Affiche le résumé dans le terminal
5. Sauvegarde une image annotée dans `output/`

## Usage

```bash
# Depuis la racine du projet
cd /home/loan/Documents/Junia/AP5/projet_chess/chess-project

# Avec prise de photo (caméra requise)
python -m test.test_aruco_detection

# Avec une image existante
python -m test.test_aruco_detection --image path/to/photo.jpg

# Afficher le résultat dans une fenêtre
python -m test.test_aruco_detection --image photo.jpg --show
```

## Mapping ArUco → Pièces

| IDs   | Couleur | Pièces                         |
|-------|---------|--------------------------------|
| 0–7   | Blanc   | Pions WP1–WP8                  |
| 8–9   | Blanc   | Tours WR1–WR2                  |
| 10–11 | Blanc   | Cavaliers WN1–WN2              |
| 12–13 | Blanc   | Fous WB1–WB2                   |
| 14    | Blanc   | Dame WQ                        |
| 15    | Blanc   | Roi WK                         |
| 16–23 | Noir    | Pions BP1–BP8                  |
| 24–25 | Noir    | Tours BR1–BR2                  |
| 26–27 | Noir    | Cavaliers BN1–BN2              |
| 28–29 | Noir    | Fous BB1–BB2                   |
| 30    | Noir    | Dame BQ                        |
| 31    | Noir    | Roi BK                         |
| 32–35 | —       | Coins plateau CAL (TL/TR/BL/BR)|

## Étapes suivantes

- Appliquer des prétraitements d'image (CLAHE, débruitage…) pour améliorer la détection
- Tester différents paramètres `ARUCO_PARAMS` dans `chess_vision/config.py`
