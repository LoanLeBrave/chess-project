"""
Détection de marqueurs ArUco pour pièces d'échecs
Ultra-rapide et natif OpenCV (pas de dépendance externe)t
"""



import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import glob
import time

# ============================================================
# CONFIGURATION
# ============================================================
MAX_DIMENSION = 1500

# Dictionnaire ArUco (doit correspondre à celui utilisé pour la génération)
ARUCO_DICT = cv2.aruco.DICT_4X4_50

# Mapping ID ArUco -> Pièce
PIECES = {
    # Pièces blanches (IDs 0-15)
    0: {'code': 'WK', 'nom': 'Roi', 'couleur': 'Blanc', 'symbole': '♔'},
    1: {'code': 'WQ', 'nom': 'Dame', 'couleur': 'Blanc', 'symbole': '♕'},
    2: {'code': 'WR1', 'nom': 'Tour 1', 'couleur': 'Blanc', 'symbole': '♖'},
    3: {'code': 'WR2', 'nom': 'Tour 2', 'couleur': 'Blanc', 'symbole': '♖'},
    4: {'code': 'WB1', 'nom': 'Fou 1', 'couleur': 'Blanc', 'symbole': '♗'},
    5: {'code': 'WB2', 'nom': 'Fou 2', 'couleur': 'Blanc', 'symbole': '♗'},
    6: {'code': 'WN1', 'nom': 'Cavalier 1', 'couleur': 'Blanc', 'symbole': '♘'},
    7: {'code': 'WN2', 'nom': 'Cavalier 2', 'couleur': 'Blanc', 'symbole': '♘'},
    8: {'code': 'WP1', 'nom': 'Pion 1', 'couleur': 'Blanc', 'symbole': '♙'},
    9: {'code': 'WP2', 'nom': 'Pion 2', 'couleur': 'Blanc', 'symbole': '♙'},
    10: {'code': 'WP3', 'nom': 'Pion 3', 'couleur': 'Blanc', 'symbole': '♙'},
    11: {'code': 'WP4', 'nom': 'Pion 4', 'couleur': 'Blanc', 'symbole': '♙'},
    12: {'code': 'WP5', 'nom': 'Pion 5', 'couleur': 'Blanc', 'symbole': '♙'},
    13: {'code': 'WP6', 'nom': 'Pion 6', 'couleur': 'Blanc', 'symbole': '♙'},
    14: {'code': 'WP7', 'nom': 'Pion 7', 'couleur': 'Blanc', 'symbole': '♙'},
    15: {'code': 'WP8', 'nom': 'Pion 8', 'couleur': 'Blanc', 'symbole': '♙'},
    # Pièces noires (IDs 16-31)
    16: {'code': 'BK', 'nom': 'Roi', 'couleur': 'Noir', 'symbole': '♚'},
    17: {'code': 'BQ', 'nom': 'Dame', 'couleur': 'Noir', 'symbole': '♛'},
    18: {'code': 'BR1', 'nom': 'Tour 1', 'couleur': 'Noir', 'symbole': '♜'},
    19: {'code': 'BR2', 'nom': 'Tour 2', 'couleur': 'Noir', 'symbole': '♜'},
    20: {'code': 'BB1', 'nom': 'Fou 1', 'couleur': 'Noir', 'symbole': '♝'},
    21: {'code': 'BB2', 'nom': 'Fou 2', 'couleur': 'Noir', 'symbole': '♝'},
    22: {'code': 'BN1', 'nom': 'Cavalier 1', 'couleur': 'Noir', 'symbole': '♞'},
    23: {'code': 'BN2', 'nom': 'Cavalier 2', 'couleur': 'Noir', 'symbole': '♞'},
    24: {'code': 'BP1', 'nom': 'Pion 1', 'couleur': 'Noir', 'symbole': '♟'},
    25: {'code': 'BP2', 'nom': 'Pion 2', 'couleur': 'Noir', 'symbole': '♟'},
    26: {'code': 'BP3', 'nom': 'Pion 3', 'couleur': 'Noir', 'symbole': '♟'},
    27: {'code': 'BP4', 'nom': 'Pion 4', 'couleur': 'Noir', 'symbole': '♟'},
    28: {'code': 'BP5', 'nom': 'Pion 5', 'couleur': 'Noir', 'symbole': '♟'},
    29: {'code': 'BP6', 'nom': 'Pion 6', 'couleur': 'Noir', 'symbole': '♟'},
    30: {'code': 'BP7', 'nom': 'Pion 7', 'couleur': 'Noir', 'symbole': '♟'},
    31: {'code': 'BP8', 'nom': 'Pion 8', 'couleur': 'Noir', 'symbole': '♟'},
}

