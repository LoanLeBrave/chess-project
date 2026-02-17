#!/usr/bin/env python3
"""
Module de replacement du plateau a la position initiale.

Lit l'etat reel du plateau via la vision (game_state.json) et
pilote le robot pour replacer chaque piece a sa position de depart.

Approche :
    - PICK  : coordonnees vision (position reelle precise de la piece)
    - PLACE : centre geometrique de la case cible (calibration robot)

Algorithme :
    1. Lecture de game_state.json (derniere capture camera)
    2. Association optimale piece detectee <-> case initiale
       (greedy par distance minimale, pieces du meme type interchangeables)
    3. Resolution des dependances (une piece bloque la destination d'une autre)
    4. Execution sequentielle des mouvements par le robot
"""

import json
import os
from typing import Callable, Dict, List, Optional, Set, Tuple

import chess

from config import (
    DELTA_TRANSIT,
    HAUTEUR_PIECES,
    PIECE_TYPE_MAP,
    POSITION_INITIALE,
)
from robot_controller import RobotController


# ---------------------------------------------------------------------------
#  Constantes
# ---------------------------------------------------------------------------

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GAME_STATE_PATH = os.path.join(
    _BACKEND_DIR, "chess_vision", "output", "latest", "game_state.json"
)

# Mapping vision type string -> chess piece type
_VISION_TYPE_MAP: Dict[str, int] = {
    "Pawn": chess.PAWN,
    "Knight": chess.KNIGHT,
    "Bishop": chess.BISHOP,
    "Rook": chess.ROOK,
    "Queen": chess.QUEEN,
    "King": chess.KING,
}


# ---------------------------------------------------------------------------
#  Module public
# ---------------------------------------------------------------------------

