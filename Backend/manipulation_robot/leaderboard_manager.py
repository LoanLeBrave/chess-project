#!/usr/bin/env python3
"""
Gestionnaire du leaderboard (classement)
Stockage des 10 meilleurs scores (ACPL le plus bas)
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class LeaderboardManager:
    """Gestionnaire du classement des joueurs (Top 10 ACPL)"""
    
    def __init__(self, data_file: str = "leaderboard_data.json"):
        self.data_file = data_file
        self.scores: List[Dict] = []
        self.load_data()
    
    def load_data(self):
        """Charge les scores depuis le fichier JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.scores = json.load(f)
                print(f"✓ Leaderboard chargé: {len(self.scores)} entrées")
            except Exception as e:
                print(f"⚠ Erreur chargement leaderboard: {e}")
                self.scores = []
        else:
            self.scores = []
    
    def save_data(self):
        """Sauvegarde les scores dans le fichier JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.scores, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠ Erreur sauvegarde leaderboard: {e}")
            return False
    
    def add_game(self, player_name: str, acpl: float, result: str, difficulty: str, moves_played: int, game_duration: Optional[float] = None):
        """
        Ajoute un nouveau score, trie par ACPL et ne garde que les 10 meilleurs.
        L'ACPL (Average Centipawn Loss) le plus bas est le meilleur.
        """
        new_entry = {
            "name": player_name,
            "acpl": round(acpl, 2),
            "result": result,
            "difficulty": difficulty,
            "moves": moves_played,
            "duration": round(game_duration, 1) if game_duration else None,
            "date": datetime.now().isoformat()
        }
        
        self.scores.append(new_entry)
        
        # Trier par ACPL croissant (le plus bas est premier)
        self.scores.sort(key=lambda x: x['acpl'])
        
        # Garder uniquement les 10 meilleurs
        self.scores = self.scores[:10]
        
        return self.save_data()
    
    def get_leaderboard(self, limit: Optional[int] = None) -> List[Dict]:
        """Récupère le top 10 actuel avec les rangs"""
        leaderboard = []
        for i, score in enumerate(self.scores, 1):
            entry = score.copy()
            entry['rank'] = i
            leaderboard.append(entry)
            
        if limit:
            leaderboard = leaderboard[:limit]
            
        return leaderboard
    
    def reset_leaderboard(self) -> bool:
        """Efface tout le classement"""
        self.scores = []
        return self.save_data()
