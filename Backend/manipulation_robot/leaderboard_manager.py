#!/usr/bin/env python3
"""
Gestionnaire du leaderboard (classement)
Stocke les stats agrégées par joueur (top 10 par ACPL moyen).
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class LeaderboardManager:
    """Gestionnaire du classement — une entrée par joueur avec stats cumulées"""

    def __init__(self, data_file: str = "leaderboard_data.json"):
        self.data_file = data_file
        self.players: List[Dict] = []
        self.load_data()

    def load_data(self):
        """Charge les joueurs depuis le fichier JSON, migre l'ancien format si nécessaire"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if not isinstance(data, list):
                    self.players = []
                    return

                # Détection de l'ancien format (entrées par partie, champ 'result' présent,
                # champ 'games' absent)
                if data and 'result' in data[0] and 'games' not in data[0]:
                    print("⚠ Leaderboard ancien format détecté — migration en cours...")
                    self.players = self._migrate_old_data(data)
                    self.save_data()
                    print(f"✓ Migration terminée: {len(self.players)} joueur(s)")
                else:
                    self.players = data
                    print(f"✓ Leaderboard chargé: {len(self.players)} joueur(s)")
            except Exception as e:
                print(f"⚠ Erreur chargement leaderboard: {e}")
                self.players = []
        else:
            self.players = []

    def _migrate_old_data(self, old_entries: List[Dict]) -> List[Dict]:
        """Convertit les anciennes entrées (1 par partie) en profils joueur agrégés"""
        player_stats: Dict[str, Dict] = {}

        for entry in old_entries:
            name = entry.get('name', 'Inconnu')
            if name not in player_stats:
                player_stats[name] = {
                    'total_acpl': 0.0,
                    'games': 0,
                    'wins': 0,
                    'losses': 0,
                    'abandoned': 0,
                    'date': entry.get('date', ''),
                }
            stats = player_stats[name]
            stats['total_acpl'] += entry.get('acpl', 0.0)
            stats['games'] += 1
            result = entry.get('result', '')
            if result == 'win':
                stats['wins'] += 1
            elif result == 'lose':
                stats['losses'] += 1
            elif result == 'abandoned':
                stats['abandoned'] += 1
            # Garder la date la plus récente
            if entry.get('date', '') > stats['date']:
                stats['date'] = entry['date']

        players = []
        for name, stats in player_stats.items():
            players.append({
                'name': name,
                'acpl': round(stats['total_acpl'] / stats['games'], 2),
                'games': stats['games'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'abandoned': stats['abandoned'],
                'date': stats['date'],
            })

        players.sort(key=lambda x: x['acpl'])
        return players[:10]

    def save_data(self):
        """Sauvegarde les profils joueurs dans le fichier JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.players, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠ Erreur sauvegarde leaderboard: {e}")
            return False

    def add_game(self, player_name: str, acpl: float, result: str, difficulty: str,
                 moves_played: int, game_duration: Optional[float] = None):
        """
        Ajoute une partie au profil du joueur (crée le profil si premier jeu).
        L'ACPL affiché est la moyenne de toutes ses parties.
        """
        existing = next((p for p in self.players if p['name'] == player_name), None)

        if existing:
            # Mise à jour : recalcul de l'ACPL moyen par incrément
            old_games = existing['games']
            existing['acpl'] = round(
                (existing['acpl'] * old_games + acpl) / (old_games + 1), 2
            )
            existing['games'] += 1
            if result == 'win':
                existing['wins'] += 1
            elif result == 'lose':
                existing['losses'] += 1
            elif result == 'abandoned':
                existing['abandoned'] += 1
            existing['date'] = datetime.now().isoformat()
        else:
            # Nouveau joueur
            self.players.append({
                'name': player_name,
                'acpl': round(acpl, 2),
                'games': 1,
                'wins': 1 if result == 'win' else 0,
                'losses': 1 if result == 'lose' else 0,
                'abandoned': 1 if result == 'abandoned' else 0,
                'date': datetime.now().isoformat(),
            })

        # Trier par ACPL moyen croissant (plus bas = meilleur) et garder le top 10
        self.players.sort(key=lambda x: x['acpl'])
        self.players = self.players[:10]

        return self.save_data()

    def get_leaderboard(self, limit: Optional[int] = None) -> dict:
        """
        Retourne le classement sous forme {leaderboard: [...]} avec les rangs.
        Le frontend attend cette structure.
        """
        entries = []
        players = self.players[:limit] if limit else self.players
        for i, player in enumerate(players, 1):
            entry = player.copy()
            entry['rank'] = i
            entries.append(entry)
        return {"leaderboard": entries}

    def reset_leaderboard(self) -> bool:
        """Efface tout le classement"""
        self.players = []
        return self.save_data()
