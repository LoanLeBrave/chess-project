"""
HybridBoardManager
==================
Gère un état de plateau hybride combinant la détection caméra et la simulation
des pièces non détectées.

Problème résolu :
    La caméra ne détecte pas toujours toutes les pièces au démarrage (marqueur
    ArUco caché, mal éclairé, etc.). Si la camera_baseline ne contient que les
    pièces visibles, toute pièce qui "apparaît" ensuite est vue comme un
    placement illégal par Stockfish.

Solution :
    Injecter les pièces manquantes (simulées) dans la camera_baseline initiale.
    Ainsi, quand la caméra finit par voir une pièce simulée :
    - À sa case attendue  → pas de delta, rien ne se passe (correct)
    - À une autre case    → delta "disappeared from baseline, appeared at X"
                           → Stockfish valide le coup normalement (correct)
"""

from typing import Optional


# Position de départ standard (32 pièces)
STARTING_POSITION: dict[str, str] = {
    "a1": "WR", "b1": "WN", "c1": "WB", "d1": "WQ",
    "e1": "WK", "f1": "WB", "g1": "WN", "h1": "WR",
    "a2": "WP", "b2": "WP", "c2": "WP", "d2": "WP",
    "e2": "WP", "f2": "WP", "g2": "WP", "h2": "WP",
    "a7": "BP", "b7": "BP", "c7": "BP", "d7": "BP",
    "e7": "BP", "f7": "BP", "g7": "BP", "h7": "BP",
    "a8": "BR", "b8": "BN", "c8": "BB", "d8": "BQ",
    "e8": "BK", "f8": "BB", "g8": "BN", "h8": "BR",
}

PIECE_NAMES: dict[str, str] = {
    "WP": "Pion Blanc",   "BP": "Pion Noir",
    "WR": "Tour Blanche",  "BR": "Tour Noire",
    "WN": "Cavalier Blanc","BN": "Cavalier Noir",
    "WB": "Fou Blanc",     "BB": "Fou Noir",
    "WQ": "Dame Blanche",  "BQ": "Dame Noire",
    "WK": "Roi Blanc",     "BK": "Roi Noir",
}


