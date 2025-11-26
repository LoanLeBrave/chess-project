import cv2
import numpy as np

def detect_wood_frame_boundary(image_path, output_path="detected_boundary.png", line_thickness=80):
    """
    Détecte la démarcation entre le cadre en bois et l'intérieur de la scène.
    
    Args:
        image_path: Chemin de l'image d'entrée
        output_path: Chemin de l'image de sortie
        line_thickness: Épaisseur du trait noir (défaut: 80)
    """
    # === Charger l'image ===
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Impossible de charger l'image: {image_path}")
        return None
    
    height, width = img.shape[:2]
    output = img.copy()
    
    # === Approche 1: Détection par couleur (bois vs intérieur) ===
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Masque pour détecter les tons bois (marron/beige)
    # Ajustez ces valeurs selon votre image
    lower_wood = np.array([5, 20, 50])
    upper_wood = np.array([30, 255, 200])
    wood_mask = cv2.inRange(hsv, lower_wood, upper_wood)
    
    # Inverser pour avoir l'intérieur en blanc
    interior_mask = cv2.bitwise_not(wood_mask)
    
    # === Approche 2: Détection par gradient de couleur ===
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Appliquer un filtre bilatéral pour réduire le bruit tout en gardant les bords
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Détection de bords avec des seuils adaptés
    edges = cv2.Canny(bilateral, 20, 60)
    
    # Fermeture morphologique pour combler les trous
    kernel = np.ones((5, 5), np.uint8)
    edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    # Dilatation pour renforcer les lignes
    edges_dilated = cv2.dilate(edges_closed, kernel, iterations=2)
    
    # === Combiner les deux approches ===
    # Combiner les bords détectés avec le masque de couleur
    combined = cv2.bitwise_or(edges_dilated, cv2.Canny(interior_mask, 100, 200))
    
    # === Trouver le plus grand contour rectangulaire ===
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    biggest_quad = None
    max_area = 0
    min_area = (height * width) * 0.05  # Au moins 5% de l'image
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        if area < min_area:
            continue
        
        peri = cv2.arcLength(cnt, True)
        # Approximation plus tolérante pour capturer le cadre légèrement déformé
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
        
        # Accepter 4 à 6 points (pour gérer les légères déformations)
        if 4 <= len(approx) <= 8:
            if area > max_area:
                max_area = area
                biggest_quad = approx
    
    # === Si pas de contour trouvé, méthode alternative ===
    if biggest_quad is None:
        print("⚠️  Méthode par contour échouée, essai avec détection de région...")
        
        # Trouver la plus grande région connexe dans le masque intérieur
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(interior_mask, connectivity=8)
        
        if num_labels > 1:
            # Ignorer le fond (label 0)
            largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            largest_mask = (labels == largest_label).astype(np.uint8) * 255
            
            # Trouver le contour de cette région
            contours, _ = cv2.findContours(largest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                biggest_quad = max(contours, key=cv2.contourArea)
    
    # === Dessiner le contour ===
    if biggest_quad is not None:
        cv2.drawContours(output, [biggest_quad], -1, (0, 0, 0), line_thickness)
        
        print("✅ Démarcation détectée avec succès!")
        print(f"   Surface: {cv2.contourArea(biggest_quad):.0f} pixels²")
        print(f"   Nombre de points: {len(biggest_quad)}")
    else:
        print("❌ Aucune démarcation détectée.")
        print("   Essayez d'ajuster les paramètres de couleur.")
    
    # === Sauvegardes pour debug ===
    cv2.imwrite(output_path, output)
    cv2.imwrite("debug_edges.png", edges_dilated)
    cv2.imwrite("debug_mask.png", interior_mask)
    
    print(f"\n💾 Images sauvegardées:")
    print(f"   - Résultat: {output_path}")
    print(f"   - Debug edges: debug_edges.png")
    print(f"   - Debug mask: debug_mask.png")
    
    return output


# === Utilisation ===
if __name__ == "__main__":
    detect_wood_frame_boundary("test/test7.jpg", "detected_boundary.png", line_thickness=80)