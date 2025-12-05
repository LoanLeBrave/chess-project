#!/usr/bin/env python3
"""
Interface graphique moderne pour calibrer les offsets des coins du plateau.

Utilise Tkinter pour une interface propre avec:
- Canvas pour l'image avec drag & drop des coins
- Panneau latéral avec les valeurs et bouton "Copier"
- Prévisualisation de la grille 8x8

Usage:
    python calibrate_offsets_gui.py                # Mode interactif
    python calibrate_offsets_gui.py [chemin_image] # Avec une image existante
    python calibrate_offsets_gui.py --photo        # Prendre une photo d'abord
"""

import cv2
import numpy as np
import os
import sys
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMAGES_DIR = os.path.join(SCRIPT_DIR, "..", "analyse", "images")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

EXTRACTED_BOARD_SIZE = 800
ARUCO_DICT = cv2.aruco.DICT_4X4_50

CALIBRATION_IDS = {
    32: 'CAL_TL',
    33: 'CAL_TR',
    34: 'CAL_BL',
    35: 'CAL_BR',
}

# Couleurs (RGB pour Tkinter)
COLORS = {
    'bg': '#1e1e1e',
    'panel_bg': '#252526',
    'text': '#ffffff',
    'text_dim': '#888888',
    'accent': '#007acc',
    'success': '#4ec9b0',
    'warning': '#dcdcaa',
    'error': '#f44747',
    'aruco': '#00ff00',
    'corner': '#ff00ff',
    'corner_hover': '#ffff00',
    'corner_drag': '#00ffff',
    'corner_estimated': '#ff8888',
    'outline': '#ffa500',
    'offset_line': '#ffff00',
    'grid': '#00ff00',
}

# ============================================================
# CONFIGURATION CAMÉRA
# ============================================================
def _check_rpicam_available():
    return shutil.which('rpicam-still') is not None or shutil.which('libcamera-still') is not None

def _check_picamera2_available():
    try:
        from picamera2 import Picamera2
        return True
    except ImportError:
        return False

if _check_rpicam_available():
    CAMERA_MODE = 'rpicam'
elif _check_picamera2_available():
    CAMERA_MODE = 'picamera2'
else:
    CAMERA_MODE = 'opencv'