class HybridBoardManager:
    """
    Gère la simulation des pièces non détectées par la caméra.

    Workflow :
        1. Le joueur place toutes les pièces sur le plateau.
        2. GET /vision/hybrid/missing  → voir quelles pièces manquent.
        3. POST /vision/hybrid/confirm → confirmer que tout est bien placé,
           les pièces manquantes sont simulées dans le baseline caméra.
        4. Pendant la partie, GET /vision/hybrid/simulated montre quelles
           pièces restent simulées (la caméra ne les a pas encore vues).

    Attributs :
        simulated_squares : cases dont la pièce est simulée (pas vue par caméra)
        phase             : "idle" | "confirmed"
        hybrid_baseline   : baseline enrichi (caméra + simulées)
    """

    def __init__(self):
        self.simulated_squares: set[str] = set()
        self.phase: str = "idle"
        self.hybrid_baseline: dict[str, str] = {}
        self._last_camera_board: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Analyse
    # ------------------------------------------------------------------

    def analyze_missing_pieces(self, camera_board: dict[str, str]) -> list[dict]:
        """
        Compare le plateau caméra avec la position de départ standard.

        Args:
            camera_board: {case: code_pièce} vu par la caméra (stable_board)

        Returns:
            Liste de dicts décrivant chaque pièce absente :
            [{"square": "a2", "code": "WP", "name": "Pion Blanc", "color": "white"}, ...]
        """
        missing = []
        for square, expected_code in STARTING_POSITION.items():
            camera_code = camera_board.get(square)
            if not camera_code:
                color = "white" if expected_code.startswith("W") else "black"
                missing.append({
                    "square": square,
                    "code": expected_code,
                    "name": PIECE_NAMES.get(expected_code, expected_code),
                    "color": color,
                })
        return missing

    # ------------------------------------------------------------------
    # Confirmation / simulation
    # ------------------------------------------------------------------

    def build_hybrid_baseline(self, camera_board: dict[str, str]) -> dict[str, str]:
        """
        Construit le baseline hybride : pièces caméra + pièces simulées.

        Les pièces présentes dans la position de départ mais absentes de
        camera_board sont ajoutées au baseline et marquées comme simulées.

        Args:
            camera_board: stable_board actuel de VisionService

        Returns:
            Baseline complet (camera + simulé) à utiliser comme camera_baseline.
        """
        missing = self.analyze_missing_pieces(camera_board)

        # Baseline = ce que la caméra voit + les pièces manquantes simulées
        baseline = dict(camera_board)
        self.simulated_squares = set()

        for piece_info in missing:
            sq = piece_info["square"]
            baseline[sq] = piece_info["code"]
            self.simulated_squares.add(sq)

        self.hybrid_baseline = baseline
        self._last_camera_board = dict(camera_board)
        self.phase = "confirmed"
        return baseline

    def get_hybrid_baseline(self, camera_board: dict[str, str]) -> dict[str, str]:
        """
        Reconstruit un baseline hybride en utilisant les simulated_squares existantes.

        Contrairement à build_hybrid_baseline(), ne réinitialise pas simulated_squares.
        À utiliser après chaque coup pour rafraîchir la baseline caméra tout en
        conservant les pièces encore simulées.

        Args:
            camera_board: stable_board actuel de VisionService

        Returns:
            Baseline = caméra + pièces encore simulées à leur position attendue.
        """
        baseline = dict(camera_board)
        for sq in self.simulated_squares:
            if sq not in baseline and sq in STARTING_POSITION:
                baseline[sq] = STARTING_POSITION[sq]
        return baseline

    # ------------------------------------------------------------------
    # Mise à jour pendant la partie
    # ------------------------------------------------------------------

    def on_camera_update(self, camera_board: dict[str, str]) -> set[str]:
        """
        Appelle quand stable_board est mis à jour.

        Vérifie si des pièces simulées sont maintenant visibles par la caméra.
        Si oui, elles sont retirées de simulated_squares (elles sont réelles).

        Args:
            camera_board: stable_board actuel de VisionService

        Returns:
            Ensemble des cases qui ont été de-simulées (pour log).
        """
        if self.phase != "confirmed":
            return set()

        de_simulated: set[str] = set()
        for sq in list(self.simulated_squares):
            if camera_board.get(sq):
                self.simulated_squares.discard(sq)
                de_simulated.add(sq)

        self._last_camera_board = dict(camera_board)
        return de_simulated

    def on_move_played(self, from_sq: str, to_sq: str, is_capture: bool = False):
        """
        Notifie qu'un coup a été joué (humain ou robot).

        Met à jour simulated_squares : si une pièce simulée a été bougée,
        elle n'est plus simulée (elle a été vue en mouvement).

        Args:
            from_sq   : case de départ du coup
            to_sq     : case d'arrivée du coup
            is_capture: True si capture
        """
        if from_sq in self.simulated_squares:
            self.simulated_squares.discard(from_sq)
        # La pièce arrivée n'est plus simulée non plus
        self.simulated_squares.discard(to_sq)

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def get_status(self, camera_board: Optional[dict[str, str]] = None) -> dict:
        """
        Retourne l'état complet du gestionnaire hybride.

        Args:
            camera_board: stable_board actuel (pour calculer les manquants à la volée)

        Returns:
            Dict pour réponse API.
        """
        board = camera_board or self._last_camera_board

        missing = self.analyze_missing_pieces(board)
        simulated_list = [
            {
                "square": sq,
                "code": STARTING_POSITION.get(sq, "?"),
                "name": PIECE_NAMES.get(STARTING_POSITION.get(sq, ""), sq),
                "color": "white" if STARTING_POSITION.get(sq, "?").startswith("W") else "black",
            }
            for sq in sorted(self.simulated_squares)
        ]

        return {
            "phase": self.phase,
            "camera_pieces_count": len([v for v in board.values() if v]),
            "missing_count": len(missing),
            "missing_pieces": missing,
            "simulated_count": len(self.simulated_squares),
            "simulated_pieces": simulated_list,
        }

    def reset(self):
        """Réinitialise le gestionnaire (nouvelle partie)."""
        self.simulated_squares = set()
        self.phase = "idle"
        self.hybrid_baseline = {}
        self._last_camera_board = {}
