#!/usr/bin/env python3
"""
Gestionnaire du leaderboard (classement)
Agrège les scores par joueur et calcule les statistiques
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class LeaderboardManager:
    """Gestionnaire du classement des joueurs avec agrégation des stats"""
    
    def __init__(self, data_file: str = "leaderboard_data.json"):
        # On s'assure que le chemin est absolu par rapport au fichier
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(base_dir, data_file)
        self.all_games: List[Dict] = []
        self.load_data()
    
    def load_data(self):
        """Charge toutes les parties depuis le fichier JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.all_games = json.load(f)
                print(f"✓ Leaderboard chargé: {len(self.all_games)} parties enregistrées")
            except Exception as e:
                print(f"⚠ Erreur chargement leaderboard: {e}")
                self.all_games = []
        else:
            self.all_games = []
    
    def save_data(self):
        """Sauvegarde toutes les parties dans le fichier JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_games, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠ Erreur sauvegarde leaderboard: {e}")
            return False
    
    def add_game(self, player_name: str, acpl: float, result: str, difficulty: str, moves_played: int, game_duration: Optional[float] = None):
        """Ajoute une nouvelle partie à l'historique"""
        new_entry = {
            "player_name": player_name,
            "acpl": round(acpl, 2),
            "result": str(result).replace("ResultEnum.", "").lower(), # Nettoyage de l'enum si besoin
            "difficulty": difficulty,
            "moves": moves_played,
            "duration": round(game_duration, 1) if game_duration else None,
            "date": datetime.now().isoformat()
        }
        
        self.all_games.append(new_entry)
        return self.save_data()
    
    def get_leaderboard(self, limit: Optional[int] = 10) -> List[Dict]:
        """Agrège les statistiques par joueur et renvoie le top 10 par ACPL moyen"""
        player_stats = {}
        
        for game in self.all_games:
            name = game["player_name"]
            if name not in player_stats:
                player_stats[name] = {
                    "name": name,
                    "total_acpl": 0,
                    "games": 0,
                    "wins": 0,
                    "losses": 0,
                    "abandoned": 0
                }
            
            stats = player_stats[name]
            stats["total_acpl"] += game["acpl"]
            stats["games"] += 1
            
            res = game["result"].lower()
            if "win" in res: stats["wins"] += 1
            elif "lose" in res or "loss" in res: stats["losses"] += 1
            elif "abandoned" in res: stats["abandoned"] += 1
            
        # Calculer les moyennes et transformer en liste
        leaderboard = []
        for name, stats in player_stats.items():
            leaderboard.append({
                "name": name,
                "acpl": round(stats["total_acpl"] / stats["games"], 1),
                "games": stats["games"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "abandoned": stats["abandoned"]
            })
            
        # Trier par ACPL croissant (le plus bas est premier)
        leaderboard.sort(key=lambda x: x['acpl'])
        
        # Ajouter le rang
        for i, entry in enumerate(leaderboard, 1):
            entry['rank'] = i
            
        if limit:
            leaderboard = leaderboard[:limit]
            
        return leaderboard
    
    def reset_leaderboard(self) -> bool:
        """Efface tout l'historique"""
        self.all_games = []
        return self.save_data()