# ============================================================
# PRISE DE PHOTO
# ============================================================
def take_photo(filename=None):
    """Prend une photo"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"calibration_{timestamp}.jpg"
    
    filepath = os.path.join(IMAGES_DIR, filename)
    
    if CAMERA_MODE == 'rpicam':
        cmd = 'rpicam-still' if shutil.which('rpicam-still') else 'libcamera-still'
        args = [cmd, '-n', '-o', filepath, '--timeout', '2000']
        subprocess.run(args, capture_output=True, timeout=30)
    elif CAMERA_MODE == 'picamera2':
        from picamera2 import Picamera2
        import time
        picam2 = Picamera2()
        picam2.configure(picam2.create_still_configuration())
        picam2.start()
        time.sleep(2)
        picam2.capture_file(filepath)
        picam2.stop()
        picam2.close()
    else:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filepath, frame)
        cap.release()
    
    return filepath if os.path.exists(filepath) else None


# ============================================================
# DÉTECTION ARUCO
# ============================================================
def detect_calibration_markers(img_np):
    """Détecte les marqueurs ArUco de calibration"""
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY) if len(img_np.shape) == 3 else img_np
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = cv2.aruco.DetectorParameters()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_CONTOUR
    
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, _ = detector.detectMarkers(gray)
    
    calibration_markers = {}
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id in CALIBRATION_IDS:
                marker_corners = corners[i][0]
                center_x = sum(c[0] for c in marker_corners) / 4
                center_y = sum(c[1] for c in marker_corners) / 4
                calibration_markers[marker_id] = {
                    'center': (center_x, center_y),
                    'corners': marker_corners,
                    'code': CALIBRATION_IDS[marker_id]
                }
    
    return calibration_markers


# ============================================================
# APPLICATION PRINCIPALE
# ============================================================
class CalibrationApp:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("🎯 Calibration des Offsets - Chess Board")
        self.root.configure(bg=COLORS['bg'])
        
        # Charger l'image
        self.image_path = image_path
        self.img_original = cv2.imread(image_path)
        if self.img_original is None:
            raise ValueError(f"Impossible de charger: {image_path}")
        
        self.img_h, self.img_w = self.img_original.shape[:2]
        
        # Calculer l'échelle d'affichage
        max_canvas_w, max_canvas_h = 900, 700
        self.scale = min(max_canvas_w / self.img_w, max_canvas_h / self.img_h, 1.0)
        self.canvas_w = int(self.img_w * self.scale)
        self.canvas_h = int(self.img_h * self.scale)
        
        # Détecter les ArUcos
        self.calibration_markers = detect_calibration_markers(self.img_original)
        
        # Initialiser les offsets
        self.offsets = {
            "CAL_TL": {"offset_x": tk.IntVar(value=0), "offset_y": tk.IntVar(value=0)},
            "CAL_TR": {"offset_x": tk.IntVar(value=0), "offset_y": tk.IntVar(value=0)},
            "CAL_BL": {"offset_x": tk.IntVar(value=0), "offset_y": tk.IntVar(value=0)},
            "CAL_BR": {"offset_x": tk.IntVar(value=0), "offset_y": tk.IntVar(value=0)},
        }
        
        # État du drag
        self.dragging = None
        self.hover = None
        self.corner_items = {}
        
        # Coins du plateau
        self.board_corners = {}
        self.estimated_codes = []
        
        # Construire l'interface
        self.build_ui()
        
        # Calculer les coins initiaux
        self.update_board_corners()
        self.draw_canvas()
    
    def build_ui(self):
        """Construit l'interface utilisateur"""
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=COLORS['bg'])
        style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'])
        style.configure('TButton', padding=6)
        style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'), foreground=COLORS['accent'])
        style.configure('SubHeader.TLabel', font=('Segoe UI', 11, 'bold'), foreground=COLORS['warning'])
        style.configure('Code.TLabel', font=('Consolas', 10), foreground=COLORS['success'])
        style.configure('Status.TLabel', font=('Segoe UI', 10))
        
        # === Colonne gauche: Canvas ===
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Titre
        ttk.Label(left_frame, text="📷 Image avec Coins Ajustables", style='Header.TLabel').pack(anchor='w', pady=(0, 5))
        
        # Canvas pour l'image
        self.canvas = tk.Canvas(left_frame, width=self.canvas_w, height=self.canvas_h, 
                                bg='black', highlightthickness=2, highlightbackground=COLORS['accent'])
        self.canvas.pack(pady=5)
        
        # Bindings souris
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        
        # Instructions
        instructions = ttk.Label(left_frame, text="🖱️ Glissez-déposez les coins magenta pour ajuster les offsets", 
                                 style='Status.TLabel', foreground=COLORS['text_dim'])
        instructions.pack(anchor='w', pady=5)
        
        # Boutons d'action
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="🔄 Reset Offsets", command=self.reset_offsets).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 Voir Grille 8x8", command=self.show_grid_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Sauvegarder Image", command=self.save_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Ouvrir Image", command=self.open_image).pack(side=tk.LEFT, padx=5)
        
        # === Colonne droite: Panneau de contrôle ===
        right_frame = ttk.Frame(main_frame, width=380)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        right_frame.pack_propagate(False)
        
        # Statut ArUcos
        ttk.Label(right_frame, text="🎯 Statut des ArUcos", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        self.aruco_status_frame = ttk.Frame(right_frame)
        self.aruco_status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.aruco_labels = {}
        for marker_id in [32, 33, 34, 35]:
            code = CALIBRATION_IDS[marker_id]
            frame = ttk.Frame(self.aruco_status_frame)
            frame.pack(fill=tk.X, pady=2)
            
            detected = marker_id in self.calibration_markers
            status_text = "✅" if detected else "❌"
            status_color = COLORS['success'] if detected else COLORS['error']
            
            lbl = ttk.Label(frame, text=f"{status_text} ArUco {marker_id} ({code})", 
                           foreground=status_color, font=('Segoe UI', 10))
            lbl.pack(side=tk.LEFT)
            self.aruco_labels[marker_id] = lbl
        
        # Séparateur
        ttk.Separator(right_frame, orient='horizontal').pack(fill=tk.X, pady=15)
        
        # Valeurs des offsets
        ttk.Label(right_frame, text="📐 Valeurs des Offsets", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        self.offset_entries = {}
        for code in ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']:
            frame = ttk.Frame(right_frame)
            frame.pack(fill=tk.X, pady=5)
            
            # Label du coin
            short = code.replace('CAL_', '')
            ttk.Label(frame, text=f"{short}:", font=('Segoe UI', 10, 'bold'), width=5).pack(side=tk.LEFT)
            
            # X
            ttk.Label(frame, text="X:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(10, 2))
            entry_x = ttk.Spinbox(frame, from_=-500, to=500, width=6, 
                                  textvariable=self.offsets[code]['offset_x'],
                                  command=lambda c=code: self.on_spinbox_change(c))
            entry_x.pack(side=tk.LEFT)
            entry_x.bind('<Return>', lambda e, c=code: self.on_spinbox_change(c))
            entry_x.bind('<FocusOut>', lambda e, c=code: self.on_spinbox_change(c))
            
            # Y
            ttk.Label(frame, text="Y:", font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(15, 2))
            entry_y = ttk.Spinbox(frame, from_=-500, to=500, width=6,
                                  textvariable=self.offsets[code]['offset_y'],
                                  command=lambda c=code: self.on_spinbox_change(c))
            entry_y.pack(side=tk.LEFT)
            entry_y.bind('<Return>', lambda e, c=code: self.on_spinbox_change(c))
            entry_y.bind('<FocusOut>', lambda e, c=code: self.on_spinbox_change(c))
            
            self.offset_entries[code] = {'x': entry_x, 'y': entry_y}
        
        # Séparateur
        ttk.Separator(right_frame, orient='horizontal').pack(fill=tk.X, pady=15)
        
        # Code à copier
        ttk.Label(right_frame, text="📋 Code Python à Copier", style='Header.TLabel').pack(anchor='w', pady=(0, 10))
        
        # Zone de texte pour le code
        code_frame = ttk.Frame(right_frame)
        code_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.code_text = tk.Text(code_frame, height=12, width=45, font=('Consolas', 9),
                                 bg='#1e1e1e', fg=COLORS['success'], insertbackground='white',
                                 relief='flat', padx=10, pady=10)
        self.code_text.pack(fill=tk.BOTH, expand=True)
        
        # Bouton Copier
        copy_btn = ttk.Button(right_frame, text="📋 Copier le Code", command=self.copy_code)
        copy_btn.pack(fill=tk.X, pady=(0, 10))
        
        # Label de confirmation
        self.copy_label = ttk.Label(right_frame, text="", foreground=COLORS['success'])
        self.copy_label.pack()
        
        # Mettre à jour le code initial
        self.update_code_text()
    
    def on_spinbox_change(self, code):
        """Appelé quand une spinbox change"""
        self.update_board_corners()
        self.draw_canvas()
        self.update_code_text()
    
    def update_board_corners(self):
        """Met à jour les coins du plateau"""
        self.board_corners = {}
        for marker_id, marker_data in self.calibration_markers.items():
            code = marker_data['code']
            center = marker_data['center']
            self.board_corners[code] = (
                center[0] + self.offsets[code]['offset_x'].get(),
                center[1] + self.offsets[code]['offset_y'].get()
            )
        
        self.estimate_missing_corners()
    
    def estimate_missing_corners(self):
        """Estime les coins manquants"""
        codes = ['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']
        detected = list(self.board_corners.keys())
        missing = [c for c in codes if c not in detected]
        
        self.estimated_codes = []
        
        if len(missing) == 1:
            m = missing[0]
            if m == 'CAL_TL' and all(c in detected for c in ['CAL_TR', 'CAL_BL', 'CAL_BR']):
                tr, bl, br = self.board_corners['CAL_TR'], self.board_corners['CAL_BL'], self.board_corners['CAL_BR']
                self.board_corners['CAL_TL'] = (tr[0] + bl[0] - br[0], tr[1] + bl[1] - br[1])
                self.estimated_codes.append('CAL_TL')
            elif m == 'CAL_TR' and all(c in detected for c in ['CAL_TL', 'CAL_BL', 'CAL_BR']):
                tl, bl, br = self.board_corners['CAL_TL'], self.board_corners['CAL_BL'], self.board_corners['CAL_BR']
                self.board_corners['CAL_TR'] = (tl[0] + br[0] - bl[0], tl[1] + br[1] - bl[1])
                self.estimated_codes.append('CAL_TR')
            elif m == 'CAL_BL' and all(c in detected for c in ['CAL_TL', 'CAL_TR', 'CAL_BR']):
                tl, tr, br = self.board_corners['CAL_TL'], self.board_corners['CAL_TR'], self.board_corners['CAL_BR']
                self.board_corners['CAL_BL'] = (tl[0] + br[0] - tr[0], tl[1] + br[1] - tr[1])
                self.estimated_codes.append('CAL_BL')
            elif m == 'CAL_BR' and all(c in detected for c in ['CAL_TL', 'CAL_TR', 'CAL_BL']):
                tl, tr, bl = self.board_corners['CAL_TL'], self.board_corners['CAL_TR'], self.board_corners['CAL_BL']
                self.board_corners['CAL_BR'] = (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1])
                self.estimated_codes.append('CAL_BR')
    
    def draw_canvas(self):
        """Dessine l'image et les annotations sur le canvas"""
        # Redimensionner l'image
        img_rgb = cv2.cvtColor(self.img_original, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (self.canvas_w, self.canvas_h))
        
        # Convertir en ImageTk
        self.photo = ImageTk.PhotoImage(Image.fromarray(img_resized))
        
        # Effacer le canvas
        self.canvas.delete('all')
        
        # Afficher l'image
        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
        
        # Dessiner les ArUcos
        for marker_id, marker_data in self.calibration_markers.items():
            corners = marker_data['corners'] * self.scale
            pts = [(int(c[0]), int(c[1])) for c in corners]
            self.canvas.create_polygon(pts, outline=COLORS['aruco'], fill='', width=2)
            
            cx = int(marker_data['center'][0] * self.scale)
            cy = int(marker_data['center'][1] * self.scale)
            self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=COLORS['error'], outline='')
            self.canvas.create_text(cx, cy-20, text=f"ID:{marker_id}", fill=COLORS['text'], font=('Segoe UI', 9))
        
        # Dessiner les lignes d'offset
        for marker_id, marker_data in self.calibration_markers.items():
            code = marker_data['code']
            if code in self.board_corners:
                ax = int(marker_data['center'][0] * self.scale)
                ay = int(marker_data['center'][1] * self.scale)
                bx = int(self.board_corners[code][0] * self.scale)
                by = int(self.board_corners[code][1] * self.scale)
                self.canvas.create_line(ax, ay, bx, by, fill=COLORS['offset_line'], width=2, dash=(4, 4))
        
        # Dessiner le contour du plateau
        if len(self.board_corners) >= 2:
            adjacencies = [('CAL_TL', 'CAL_TR'), ('CAL_TR', 'CAL_BR'),
                          ('CAL_BR', 'CAL_BL'), ('CAL_BL', 'CAL_TL')]
            for c1, c2 in adjacencies:
                if c1 in self.board_corners and c2 in self.board_corners:
                    x1 = int(self.board_corners[c1][0] * self.scale)
                    y1 = int(self.board_corners[c1][1] * self.scale)
                    x2 = int(self.board_corners[c2][0] * self.scale)
                    y2 = int(self.board_corners[c2][1] * self.scale)
                    self.canvas.create_line(x1, y1, x2, y2, fill=COLORS['outline'], width=3)
        
        # Dessiner les coins du plateau (draggables)
        self.corner_items = {}
        for code, corner in self.board_corners.items():
            cx = int(corner[0] * self.scale)
            cy = int(corner[1] * self.scale)
            
            # Déterminer la couleur
            if code == self.dragging:
                color = COLORS['corner_drag']
                size = 12
            elif code == self.hover:
                color = COLORS['corner_hover']
                size = 10
            elif code in self.estimated_codes:
                color = COLORS['corner_estimated']
                size = 8
            else:
                color = COLORS['corner']
                size = 10
            
            # Dessiner la croix
            self.canvas.create_line(cx-size, cy, cx+size, cy, fill=color, width=3)
            self.canvas.create_line(cx, cy-size, cx, cy+size, fill=color, width=3)
            self.canvas.create_oval(cx-size, cy-size, cx+size, cy+size, outline=color, width=2)
            
            # Label
            short = code.replace('CAL_', '')
            suffix = " (est.)" if code in self.estimated_codes else ""
            self.canvas.create_text(cx+15, cy-15, text=f"{short}{suffix}", fill=color, 
                                   font=('Segoe UI', 9, 'bold'), anchor='w')
            
            # Stocker la zone cliquable
            self.corner_items[code] = (cx, cy, size + 5)
    
    def get_corner_at_pos(self, x, y):
        """Retourne le coin à la position donnée"""
        for code, (cx, cy, radius) in self.corner_items.items():
            if code not in self.estimated_codes:
                if (x - cx)**2 + (y - cy)**2 < radius**2:
                    return code
        return None
    
    def on_mouse_move(self, event):
        """Gère le mouvement de la souris"""
        if not self.dragging:
            new_hover = self.get_corner_at_pos(event.x, event.y)
            if new_hover != self.hover:
                self.hover = new_hover
                self.draw_canvas()
                self.canvas.config(cursor='hand2' if self.hover else '')
    
    def on_mouse_down(self, event):
        """Gère le clic souris"""
        corner = self.get_corner_at_pos(event.x, event.y)
        if corner:
            self.dragging = corner
            self.canvas.config(cursor='fleur')
            self.draw_canvas()
    
    def on_mouse_drag(self, event):
        """Gère le drag"""
        if self.dragging:
            img_x = event.x / self.scale
            img_y = event.y / self.scale
            
            for marker_id, marker_data in self.calibration_markers.items():
                if marker_data['code'] == self.dragging:
                    center = marker_data['center']
                    self.offsets[self.dragging]['offset_x'].set(int(img_x - center[0]))
                    self.offsets[self.dragging]['offset_y'].set(int(img_y - center[1]))
                    break
            
            self.update_board_corners()
            self.draw_canvas()
            self.update_code_text()
    
    def on_mouse_up(self, event):
        """Gère le relâchement du clic"""
        self.dragging = None
        self.canvas.config(cursor='hand2' if self.hover else '')
        self.draw_canvas()
    
    def update_code_text(self):
        """Met à jour le texte du code Python"""
        self.code_text.delete('1.0', tk.END)
        
        lines = ["OFFSETS = {"]
        for i, code in enumerate(['CAL_TL', 'CAL_TR', 'CAL_BL', 'CAL_BR']):
            ox = self.offsets[code]['offset_x'].get()
            oy = self.offsets[code]['offset_y'].get()
            
            dir_x = "+x droite" if ox >= 0 else "-x gauche"
            dir_y = "+y bas" if oy >= 0 else "-y haut"
            
            comma = "," if i < 3 else ""
            lines.append(f'    "{code}": {{"offset_x": {ox}, "offset_y": {oy}}}{comma}  # {dir_x}, {dir_y}')
        
        lines.append("}")
        
        self.code_text.insert('1.0', '\n'.join(lines))
    
    def copy_code(self):
        """Copie le code dans le presse-papier"""
        code = self.code_text.get('1.0', tk.END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        
        self.copy_label.config(text="✅ Code copié dans le presse-papier!")
        self.root.after(2000, lambda: self.copy_label.config(text=""))
    
    def reset_offsets(self):
        """Remet tous les offsets à zéro"""
        for code in self.offsets:
            self.offsets[code]['offset_x'].set(0)
            self.offsets[code]['offset_y'].set(0)
        
        self.update_board_corners()
        self.draw_canvas()
        self.update_code_text()
    
    def extract_board(self):
        """Extrait le plateau"""
        if len(self.board_corners) < 4:
            return None
        
        src_points = np.array([
            [self.board_corners['CAL_TL'][0], self.board_corners['CAL_TL'][1]],
            [self.board_corners['CAL_TR'][0], self.board_corners['CAL_TR'][1]],
            [self.board_corners['CAL_BR'][0], self.board_corners['CAL_BR'][1]],
            [self.board_corners['CAL_BL'][0], self.board_corners['CAL_BL'][1]],
        ], dtype=np.float32)
        
        size = EXTRACTED_BOARD_SIZE
        dst_points = np.array([
            [0, 0], [size-1, 0], [size-1, size-1], [0, size-1]
        ], dtype=np.float32)
        
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        return cv2.warpPerspective(self.img_original, matrix, (size, size))
    
    def show_grid_preview(self):
        """Affiche une fenêtre avec la grille 8x8"""
        board_img = self.extract_board()
        if board_img is None:
            messagebox.showwarning("Attention", "Impossible d'extraire le plateau.\nIl faut 4 coins détectés.")
            return
        
        h, w = board_img.shape[:2]
        cell_w, cell_h = w / 8, h / 8
        
        for i in range(9):
            x = int(i * cell_w)
            cv2.line(board_img, (x, 0), (x, h), (0, 255, 0), 2)
            y = int(i * cell_h)
            cv2.line(board_img, (0, y), (w, y), (0, 255, 0), 2)
        
        for i, col in enumerate('abcdefgh'):
            x = int((i + 0.5) * cell_w) - 10
            cv2.putText(board_img, col, (x, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        for i, row in enumerate('87654321'):
            y = int((i + 0.5) * cell_h) + 10
            cv2.putText(board_img, row, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title("📊 Prévisualisation Grille 8x8")
        preview_window.configure(bg=COLORS['bg'])
        
        display_size = 600
        board_resized = cv2.resize(board_img, (display_size, display_size))
        board_rgb = cv2.cvtColor(board_resized, cv2.COLOR_BGR2RGB)
        
        photo = ImageTk.PhotoImage(Image.fromarray(board_rgb))
        label = ttk.Label(preview_window, image=photo)
        label.image = photo
        label.pack(padx=10, pady=10)
        
        ttk.Button(preview_window, text="Fermer", command=preview_window.destroy).pack(pady=10)
    
    def save_image(self):
        """Sauvegarde l'image du plateau avec grille"""
        board_img = self.extract_board()
        if board_img is None:
            messagebox.showwarning("Attention", "Impossible d'extraire le plateau.")
            return
        
        h, w = board_img.shape[:2]
        cell_w, cell_h = w / 8, h / 8
        
        for i in range(9):
            x = int(i * cell_w)
            cv2.line(board_img, (x, 0), (x, h), (0, 255, 0), 2)
            y = int(i * cell_h)
            cv2.line(board_img, (0, y), (w, y), (0, 255, 0), 2)
        
        for i, col in enumerate('abcdefgh'):
            x = int((i + 0.5) * cell_w) - 10
            cv2.putText(board_img, col, (x, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        for i, row in enumerate('87654321'):
            y = int((i + 0.5) * cell_h) + 10
            cv2.putText(board_img, row, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"calibrated_board_{timestamp}.jpg")
        cv2.imwrite(output_path, board_img)
        
        messagebox.showinfo("Sauvegardé", f"Image sauvegardée:\n{output_path}")
    
    def open_image(self):
        """Ouvre une nouvelle image"""
        filetypes = [("Images", "*.jpg *.jpeg *.png *.bmp"), ("Tous", "*.*")]
        path = filedialog.askopenfilename(
            title="Sélectionner une image",
            initialdir=IMAGES_DIR if os.path.exists(IMAGES_DIR) else SCRIPT_DIR,
            filetypes=filetypes
        )
        
        if path:
            self.image_path = path
            self.img_original = cv2.imread(path)
            if self.img_original is None:
                messagebox.showerror("Erreur", f"Impossible de charger:\n{path}")
                return
            
            self.img_h, self.img_w = self.img_original.shape[:2]
            
            max_canvas_w, max_canvas_h = 900, 700
            self.scale = min(max_canvas_w / self.img_w, max_canvas_h / self.img_h, 1.0)
            self.canvas_w = int(self.img_w * self.scale)
            self.canvas_h = int(self.img_h * self.scale)
            
            self.canvas.config(width=self.canvas_w, height=self.canvas_h)
            
            self.calibration_markers = detect_calibration_markers(self.img_original)
            
            for marker_id in [32, 33, 34, 35]:
                detected = marker_id in self.calibration_markers
                status_text = f"{'✅' if detected else '❌'} ArUco {marker_id} ({CALIBRATION_IDS[marker_id]})"
                color = COLORS['success'] if detected else COLORS['error']
                self.aruco_labels[marker_id].config(text=status_text, foreground=color)
            
            self.reset_offsets()


# ============================================================
# SÉLECTION D'IMAGE (mode console)
# ============================================================
def select_image_console():
    """Sélectionne une image en mode console"""
    import glob
    
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        images.extend(glob.glob(os.path.join(DEFAULT_IMAGES_DIR, ext)))
        images.extend(glob.glob(os.path.join(IMAGES_DIR, ext)))
        images.extend(glob.glob(os.path.join(SCRIPT_DIR, ext)))
    
    images = sorted(set(images))
    
    if not images:
        print("❌ Aucune image trouvée.")
        return None
    
    print("\n📷 Images disponibles:")
    print("-" * 50)
    for i, img_path in enumerate(images, 1):
        print(f"  {i}. {os.path.basename(img_path)}")
    print("-" * 50)
    
    while True:
        try:
            choice = input("\nNuméro de l'image (ou 'q' pour quitter): ").strip()
            if choice.lower() == 'q':
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(images):
                return images[choice_num - 1]
        except ValueError:
            pass
        print(f"⚠️  Entrez un numéro entre 1 et {len(images)}")


# ============================================================
# POINT D'ENTRÉE
# ============================================================
def main():
    print("="*60)
    print("🎯 CALIBRATION INTERACTIVE DES OFFSETS")
    print("   Interface graphique avec drag & drop")
    print(f"   Mode caméra: {CAMERA_MODE}")
    print("="*60)
    
    image_path = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--photo' or arg == '-p':
            print("\n📷 Prise de photo...")
            image_path = take_photo()
            if image_path:
                print(f"✅ Photo enregistrée: {image_path}")
        elif os.path.exists(arg):
            image_path = arg
        else:
            print(f"❌ Image non trouvée: {arg}")
    else:
        print("\nChoisissez une option:")
        print("  1. Prendre une photo")
        print("  2. Utiliser une image existante")
        print("  q. Quitter")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == '1':
            print("\n📷 Prise de photo...")
            image_path = take_photo()
            if image_path:
                print(f"✅ Photo enregistrée: {image_path}")
        elif choice == '2':
            image_path = select_image_console()
        elif choice.lower() == 'q':
            print("Au revoir!")
            return
    
    if not image_path or not os.path.exists(image_path):
        print("❌ Aucune image sélectionnée.")
        return
    
    root = tk.Tk()
    root.geometry("1400x800")
    
    try:
        app = CalibrationApp(root, image_path)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Erreur", str(e))
        raise


if __name__ == "__main__":
    main()
