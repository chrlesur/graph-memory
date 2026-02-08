#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 MCP Memory CLI - Point d'entrée.

Usage:
    python scripts/mcp_cli.py [COMMAND] [ARGS]
    python scripts/mcp_cli.py shell          # Mode interactif

Toute la logique est dans le package scripts/cli/ :
    cli/__init__.py  - Configuration
    cli/client.py    - Communication serveur MCP
    cli/commands.py  - Commandes Click
    cli/display.py   - Affichage Rich
    cli/shell.py     - Shell interactif prompt_toolkit
"""

import os
import sys

# Ajouter le chemin racine du projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.cli.commands import cli

if __name__ == "__main__":
    cli()
