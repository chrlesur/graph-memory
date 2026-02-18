# 🚀 Starter Kit — Créer un serveur MCP Cloud Temple

> **Audience** : Assistant IA (Cline, Cursor, etc.) ou développeur humain.
> Ce guide contient le **pattern architectural** et les **conventions** pour créer
> un nouveau serveur MCP chez Cloud Temple, avec une CLI complète.
>
> **Référence vivante** : le projet [graph-memory](https://github.com/chrlesur/graph-memory)
> est une implémentation concrète de ce pattern (mémoire Knowledge Graph pour agents IA).

---

## 1. Qu'est-ce qu'un serveur MCP ?

### Le protocole MCP (Model Context Protocol)
MCP est un protocole ouvert qui permet à des **agents IA** (Cline, Claude Desktop,
curseurs IA, agents autonomes) d'appeler des **outils** exposés par un serveur.

Un serveur MCP Cloud Temple :
- Expose des **outils** (`@mcp.tool()`) via HTTP/SSE
- Est consommé par des **clients MCP** (agents IA, CLI, applications web)
- Fournit un domaine métier spécifique (mémoire, monitoring, déploiement, etc.)

### Pourquoi ce starter-kit ?
Chaque serveur MCP Cloud Temple suit le **même pattern architectural** :
- **3 couches** d'interface (API MCP + CLI scriptable + shell interactif)
- **Mêmes conventions** (format retour, auth, nommage, logs)
- **Mêmes outils** (FastMCP, Click, prompt_toolkit, Rich)
- **Même infra** (Docker, reverse proxy, auth token)

Ce guide vous permet de démarrer un nouveau serveur MCP en quelques heures
au lieu de quelques jours.

---

## 2. Architecture — La règle des 3 couches

**Toute fonctionnalité DOIT être exposée dans les 3 couches** :

```
┌─────────────────────────────────────────────────────┐
│  COUCHE 1 : Outil MCP (server.py)                   │
│  @mcp.tool() async def mon_outil(...) -> dict       │
│  → L'API, appelée par tout client MCP               │
├─────────────────────────────────────────────────────┤
│  COUCHE 2 : CLI Click (commands.py)                  │
│  @cli.command() def mon_outil(ctx, ...):            │
│  → Interface scriptable en ligne de commande         │
├─────────────────────────────────────────────────────┤
│  COUCHE 3 : Shell interactif (shell.py)              │
│  async def cmd_mon_outil(client, state, args):      │
│  → Interface interactive avec autocomplétion         │
├─────────────────────────────────────────────────────┤
│  PARTAGÉ : Affichage Rich (display.py)               │
│  def show_mon_outil_result(result):                 │
│  → Tables, panels, couleurs — utilisé par 2 et 3   │
└─────────────────────────────────────────────────────┘
```

### Pourquoi 3 couches ?

| Couche         | Consommateur                          | Usage                       |
| -------------- | ------------------------------------- | --------------------------- |
| Outil MCP      | Agents IA (Cline, Claude Desktop)     | Automatisation, intégration |
| CLI Click      | DevOps, scripts CI/CD, cron           | Scriptable, composable      |
| Shell interactif | Humains en exploration              | Découverte, debug, admin    |

---

## 3. Stack technique de base

Chaque serveur MCP Cloud Temple utilise cette fondation commune :

| Composant        | Technologie             | Rôle                                |
| ---------------- | ----------------------- | ----------------------------------- |
| Framework MCP    | `FastMCP` (Python SDK)  | Expose les outils via HTTP/SSE      |
| Serveur HTTP     | `Uvicorn` (ASGI)        | Sert l'application FastMCP          |
| Configuration    | `pydantic-settings`     | Variables d'environnement + `.env`  |
| CLI scriptable   | `Click`                 | Commandes en ligne                  |
| Shell interactif | `prompt_toolkit`        | Autocomplétion, historique          |
| Affichage        | `Rich`                  | Tables, panels, couleurs, Markdown  |
| Communication    | `httpx` + `httpx-sse`   | Client HTTP/SSE vers le serveur     |
| Auth             | Bearer Token            | Authentification par token          |
| Conteneur        | Docker + Docker Compose | Déploiement                         |
| Reverse proxy    | Caddy (ou nginx)        | TLS, WAF (optionnel : Coraza)       |

Les **services métier** (bases de données, APIs externes, etc.) sont propres
à chaque serveur MCP et ne font PAS partie de la base commune.

---

## 4. Structure de fichiers recommandée

```
mon-mcp-server/
├── src/
│   └── mon_service/
│       ├── __init__.py
│       ├── server.py           # ← Couche 1 : outils MCP (@mcp.tool())
│       ├── config.py           # Configuration pydantic-settings
│       ├── auth/
│       │   ├── middleware.py    # Middleware ASGI (auth, logging)
│       │   ├── context.py      # Helpers auth (check_access, etc.)
│       │   └── token_manager.py # Gestion des tokens
│       └── core/
│           ├── mon_service_a.py # Service métier A (ex: graphe, monitoring...)
│           ├── mon_service_b.py # Service métier B (ex: stockage, API externe...)
│           └── models.py        # Modèles Pydantic
├── scripts/
│   ├── mcp_cli.py              # Point d'entrée CLI (importe commands.py)
│   └── cli/
│       ├── __init__.py         # Config globale (BASE_URL, TOKEN)
│       ├── client.py           # Client HTTP/SSE vers le serveur
│       ├── commands.py         # ← Couche 2 : commandes Click
│       ├── shell.py            # ← Couche 3 : shell interactif
│       └── display.py          # Affichage Rich partagé (couches 2+3)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── VERSION
└── README.md
```

---

## 5. Conventions et patterns

### 5.1 Format de retour standardisé

**Chaque outil MCP retourne un `dict`** avec un champ `status` :

```python
# Succès
return {"status": "ok", "data": ...}

# Erreur
return {"status": "error", "message": "Description de l'erreur"}

# Cas spéciaux
return {"status": "created", ...}
return {"status": "deleted", ...}
return {"status": "already_exists", ...}
return {"status": "not_found", ...}
return {"status": "warning", "message": "..."}
```

> **Règle** : ne jamais lever d'exception dans un outil MCP.
> Toujours `try/except` et retourner `{"status": "error", "message": str(e)}`.

### 5.2 Nommage

| Couche                  | Convention        | Exemple                              |
| ----------------------- | ----------------- | ------------------------------------ |
| Outil MCP (server.py)   | `snake_case`      | `project_create`, `deploy_status`    |
| CLI Click (commands.py) | `kebab-case`      | `project create`, `deploy status`    |
| Shell (shell.py)        | `kebab-case`      | `create`, `deploy-status`            |
| Display (display.py)    | `show_xxx_result` | `show_deploy_result()`               |
| Handler shell           | `cmd_xxx`         | `cmd_deploy_status()`                |

### 5.3 Authentification

Pattern standard à mettre en première ligne de chaque outil :

```python
@mcp.tool()
async def mon_outil(resource_id: str, ...) -> dict:
    try:
        # 1. Vérifier l'accès (SI l'outil touche une ressource protégée)
        access_err = check_access(resource_id)
        if access_err:
            return access_err

        # 2. Vérifier permission write (SI l'outil modifie des données)
        write_err = check_write_permission()
        if write_err:
            return write_err

        # 3. Logique métier...
```

3 niveaux d'auth possibles :

| Niveau  | Quand                                  | Exemple                              |
| ------- | -------------------------------------- | ------------------------------------ |
| Aucun   | Outils publics                         | `system_health`, `system_about`      |
| Lecture  | Tout outil qui lit une ressource       | `project_list`, `deploy_status`      |
| Écriture | Tout outil qui modifie des données    | `project_create`, `deploy_rollback`  |

### 5.4 Lazy-loading des services

Ne **jamais** instancier un service au top-level du module.
Utiliser un getter singleton :

```python
# ❌ MAL — import au top level (bloque le démarrage si le service est down)
from .core.database import DatabaseService
db = DatabaseService()

# ✅ BIEN — lazy-load via getter singleton
_db_service = None

def get_db():
    global _db_service
    if _db_service is None:
        from .core.database import DatabaseService
        _db_service = DatabaseService()
    return _db_service

# Utilisation dans un outil :
result = await get_db().query(...)
```

### 5.5 Logs serveur

Toujours sur `stderr` (jamais `stdout` qui pollue le flux MCP) avec des emoji-préfixes :

```python
print(f"🔧 [MonOutil] Message de debug", file=sys.stderr)
sys.stderr.flush()
```

### 5.6 Progression temps réel (pour outils longs)

Si votre outil dure plus de quelques secondes :

```python
@mcp.tool()
async def mon_outil_long(
    param: str,
    ctx: Optional[Context] = None   # ← Ajouter ctx
) -> dict:
    async def _log(msg):
        print(f"📋 [MonOutil] {msg}", file=sys.stderr)
        if ctx:
            try:
                await ctx.info(msg)  # Notification MCP temps réel
            except Exception:
                pass

    await _log("Étape 1/3 : préparation...")
    # ... travail ...
    await _log("Étape 2/3 : traitement...")
    # ... travail ...
    await _log("Étape 3/3 : finalisation...")
```

Le client CLI peut écouter ces notifications pour afficher une progression
Rich en temps réel (voir les templates).

### 5.7 Bloquer l'event loop

Si un outil doit exécuter du code CPU-bound (pas d'I/O async) :

```python
import asyncio

loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, cpu_bound_function, args)
```

---

## 6. Checklist — Créer un serveur MCP from scratch

### Phase 1 : Fondation

- [ ] Créer la structure de fichiers (voir §4)
- [ ] `config.py` — Variables d'environnement (pydantic-settings)
- [ ] `server.py` — Instance FastMCP + premier outil (`system_health`)
- [ ] `client.py` — Client HTTP/SSE générique
- [ ] `commands.py` — Groupe Click principal + commande `health`
- [ ] `shell.py` — Boucle shell avec `prompt_toolkit`
- [ ] `display.py` — Fonctions `show_error()`, `show_success()`
- [ ] `Dockerfile` + `docker-compose.yml`
- [ ] `.env.example` + `requirements.txt`

### Phase 2 : Outils métier

Pour **chaque** outil métier, suivre le processus 4 fichiers :

- [ ] **server.py** — `@mcp.tool()` avec docstring, auth, try/except
- [ ] **display.py** — Fonction `show_xxx_result()` Rich
- [ ] **commands.py** — Commande Click (ou sous-commande d'un groupe)
- [ ] **shell.py** — Handler `cmd_xxx()` + dispatch + autocomplétion + aide

### Phase 3 : Infra

- [ ] Auth middleware (token Bearer)
- [ ] WAF / reverse proxy (Caddy + Coraza optionnel)
- [ ] TLS (Let's Encrypt ou reverse proxy amont)
- [ ] Rate limiting
- [ ] Déploiement Docker

---

## 7. Processus détaillé — Ajouter un outil

### Étape 1 : L'outil MCP dans `server.py`

```python
@mcp.tool()
async def mon_nouvel_outil(
    resource_id: str,
    param1: str,
    param2: Optional[int] = None
) -> dict:
    """
    Description courte (1 ligne).

    Description longue visible dans la doc MCP auto-générée.
    Expliquer le comportement, les cas limites, les effets de bord.

    Args:
        resource_id: ID de la ressource concernée
        param1: Description du paramètre
        param2: Description optionnelle (défaut: None)

    Returns:
        Données de résultat
    """
    try:
        # 1. Auth
        access_err = check_access(resource_id)
        if access_err:
            return access_err

        # 2. Logique métier
        result = await get_my_service().do_something(resource_id, param1)

        # 3. Retour standardisé
        return {
            "status": "ok",
            "resource_id": resource_id,
            "data": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Puis** : mettre à jour le banner dans `main()` de server.py.

### Étape 2 : L'affichage Rich dans `display.py`

```python
def show_mon_outil_result(result: dict):
    """Affiche le résultat de mon_nouvel_outil."""
    from rich.panel import Panel

    console.print(Panel.fit(
        f"[bold]Ressource:[/bold] [cyan]{result.get('resource_id', '?')}[/cyan]\n"
        f"[bold]Données:[/bold]   [green]{result.get('data', 'N/A')}[/green]",
        title="🔧 Mon outil",
        border_style="cyan",
    ))
```

### Étape 3 : La commande CLI Click dans `commands.py`

```python
@cli.command("mon-outil")
@click.argument("resource_id")
@click.option("--param1", required=True, help="Description")
@click.option("--param2", type=int, default=None, help="Optionnel")
@click.pass_context
def mon_outil_cmd(ctx, resource_id, param1, param2):
    """🔧 Description courte pour l'aide Click."""
    async def _run():
        try:
            client = MCPClient(ctx.obj["url"], ctx.obj["token"])
            params = {"resource_id": resource_id, "param1": param1}
            if param2 is not None:
                params["param2"] = param2

            result = await client.call_tool("mon_nouvel_outil", params)

            if result.get("status") == "ok":
                show_mon_outil_result(result)
            else:
                show_error(result.get("message", "Erreur"))
        except Exception as e:
            show_error(str(e))
    asyncio.run(_run())
```

### Étape 4 : Le handler Shell dans `shell.py`

**4a. Handler :**
```python
async def cmd_mon_outil(client: MCPClient, state: dict, args: str = "",
                         json_output: bool = False):
    """Description courte."""
    if not args:
        show_warning("Usage: mon-outil <param1>")
        return

    result = await client.call_tool("mon_nouvel_outil", {
        "resource_id": state.get("current_resource", ""),
        "param1": args.strip(),
    })

    if json_output:
        _json_dump(result)
        return

    if result.get("status") == "ok":
        show_mon_outil_result(result)
    else:
        show_error(result.get("message", "Erreur"))
```

**4b.** Ajouter `"mon-outil"` dans la liste `SHELL_COMMANDS`

**4c.** Ajouter le dispatch dans la boucle `if/elif` de `run_shell()` :
```python
elif command == "mon-outil":
    asyncio.run(cmd_mon_outil(client, state, args, json_output=json_output))
```

**4d.** Ajouter dans la table d'aide :
```python
"mon-outil <p>": "Description courte",
```

---

## 8. Pièges à éviter

| Piège                        | Conséquence                                           | Solution                                 |
| ---------------------------- | ----------------------------------------------------- | ---------------------------------------- |
| Oublier une couche           | L'outil existe côté serveur mais pas dans le shell    | Toujours les 4 fichiers                  |
| Dupliquer du code display    | Copier les tables Rich dans commands.py ET shell.py   | Centraliser dans display.py (DRY)        |
| Auth oubliée                 | Un outil expose des données sans contrôle             | `check_access()` systématiquement        |
| `stdout` au lieu de `stderr` | Les logs polluent le flux JSON MCP                    | Toujours `file=sys.stderr`               |
| Import circulaire            | Crash au démarrage                                    | Utiliser les getters lazy-load (§5.4)    |
| Bloquer l'event loop         | Le serveur freeze sur du CPU-bound                    | `await loop.run_in_executor(None, func)` |
| Oublier le banner            | L'outil n'apparaît pas dans les logs de démarrage     | Ajouter dans `main()` de server.py       |
| Shell sans autocomplétion    | L'utilisateur ne découvre pas la commande             | Ajouter dans `SHELL_COMMANDS`            |
| Exception non catchée        | Le client MCP reçoit une stacktrace au lieu d'un dict | `try/except` → `{"status": "error"}`     |
| Lever une exception          | Le protocole MCP ne gère pas les exceptions Python    | Toujours retourner un `dict`             |

---

## 9. Docker — Pattern type

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY VERSION .

# Sécurité : utilisateur non-root
RUN useradd -r -s /bin/false mcp
USER mcp

EXPOSE 8002

CMD ["python", "-m", "mon_service.server", "--host", "0.0.0.0", "--port", "8002"]
```

### docker-compose.yml (pattern)

```yaml
services:
  mon-mcp:
    build: .
    ports:
      - "8002:8002"
    env_file: .env
    restart: unless-stopped
    networks:
      - mcp-net

  # Ajouter vos services backend ici (base de données, cache, etc.)
  # Ils ne sont PAS exposés publiquement, seul mon-mcp est le point d'entrée.

networks:
  mcp-net:
    driver: bridge
```

---

## 10. Boilerplate — Projet complet prêt à démarrer

Le dossier [`boilerplate/`](boilerplate/) contient un **projet MCP complet et fonctionnel** :

```
boilerplate/
├── src/mon_service/
│   ├── __init__.py
│   ├── server.py           # FastMCP + system_health + system_about + main()
│   ├── config.py            # pydantic-settings
│   └── auth/
│       ├── __init__.py
│       ├── middleware.py     # Auth + Logging + HostNormalizer ASGI
│       └── context.py       # check_access, check_write_permission (contextvars)
├── scripts/
│   ├── mcp_cli.py           # Point d'entrée CLI
│   └── cli/
│       ├── __init__.py      # Config globale (MCP_URL, MCP_TOKEN)
│       ├── client.py        # Client HTTP/SSE complet
│       ├── commands.py      # CLI Click (health, about, shell)
│       ├── shell.py         # Shell interactif (prompt_toolkit)
│       └── display.py       # Affichage Rich partagé
├── waf/
│   ├── Dockerfile           # Caddy + Coraza WAF + Rate Limiting (xcaddy build)
│   └── Caddyfile            # Config WAF : routes SSE/messages/API, OWASP CRS
├── Dockerfile               # Python 3.11, utilisateur non-root
├── docker-compose.yml       # WAF (port 8080) → MCP (port 8002, interne)
├── requirements.txt         # Dépendances MCP + CLI + HTTP
├── .env.example             # Variables d'environnement documentées
├── VERSION                  # 0.1.0
└── README.md                # Guide de démarrage rapide
```

**Pour démarrer un nouveau projet MCP** :
1. Copier le dossier `boilerplate/` dans un nouveau repo
2. Renommer `mon_service` → votre nom de service
3. Adapter `config.py` avec vos variables d'environnement
4. Ajouter vos services métier dans `src/mon_service/core/`
5. Ajouter vos outils MCP dans `server.py`
6. Pour chaque outil : compléter display.py → commands.py → shell.py

---

## 11. Exemple de référence : graph-memory

Le projet [graph-memory](https://github.com/chrlesur/graph-memory) implémente
ce pattern avec ~28 outils MCP couvrant :

- Gestion de mémoires (namespaces isolés)
- Ingestion de documents (PDF, DOCX, MD, HTML, CSV)
- Recherche hybride (Knowledge Graph + RAG vectoriel)
- Q&A avec génération LLM
- Backup/restore complet (3 couches de données)
- Administration des tokens d'accès

C'est la **référence vivante** de ce starter-kit. Les fichiers clés :

| Rôle                  | Fichier dans graph-memory              |
| --------------------- | -------------------------------------- |
| Outils MCP            | `src/mcp_memory/server.py`             |
| CLI Click             | `scripts/cli/commands.py`              |
| Shell interactif      | `scripts/cli/shell.py`                 |
| Affichage Rich        | `scripts/cli/display.py`              |
| Client HTTP/SSE       | `scripts/cli/client.py`               |
| Config                | `src/mcp_memory/config.py`            |
| Auth middleware        | `src/mcp_memory/auth/middleware.py`    |