class BoardResetManager:
    """
    Gestionnaire de replacement du plateau.

    Lit l'etat physique via la vision camera, calcule un plan de
    mouvements optimal et l'execute via le RobotController.
    """

    def __init__(self, robot: RobotController):
        self.robot = robot
        self.is_paused = False

        # Callbacks injectes par l'appelant (ApplicationManager)
        self._log_cb: Optional[Callable] = None
        self._broadcast_cb: Optional[Callable] = None

    # ------------------------------------------------------------------
    #  Configuration des callbacks
    # ------------------------------------------------------------------

    def set_log_callback(self, callback: Callable) -> None:
        self._log_cb = callback

    def set_broadcast_callback(self, callback: Callable) -> None:
        self._broadcast_cb = callback

    async def _log(self, log_type: str, message: str) -> None:
        if self._log_cb:
            await self._log_cb(log_type, message)

    async def _broadcast(self, message: dict) -> None:
        if self._broadcast_cb:
            await self._broadcast_cb(message)

    # ------------------------------------------------------------------
    #  Controle (pause / reprise)
    # ------------------------------------------------------------------

    def pause(self) -> None:
        """Interrompt le replacement en cours."""
        self.is_paused = True
        self.robot.pause_urgence()

    def resume(self) -> None:
        """Reprend apres une pause."""
        self.is_paused = False
        self.robot.reprendre_script()

    # ------------------------------------------------------------------
    #  Point d'entree principal
    # ------------------------------------------------------------------

    async def replace_board(self) -> dict:
        """
        Lit la vision, calcule le plan, execute les mouvements.

        Returns:
            dict {success, message|error, moves_executed, total_planned}
        """
        self.is_paused = False

        # 1 — Lecture de la vision
        pieces = self._read_detected_pieces()
        if pieces is None:
            return self._error("Vision indisponible (game_state.json introuvable)")

        if not pieces:
            return self._error("Aucune piece detectee par la camera")

        await self._log("info", f"{len(pieces)} pieces detectees par la vision")

        # 2 — Calcul des assignations piece -> case initiale
        assignments = self._build_assignments(pieces)

        if not assignments:
            await self._log("info", "Toutes les pieces sont deja en position initiale")
            return {"success": True, "message": "Plateau deja en position initiale",
                    "moves_executed": 0, "total_planned": 0}

        total = len(assignments)
        await self._log("info", f"{total} mouvement(s) a effectuer")
        await self._broadcast({"type": "board_reset_started", "total_moves": total})

        # 3 — Execution avec gestion des collisions
        result = await self._execute_assignments(assignments, pieces)
        return result

    # ------------------------------------------------------------------
    #  Lecture vision
    # ------------------------------------------------------------------

    def _read_detected_pieces(self) -> Optional[List[dict]]:
        """Lit game_state.json et retourne la liste des pieces ou None."""
        if not os.path.exists(GAME_STATE_PATH):
            return None
        try:
            with open(GAME_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("pieces", [])
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------
    #  Calcul du plan
    # ------------------------------------------------------------------

    def _build_assignments(self, pieces: List[dict]) -> List[dict]:
        """
        Associe chaque piece detectee a la case initiale la plus proche
        de meme type et couleur.

        Les pieces deja en place sont exclues du plan.

        Returns:
            Liste de mouvements [{piece, from_square, from_zone, to_square}, ...]
        """
        targets_by_key = self._group_targets_by_type()
        pieces_by_key = self._group_pieces_by_type(pieces)

        assignments: List[dict] = []
        for key, target_squares in targets_by_key.items():
            available = list(pieces_by_key.get(key, []))
            matched = self._greedy_match(target_squares, available)
            assignments.extend(matched)

        return assignments

    @staticmethod
    def _group_targets_by_type() -> Dict[Tuple[int, bool], List[str]]:
        """Regroupe les cases initiales par (type_chess, couleur)."""
        groups: Dict[Tuple[int, bool], List[str]] = {}
        for square, (symbol, color) in POSITION_INITIALE.items():
            piece_type = PIECE_TYPE_MAP[symbol.upper()]
            groups.setdefault((piece_type, color), []).append(square)
        return groups

    @staticmethod
    def _group_pieces_by_type(
        pieces: List[dict],
    ) -> Dict[Tuple[int, bool], List[dict]]:
        """Regroupe les pieces detectees par (type_chess, couleur)."""
        groups: Dict[Tuple[int, bool], List[dict]] = {}
        for p in pieces:
            chess_type = _VISION_TYPE_MAP.get(p.get("type"))
            if chess_type is None:
                continue
            color = chess.WHITE if p["color"] == "white" else chess.BLACK
            groups.setdefault((chess_type, color), []).append(p)
        return groups

    def _greedy_match(
        self, target_squares: List[str], available: List[str],
    ) -> List[dict]:
        """Associe les pieces aux cibles par distance minimale (greedy)."""
        remaining_targets = list(target_squares)
        assignments: List[dict] = []

        while remaining_targets and available:
            best = self._closest_pair(remaining_targets, available)
            if best is None:
                break

            piece, target = best
            current_sq = (
                piece.get("position", {}).get("chess", "").lower()
            )

            if current_sq != target:
                assignments.append({
                    "piece": piece,
                    "from_square": current_sq or None,
                    "from_zone": piece.get("zone", "board"),
                    "to_square": target,
                })

            available.remove(piece)
            remaining_targets.remove(target)

        return assignments

    def _closest_pair(
        self, targets: List[str], pieces: List[dict],
    ) -> Optional[Tuple[dict, str]]:
        """Trouve la paire (piece, case cible) la plus proche."""
        best_dist = float("inf")
        best_pair = None

        for target in targets:
            for piece in pieces:
                # Utiliser la case chess de la vision plutot que calculer
                current_sq = piece.get("position", {}).get("chess", "").lower()
                if not current_sq or len(current_sq) != 2:
                    # Piece sans position valide (ex: au cimetiere)
                    # Utiliser une distance tres elevee
                    d = 1000.0
                else:
                    # Distance en cases (Manhattan)
                    file_curr = chess.FILE_NAMES.index(current_sq[0])
                    rank_curr = int(current_sq[1]) - 1
                    file_tgt = chess.FILE_NAMES.index(target[0])
                    rank_tgt = int(target[1]) - 1
                    d = abs(file_curr - file_tgt) + abs(rank_curr - rank_tgt)
                
                if d < best_dist:
                    best_dist = d
                    best_pair = (piece, target)

        return best_pair

    # ------------------------------------------------------------------
    #  Execution
    # ------------------------------------------------------------------

    async def _execute_assignments(
        self, assignments: List[dict], all_pieces: List[dict]
    ) -> dict:
        """
        Execute les mouvements dans un ordre qui evite les collisions.

        Strategie :
            1. Executer les mouvements dont la case cible est libre.
            2. Iterer jusqu'a epuisement.
            3. Si blocage circulaire, deplacer la piece bloquante vers
               une position temporaire puis continuer.
        """
        occupied = self._build_occupied_set(all_pieces)
        pending = list(assignments)
        total = len(pending)
        executed = 0

        for _ in range(total * total + total + 1):
            if not pending:
                break

            move, error = await self._pick_next_move(pending, occupied,
                                                     executed, total)
            if error:
                return error

            result = await self._run_move(move, pending, occupied,
                                          executed, total)
            if result is not None:
                return result

            executed += 1

        await self._go_safe()
        await self._log("info",
                        f"Replacement termine : {executed}/{total} mouvements")
        await self._broadcast({
            "type": "board_reset_complete",
            "moves_executed": executed,
        })

        return {
            "success": True,
            "message": f"Plateau replace ({executed} mouvements)",
            "moves_executed": executed,
            "total_planned": total,
        }

    @staticmethod
    def _build_occupied_set(all_pieces: List[dict]) -> Set[str]:
        """Construit l'ensemble des cases actuellement occupees."""
        occupied: Set[str] = set()
        for p in all_pieces:
            if p.get("zone") != "board":
                continue
            sq = p.get("position", {}).get("chess", "").lower()
            if sq:
                occupied.add(sq)
        return occupied

    async def _pick_next_move(
        self, pending: List[dict], occupied: Set[str],
        executed: int, total: int,
    ) -> Tuple[Optional[dict], Optional[dict]]:
        """Selectionne le prochain mouvement, en gerant les blocages."""
        idx = self._find_free_target(pending, occupied)
        if idx is not None:
            return pending.pop(idx), None

        # Tentative de liberation de la case bloquee
        freed = await self._clear_target(
            pending[0]["to_square"], pending, occupied
        )
        if not freed:
            return None, self._error(
                "Impossible de liberer la case cible",
                moves_executed=executed, total_planned=total,
            )

        idx = self._find_free_target(pending, occupied)
        if idx is None:
            return None, self._error(
                "Blocage inattendu apres liberation",
                moves_executed=executed, total_planned=total,
            )
        return pending.pop(idx), None

    async def _run_move(
        self, move: dict, _pending: List[dict], occupied: Set[str],
        executed: int, total: int,
    ) -> Optional[dict]:
        """Execute un mouvement et met a jour l'occupation. Retourne une erreur ou None."""
        if self.is_paused:
            await self._on_interrupted(executed, total)
            return self._error("Interrompu", moves_executed=executed,
                               total_planned=total)

        success = await self._execute_single_move(move, executed + 1, total)
        if not success:
            await self._on_interrupted(executed, total)
            return self._error("Interrompu", moves_executed=executed,
                               total_planned=total)

        if move.get("from_square"):
            occupied.discard(move["from_square"])
        occupied.add(move["to_square"])
        return None

    def _find_free_target(
        self, pending: List[dict], occupied: Set[str]
    ) -> Optional[int]:
        """Retourne l'index du premier mouvement dont la cible est libre."""
        for i, move in enumerate(pending):
            target = move["to_square"]
            from_sq = move.get("from_square")
            # Libre si la case n'est pas occupee,
            # ou si la piece y est deja (auto-deplacement)
            if target not in occupied or target == from_sq:
                return i
        return None

    async def _clear_target(
        self, target: str, pending: List[dict], occupied: Set[str]
    ) -> bool:
        """
        Deplace la piece qui bloque ``target`` vers une position tampon.

        Cherche d'abord si la piece bloquante a un mouvement planifie
        (et tente de l'executer vers sa propre cible). Sinon, utilise
        une case temporaire sur le plateau.

        Retourne True si la case a ete liberee.
        """
        blocker_idx = self._find_blocker_index(target, pending)

        # Cas 1 : le bloqueur a une cible libre -> l'executer directement
        if blocker_idx is not None:
            blocker_target = pending[blocker_idx]["to_square"]
            if blocker_target not in occupied or blocker_target == target:
                return await self._execute_blocker_direct(
                    blocker_idx, pending, occupied
                )

        # Cas 2 : deplacer le bloqueur vers une case temporaire
        return await self._displace_to_temp(
            target, blocker_idx, pending, occupied
        )

    @staticmethod
    def _find_blocker_index(target: str, pending: List[dict]) -> Optional[int]:
        """Retourne l'index du mouvement dont la source est ``target``."""
        for i, m in enumerate(pending):
            if m.get("from_square") == target:
                return i
        return None

    async def _execute_blocker_direct(
        self, idx: int, pending: List[dict], occupied: Set[str]
    ) -> bool:
        """Execute le mouvement du bloqueur directement vers sa cible."""
        move = pending.pop(idx)
        success = await self._execute_single_move(move, 0, 0)
        if success:
            occupied.discard(move["from_square"])
            occupied.add(move["to_square"])
        return success

    async def _displace_to_temp(
        self, target: str, blocker_idx: Optional[int],
        pending: List[dict], occupied: Set[str],
    ) -> bool:
        """Deplace la piece bloquante vers une case temporaire."""
        temp_square = self._find_empty_square(occupied)
        if temp_square is None:
            return False

        blocker_piece = (
            pending[blocker_idx]["piece"] if blocker_idx is not None
            else self._find_piece_at_square(target, pending)
        )
        if blocker_piece is None:
            return False

        temp_move = {
            "piece": blocker_piece,
            "from_square": target,
            "from_zone": "board",
            "to_square": temp_square,
        }

        success = await self._execute_single_move(temp_move, 0, 0)
        if not success:
            return False

        occupied.discard(target)
        occupied.add(temp_square)

        # Mettre a jour les coordonnees du bloqueur dans le plan
        if blocker_idx is not None:
            self._update_blocker_source(pending[blocker_idx], temp_square)

        return True

    def _update_blocker_source(self, move: dict, new_square: str) -> None:
        """Met a jour la source et les coordonnees d'un mouvement redirige."""
        move["from_square"] = new_square
        # Mettre a jour avec les coordonnees du centre de la case (robot calibre)
        cx, cy = self.robot.get_square_center(new_square)
        move["piece"] = dict(move["piece"])
        move["piece"]["position"] = dict(move["piece"]["position"])
        move["piece"]["position"]["board"] = {"x": cx, "y": cy}
        move["piece"]["position"]["chess"] = new_square

    def _find_piece_at_square(
        self, square: str, pending: List[dict]
    ) -> Optional[dict]:
        """Cherche la piece a ``square`` dans les mouvements en attente."""
        for m in pending:
            if m.get("from_square") == square:
                return m["piece"]
        return None

    def _find_empty_square(self, occupied: Set[str]) -> Optional[str]:
        """Trouve une case vide sur le plateau (preferant les rangees centrales)."""
        # Rangees centrales d'abord (3-6), puis bords (1,2,7,8)
        rank_order = [4, 5, 3, 6, 2, 7, 1, 8]
        for rank in rank_order:
            for file_ch in "abcdefgh":
                sq = f"{file_ch}{rank}"
                if sq not in occupied:
                    return sq
        return None

    async def _execute_single_move(
        self, move: dict, step: int, total: int
    ) -> bool:
        """Execute un mouvement physique (pick vision + place geometrique)."""
        piece_data = move["piece"]
        target = move["to_square"]
        from_label = move.get("from_square") or move.get("from_zone", "?")
        color_label = piece_data.get("color", "?")
        type_label = piece_data.get("type", "?")

        if step > 0:
            await self._log(
                "robot",
                f"[{step}/{total}] {color_label} {type_label} : "
                f"{from_label} -> {target}",
            )
            await self._broadcast({
                "type": "board_reset_progress",
                "current": step,
                "total": total,
                "piece_color": color_label,
                "piece_type": type_label,
                "from": from_label,
                "to": target,
            })

        # Type de piece (pour hauteur Z)
        chess_type = _VISION_TYPE_MAP.get(piece_data.get("type"), chess.PAWN)
        self.robot.piece_courante = chess_type

        # PICK : coordonnees vision
        pick_x = piece_data["position"]["board"]["x"]
        pick_y = piece_data["position"]["board"]["y"]
        p_pick = self.robot.cam_to_robot(pick_x, pick_y, use_piece_height=True)

        # PLACE : centre geometrique de la case cible
        cx, cy = self.robot.get_square_center(target)
        p_place = self.robot.cam_to_robot(cx, cy, use_piece_height=True)

        return await self.robot._sequence_pick_and_place(p_pick, p_place)

    async def _go_safe(self) -> None:
        """Remonte en position de securite et retour home si disponible."""
        safe = list(self.robot.calib_origin)
        safe[2] += DELTA_TRANSIT
        safe.extend([3.14, 0.0, 0.0])
        await self.robot._move_tcp(safe)

        if self.robot.position_depart:
            await self.robot._move_tcp(self.robot.position_depart)

    async def _on_interrupted(self, executed: int, total: int) -> None:
        await self._log("warning", "Replacement interrompu")
        await self._broadcast({
            "type": "board_reset_interrupted",
            "moves_completed": executed,
            "total_moves": total,
        })

    # ------------------------------------------------------------------
    #  Utilitaires
    # ------------------------------------------------------------------

    @staticmethod
    def _square_center_cam(square: str) -> Tuple[float, float]:
        """Centre d'une case en coordonnees camera (meme formule que RobotController)."""
        file_idx = chess.FILE_NAMES.index(square[0])
        rank_idx = int(square[1]) - 1
        unit = 2.5
        return (file_idx - 3.5) * unit, (rank_idx - 3.5) * unit

    @staticmethod
    def _error(msg: str, **extra) -> dict:
        return {"success": False, "error": msg, **extra}