# ============================================================
# SÉLECTION DE L'IMAGE
# ============================================================
def select_image():
    """Liste les images disponibles et demande à l'utilisateur de choisir"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(script_dir, ext)))
    
    if not images:
        print(" Aucune image trouvée dans le répertoire.")
        return None
    
    images = sorted(images)
    
    print("\nImages disponibles:")
    print("-" * 40)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 40)
    
    while True:
        try:
            choice = input("\nEntrez le numéro de l'image (ou 'q' pour quitter): ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(images):
                return images[choice_num - 1]
            else:
                print(f" Veuillez entrer un numéro entre 1 et {len(images)}")
        except ValueError:
            print(" Veuillez entrer un numéro valide")

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================
def create_output_dir(base_path):
    """Crée le dossier de traitement s'il n'existe pas"""
    output_dir = os.path.join(os.path.dirname(base_path), "traitement_aruco")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_step(img, output_dir, step_name, base_name):
    """Sauvegarde une étape de traitement"""
    filename = f"{base_name}_{step_name}.png"
    filepath = os.path.join(output_dir, filename)
    
    if isinstance(img, np.ndarray):
        if len(img.shape) == 2:
            Image.fromarray(img).save(filepath)
        else:
            Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(filepath)
    else:
        img.save(filepath)
    
    print(f"   Sauvegardé: {filename}")
    return filepath

def get_piece_info(marker_id):
    """Retourne les informations d'une pièce à partir de son ID ArUco"""
    if marker_id in PIECES:
        return PIECES[marker_id]
    return {'code': f'?{marker_id}', 'nom': 'Inconnu', 'couleur': '?', 'symbole': '?'}

# ============================================================
# DÉTECTION ARUCO
# ============================================================
def detect_aruco_markers(img_np):
    """
    Détecte tous les marqueurs ArUco dans une image.
    Retourne une liste de détections avec ID, position, etc.
    """
    detections = []
    
    # Conversion en niveaux de gris
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    # Charger le dictionnaire ArUco
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    
    # Paramètres de détection (optimisés)
    parameters = cv2.aruco.DetectorParameters()
    
    # Créer le détecteur
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Détecter les marqueurs
    corners, ids, rejected = detector.detectMarkers(gray)
    
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            # Coins du marqueur (4 points)
            marker_corners = corners[i][0]
            
            # Convertir en liste
            position = [[int(c[0]), int(c[1])] for c in marker_corners]
            
            # Centre du marqueur
            center_x = sum(c[0] for c in marker_corners) / 4
            center_y = sum(c[1] for c in marker_corners) / 4
            
            # Informations de la pièce
            piece_info = get_piece_info(marker_id)
            
            detections.append({
                'id': int(marker_id),
                'code': piece_info['code'],
                'piece': piece_info,
                'position': position,
                'center': (center_x, center_y),
                'corners': marker_corners
            })
    
    return detections, rejected

# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================
def main():
    print("=" * 60)
    print(" DÉTECTION ARUCO - PIÈCES D'ÉCHECS")
    print("   (Ultra-rapide, natif OpenCV)")
    print("=" * 60)
    
    # Sélection de l'image
    print("\n Sélectionnez une image...")
    image_path = select_image()
    
    if not image_path:
        print(" Aucune image sélectionnée. Arrêt du programme.")
        return
    
    print(f" Image sélectionnée: {os.path.basename(image_path)}")
    
    # Créer le dossier de sortie
    output_dir = create_output_dir(image_path)
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    print(f" Dossier de sortie: {output_dir}")
    
    # Charger l'image
    original_img = Image.open(image_path)
    
    # Redimensionnement si nécessaire
    width, height = original_img.size
    if max(width, height) > MAX_DIMENSION:
        scale_factor = MAX_DIMENSION / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        original_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(f" Image redimensionnée: {width}x{height} → {new_width}x{new_height}")
    else:
        print(f"Image conservée: {width}x{height}")
    
    # Sauvegarder l'original
    save_step(original_img, output_dir, "00_original", base_name)
    
    # Conversion en numpy array (RGB)
    img_np = np.array(original_img)
    
    # Détection des marqueurs ArUco
    print("\n Détection des marqueurs ArUco...")
    start_time = time.time()
    
    detections, rejected = detect_aruco_markers(img_np)
    
    detection_time = time.time() - start_time
    print(f"  Temps de détection: {detection_time*1000:.1f} ms")  # En millisecondes!
    print(f"   Marqueurs détectés: {len(detections)}")
    print(f"   Candidats rejetés: {len(rejected)}")
    
    # Charger la font
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        font_small = ImageFont.load_default()
        font_large = ImageFont.load_default()
    
    # Dessiner les annotations
    img_annotated = original_img.copy()
    draw = ImageDraw.Draw(img_annotated)
    
    for det in detections:
        position = det['position']
        marker_id = det['id']
        piece = det['piece']
        center = det['center']
        
        # Couleur selon la pièce
        if marker_id < 16:  # Blancs
            color = (0, 180, 0)  # Vert
        else:  # Noirs
            color = (0, 100, 255)  # Bleu
        
        # Dessiner le contour du marqueur
        points = [(int(p[0]), int(p[1])) for p in position]
        draw.polygon(points, outline=color, width=3)
        
        # Dessiner les coins (pour voir l'orientation)
        for j, pt in enumerate(points):
            radius = 6 if j == 0 else 4  # Premier coin plus gros
            draw.ellipse([pt[0]-radius, pt[1]-radius, pt[0]+radius, pt[1]+radius], 
                        fill=color if j == 0 else 'white', outline=color)
        
        # Dessiner le centre
        cx, cy = int(center[0]), int(center[1])
        draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill='red')
        
        # Label
        label = f"{piece['symbole']} {piece['code']} (ID:{marker_id})"
        text_bbox = draw.textbbox((0, 0), label, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position du texte
        top_y = min(p[1] for p in position)
        text_x = int(center[0] - text_width / 2)
        text_y = int(top_y) - text_height - 10
        
        # Fond blanc pour le texte
        draw.rectangle(
            [text_x - 3, text_y - 2, text_x + text_width + 3, text_y + text_height + 2],
            fill='white', outline=color
        )
        draw.text((text_x, text_y), label, fill=color, font=font_large)
    
    # Sauvegarder le résultat
    save_step(img_annotated, output_dir, "99_resultat_final", base_name)
    
    # Afficher les résultats
    print("\n" + "=" * 60)
    print("📋 PIÈCES DÉTECTÉES")
    print("=" * 60)
    
    # Trier par ID
    whites = [d for d in detections if d['id'] < 16]
    blacks = [d for d in detections if d['id'] >= 16]
    
    if whites:
        print("\n PIÈCES BLANCHES:")
        for det in sorted(whites, key=lambda x: x['id']):
            piece = det['piece']
            center = det['center']
            print(f"   ID {det['id']:2} = {piece['symbole']} {piece['code']:4} @ ({center[0]:.0f}, {center[1]:.0f})")
    
    if blacks:
        print("\n PIÈCES NOIRES:")
        for det in sorted(blacks, key=lambda x: x['id']):
            piece = det['piece']
            center = det['center']
            print(f"   ID {det['id']:2} = {piece['symbole']} {piece['code']:4} @ ({center[0]:.0f}, {center[1]:.0f})")
    
    # Statistiques
    print("\n" + "=" * 60)
    print(" STATISTIQUES")
    print("=" * 60)
    print(f"  Total détecté: {len(detections)}/32 marqueurs")
    print(f"  Pièces blanches: {len(whites)}/16")
    print(f"  Pièces noires: {len(blacks)}/16")
    print(f"  Temps de détection: {detection_time*1000:.1f} ms")
    
    # Pièces manquantes
    all_ids = set(PIECES.keys())
    detected_ids = set(d['id'] for d in detections)
    missing = all_ids - detected_ids
    
    if missing:
        print(f"\n  Pièces manquantes ({len(missing)}):")
        for marker_id in sorted(missing):
            piece = PIECES[marker_id]
            print(f"     ID {marker_id:2} - {piece['symbole']} {piece['code']} ({piece['couleur']} {piece['nom']})")
    else:
        print("\nToutes les 32 pièces ont été détectées!")
    
    print(f"\n Résultats sauvegardés dans: {output_dir}")


if __name__ == "__main__":
    main()