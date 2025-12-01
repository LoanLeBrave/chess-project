"""
Configuration Génération 2 - Évolution basée sur E, F, J (meilleurs de Gen1)

Gagnants Gen1:
- J_combo1:     bright=1.2, sat=2.5, contrast=1.8, hue1=[0,10], hue2=[160,180], sat_min=60, val_min=50
- F_sat_strict: bright=1.0, sat=2.0, contrast=1.5, hue1=[0,12], hue2=[155,180], sat_min=60, val_min=40
- E_hue_strict: bright=1.0, sat=2.0, contrast=1.5, hue1=[0,8],  hue2=[165,180], sat_min=40, val_min=40

Stratégie Gen2: Créer des variations autour de ces 3 gagnants
"""

CONFIGS = [
    # =========================================
    # VARIATIONS DE J (combo1) - Le meilleur
    # =========================================
    {
        "name": "J1_base",
        "description": "J original - référence",
        "brightness": 1.2,
        "saturation": 2.5,
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 10,
        "hue_low2": 160, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 50,
    },
    {
        "name": "J2_sat_plus",
        "description": "J avec plus de saturation",
        "brightness": 1.2,
        "saturation": 2.8,  # +0.3
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 10,
        "hue_low2": 160, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 50,
    },
    {
        "name": "J3_sat_min_plus",
        "description": "J avec sat_min plus strict",
        "brightness": 1.2,
        "saturation": 2.5,
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 10,
        "hue_low2": 160, "hue_high2": 180,
        "sat_min": 70,  # +10
        "val_min": 50,
    },
    {
        "name": "J4_contrast_plus",
        "description": "J avec plus de contraste",
        "brightness": 1.2,
        "saturation": 2.5,
        "contrast": 2.0,  # +0.2
        "hue_low1": 0, "hue_high1": 10,
        "hue_low2": 160, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 50,
    },
    
    # =========================================
    # VARIATIONS DE F (sat_strict)
    # =========================================
    {
        "name": "F1_base",
        "description": "F original - référence",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 12,
        "hue_low2": 155, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    {
        "name": "F2_sat_min_plus",
        "description": "F avec sat_min encore plus strict",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 12,
        "hue_low2": 155, "hue_high2": 180,
        "sat_min": 75,  # +15
        "val_min": 40,
    },
    {
        "name": "F3_bright_like_J",
        "description": "F avec brightness de J",
        "brightness": 1.2,  # comme J
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 12,
        "hue_low2": 155, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    {
        "name": "F4_sat_like_J",
        "description": "F avec saturation de J",
        "brightness": 1.0,
        "saturation": 2.5,  # comme J
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 12,
        "hue_low2": 155, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    
    # =========================================
    # VARIATIONS DE E (hue_strict)
    # =========================================
    {
        "name": "E1_base",
        "description": "E original - référence",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 40,
        "val_min": 40,
    },
    {
        "name": "E2_sat_min_like_F",
        "description": "E avec sat_min de F",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 60,  # comme F
        "val_min": 40,
    },
    {
        "name": "E3_hue_more_strict",
        "description": "E avec hue encore plus strict",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,   # -2
        "hue_low2": 170, "hue_high2": 180,  # +5
        "sat_min": 40,
        "val_min": 40,
    },
    {
        "name": "E4_all_J_params",
        "description": "E avec bright/sat/contrast de J",
        "brightness": 1.2,
        "saturation": 2.5,
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 40,
        "val_min": 40,
    },
    
    # =========================================
    # HYBRIDES E+F+J
    # =========================================
    {
        "name": "H1_E_hue_F_sat",
        "description": "Hue strict de E + sat_min de F",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,   # E
        "hue_low2": 165, "hue_high2": 180,  # E
        "sat_min": 60,  # F
        "val_min": 40,
    },
    {
        "name": "H2_J_enhance_E_hue",
        "description": "Enhancements de J + hue de E",
        "brightness": 1.2,
        "saturation": 2.5,
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 8,   # E strict
        "hue_low2": 165, "hue_high2": 180,  # E strict
        "sat_min": 60,  # J
        "val_min": 50,  # J
    },
    {
        "name": "H3_best_of_all",
        "description": "Meilleur de chaque: J enhance + E hue + F sat_min",
        "brightness": 1.2,
        "saturation": 2.5,
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 70,  # Plus strict que J
        "val_min": 50,
    },
    {
        "name": "H4_ultra_strict",
        "description": "Configuration ultra stricte",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
]
