# 🔧 Mon Service MCP

> Service MCP Cloud Temple — [décrire le domaine métier ici].

## Démarrage rapide

### 1. Configuration

```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

### 2. Lancement (Docker)

```bash
docker compose build
docker compose up -d
docker compose logs -f mon-mcp
```

### 3. Vérification

```bash
# Health check
python scripts/mcp_cli.py health

# Informations
python scripts/mcp_cli.py about

# Shell interactif
python scripts/mcp_cli.py shell
```

### 4. Lancement (local, sans Docker)

```bash
pip install -r requirements.txt
python -m src.mon_service.server
```

## Architecture

Ce service suit le pattern **3 couches** Cloud Temple :

| Couche          | Fichier                 | Rôle                      |
| --------------- | ----------------------- | ------------------------- |
| Outils MCP      | `src/mon_service/server.py`  | API MCP (HTTP/SSE)   |
| CLI Click       | `scripts/cli/commands.py`    | Interface scriptable  |
| Shell interactif| `scripts/cli/shell.py`       | Interface interactive |
| Affichage       | `scripts/cli/display.py`     | Rich partagé          |

## Variables d'environnement

### Serveur (.env)

| Variable              | Description                    | Défaut                    |
| --------------------- | ------------------------------ | ------------------------- |
| `MCP_SERVER_NAME`     | Nom du service                 | `mon-mcp-service`         |
| `MCP_SERVER_PORT`     | Port d'écoute                  | `8002`                    |
| `ADMIN_BOOTSTRAP_KEY` | Token admin (⚠️ changer !)    | `change_me_in_production` |

### Client CLI (variables shell)

| Variable    | Description        | Défaut                   |
| ----------- | ------------------ | ------------------------ |
| `MCP_URL`   | URL du serveur     | `http://localhost:8002`  |
| `MCP_TOKEN` | Token d'auth       | (vide)                   |

## Ajouter un outil métier

Voir le guide complet : [Starter Kit MCP Cloud Temple](../README.md)

1. `server.py` — `@mcp.tool()` avec docstring, auth, try/except
2. `display.py` — Fonction `show_xxx_result()` Rich
3. `commands.py` — Commande Click
4. `shell.py` — Handler + autocomplétion + aide

## License

Cloud Temple — Usage interne.
