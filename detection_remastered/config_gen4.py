"""
Configuration Génération 4 - Évolution basée sur B, C, D, H, L, O (meilleurs de Gen3)

Gagnants Gen3:
- B_H4_ref:           bright=1.2, sat=2.8, contrast=2.0, hue1=[0,6], hue2=[170,180], sat_min=80, val_min=60
- C_E2_sat_min_plus:  bright=1.0, sat=2.0, contrast=1.5, hue1=[0,8], hue2=[165,180], sat_min=70, val_min=40
- D_E2_hue_like_H4:   bright=1.0, sat=2.0, contrast=1.5, hue1=[0,6], hue2=[170,180], sat_min=60, val_min=40
- H_H4_val_min_moins: bright=1.2, sat=2.8, contrast=2.0, hue1=[0,6], hue2=[170,180], sat_min=80, val_min=50
- L_mid_enhance_H4:   bright=1.1, sat=2.4, contrast=1.75, hue1=[0,6], hue2=[170,180], sat_min=80, val_min=60
- O_ultra_sat_min:    bright=1.1, sat=2.4, contrast=1.75, hue1=[0,7], hue2=[167,180], sat_min=90, val_min=50

Patterns identifiés:
- hue1=[0,6] et hue2=[170,180] très populaires (hue strict H4)
- sat_min entre 60-90 (tendance vers le strict)
- val_min entre 40-60
- enhance moyen (bright=1.1, sat=2.4, contrast=1.75) ou H4 (1.2, 2.8, 2.0)
"""

CONFIGS = [
    # =========================================
    # RÉFÉRENCES - Les 6 gagnants
    # =========================================
    {
        "name": "A_B_ref",
        "description": "B_H4_ref original",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "B_C_ref",
        "description": "C_E2_sat_min_plus original",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 8,
        "hue_low2": 165, "hue_high2": 180,
        "sat_min": 70,
        "val_min": 40,
    },
    {
        "name": "C_D_ref",
        "description": "D_E2_hue_like_H4 original",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 60,
        "val_min": 40,
    },
    {
        "name": "D_H_ref",
        "description": "H_H4_val_min_moins original",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 50,
    },
    {
        "name": "E_L_ref",
        "description": "L_mid_enhance_H4 original",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "F_O_ref",
        "description": "O_ultra_sat_min original",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 7,
        "hue_low2": 167, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 50,
    },
    
    # =========================================
    # HYBRIDES des gagnants - Combinaisons clés
    # =========================================
    {
        "name": "G_L_sat95",
        "description": "L avec sat_min encore plus strict",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 95,  # ultra strict
        "val_min": 60,
    },
    {
        "name": "H_O_sat85",
        "description": "O avec sat_min légèrement réduit",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 7,
        "hue_low2": 167, "hue_high2": 180,
        "sat_min": 85,
        "val_min": 50,
    },
    {
        "name": "I_D_sat70",
        "description": "D avec sat_min comme C",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 70,  # comme C
        "val_min": 40,
    },
    {
        "name": "J_D_sat80",
        "description": "D avec sat_min plus strict",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,  # comme B/H
        "val_min": 40,
    },
    {
        "name": "K_C_hue_strict",
        "description": "C avec hue strict comme H4",
        "brightness": 1.0,
        "saturation": 2.0,
        "contrast": 1.5,
        "hue_low1": 0, "hue_high1": 6,   # H4
        "hue_low2": 170, "hue_high2": 180,  # H4
        "sat_min": 70,
        "val_min": 40,
    },
    {
        "name": "L_B_val50",
        "description": "B avec val_min réduit comme H",
        "brightness": 1.2,
        "saturation": 2.8,
        "contrast": 2.0,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 50,  # comme H
    },
    
    # =========================================
    # Fine-tuning autour de L et O (les plus prometteurs)
    # =========================================
    {
        "name": "M_L_sat85_val55",
        "description": "L avec sat_min=85, val_min=55",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 85,
        "val_min": 55,
    },
    {
        "name": "N_L_hue5",
        "description": "L avec hue1 encore plus strict",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,   # -1
        "hue_low2": 172, "hue_high2": 180,  # +2
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "O_O_hue5",
        "description": "O avec hue encore plus strict",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 5,
        "hue_low2": 172, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 50,
    },
    {
        "name": "P_O_val45",
        "description": "O avec val_min réduit",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 7,
        "hue_low2": 167, "hue_high2": 180,
        "sat_min": 90,
        "val_min": 45,  # -5
    },
    
    # =========================================
    # Variations d'enhance sur les meilleurs filtres
    # =========================================
    {
        "name": "Q_L_bright115",
        "description": "L avec brightness légèrement plus haut",
        "brightness": 1.15,
        "saturation": 2.4,
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "R_L_sat26",
        "description": "L avec saturation légèrement plus haute",
        "brightness": 1.1,
        "saturation": 2.6,  # +0.2
        "contrast": 1.75,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "S_L_contrast185",
        "description": "L avec contraste légèrement plus haut",
        "brightness": 1.1,
        "saturation": 2.4,
        "contrast": 1.85,  # +0.1
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 80,
        "val_min": 60,
    },
    {
        "name": "T_ultimate",
        "description": "Combinaison optimale de tous les patterns",
        "brightness": 1.1,
        "saturation": 2.5,
        "contrast": 1.8,
        "hue_low1": 0, "hue_high1": 6,
        "hue_low2": 170, "hue_high2": 180,
        "sat_min": 85,
        "val_min": 55,
    },
]
