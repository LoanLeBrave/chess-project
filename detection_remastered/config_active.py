"""
Configuration Active - Paramètres de traitement d'image sélectionnés

Ce fichier contient la configuration actuellement utilisée par le script de détection.
Pour changer la configuration, modifiez les valeurs ci-dessous ou copiez une config
depuis les fichiers config_gen1.py à config_gen5.py.

Configuration actuelle: N_optimal_v2 (Gen5)
"""

# ============================================================
# CONFIGURATION ACTIVE
# ============================================================
ACTIVE_CONFIG = {
    "name": "N_optimal_v2",
    "description": "Optimal: hue très strict + sat_min=88",
    
    # Paramètres d'amélioration d'image
    "brightness": 1.1,
    "saturation": 2.4,
    "contrast": 1.75,
    
    # Paramètres de détection du rouge (HSV)
    # Plage 1: rouges bas (0-5)
    "hue_low1": 0,
    "hue_high1": 5,
    # Plage 2: rouges hauts (172-180)
    "hue_low2": 172,
    "hue_high2": 180,
    
    # Seuils de saturation et valeur
    "sat_min": 88,
    "val_min": 52,
}

# ============================================================
# ACCÈS RAPIDE AUX PARAMÈTRES
# ============================================================
# Enhancement
BRIGHTNESS_FACTOR = ACTIVE_CONFIG["brightness"]
SATURATION_FACTOR = ACTIVE_CONFIG["saturation"]
CONTRAST_FACTOR = ACTIVE_CONFIG["contrast"]

# Hue ranges
RED_HUE_LOW1 = ACTIVE_CONFIG["hue_low1"]
RED_HUE_HIGH1 = ACTIVE_CONFIG["hue_high1"]
RED_HUE_LOW2 = ACTIVE_CONFIG["hue_low2"]
RED_HUE_HIGH2 = ACTIVE_CONFIG["hue_high2"]

# Thresholds
RED_SAT_MIN = ACTIVE_CONFIG["sat_min"]
RED_VAL_MIN = ACTIVE_CONFIG["val_min"]
