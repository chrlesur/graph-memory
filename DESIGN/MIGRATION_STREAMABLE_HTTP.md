# Guide de Migration SSE → Streamable HTTP

> Ce document documente la migration effectuée sur Graph Memory et sert de guide
> pour reproduire la même migration sur **Live Memory** et tout autre serveur MCP.

## Contexte

Le protocole MCP a déprécié le transport HTTP+SSE (endpoints `/sse` + `/messages`)
dans la spec 2025-03-26 au profit de **Streamable HTTP** (endpoint unique `/mcp`).

- **Issue** : https://github.com/chrlesur/graph-memory/issues/1
- **Spec MCP** : Streamable HTTP remplace HTTP+SSE
- **SDK Python** : `mcp>=1.8.0` requis pour Streamable HTTP

## Résumé des changements (Graph Memory)

### 1. Côté Serveur

**Fichier** : `server.py` (point d'entrée)

```python
# AVANT (SSE)
from .auth.middleware import AuthMiddleware, LoggingMiddleware, StaticFilesMiddleware, HostNormalizerMiddleware

base_app = mcp.sse_app()
app = HostNormalizerMiddleware(base_app)  # Workaround Host header
app = StaticFilesMiddleware(app)
app = LoggingMiddleware(app, debug=args.debug)
app = AuthMiddleware(app, debug=args.debug)

# APRÈS (Streamable HTTP)
from .auth.middleware import AuthMiddleware, LoggingMiddleware, StaticFilesMiddleware

base_app = mcp.streamable_http_app()
# Plus de HostNormalizerMiddleware nécessaire !
app = StaticFilesMiddleware(base_app)
app = LoggingMiddleware(app, debug=args.debug)
app = AuthMiddleware(app, debug=args.debug)
```

**Points clés** :
- `mcp.sse_app()` → `mcp.streamable_http_app()`
- Le `HostNormalizerMiddleware` n'est plus nécessaire (Streamable HTTP n'a pas le problème de validation Host)
- Les `@mcp.tool()` ne changent PAS — seule la couche transport change
- L'instance `FastMCP()` reste identique

### 2. Côté Client

**Fichier** : `client.py` (communication avec le serveur)

```python
# AVANT (SSE)
from mcp.client.sse import sse_client

async with sse_client(
    f"{self.base_url}/sse",
    headers=headers,
    timeout=30,
    sse_read_timeout=900
) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool(tool_name, args)

# APRÈS (Streamable HTTP)
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client(
    f"{self.base_url}/mcp",
    headers=headers,
    timeout=30,
    sse_read_timeout=900
) as (read, write, _):  # ← 3ème élément (session info)
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool(tool_name, args)
```

**Points clés** :
- Import : `mcp.client.sse` → `mcp.client.streamable_http`
- Fonction : `sse_client` → `streamablehttp_client`
- URL : `/sse` → `/mcp`
- Context manager retourne un tuple de 3 (pas 2) : `(read, write, _)`
- Les paramètres `timeout` et `sse_read_timeout` sont supportés par les deux
- Le mécanisme de notifications (`_received_notification`) fonctionne à l'identique

### 3. Dépendances

**Fichier** : `requirements.txt`

```
# AVANT
mcp>=1.0.0

# APRÈS
mcp>=1.8.0
```

### 4. WAF / Reverse Proxy (Caddy)

**Fichier** : `waf/Caddyfile`

```caddy
# AVANT (2 routes SSE)
handle /sse* {
    reverse_proxy backend:8002 {
        flush_interval -1
        transport http { read_timeout 0; write_timeout 0 }
    }
}
handle /messages/* {
    reverse_proxy backend:8002 {
        transport http { read_timeout 1800s; write_timeout 1800s }
    }
}

# APRÈS (1 route Streamable HTTP)
handle /mcp* {
    reverse_proxy backend:8002 {
        flush_interval -1
        transport http {
            read_timeout 1800s
            write_timeout 1800s
            response_header_timeout 1800s
        }
    }
}
```

**Points clés** :
- 2 routes → 1 route unique `/mcp*`
- `flush_interval -1` toujours nécessaire (SSE optionnel en downstream)
- Timeouts longs conservés (ingestion LLM peut prendre 15-30 min)

### 5. Rate Limiting

**ATTENTION** : Streamable HTTP utilise **3 requêtes HTTP par appel d'outil** :
1. `POST /mcp` — Initialize session
2. `POST /mcp` — Call tool
3. `DELETE /mcp` — Close session

L'ancien rate limiting SSE (10 connexions/min + 60 messages/min) doit être
recalibré. Pour supporter 60 appels d'outils/min → 180 HTTP requests/min minimum.

```
# Recommandation
zone mcp: 200 events/min
zone global: 500 events/min
```

### 6. Dockerfile

```dockerfile
# AVANT
HEALTHCHECK CMD curl -sf http://localhost:8002/sse --max-time 2 -o /dev/null

# APRÈS
HEALTHCHECK CMD curl -sf http://localhost:8002/health -o /dev/null
```

### 7. Middleware `HostNormalizerMiddleware`

**Peut être supprimé**. Ce middleware normalisait le Host header pour contourner
la protection DNS rebinding de Starlette (HTTP 421). Streamable HTTP n'utilise
plus Starlette pour le routage → le problème n'existe plus.

### 8. Configuration client (Claude Desktop, Cline)

```json
{
  "mcpServers": {
    "graph-memory": {
      "url": "http://localhost:8080/mcp",
      "headers": { "Authorization": "Bearer TOKEN" }
    }
  }
}
```

## Checklist de migration

- [ ] Mettre à jour `requirements.txt` : `mcp>=1.8.0`
- [ ] Serveur : `sse_app()` → `streamable_http_app()`
- [ ] Serveur : supprimer `HostNormalizerMiddleware` de la pile de middlewares
- [ ] Client : `sse_client` → `streamablehttp_client`, `/sse` → `/mcp`
- [ ] Client : context manager `(read, write)` → `(read, write, _)`
- [ ] WAF : fusionner routes `/sse*` + `/messages/*` → `/mcp*`
- [ ] WAF : ajuster rate limiting (×3 pour Streamable HTTP)
- [ ] Dockerfile : healthcheck `/sse` → `/health`
- [ ] README : mettre à jour les exemples d'intégration
- [ ] Tester : `system_health`, ingestion, recherche, backup, tokens

## Pièges identifiés

1. **Rate limiting trop bas** → 429 après ~20 appels d'outils. Chaque appel = 3 HTTP requests.
2. **Healthcheck /sse qui 404** → Le serveur semble down mais tourne bien. Changer en /health.
3. **VERSION non copiée dans Docker** → /health retourne "unknown" au lieu de la version.
4. **`httpx-sse` n'est plus nécessaire** côté client (le SDK MCP gère le SSE en interne).
5. **Notifications de progression** fonctionnent toujours via `_received_notification` — pas de changement.

## Validation

Script de test : `scripts/test_streamable_http.py`

```bash
# Prérequis
python3 -m venv .venv
source .venv/bin/activate
pip install httpx mcp

# Lancer
python3 scripts/test_streamable_http.py      # 27 tests
python3 scripts/test_streamable_http.py -v   # verbose
```

Résultat attendu : **27/27 PASS, 0 FAIL, ~10s**
