"""
Script de test pour trouver les meilleurs paramètres de traitement d'image.
Génère plusieurs variantes avec différents paramètres.

Usage:
    python test_params.py              # Utilise config_gen5 par défaut
    python test_params.py gen1         # Utilise config_gen1
    python test_params.py gen2         # Utilise config_gen2
    python test_params.py gen3         # Utilise config_gen3
    python test_params.py gen4         # Utilise config_gen4
    python test_params.py gen5         # Utilise config_gen5 (FINALE)
"""

from PIL import Image, ImageEnhance
import numpy as np
import cv2
import os
import glob
import sys

# ============================================================
# IMPORT DE LA CONFIGURATION
# ============================================================
def load_config(gen_name=None):
    """Charge la configuration selon la génération demandée"""
    if gen_name is None:
        # Par défaut, utilise la génération la plus récente
        gen_name = "gen5"
    
    if gen_name == "gen1":
        from config_gen1 import CONFIGS
        return CONFIGS, "Génération 1"
    elif gen_name == "gen2":
        from config_gen2 import CONFIGS
        return CONFIGS, "Génération 2 (basée sur E, F, J)"
    elif gen_name == "gen3":
        from config_gen3 import CONFIGS
        return CONFIGS, "Génération 3 (basée sur E2, H1, H4)"
    elif gen_name == "gen4":
        from config_gen4 import CONFIGS
        return CONFIGS, "Génération 4 (basée sur B, C, D, H, L, O)"
    elif gen_name == "gen5":
        from config_gen5 import CONFIGS
        return CONFIGS, "Génération 5 FINALE (basée sur E_L, F_O, K_C, M_L, O_O)"
    else:
        print(f"❌ Génération inconnue: {gen_name}")
        print("   Utilise 'gen1', 'gen2', 'gen3', 'gen4' ou 'gen5'")
        sys.exit(1)

# ============================================================
# SÉLECTION DE L'IMAGE
# ============================================================
def select_image():
    """Liste les images disponibles dans le même répertoire que ce script"""
    # Répertoire du script (detection_remastered/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"📁 Recherche dans: {script_dir}")
    
    extensions = ['jpg', 'jpeg', 'png', 'bmp', 'tiff']
    images = []
    
    # Lister uniquement les fichiers dans script_dir (pas récursif)
    for filename in os.listdir(script_dir):
        filepath = os.path.join(script_dir, filename)
        if os.path.isfile(filepath):
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if ext in extensions:
                images.append(filepath)
    
    if not images:
        print("❌ Aucune image trouvée dans le répertoire.")
        return None
    
    images = sorted(images)
    
    print("\n📂 Images disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("\n🔢 Entrez le numéro de l'image (ou 'q' pour quitter): ").strip()
            if choice.lower() == 'q':
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(images):
                return images[choice_num - 1]
            else:
                print(f"⚠️  Veuillez entrer un numéro entre 1 et {len(images)}")
        except ValueError:
            print("⚠️  Veuillez entrer un numéro valide")

# ============================================================
# FONCTIONS DE TRAITEMENT
# ============================================================
def process_image(img, config):
    """Applique le traitement avec les paramètres donnés"""
    
    # Luminosité
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(config["brightness"])
    
    # Saturation
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(config["saturation"])
    
    # Contraste
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(config["contrast"])
    
    # Extraction du rouge
    img_np = np.array(img)
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    
    # Masque rouge
    mask1 = cv2.inRange(hsv, 
                        (config["hue_low1"], config["sat_min"], config["val_min"]), 
                        (config["hue_high1"], 255, 255))
    mask2 = cv2.inRange(hsv, 
                        (config["hue_low2"], config["sat_min"], config["val_min"]), 
                        (config["hue_high2"], 255, 255))
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Rouge extrait
    red_only = cv2.bitwise_and(img_np, img_np, mask=mask)
    
    # Masque inversé
    mask_inverted = cv2.bitwise_not(mask)
    
    return red_only, mask_inverted

def main():
    # Déterminer la génération à utiliser
    gen_name = sys.argv[1] if len(sys.argv) > 1 else None
    CONFIGS, gen_desc = load_config(gen_name)
    
    print("=" * 60)
    print(f"🧪 TEST DE PARAMÈTRES DE TRAITEMENT - {gen_desc}")
    print("=" * 60)
    
    # Sélection de l'image
    image_path = select_image()
    if not image_path:
        return
    
    print(f"\n✅ Image: {os.path.basename(image_path)}")
    
    # Créer le dossier de sortie
    folder_name = f"test_params_{gen_name or 'gen2'}"
    output_dir = os.path.join(os.path.dirname(image_path), folder_name)
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Sortie: {output_dir}")
    
    # Charger l'image
    original_img = Image.open(image_path)
    
    # Redimensionner si trop grande
    MAX_DIM = 1200
    w, h = original_img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        original_img = original_img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        print(f"📐 Redimensionnée: {w}x{h} → {original_img.size}")
    
    # Tester chaque configuration
    print(f"\n🔄 Test de {len(CONFIGS)} configurations...\n")
    
    for config in CONFIGS:
        name = config["name"]
        print(f"  Processing {name}...")
        
        red_only, mask_inverted = process_image(original_img.copy(), config)
        
        # Sauvegarder
        Image.fromarray(red_only).save(os.path.join(output_dir, f"{name}_rouge_extrait.png"))
        Image.fromarray(mask_inverted).save(os.path.join(output_dir, f"{name}_masque_inverse.png"))
    
    print(f"\n✅ Terminé ! {len(CONFIGS) * 2} images générées dans {output_dir}")
    print("\n📋 Configurations testées:")
    print("-" * 60)
    for c in CONFIGS:
        desc = c.get('description', '')
        print(f"  {c['name']}: bright={c['brightness']}, sat={c['saturation']}, "
              f"contrast={c['contrast']}, sat_min={c['sat_min']}, val_min={c['val_min']}")
        if desc:
            print(f"      → {desc}")
    print("-" * 60)
    print("\n🔍 Regarde les images et dis-moi laquelle est la meilleure !")

if __name__ == "__main__":
    main()
