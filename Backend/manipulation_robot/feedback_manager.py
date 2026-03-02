#!/usr/bin/env python3
"""
Gestionnaire des feedbacks
Stockage des avis et commentaires des utilisateurs
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class FeedbackManager:
    """Gestionnaire des feedbacks utilisateurs"""
    
    def __init__(self, data_file: str = "feedback_data.json"):
        self.data_file = data_file
        self.feedbacks: List[Dict] = []
        self.load_data()
    
    def load_data(self):
        """Charge les feedbacks depuis le fichier JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.feedbacks = json.load(f)
                print(f"✓ Feedbacks chargés: {len(self.feedbacks)} entrées")
            except Exception as e:
                print(f"⚠ Erreur chargement feedbacks: {e}")
                self.feedbacks = []
        else:
            self.feedbacks = []
    
    def save_data(self):
        """Sauvegarde les feedbacks dans le fichier JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedbacks, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"⚠ Erreur sauvegarde feedbacks: {e}")
            return False
    
    def add_feedback(self, player_name: str, rating: int, comment: str, difficulty: str, result: str, acpl_score: float):
        """Ajoute un nouveau feedback"""
        new_entry = {
            "id": str(uuid.uuid4()),
            "playerName": player_name,
            "rating": rating,
            "comment": comment,
            "difficulty": difficulty,
            "result": result,
            "acplScore": acpl_score,
            "timestamp": datetime.now().isoformat()
        }
        self.feedbacks.insert(0, new_entry)  # Ajouter au début pour avoir les plus récents d'abord
        return self.save_data()
    
    def get_feedbacks(self) -> List[Dict]:
        """Récupère tous les feedbacks"""
        return self.feedbacks
    
    def reset_feedbacks(self) -> bool:
        """Efface tous les feedbacks"""
        self.feedbacks = []
        return self.save_data()
