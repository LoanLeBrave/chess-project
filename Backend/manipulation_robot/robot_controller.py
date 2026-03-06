#!/usr/bin/env python3
"""
Contrôle du robot UR5e - Version Dynamique Complète
Utilise la calibration 2 points pour calculer toutes les positions.
Compatible avec chess_manager_updated.py et api_updated.py
"""

import time
import math
import json
import os
import sys
import asyncio
import threading
from typing import List, Optional, Set, Tuple
import chess

from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper

from config import (
    ROBOT_IP, VITESSE, ACCELERATION,
    GRIPPER_OUVERTURE,
    DELTA_TRANSIT, DELTA_RELACHE_BASE,
    FICHIER_CALIBRATION, FICHIER_POSITION_DEPART,
    PIECE_TYPE_MAP, HAUTEUR_PIECES,
    CIMETIERE_BLANCS, CIMETIERE_NOIRS,
)
from models import PieceEliminee

MOVE_TIMEOUT = 45.0  # secondes — timeout par mouvement robot


class RobotController:
    """Contrôleur dynamique pour le robot UR5e"""

    def __init__(self):
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.connected = False

        # Données de calibration
        self.calib_origin = [0, 0, 0]
        self.calib_rotation = 0.0
        self.calib_scale = 1.0
        self.is_calibrated = False

        # Pièce courante pour ajuster la hauteur (Z)
        self.piece_courante = chess.PAWN

        # Position de départ (home)
        self.position_depart = None

        # Pièces éliminées — stockées dans les cases du cimetière (grille 10x10)
        self.pieces_blanches_eliminees: List[PieceEliminee] = []
        self.pieces_noires_eliminees: List[PieceEliminee] = []

        # Cases du cimetière occupées pendant la partie en cours.
        # Vidé à chaque arrêt de partie (reset_tracking) et à chaque reset physique.
        # Garantit que le robot ne posera jamais deux pièces sur la même case
        # au cours d'une même partie, même si la vision est défaillante.
        self._cemetery_permanently_occupied: Set[str] = set()

        # Callback pour logs
        self.log_callback = None

        # Flag de pause
        self.is_paused = False

        # Callback pour vérifier les cases du cimetière occupées physiquement (vision)
        # Signature : () -> Set[str]  (cases en notation robot, ex: {"a0", "b0"})
        self._get_vision_occupied_cimetiere = None

    def pause_urgence(self):
        """Met le robot en pause immédiate (arrêt d'urgence)"""
        if self.connected and self.rtde_c:
            try:
                self.rtde_c.stopScript()  # Arrêt immédiat sécurisé
                self.is_paused = True
                print(" Robot arrêté en urgence")
            except Exception as e:
                print(f" Erreur pause urgence: {e}")

    def reprendre_script(self):
        """Tente de relancer le programme après une pause"""
        if self.connected and self.rtde_c:
            try:
                self.rtde_c.reuploadScript()  # Relance la connexion
                self.is_paused = False
                print("Robot repris")
            except Exception as e:
                print(f" Erreur reprise: {e}")

    def set_log_callback(self, callback):
        """Définit le callback pour les logs"""
        self.log_callback = callback

    def set_cimetiere_vision_callback(self, callback):
        """
        Définit le callback qui retourne les cases du cimetière occupées physiquement.
        Utilisé pour éviter de poser une pièce sur une case déjà occupée par un humain.
        Signature du callback : () -> Set[str]
        """
        self._get_vision_occupied_cimetiere = callback

    async def log(self, log_type: str, message: str):
        """Envoie un log via le callback"""
        if self.log_callback:
            await self.log_callback(log_type, message)

    def reset_tracking(self):
        """Réinitialise le suivi des pièces éliminées entre deux parties."""
        self.pieces_blanches_eliminees.clear()
        self.pieces_noires_eliminees.clear()
        self.reset_cemetery_tracking()
        self.is_paused = False

    def reset_cemetery_tracking(self):
        """Vide le tracking permanent du cimetière.
        À appeler UNIQUEMENT après que le robot a physiquement remis toutes
        les pièces à leur position initiale (replace_board ou reset_plateau).
        """
        self._cemetery_permanently_occupied.clear()

    def init_robot(self):
        """Initialise la connexion et charge la calibration"""
        _SEP = "=" * 60

        # --- Calibration (rapide, pas de réseau) ---
        try:
            if not os.path.exists(FICHIER_CALIBRATION):
                print(f"⚠  Fichier calibration introuvable: {FICHIER_CALIBRATION}")
                self._print_simulation_banner("Calibration manquante")
                return False

            with open(FICHIER_CALIBRATION, 'r') as f:
                data = json.load(f)
                self.calib_origin = data["origin"]
                self.calib_rotation = data["rotation"]
                self.calib_scale = data.get("camera_scale", data.get("board_size", 20.0) / 20.0)
                self.is_calibrated = True
                print(f"✓ Calibration chargée (scale={self.calib_scale:.4f})")

            if os.path.exists(FICHIER_POSITION_DEPART):
                with open(FICHIER_POSITION_DEPART, 'r') as f:
                    self.position_depart = json.load(f).get("position_depart")
                print("✓ Position de départ chargée")

        except Exception as e:
            print(f"✗ Erreur lecture calibration: {e}")
            self._print_simulation_banner(str(e))
            return False

        # --- Connexion RTDE (bloquante — on tourne dans un thread avec spinner) ---
        print(_SEP)
        print(f"  Connexion au robot UR5e  ({ROBOT_IP})")
        print(_SEP)

        result   = {"ok": False, "error": None}
        rtde_c_r = [None, None, None]   # [rtde_c, rtde_r, gripper]

        def _connect():
            try:
                rtde_c_r[0] = RTDEControlInterface(ROBOT_IP)
                rtde_c_r[1] = RTDEReceiveInterface(ROBOT_IP)
                g = RobotiqGripper(rtde_c_r[0])
                g.activate()
                g.set_force(50)
                g.set_speed(150)
                g.move(GRIPPER_OUVERTURE)
                rtde_c_r[2] = g
                result["ok"] = True
            except Exception as e:
                result["error"] = e

        t = threading.Thread(target=_connect, daemon=True)
        t.start()

        # Spinner pendant l'attente
        frames  = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        bars    = ["▏","▎","▍","▌","▋","▊","▉","█"]
        max_wait = 20.0
        interval = 0.1
        elapsed  = 0.0
        bar_len  = 30

        while t.is_alive() and elapsed < max_wait:
            pct      = min(elapsed / max_wait, 1.0)
            filled   = int(pct * bar_len)
            partial  = bars[int((pct * bar_len - filled) * len(bars))] if filled < bar_len else ""
            bar      = "█" * filled + partial + "░" * (bar_len - filled - len(partial))
            frame    = frames[int(elapsed / interval) % len(frames)]
            sys.stdout.write(f"\r  {frame} [{bar}]  {elapsed:4.1f}s / {max_wait:.0f}s")
            sys.stdout.flush()
            time.sleep(interval)
            elapsed += interval

        # Attendre la fin du thread (il a peut-être fini avant max_wait)
        t.join(timeout=2.0)
        sys.stdout.write("\r" + " " * 70 + "\r")
        sys.stdout.flush()

        if result["ok"]:
            self.rtde_c, self.rtde_r, self.gripper = rtde_c_r
            self.connected = True
            print(f"✓ Robot connecté et prêt !  (en {elapsed:.1f}s)")
            print(_SEP)
            return True
        else:
            err_msg = str(result["error"]) if result["error"] else f"timeout {max_wait:.0f}s"
            print(f"✗ Connexion échouée : {err_msg}")
            self._print_simulation_banner(err_msg)
            self.connected = False
            return False

    def _print_simulation_banner(self, reason: str = ""):
        _SEP = "=" * 60
        print(_SEP)
        print("  ⚠   MODE SIMULATION")
        if reason:
            print(f"  Raison : {reason}")
        print()
        print("  Le frontend se lance normalement.")
        print("  Le robot ne sera PAS contrôlé.")
        print("  La caméra et la vision seront désactivées.")
        print(_SEP)

    def get_position(self):
        """Retourne la position actuelle du TCP via l'interface de réception"""
        if self.connected and self.rtde_r:
            try:
                pose = self.rtde_r.getActualTCPPose()
                return {
                    "x": pose[0],
                    "y": pose[1],
                    "z": pose[2],
                    "rx": pose[3],
                    "ry": pose[4],
                    "rz": pose[5]
                }
            except Exception as e:
                print(f"Erreur lecture position: {e}")
                return None
        return None

    def _get_current_pose_list(self) -> List[float]:
        """Retourne la pose TCP courante sous forme de liste [x, y, z, rx, ry, rz]"""
        if self.connected and self.rtde_r:
            try:
                return list(self.rtde_r.getActualTCPPose())
            except Exception:
                pass
        # En mode simulation, retourner une pose par défaut en hauteur de transit
        return [0, 0, self.calib_origin[2] + DELTA_TRANSIT, 3.14, 0.0, 0.0]

    def cam_to_robot(self, cam_x: float, cam_y: float, use_piece_height: bool = True) -> List[float]:
        """
        Transforme coordonnées Caméra -> Robot.
        use_piece_height: Ajoute la hauteur de la pièce au Z du plateau.
        """
        # Mise à l'échelle
        x_scaled = cam_x * self.calib_scale
        y_scaled = cam_y * self.calib_scale

        # Rotation
        cos_t = math.cos(self.calib_rotation)
        sin_t = math.sin(self.calib_rotation)

        x_rot = x_scaled * cos_t - y_scaled * sin_t
        y_rot = x_scaled * sin_t + y_scaled * cos_t

        # Translation
        rx = self.calib_origin[0] + x_rot
        ry = self.calib_origin[1] + y_rot

        # GESTION HAUTEUR Z
        rz = self.calib_origin[2]

        if use_piece_height:
            z_offset = HAUTEUR_PIECES.get(self.piece_courante, 0.010)
            rz += z_offset

        # Orientation fixe
        return [rx, ry, rz, 3.14, 0.0, 0.0]

    def get_square_center(self, square_name: str) -> Tuple[float, float]:
        """
        Calcule le centre d'une case en coordonnées caméra (repère -12.5 à +12.5, pas 2.5).

        Accepte la notation standard (a1-h8) ET les cases du cimetière de la
        grille 10x10 étendue :
          - Colonnes : '0' (gauche), 'a'-'h' (échiquier), '9' (droite)
          - Rangées  : '0' (bas), '1'-'8' (échiquier), '9' (haut)
        Exemples valides : "e4", "a0", "h9", "00", "99", "01", "91"
        """
        col_char = square_name[0].lower()
        row_char = square_name[1]

        col_to_idx = {
            '0': 0,
            'a': 1, 'b': 2, 'c': 3, 'd': 4,
            'e': 5, 'f': 6, 'g': 7, 'h': 8,
            '9': 9,
        }

        col_idx = col_to_idx[col_char]
        row_idx = int(row_char)

        unit_per_square = 2.5
        cam_x = (col_idx - 4.5) * unit_per_square  # -11.25 à +11.25
        cam_y = (row_idx - 4.5) * unit_per_square
        return cam_x, cam_y

    def _next_cimetiere_cell(self, is_white: bool, vision_occupied: set = None) -> Optional[str]:
        """
        Retourne la prochaine case libre du cimetière pour la couleur donnée.
        Les blancs capturés vont en rangée 0, les noirs capturés en rangée 9.

        Priorité des blocages (du plus fiable au moins fiable) :
        1. _cemetery_permanently_occupied : toutes les cases où le robot a déjà
           posé une pièce depuis le dernier reset physique — source de vérité absolue.
        2. vision_occupied : pièces détectées par la caméra (fiabilité variable).
        """
        cells = CIMETIERE_BLANCS if is_white else CIMETIERE_NOIRS

        # Cases supplémentaires occupées physiquement (détectées par la vision),
        # utilisées comme filet de sécurité secondaire uniquement.
        physically_blocked = vision_occupied or set()

        for cell in cells:
            if cell in self._cemetery_permanently_occupied:
                continue  # Le robot a déjà posé quelque chose ici — interdit absolu
            if cell in physically_blocked:
                continue  # La vision détecte quelque chose ici (humain ou erreur vision)
            return cell
        return None  # Ne devrait pas arriver en partie normale (max 15 captures)

    async def _wait_with_pause_check(self, duration):
        """Attend avec vérifications fréquentes de la pause (toutes les 10ms)"""
        start = time.time()
        while time.time() - start < duration:
            if self.is_paused:
                return False
            await asyncio.sleep(0.01)  # Vérifier toutes les 10ms
        return True

    async def _gripper_open(self):
        """Ouvre le gripper via executor — ne bloque pas l'event loop."""
        if not self.connected or not self.gripper:
            return
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self.gripper.move(GRIPPER_OUVERTURE)),
                timeout=5.0
            )
        except Exception:
            pass

    async def _gripper_close(self):
        """Ferme le gripper via executor — ne bloque pas l'event loop."""
        if not self.connected or not self.gripper:
            return
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, self.gripper.close),
                timeout=5.0
            )
        except Exception:
            pass

    async def _move_tcp(self, target_pose, speed=VITESSE, acc=ACCELERATION):
        """Déplace le TCP — non-bloquant via run_in_executor. Timeout après MOVE_TIMEOUT secondes."""
        if self.is_paused:
            return False

        if self.connected:
            loop = asyncio.get_running_loop()
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.rtde_c.moveL(target_pose, speed, acc)
                    ),
                    timeout=MOVE_TIMEOUT
                )
            except asyncio.TimeoutError:
                await self.log("error", f"Timeout moveL ({MOVE_TIMEOUT}s) — récupération en cours")
                await self._recover_from_timeout()
                return False
            except Exception:
                # moveL peut lever une exception si stopScript() a été appelé en parallèle
                return False
            # Vérifier si une pause a été demandée pendant le mouvement
            if self.is_paused:
                return False
            return True
        else:
            await self.log("debug", f"Simu Move: {target_pose}")
            await asyncio.sleep(0.1)
            return True

    async def _recover_from_timeout(self):
        """Récupération après timeout moveL : récupération douce, puis reconnexion si nécessaire."""
        await self.log("warning", "Tentative de récupération douce (stopScript + reuploadScript)")
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, self._do_soft_recover),
                timeout=5.0
            )
            await self.log("info", "Récupération douce réussie après timeout")
            return
        except Exception as e:
            await self.log("warning", f"Récupération douce échouée ({e}) — reconnexion complète")
        await self.reconnect()

    def _do_connect(self):
        """Connexion synchrone complète (à exécuter dans un executor)."""
        self.rtde_c = RTDEControlInterface(ROBOT_IP)
        self.rtde_r = RTDEReceiveInterface(ROBOT_IP)
        self.gripper = RobotiqGripper(self.rtde_c)
        self.gripper.activate()
        self.gripper.set_force(50)
        self.gripper.set_speed(150)
        self.gripper.move(GRIPPER_OUVERTURE)

    def _do_disconnect(self):
        """Déconnexion synchrone propre (à exécuter dans un executor)."""
        try:
            if self.rtde_c:
                self.rtde_c.stopScript()
                self.rtde_c.disconnect()
        except Exception:
            pass
        try:
            if self.rtde_r:
                self.rtde_r.disconnect()
        except Exception:
            pass

    def _do_soft_recover(self):
        """Récupération douce synchrone — stopScript + reuploadScript (à exécuter dans un executor)."""
        self.rtde_c.stopScript()
        time.sleep(0.2)
        self.rtde_c.reuploadScript()
        time.sleep(0.2)

    async def reconnect(self) -> bool:
        """Reconnexion complète RTDE + gripper avec retries. Appelé manuellement ou après un timeout."""
        MAX_RETRIES = 8          # Nombre maximum de tentatives
        RETRY_DELAY = 3.0        # Secondes entre chaque tentative
        CONNECT_TIMEOUT = 12.0   # Timeout par tentative (la lib ur_rtde a 5s en interne)

        await self.log("info", "Reconnexion au robot en cours...")

        # Fermer les connexions existantes dans un executor pour ne pas bloquer l'event loop
        # (stopScript/disconnect peuvent bloquer si la connexion TCP est morte)
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, self._do_disconnect),
                timeout=5.0
            )
        except Exception:
            pass  # Timeout ou erreur de déconnexion : on continue quand même

        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.connected = False

        await asyncio.sleep(1.0)  # Laisser le robot se stabiliser

        for attempt in range(1, MAX_RETRIES + 1):
            await self.log("info", f"Tentative {attempt}/{MAX_RETRIES}...")
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, self._do_connect),
                    timeout=CONNECT_TIMEOUT
                )
                self.connected = True
                await self.log("info", f"Robot reconnecté avec succès (tentative {attempt})")
                return True
            except asyncio.TimeoutError:
                await self.log("warning", f"Tentative {attempt}/{MAX_RETRIES} : timeout ({CONNECT_TIMEOUT}s)")
            except Exception as e:
                await self.log("warning", f"Tentative {attempt}/{MAX_RETRIES} : {e}")

            # Nettoyer les objets partiellement créés avant de réessayer
            self.rtde_c = None
            self.rtde_r = None
            self.gripper = None

            if attempt < MAX_RETRIES:
                await self.log("info", f"Nouvelle tentative dans {RETRY_DELAY:.0f}s...")
                await asyncio.sleep(RETRY_DELAY)

        self.connected = False
        await self.log("error", f"Échec de la reconnexion après {MAX_RETRIES} tentatives")
        return False

    async def execute_move(self, from_sq: str, to_sq: str, is_capture: bool, captured_piece=None,
                           precise_pick_coords=None, castling_rook: Optional[Tuple[str, str]] = None,
                           capture_sq: Optional[str] = None):
        """
        Exécute un mouvement complet sur le robot.
        Retourne True si succès, False si interrompu par pause.

        precise_pick_coords: tuple (x, y) en coordonnées caméra précises pour le pick.
                             Si None, utilise le centre géométrique de la case.
        castling_rook: tuple (case_origine, case_dest) de la tour pour le roque.
                       Ex: ('h1', 'f1') pour le petit roque blanc, ('a1', 'd1') pour le grand.
        capture_sq: case où se trouve physiquement la pièce capturée.
                    Différent de to_sq pour l'en passant. Si None, utilise to_sq.
        """
        if not self.is_calibrated:
            await self.log("error", "Robot non calibré !")
            return False

        try:
            # Position de depart : coords precises camera si dispo, sinon centre geometrique
            if precise_pick_coords:
                cx1, cy1 = precise_pick_coords
            else:
                cx1, cy1 = self.get_square_center(from_sq)
            p_start = self.cam_to_robot(cx1, cy1, use_piece_height=True)

            cx2, cy2 = self.get_square_center(to_sq)
            p_end = self.cam_to_robot(cx2, cy2, use_piece_height=True)

            # Gestion de la capture
            if is_capture and captured_piece:
                # En passant : la pièce capturée peut être sur une case différente de to_sq
                cap_sq = capture_sq if capture_sq else to_sq
                await self.log("robot", f"Capture de {cap_sq}...")

                # Sauvegarde type pièce courante
                attaquant = self.piece_courante

                # On utilise la hauteur de la pièce capturée
                self.piece_courante = captured_piece.piece_type

                cx_cap, cy_cap = self.get_square_center(cap_sq)
                p_capture = self.cam_to_robot(cx_cap, cy_cap, use_piece_height=True)
                success = await self._sequence_elimination(p_capture, captured_piece, cap_sq)

                if not success:
                    return False  # Interrompu par pause

                # Restaure pièce courante
                self.piece_courante = attaquant

            # Déplacement de la pièce principale (roi pour le roque, pièce normale sinon)
            await self.log("robot", f"Mouvement {from_sq} → {to_sq}")
            success = await self._sequence_pick_and_place(p_start, p_end)

            if not success:
                return False  # Interrompu par pause

            # ── ROQUE : déplacer la tour ────────────────────────────────────
            if castling_rook:
                rook_from, rook_to = castling_rook
                await self.log("robot", f"Roque — Tour {rook_from} → {rook_to}")
                self.piece_courante = chess.ROOK

                cx_rf, cy_rf = self.get_square_center(rook_from)
                p_rook_pick = self.cam_to_robot(cx_rf, cy_rf, use_piece_height=True)
                cx_rt, cy_rt = self.get_square_center(rook_to)
                p_rook_place = self.cam_to_robot(cx_rt, cy_rt, use_piece_height=True)

                success = await self._sequence_pick_and_place(p_rook_pick, p_rook_place)
                if not success:
                    return False  # Interrompu par pause

                # Position de sécurité au-dessus de la tour (dernière pièce déposée)
                p_safe = list(p_rook_place)
            else:
                p_safe = list(p_end)
            # ────────────────────────────────────────────────────────────────

            # Retour en position de sécurité
            p_safe[2] = self.calib_origin[2] + DELTA_TRANSIT
            success = await self._move_tcp(p_safe)

            if not success:
                return False

            # Retour position home si définie
            if self.position_depart and not self.is_paused:
                await self._move_tcp(self.position_depart)

            return True

        except Exception as e:
            await self.log("error", f"Erreur mouvement: {e}")
            return False

    async def _prendre_piece(self, case: str):
        """
        Prend une pièce sur une case (utilisé par chess_manager pour reset)
        Retourne True si succès, False si interrompu
        """
        try:
            cx, cy = self.get_square_center(case)
            p_pick = self.cam_to_robot(cx, cy, use_piece_height=True)
            z_transit = self.calib_origin[2] + DELTA_TRANSIT

            # 1. Monter en Z à la hauteur de transit (depuis la position courante)
            current = self._get_current_pose_list()
            p_up = list(current)
            p_up[2] = z_transit
            if not await self._move_tcp(p_up):
                return False

            # 2. Déplacement XY au-dessus de la pièce
            p_above = list(p_pick)
            p_above[2] = z_transit
            if not await self._move_tcp(p_above):
                return False

            # 3. Ouvrir le gripper
            if self.connected:
                self.gripper.move(GRIPPER_OUVERTURE)
            if not await self._wait_with_pause_check(0.05):
                return False

            # 4. Descente en Z vers la pièce (vitesse réduite)
            if not await self._move_tcp(p_pick, VITESSE / 2):
                return False

            # 5. Fermer le gripper
            if self.connected:
                self.gripper.close()
            if not await self._wait_with_pause_check(0.2):
                return False

            # 6. Remontée en Z à la hauteur de transit
            if not await self._move_tcp(p_above):
                return False

            return True

        except Exception as e:
            await self.log("error", f"Erreur prise pièce: {e}")
            return False

    async def _poser_piece(self, case: str):
        """
        Pose une pièce sur une case (utilisé par chess_manager pour reset)
        Retourne True si succès, False si interrompu
        """
        try:
            cx, cy = self.get_square_center(case)
            p_place = self.cam_to_robot(cx, cy, use_piece_height=True)
            z_transit = self.calib_origin[2] + DELTA_TRANSIT

            # 1. Monter en Z à la hauteur de transit (depuis la position courante)
            current = self._get_current_pose_list()
            p_up = list(current)
            p_up[2] = z_transit
            if not await self._move_tcp(p_up):
                return False

            # 2. Déplacement XY au-dessus de la destination
            p_above = list(p_place)
            p_above[2] = z_transit
            if not await self._move_tcp(p_above):
                return False

            # 3. Descente en Z vers le dépôt (vitesse réduite, avec offset de relâche)
            p_deposit = list(p_place)
            p_deposit[2] += DELTA_RELACHE_BASE
            if not await self._move_tcp(p_deposit, VITESSE / 2):
                return False

            # 4. Ouvrir le gripper
            if self.connected:
                self.gripper.move(GRIPPER_OUVERTURE)
            if not await self._wait_with_pause_check(0.1):
                return False

            # 5. Remontée en Z à la hauteur de transit
            if not await self._move_tcp(p_above):
                return False

            return True

        except Exception as e:
            await self.log("error", f"Erreur dépose pièce: {e}")
            return False

    async def _sequence_pick_and_place(self, p_pick, p_place):
        """
        Séquence complète prendre et poser
        Retourne True si succès, False si interrompu
        """
        z_transit = self.calib_origin[2] + DELTA_TRANSIT

        # ===== PICK =====

        # 1. Monter en Z à la hauteur de transit (depuis la position courante)
        current = self._get_current_pose_list()
        p_up = list(current)
        p_up[2] = z_transit
        if not await self._move_tcp(p_up):
            return False

        # 2. Déplacement XY pur au-dessus de la pièce à prendre
        p_above_pick = list(p_pick)
        p_above_pick[2] = z_transit
        if not await self._move_tcp(p_above_pick):
            return False

        # 3. Ouvrir le gripper
        if self.connected:
            self.gripper.move(GRIPPER_OUVERTURE)
        if not await self._wait_with_pause_check(0.05):
            return False

        # 4. Descente en Z vers la pièce (vitesse réduite)
        if not await self._move_tcp(p_pick, VITESSE / 2):
            return False

        # 5. Fermer le gripper
        if self.connected:
            self.gripper.close()
        if not await self._wait_with_pause_check(0.2):
            return False

        # 6. Remontée en Z à la hauteur de transit
        if not await self._move_tcp(p_above_pick):
            return False

        # ===== PLACE =====

        # 7. Déplacement XY pur au-dessus de la destination
        p_above_place = list(p_place)
        p_above_place[2] = z_transit
        if not await self._move_tcp(p_above_place):
            return False

        # 8. Descente en Z vers le dépôt (vitesse réduite, avec offset de relâche)
        p_deposit = list(p_place)
        p_deposit[2] += DELTA_RELACHE_BASE
        if not await self._move_tcp(p_deposit, VITESSE / 2):
            return False

        # 9. Ouvrir le gripper
        if self.connected:
            self.gripper.move(GRIPPER_OUVERTURE)
        if not await self._wait_with_pause_check(0.1):
            return False

        # 10. Remontée en Z à la hauteur de transit
        if not await self._move_tcp(p_above_place):
            return False

        return True

    async def _sequence_elimination(self, p_capture, piece_obj, square_name):
        """
        Séquence d'élimination d'une pièce capturée.
        Dépose la pièce dans la prochaine case libre du cimetière (grille 10x10).
        Vérifie via la vision si des cases sont déjà occupées physiquement avant de choisir.
        Retourne True si succès, False si interrompu.
        """
        is_white = (piece_obj.color == chess.WHITE)
        index = len(self.pieces_blanches_eliminees) if is_white else len(self.pieces_noires_eliminees)

        # Interroger la vision pour savoir quelles cases sont physiquement occupées
        vision_occupied = set()
        if self._get_vision_occupied_cimetiere:
            try:
                vision_occupied = self._get_vision_occupied_cimetiere()
                if vision_occupied:
                    await self.log("info", f"Vision cimetière : {len(vision_occupied)} case(s) occupée(s) physiquement : {sorted(vision_occupied)}")
            except Exception as e:
                await self.log("warning", f"Impossible de lire l'état du cimetière via la vision : {e}")

        # Trouver la prochaine case de cimetière disponible (en tenant compte de la vision)
        case_cimetiere = self._next_cimetiere_cell(is_white, vision_occupied)
        if case_cimetiere is None:
            await self.log("error", "Cimetière plein — impossible de déposer la pièce")
            return False

        # Calculer la position robot de la case cimetière
        self.piece_courante = piece_obj.piece_type
        cx_cem, cy_cem = self.get_square_center(case_cimetiere)
        p_drop = self.cam_to_robot(cx_cem, cy_cem, use_piece_height=True)

        await self.log("robot", f"Elimination {piece_obj.symbol()} ({square_name}) → cimetière {case_cimetiere}")

        # Exécuter le pick and place
        success = await self._sequence_pick_and_place(p_capture, p_drop)

        if not success:
            return False  # Interrompu par pause

        # Enregistrer la pièce éliminée avec sa case de cimetière
        elim = PieceEliminee(piece_obj.symbol(), piece_obj.color, square_name, case_cimetiere, index)
        if is_white:
            self.pieces_blanches_eliminees.append(elim)
        else:
            self.pieces_noires_eliminees.append(elim)

        # Marquer la case comme définitivement occupée : cette information survit
        # aux reset_tracking() inter-parties et garantit qu'aucun coup futur
        # ne viendra poser une pièce sur cette case tant que le plateau n'est pas
        # physiquement remis à zéro via reset_plateau().
        self._cemetery_permanently_occupied.add(case_cimetiere)

        return True

    async def reset_plateau(self):
        """
        Remet toutes les pièces éliminées à leur position d'origine
        Retourne dict avec success: True/False
        """
        if not self.connected:
            return {"success": True, "message": "Mode simulation"}

        try:
            await self.log("info", "Début du reset des pièces éliminées...")

            # Reset Blancs (en ordre inverse)
            for piece in reversed(self.pieces_blanches_eliminees):
                if self.is_paused:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)

                # Position dans le cimetière → coords robot
                cx_cem, cy_cem = self.get_square_center(piece.case_cimetiere)
                p_cimetiere = self.cam_to_robot(cx_cem, cy_cem, use_piece_height=True)

                # Position d'origine sur le plateau → coords robot
                cx_ori, cy_ori = self.get_square_center(piece.case_origine)
                p_origin = self.cam_to_robot(cx_ori, cy_ori, use_piece_height=True)

                await self.log("robot", f"Replacement {piece.piece_symbol} : {piece.case_cimetiere} → {piece.case_origine}")
                success = await self._sequence_pick_and_place(p_cimetiere, p_origin)

                if not success:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

            # Reset Noirs (en ordre inverse)
            for piece in reversed(self.pieces_noires_eliminees):
                if self.is_paused:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

                self.piece_courante = PIECE_TYPE_MAP.get(piece.piece_symbol.upper(), chess.PAWN)

                # Position dans le cimetière → coords robot
                cx_cem, cy_cem = self.get_square_center(piece.case_cimetiere)
                p_cimetiere = self.cam_to_robot(cx_cem, cy_cem, use_piece_height=True)

                # Position d'origine sur le plateau → coords robot
                cx_ori, cy_ori = self.get_square_center(piece.case_origine)
                p_origin = self.cam_to_robot(cx_ori, cy_ori, use_piece_height=True)

                await self.log("robot", f"Replacement {piece.piece_symbol} : {piece.case_cimetiere} → {piece.case_origine}")
                success = await self._sequence_pick_and_place(p_cimetiere, p_origin)

                if not success:
                    await self.log("warning", "Reset interrompu par pause")
                    return {"success": False, "message": "Interrompu par pause"}

            # Clear les listes et le tracking permanent : le plateau physique est remis
            # à zéro, donc toutes les cases du cimetière sont à nouveau disponibles.
            self.pieces_blanches_eliminees.clear()
            self.pieces_noires_eliminees.clear()
            self.reset_cemetery_tracking()

            await self.log("info", "✓ Reset des pièces terminé")
            return {"success": True, "message": "Toutes les pièces replacées"}

        except Exception as e:
            await self.log("error", f"Erreur lors du reset: {e}")
            return {"success": False, "message": str(e)}

    def get_pieces_eliminees(self):
        """Retourne la liste des pièces éliminées"""
        return {
            "blanches": [p.to_dict() for p in self.pieces_blanches_eliminees],
            "noires": [p.to_dict() for p in self.pieces_noires_eliminees]
        }

    def close(self):
        """Ferme la connexion au robot"""
        if self.rtde_c:
            try:
                self.rtde_c.stopScript()
                print("✓ Robot arrêté proprement")
            except:
                pass
