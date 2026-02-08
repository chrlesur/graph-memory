# -*- coding: utf-8 -*-
"""
🧠 MCP Memory CLI - Package principal.

Architecture:
    client.py   - Communication avec le serveur MCP (REST + SSE)
    commands.py - Commandes Click (health, memory, document, ask...)
    shell.py    - Shell interactif avec prompt_toolkit
    display.py  - Helpers d'affichage Rich (tables, panels)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Configuration globale
BASE_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8002")
TOKEN = os.getenv("ADMIN_BOOTSTRAP_KEY", "admin_bootstrap_key_change_me")
