#!/usr/bin/env python3
"""
Gestionnaire du leaderboard (classement)
Stockage des scores et statistiques des joueurs
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class GameResult:
    """Résultat d'une partie"""
    player_name: str
    acpl: float  # Average Centipawn Loss
    result: str  # 'win', 'lose', 'abandoned'
    difficulty: str
    moves_played: int
    timestamp: str
    game_duration: Optional[float] = None  # Durée en secondes
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PlayerStats:
    """Statistiques d'un joueur"""
    name: str
    total_acpl: float
    game_count: int
    wins: int
    losses: int
    abandoned: int
    average_acpl: float
    best_acpl: float
    worst_acpl: float
    last_played: str
    
    def to_dict(self):
        return asdict(self)


class LeaderboardManager:
    """Gestionnaire du classement des joueurs"""
    
    def __init__(self, data_file: str = "leaderboard_data.json"):
        self.data_file = data_file
        self.games: List[GameResult] = []
        self.load_data()
    
    def load_data(self):
        """Charge les données depuis le fichier JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.games = [GameResult(**game) for game in data]
                print(f"✓ Leaderboard chargé: {len(self.games)} parties")
            except Exception as e:
                print(f"⚠ Erreur chargement leaderboard: {e}")
                self.games = []
        else:
            print(f"ℹ Nouveau fichier leaderboard: {self.data_file}")
            self.games = []
    
    def save_data(self):
        """Sauvegarde les données dans le fichier JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([game.to_dict() for game in self.games], f, indent=2, ensure_ascii=False)
            print(f"✓ Leaderboard sauvegardé: {len(self.games)} parties")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde leaderboard: {e}")
            return False
    
import json
import os

class LeaderboardManager:
    def __init__(self, filename="leaderboard_data.json"):
        self.filename = filename

    def add_game(self, player_name, acpl, result, difficulty, moves_played, game_duration=None):
        # 1. Charger les données existantes
        games = []
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                try:
                    games = json.load(f)
                except json.JSONDecodeError:
                    games = []

        # 2. Préparer la nouvelle entrée
        new_game = {
            "name": player_name,
            "acpl": acpl,
            "result": result,
            "difficulty": difficulty,
            "moves_played": moves_played,
            "duration": game_duration,
            "date": datetime.now().isoformat()
        }
        
        # 3. Ajouter et Trier (ACPL le plus bas = meilleur)
        games.append(new_game)
        # On trie par ACPL croissant
        games.sort(key=lambda x: x['acpl'])

        # 4. Garder uniquement les 10 meilleurs
        top_10_games = games[:10]

        # 5. Sauvegarder immédiatement dans le fichier
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(top_10_games, f, indent=2, ensure_ascii=False)
            
        return True
    
    def get_player_stats(self, player_name: str) -> Optional[PlayerStats]:
        """Récupère les statistiques d'un joueur"""
        player_games = [g for g in self.games if g.player_name == player_name]
        
        if not player_games:
            return None
        
        acpls = [g.acpl for g in player_games]
        
        return PlayerStats(
            name=player_name,
            total_acpl=sum(acpls),
            game_count=len(player_games),
            wins=sum(1 for g in player_games if g.result == 'win'),
            losses=sum(1 for g in player_games if g.result == 'lose'),
            abandoned=sum(1 for g in player_games if g.result == 'abandoned'),
            average_acpl=round(sum(acpls) / len(acpls), 2),
            best_acpl=round(min(acpls), 2),
            worst_acpl=round(max(acpls), 2),
            last_played=player_games[-1].timestamp
        )
    
    def get_leaderboard(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Génère le classement des joueurs
        Trié par ACPL moyen (plus bas = meilleur)
        """
        # Grouper par joueur
        player_names = set(g.player_name for g in self.games)
        
        rankings = []
        for name in player_names:
            stats = self.get_player_stats(name)
            if stats:
                rankings.append({
                    'rank': 0,  # Sera défini après tri
                    'name': stats.name,
                    'acpl': stats.average_acpl,
                    'games': stats.game_count,
                    'wins': stats.wins,
                    'losses': stats.losses,
                    'abandoned': stats.abandoned,
                    'best_acpl': stats.best_acpl,
                    'worst_acpl': stats.worst_acpl,
                    'last_played': stats.last_played
                })
        
        # Trier par ACPL croissant (plus bas = meilleur)
        rankings.sort(key=lambda x: x['acpl'])
        
        
        # Assigner les rangs
        for i, player in enumerate(rankings, 1):
            player['rank'] = i
        
        # Limiter si demandé
        if limit:
            rankings = rankings[:limit]
        
        return rankings
    
    def get_all_games(self, player_name: Optional[str] = None) -> List[Dict]:
        """Récupère toutes les parties (ou d'un joueur spécifique)"""
        games = self.games
        
        if player_name:
            games = [g for g in games if g.player_name == player_name]
        
        return [g.to_dict() for g in games]
    
    def get_recent_games(self, limit: int = 10) -> List[Dict]:
        """Récupère les parties les plus récentes"""
        recent = sorted(self.games, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [g.to_dict() for g in recent]
    
    def delete_player(self, player_name: str) -> bool:
        """Supprime toutes les parties d'un joueur"""
        initial_count = len(self.games)
        self.games = [g for g in self.games if g.player_name != player_name]
        
        if len(self.games) < initial_count:
            return self.save_data()
        return False
    
    def clear_all(self) -> bool:
        """Efface toutes les données du leaderboard"""
        self.games = []
        return self.save_data()
    
    def get_statistics(self) -> Dict:
        """Récupère des statistiques globales"""
        if not self.games:
            return {
                'total_games': 0,
                'total_players': 0,
                'average_acpl': 0,
                'best_game': None,
                'total_moves': 0
            }
        
        acpls = [g.acpl for g in self.games]
        best_game = min(self.games, key=lambda x: x.acpl)
        
        return {
            'total_games': len(self.games),
            'total_players': len(set(g.player_name for g in self.games)),
            'average_acpl': round(sum(acpls) / len(acpls), 2),
            'best_game': {
                'player': best_game.player_name,
                'acpl': best_game.acpl,
                'timestamp': best_game.timestamp
            },
            'total_moves': sum(g.moves_played for g in self.games),
            'win_rate': round(sum(1 for g in self.games if g.result == 'win') / len(self.games) * 100, 1),
            'abandon_rate': round(sum(1 for g in self.games if g.result == 'abandoned') / len(self.games) * 100, 1)
        }
