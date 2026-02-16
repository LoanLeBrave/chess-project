#!/usr/bin/env python3
"""
Module de génération de l'état du jeu.
Génère les JSONs avec l'état complet du jeu dans différents formats.

Formats de sortie:
    - game_state.json: Coordonnées complètes (pixels, extended -12.5/+12.5, grid, chess)
    - board_state.json: État du plateau en notation échecs (A1, B2...) + cimetière
    - coordinates.json: Format simplifié pour le robot

Classes:
    - GameStateGenerator: Générateur d'état de jeu
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..config import PIECES, PIECE_IDS, GRID_COLUMNS, GRID_ROWS, CEMETERY_FILL_ORDER


class GameStateGenerator:
    """
    Générateur d'état de jeu d'échecs.
    Produit des JSONs dans différents formats.
    
    Formats:
        - Full: Toutes les coordonnées (pixels, extended, grid, chess) + zone
        - Board: État du plateau (case → pièce) + cimetière
        - Coordinates: Format robot (x, y en coordonnées étendues)
    """
    
    def __init__(self):
        """Initialise le générateur."""
        self.timestamp = None
    
    def generate_full_state(
        self,
        pieces: List[Dict],
        move_count: int = 0,
        turn: str = "white",
        include_metadata: bool = True
    ) -> Dict:
        """
        Génère l'état complet du jeu avec toutes les coordonnées.
        
        Args:
            pieces: Liste des pièces analysées
            move_count: Nombre de coups joués
            turn: Joueur dont c'est le tour ('white' ou 'black')
            include_metadata: Inclure les métadonnées
            
        Returns:
            Dict avec l'état complet du jeu
        """
        self.timestamp = datetime.now().isoformat()
        
        # Formater les pièces
        pieces_data = []
        for piece in pieces:
            piece_entry = {
                'id': piece['id'],
                'code': piece['code'],
                'color': piece['color'],
                'type': piece['type'],
                'initial': piece.get('initial', 'Unknown'),
                'zone': piece.get('zone', 'board'),
                'position': {
                    'grid': piece['position'].get('grid'),
                    'chess': piece['position'].get('chess'),
                    'board': {
                        'x': piece['position']['board']['x'],
                        'y': piece['position']['board']['y'],
                    },
                    'pixel': {
                        'x': round(piece['position']['pixel']['x'], 1),
                        'y': round(piece['position']['pixel']['y'], 1),
                    },
                },
            }
            pieces_data.append(piece_entry)
        
        # Trier par ID
        pieces_data.sort(key=lambda p: p['id'])
        
        # Calculer les statistiques
        white_pieces = [p for p in pieces if p['color'] == 'white']
        black_pieces = [p for p in pieces if p['color'] == 'black']
        board_pieces = [p for p in pieces if p.get('zone') == 'board']
        cemetery_pieces = [p for p in pieces if p.get('zone') == 'cemetery']
        
        # Pièces manquantes
        detected_ids = {p['id'] for p in pieces}
        missing_ids = PIECE_IDS - detected_ids
        missing_pieces = []
        for mid in sorted(missing_ids):
            piece_info = PIECES.get(mid, {})
            missing_pieces.append({
                'id': mid,
                'code': piece_info.get('code', f'?{mid}'),
                'color': piece_info.get('color', 'unknown'),
                'type': piece_info.get('type', 'Unknown'),
            })
        
        state = {
            'pieces': pieces_data,
        }
        
        if include_metadata:
            state['metadata'] = {
                'timestamp': self.timestamp,
                'turn': turn,
                'move_count': move_count,
                'total_detected': len(pieces),
                'white_count': len(white_pieces),
                'black_count': len(black_pieces),
                'on_board': len(board_pieces),
                'in_cemetery': len(cemetery_pieces),
                'missing_count': len(missing_ids),
            }
            
            if missing_pieces:
                state['missing_pieces'] = missing_pieces
        
        return state
    
    def generate_board_state(self, pieces: List[Dict]) -> Dict:
        """
        Génère l'état du plateau en notation échecs + cimetière.
        
        Format:
            board: {"a1": "WR", "a2": "WP", ...}  (plateau 8x8)
            cemetery: {"08": "BP", "07": "BN", ...}  (pièces capturées)
            
        Args:
            pieces: Liste des pièces analysées
            
        Returns:
            Dict avec l'état du plateau et du cimetière
        """
        type_codes = {
            'King': 'K', 'Queen': 'Q', 'Rook': 'R',
            'Bishop': 'B', 'Knight': 'N', 'Pawn': 'P',
        }
        
        def piece_code(piece):
            color_code = 'W' if piece['color'] == 'white' else 'B'
            return f"{color_code}{type_codes.get(piece['type'], '?')}"
        
        # Pièces sur le plateau (A1-H8)
        board_map = {}
        for piece in pieces:
            square = piece['position'].get('chess')
            if square and piece.get('zone') == 'board':
                board_map[square.lower()] = piece_code(piece)
        
        # Générer toutes les cases du plateau
        board = {}
        for row in ['8', '7', '6', '5', '4', '3', '2', '1']:
            for col in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']:
                square = f"{col}{row}"
                board[square] = board_map.get(square, None)
        
        # Pièces au cimetière
        cemetery = {}
        for piece in pieces:
            if piece.get('zone') == 'cemetery':
                grid_sq = piece['position'].get('grid')
                if grid_sq:
                    cemetery[grid_sq] = {
                        'code': piece_code(piece),
                        'id': piece['id'],
                        'full_code': piece['code'],
                    }
        
        return {
            'board': board,
            'cemetery': cemetery,
            'timestamp': datetime.now().isoformat(),
        }
    
    def generate_robot_coordinates(
        self,
        pieces: List[Dict],
        include_chess_notation: bool = True
    ) -> Dict:
        """
        Génère les coordonnées pour le robot.
        
        Utilise le repère étendu (-12.5/+12.5) qui couvre plateau et cimetière.
        Le plateau central reste dans [-10, +10].
        
        Args:
            pieces: Liste des pièces analysées
            include_chess_notation: Inclure aussi la notation échecs
            
        Returns:
            Dict avec les coordonnées robot
        """
        coordinates = []
        
        for piece in pieces:
            coord_entry = {
                'id': piece['id'],
                'color': piece['color'],
                'type': piece['type'],
                'zone': piece.get('zone', 'board'),
                'x': piece['position']['board']['x'],
                'y': piece['position']['board']['y'],
            }
            
            if include_chess_notation:
                coord_entry['grid'] = piece['position'].get('grid')
                coord_entry['chess'] = piece['position'].get('chess')
            
            coordinates.append(coord_entry)
        
        coordinates.sort(key=lambda c: c['id'])
        
        return {
            'coordinates': coordinates,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'count': len(coordinates),
                'coord_system': 'extended_-12.5_+12.5',
                'board_range': {'min': -10, 'max': 10},
                'extended_range': {'min': -12.5, 'max': 12.5},
            },
        }
    
    def generate_fen_like(self, pieces: List[Dict]) -> str:
        """
        Génère une représentation FEN-like de la position.
        (Pas un FEN complet car manque info sur roques, en passant, etc.)
        
        Args:
            pieces: Liste des pièces analysées
            
        Returns:
            String représentant la position
        """
        # Créer une grille 8x8
        grid = [[None for _ in range(8)] for _ in range(8)]
        
        # Mapping type → lettre FEN
        fen_pieces = {
            'King': 'k',
            'Queen': 'q',
            'Rook': 'r',
            'Bishop': 'b',
            'Knight': 'n',
            'Pawn': 'p',
        }
        
        # Placer les pièces (uniquement celles sur le plateau)
        for piece in pieces:
            if piece.get('zone') == 'cemetery':
                continue
            square = piece['position'].get('chess')
            if square:
                col_idx = ord(square[0]) - ord('a')
                row_idx = 8 - int(square[1])
                
                letter = fen_pieces.get(piece['type'], '?')
                if piece['color'] == 'white':
                    letter = letter.upper()
                
                if 0 <= col_idx < 8 and 0 <= row_idx < 8:
                    grid[row_idx][col_idx] = letter
        
        # Construire le FEN
        fen_rows = []
        for row in grid:
            fen_row = ""
            empty_count = 0
            for cell in row:
                if cell is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    fen_row += cell
            if empty_count > 0:
                fen_row += str(empty_count)
            fen_rows.append(fen_row)
        
        return '/'.join(fen_rows)
    
    def save_all(
        self,
        pieces: List[Dict],
        output_dir: str,
        prefix: str = "",
        move_count: int = 0,
        turn: str = "white"
    ) -> Dict[str, str]:
        """
        Sauvegarde tous les formats de fichiers JSON.
        
        Args:
            pieces: Liste des pièces analysées
            output_dir: Dossier de sortie
            prefix: Préfixe pour les noms de fichiers
            move_count: Nombre de coups joués
            turn: Joueur dont c'est le tour
            
        Returns:
            Dict avec les chemins des fichiers créés
        """
        os.makedirs(output_dir, exist_ok=True)
        
        files_created = {}
        
        # 1. État complet
        full_state = self.generate_full_state(pieces, move_count, turn)
        full_path = os.path.join(output_dir, f"{prefix}game_state.json" if prefix else "game_state.json")
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(full_state, f, indent=2, ensure_ascii=False)
        files_created['game_state'] = full_path
        
        # 2. État du plateau
        board_state = self.generate_board_state(pieces)
        board_path = os.path.join(output_dir, f"{prefix}board_state.json" if prefix else "board_state.json")
        with open(board_path, 'w', encoding='utf-8') as f:
            json.dump(board_state, f, indent=2, ensure_ascii=False)
        files_created['board_state'] = board_path
        
        # 3. Coordonnées robot
        robot_coords = self.generate_robot_coordinates(pieces)
        coords_path = os.path.join(output_dir, f"{prefix}coordinates.json" if prefix else "coordinates.json")
        with open(coords_path, 'w', encoding='utf-8') as f:
            json.dump(robot_coords, f, indent=2, ensure_ascii=False)
        files_created['coordinates'] = coords_path
        
        return files_created


def load_game_state(filepath: str) -> Dict:
    """
    Charge un état de jeu depuis un fichier JSON.
    
    Args:
        filepath: Chemin vers le fichier JSON
        
    Returns:
        Dict avec l'état du jeu
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_states(state1: Dict, state2: Dict) -> Dict:
    """
    Compare deux états de jeu pour détecter les différences.
    
    Args:
        state1: Premier état (avant)
        state2: Deuxième état (après)
        
    Returns:
        Dict avec les différences détectées
    """
    pieces1 = {p['id']: p for p in state1.get('pieces', [])}
    pieces2 = {p['id']: p for p in state2.get('pieces', [])}
    
    ids1 = set(pieces1.keys())
    ids2 = set(pieces2.keys())
    
    # Pièces apparues/disparues
    added = ids2 - ids1
    removed = ids1 - ids2
    
    # Pièces déplacées (utilise grid pour couvrir plateau + cimetière)
    moved = []
    for pid in ids1 & ids2:
        pos1 = pieces1[pid]['position'].get('grid') or pieces1[pid]['position'].get('chess')
        pos2 = pieces2[pid]['position'].get('grid') or pieces2[pid]['position'].get('chess')
        if pos1 != pos2:
            moved.append({
                'id': pid,
                'code': pieces1[pid]['code'],
                'from': pos1,
                'to': pos2,
                'zone_from': pieces1[pid].get('zone', 'board'),
                'zone_to': pieces2[pid].get('zone', 'board'),
            })
    
    return {
        'added': list(added),
        'removed': list(removed),
        'moved': moved,
        'has_changes': bool(added or removed or moved),
    }


def format_move(move_data: Dict) -> str:
    """
    Formate un mouvement en notation lisible.
    
    Args:
        move_data: Données du mouvement
        
    Returns:
        String formaté (ex: "WP e2→e4")
    """
    return f"{move_data['code']} {move_data['from']}→{move_data['to']}"
