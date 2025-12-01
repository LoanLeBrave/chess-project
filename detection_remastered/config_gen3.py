"""
Configuration Génération 3 - Évolution basée sur E2, H1, H4 (meilleurs de Gen2)

Gagnants Gen2:
- E2_sat_min_like_F: bright=1.0, sat=2.0, contrast=1.5, hue1=[0,8], hue2=[165,180], sat_min=60, val_min=40
- H1_E_hue_F_sat:    bright=1.0, sat=2.0, contrast=1.5, hue1=[0,8], hue2=[165,180], sat_min=60, val_min=40
- H4_ultra_strict:   bright=1.2, sat=2.8, contrast=2.0, hue1=[0,6], hue2=[170,180], sat_min=80, val_min=60

Note: E2 et H1 sont identiques ! On a donc 2 profils distincts:
- Profil "doux": bright=1.0, sat=2.0, contrast=1.5, hue strict, sat_min=60
- Profil "agressif" (H4): bright=1.2, sat=2.8, contrast=2.0, hue très strict, sat_min=80

Stratégie Gen3: Explorer entre ces deux profils + variations fines
"""

CONFIGS = [
    # =========================================
    # RÉFÉRENCES - Les gagnants
    # =========================================
    {
        "name": "A_E2_ref",
        "description": "E2/H1 original - référence douce",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    {
        "name": "B_H4_ref",
        "description": "H4 original - référence agressive",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    
    # =========================================
    # VARIATIONS DE E2 (profil doux)
    # =========================================
    {
        "name": "C_E2_sat_min_plus",
        "description": "E2 avec sat_min plus strict",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 70,  # +10
        "val_min": 40,
    },
    {
        "name": "D_E2_hue_like_H4",
        "description": "E2 avec hue strict comme H4",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,   # comme H4
        "hue_low2": 170, "hue_high2": 180,  # comme H4
        "sat_min": 60,
        "val_min": 40,
    },
    {
        "name": "E_E2_val_min_plus",
        "description": "E2 avec val_min plus haut",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 50,  # +10
    },
    {
        "name": "F_E2_sat_plus",
        "description": "E2 avec plus de saturation image",
        "brightness": 1.0,
        "saturation": 2.4,  # +0.4
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    
    # =========================================
    # VARIATIONS DE H4 (profil agressif)
    # =========================================
    {
        "name": "G_H4_sat_min_moins",
        "description": "H4 avec sat_min moins strict",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 70,  # -10
        "val_min": 60,
    },
    {
        "name": "H_H4_val_min_moins",
        "description": "H4 avec val_min moins strict",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 50,  # -10
    },
    {
        "name": "I_H4_hue_relax",
        "description": "H4 avec hue moins strict",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 8,   # +2
        "hue_low2": 165, "hue_high2": 180,  # -5
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "J_H4_bright_moins",
        "description": "H4 avec moins de brightness",
        "brightness": 1.1,  # -0.1
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    
    # =========================================
    # HYBRIDES E2 + H4 (entre les deux profils)
    # =========================================
    {
        "name": "K_mid_enhance_E2_filter",
        "description": "Enhance moyen + filtres E2",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    {
        "name": "L_mid_enhance_H4_filter",
        "description": "Enhance moyen + filtres H4",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "M_E2_enhance_H4_filter",
        "description": "E2 enhance + H4 filtres",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "N_H4_enhance_E2_filter",
        "description": "H4 enhance + E2 filtres",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    
    # =========================================
    # ULTRA VARIATIONS
    # =========================================
    {
        "name": "O_ultra_sat_min",
        "description": "sat_min très élevé pour éliminer tout bruit",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 7,
        "hue_low2": 167, "hue_high2": 180,
        "sat_min": 90,  # Très strict
        "val_min": 50,
    },
    {
        "name": "P_balanced_best",
        "description": "Équilibre optimisé entre E2 et H4",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 7,
        "hue_low2": 167, "hue_high2": 180,
        "sat_min": 70,
        "val_min": 50,
    },
]
