#!/usr/bin/env python3
"""
Suivi des KPI du robot d'échecs.
Thread-safe — partagé entre api.py, chess_manager.py et robot_controller.py via le singleton kpi_tracker.
"""

import time
import threading
from collections import deque


class KPITracker:
    """Collecteur de métriques de performance en temps réel."""

    def __init__(self):
        self._lock = threading.Lock()
        self._game_in_progress = False

        # 1. Temps de traitement d'image (ms)
        self._img_times_ms: deque = deque(maxlen=200)

        # 2. Temps par coup robot : {s: stockfish, p: physique, t: total}
        self._move_times: deque = deque(maxlen=100)

        # 3. Taux de parties complètes
        self._games_started: int = 0
        self._games_completed: int = 0
        self._games_abandoned: int = 0

        # 4. Taux de détection : paires (detected, expected) + historique taux
        self._detection_samples: deque = deque(maxlen=300)
        self._detection_rates: deque = deque(maxlen=60)  # pour sparkline

        # 5. Taux de saisie gripper
        self._grip_attempts: int = 0
        self._grip_successes: int = 0

    # ── Enregistrements ────────────────────────────────────────────────────────

    def record_image_processing(self, duration_s: float) -> None:
        """Enregistre la durée d'un traitement d'image complet."""
        with self._lock:
            self._img_times_ms.append(round(duration_s * 1000, 1))

    def record_move_time(self, stockfish_s: float, physical_s: float) -> None:
        """Enregistre les durées d'un coup robot (Stockfish + physique)."""
        with self._lock:
            self._move_times.append({
                "s": round(stockfish_s, 2),
                "p": round(physical_s, 2),
                "t": round(stockfish_s + physical_s, 2),
            })

    def record_game_start(self) -> None:
        """À appeler au démarrage de chaque nouvelle partie."""
        with self._lock:
            self._games_started += 1
            self._game_in_progress = True

    def record_game_end(self, completed: bool) -> None:
        """
        À appeler à la fin d'une partie.
        completed=True  → mat / pat / nulle (partie naturelle)
        completed=False → abandon / arrêt manuel
        Ignoré si aucune partie n'est en cours.
        """
        with self._lock:
            if not self._game_in_progress:
                return
            self._game_in_progress = False
            if completed:
                self._games_completed += 1
            else:
                self._games_abandoned += 1

    def record_detection(self, detected: int, expected: int) -> None:
        """Enregistre un échantillon de détection (pièces vues / pièces attendues)."""
        if expected > 0:
            rate = detected / expected * 100
            with self._lock:
                self._detection_samples.append((detected, expected))
                self._detection_rates.append(round(rate, 1))

    def record_grip(self, success: bool) -> None:
        """Enregistre le résultat d'une opération de saisie gripper."""
        with self._lock:
            self._grip_attempts += 1
            if success:
                self._grip_successes += 1

    # ── Snapshot JSON ──────────────────────────────────────────────────────────

    def get_snapshot(self) -> dict:
        """Retourne un instantané de tous les KPI (thread-safe)."""
        with self._lock:
            # 1. Image processing
            img = list(self._img_times_ms)
            avg_img  = sum(img) / len(img) if img else 0
            last_img = img[-1] if img else 0

            # 2. Move times
            mv = list(self._move_times)
            if mv:
                avg_total = sum(m["t"] for m in mv) / len(mv)
                avg_stock = sum(m["s"] for m in mv) / len(mv)
                avg_phys  = sum(m["p"] for m in mv) / len(mv)
            else:
                avg_total = avg_stock = avg_phys = 0.0

            # 3. Game completion
            total_ended = self._games_completed + self._games_abandoned
            completion_rate = (self._games_completed / total_ended * 100) if total_ended > 0 else None

            # 4. Detection
            det = list(self._detection_samples)
            det_rates = list(self._detection_rates)
            if det:
                avg_det      = sum(d / e for d, e in det) / len(det) * 100
                last_det_pct = det[-1][0] / det[-1][1] * 100
            else:
                avg_det = last_det_pct = None

            # 5. Grip
            grip_rate = (self._grip_successes / self._grip_attempts * 100) if self._grip_attempts > 0 else None

            return {
                "image_processing": {
                    "avg_ms":    round(avg_img, 1),
                    "last_ms":   round(last_img, 1),
                    "samples":   len(img),
                    "history":   img[-40:],
                    "target_ms": 500,
                },
                "move_time": {
                    "avg_total_s":    round(avg_total, 2),
                    "avg_stockfish_s": round(avg_stock, 2),
                    "avg_physical_s": round(avg_phys, 2),
                    "samples":  len(mv),
                    "history":  [{"s": m["s"], "p": m["p"], "t": m["t"]} for m in mv[-20:]],
                    "target_s": 10,
                },
                "game_completion": {
                    "games_started":   self._games_started,
                    "games_completed": self._games_completed,
                    "games_abandoned": self._games_abandoned,
                    "rate_pct":        round(completion_rate, 1) if completion_rate is not None else None,
                    "target_pct":      90,
                },
                "piece_detection": {
                    "avg_rate_pct":  round(avg_det, 1)      if avg_det      is not None else None,
                    "last_rate_pct": round(last_det_pct, 1) if last_det_pct is not None else None,
                    "samples":  len(det),
                    "history":  det_rates[-40:],
                    "target_pct": 100,
                },
                "grip_success": {
                    "attempts":  self._grip_attempts,
                    "successes": self._grip_successes,
                    "rate_pct":  round(grip_rate, 1) if grip_rate is not None else None,
                    "target_pct": 95,
                },
                "updated_at": time.time(),
            }


# Singleton partagé entre tous les modules du backend
kpi_tracker = KPITracker()
