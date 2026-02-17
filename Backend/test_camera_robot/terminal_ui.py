#!/usr/bin/env python3
"""
Interface terminal avec rafraichissement automatique.

Utilise des codes ANSI pour dessiner une zone fixe (plateau)
qui se rafraichit automatiquement, et une zone de saisie stable.
"""

import sys
import os


class TerminalUI:
    """Gestionnaire d'affichage terminal avec zones separees."""

    # Codes ANSI
    CLEAR_SCREEN = "\033[2J"
    CLEAR_LINE = "\033[2K"
    MOVE_CURSOR_HOME = "\033[H"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"

    def __init__(self):
        self.board_lines = []
        self.status_line = ""
        self.input_prompt = "> "
        self.board_height = 13  # Nombre de lignes pour l'affichage du plateau

    def init_display(self):
        """Initialise l'affichage (efface l'ecran, cache le curseur)."""
        sys.stdout.write(self.CLEAR_SCREEN)
        sys.stdout.write(self.MOVE_CURSOR_HOME)
        sys.stdout.flush()

    def update_board(self, board_text: str, status: str = ""):
        """
        Met a jour l'affichage du plateau et du status.
        
        Args:
            board_text: Texte complet du plateau (multi-lignes).
            status: Ligne de status (metadonnees).
        """
        self.board_lines = board_text.split("\n")
        self.status_line = status

        # Sauvegarder position curseur actuelle
        sys.stdout.write(self.SAVE_CURSOR)

        # Revenir en haut
        sys.stdout.write(self.MOVE_CURSOR_HOME)

        # Afficher le plateau
        for i, line in enumerate(self.board_lines[:self.board_height]):
            sys.stdout.write(self.CLEAR_LINE)
            sys.stdout.write(line + "\n")

        # Ligne blanche
        sys.stdout.write(self.CLEAR_LINE + "\n")

        # Status
        sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write(f"  {self.status_line}\n")

        # Ligne de separation
        sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write("  " + "-" * 54 + "\n")

        # Restaurer position curseur (ou on etait dans l'input)
        sys.stdout.write(self.RESTORE_CURSOR)
        sys.stdout.flush()

    def position_input_line(self):
        """Positionne le curseur sur la ligne de commande (en bas)."""
        line_number = self.board_height + 4  # Apres plateau + status + separateur
        sys.stdout.write(f"\033[{line_number};0H")
        sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write(self.input_prompt)
        sys.stdout.flush()

    def write_message(self, message: str):
        """
        Affiche un message temporaire au-dessus de la ligne de commande.
        """
        sys.stdout.write(self.SAVE_CURSOR)
        
        # Position juste au-dessus de la ligne input
        line_number = self.board_height + 3
        sys.stdout.write(f"\033[{line_number};0H")
        sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write(f"  {message}")
        
        sys.stdout.write(self.RESTORE_CURSOR)
        sys.stdout.flush()

    def cleanup(self):
        """Restore le terminal a l'etat normal."""
        sys.stdout.write(self.SHOW_CURSOR)
        sys.stdout.write("\n" * 3)
        sys.stdout.flush()
