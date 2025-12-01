"""
Configuration Génération 5 (FINALE) - Basée sur E_L, F_O, K_C, M_L, O_O (meilleurs de Gen4)

Gagnants Gen4:
- E_L_ref:         bright=1.1, sat=2.4, contrast=1.75, hue1=[0,6], hue2=[170,180], sat_min=80, val_min=60
- F_O_ref:         bright=1.1, sat=2.4, contrast=1.75, hue1=[0,7], hue2=[167,180], sat_min=90, val_min=50
- K_C_hue_strict:  bright=1.0, sat=2.0, contrast=1.5,  hue1=[0,6], hue2=[170,180], sat_min=70, val_min=40
- M_L_sat85_val55: bright=1.1, sat=2.4, contrast=1.75, hue1=[0,6], hue2=[170,180], sat_min=85, val_min=55
- O_O_hue5:        bright=1.1, sat=2.4, contrast=1.75, hue1=[0,5], hue2=[172,180], sat_min=90, val_min=50

PATTERNS FINAUX IDENTIFIÉS:
- Enhance optimal: bright=1.1, sat=2.4, contrast=1.75 (sauf K qui est plus doux)
- Hue strict: [0,5-7] et [167-172,180]
- sat_min: 70-90 (tendance 80-90)
- val_min: 40-60 (tendance 50-55)
"""

CONFIGS = [
    # =========================================
    # LES 5 RÉFÉRENCES GAGNANTES
    # =========================================
    {
        "name": "A_E_L",
        "description": "E_L original",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "B_F_O",
        "description": "F_O original",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 7,
        "hue_low2": 167, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 50,
    },
    {
        "name": "C_K_C",
        "description": "K_C original (profil doux)",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 70,
        "val_min": 40,
    },
    {
        "name": "D_M_L",
        "description": "M_L original",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 85,
        "val_min": 55,
    },
    {
        "name": "E_O_O",
        "description": "O_O original (hue très strict)",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 172, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 50,
    },
    
    # =========================================
    # FINE-TUNING FINAL - Micro-variations
    # =========================================
    {
        "name": "F_M_L_sat87",
        "description": "M_L avec sat_min=87",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 87,
        "val_min": 55,
    },
    {
        "name": "G_M_L_sat83",
        "description": "M_L avec sat_min=83",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 83,
        "val_min": 55,
    },
    {
        "name": "H_O_O_sat88",
        "description": "O_O avec sat_min=88",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 172, "hue_high2": 180,
        "sat_min": 88,
        "val_min": 50,
    },
    {
        "name": "I_O_O_val55",
        "description": "O_O avec val_min=55",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 172, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 55,
    },
    
    # =========================================
    # HYBRIDES FINAUX - Meilleurs combos
    # =========================================
    {
        "name": "J_M_O_hybrid",
        "description": "M_L filtres + O_O sat_min",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 55,
    },
    {
        "name": "K_O_M_hybrid",
        "description": "O_O hue + M_L sat_min/val_min",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 172, "hue_high2": 180,
        "sat_min": 85,
        "val_min": 55,
    },
    {
        "name": "L_E_O_hybrid",
        "description": "E_L + O_O sat_min",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 60,
    },
    
    # =========================================
    # CANDIDATS OPTIMAUX FINAUX
    # =========================================
    {
        "name": "M_optimal_v1",
        "description": "Optimal: enhance standard + sat_min=86 + val_min=55",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 86,
        "val_min": 55,
    },
    {
        "name": "N_optimal_v2",
        "description": "Optimal: hue très strict + sat_min=88",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 172, "hue_high2": 180,
        "sat_min": 88,
        "val_min": 52,
    },
    {
        "name": "O_optimal_v3",
        "description": "Optimal: équilibre parfait",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 171, "hue_high2": 180,
        "sat_min": 87,
        "val_min": 53,
    },
    {
        "name": "P_FINAL",
        "description": "CONFIGURATION FINALE RECOMMANDÉE",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 85,
        "val_min": 55,
    },
]
