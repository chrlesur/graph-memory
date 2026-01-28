# 🧠 MCP Memory Service

Service de mémoire persistante basé sur un graphe de connaissances pour les agents IA, implémenté avec le protocole **MCP (Model Context Protocol)**.

## 🎯 Concept

L'approche **Graph-First** : au lieu d'utiliser du RAG vectoriel classique, ce service extrait des entités et relations structurées pour construire un graphe de connaissances interrogeable.

```
Document → LLM Extraction → Entités + Relations → Neo4j Graph
                                                     ↓
Query → Graph Search → Contexte structuré → Réponse précise
```

## ✨ Fonctionnalités

- **Extraction intelligente** via LLMaaS Cloud Temple (gpt-oss:120b)
- **Stockage S3** sur Dell ECS Cloud Temple
- **Graphe Neo4j** pour les entités et relations
- **API MCP** via HTTP/SSE avec authentification Bearer
- **Multi-tenant** : isolation par mémoire (namespace)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Memory Service                        │
│                    (localhost:8002)                          │
├─────────────────────────────────────────────────────────────┤
│  FastMCP Server + Auth Middleware                           │
│  ├── memory_create/delete/list/stats                        │
│  ├── memory_ingest (S3 + LLM + Neo4j)                       │
│  ├── memory_search (graph-first)                            │
│  └── memory_get_context                                     │
├─────────────────────────────────────────────────────────────┤
│                    Services Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   S3 Dell   │  │  LLMaaS CT  │  │   Neo4j     │         │
│  │    ECS      │  │ gpt-oss:120b│  │   5.x       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Démarrage Rapide

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Clés API Cloud Temple (S3 + LLMaaS)

### Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer avec vos clés
nano .env
```

Variables requises :
```bash
# S3 Cloud Temple
S3_ACCESS_KEY_ID=votre_access_key
S3_SECRET_ACCESS_KEY=votre_secret_key

# LLMaaS Cloud Temple
LLMAAS_API_KEY=votre_api_key

# Neo4j
NEO4J_PASSWORD=votre_password

# Auth
ADMIN_BOOTSTRAP_KEY=votre_clé_admin
```

### Lancement

```bash
# Démarrer les services
docker compose up -d

# Vérifier le statut
docker compose ps

# Voir les logs
docker compose logs mcp-memory --tail 50
```

## 🧪 Tests

```bash
# Test de santé (connexions services)
python scripts/test_health.py

# Test workflow complet (ingestion + recherche)
python scripts/test_memory_workflow.py --token admin_bootstrap_key_change_me

# Test qualité Q/R (5 questions sur un contrat)
python scripts/test_graph_qa.py
```

### Résultats Attendus

- **test_memory_workflow.py** : 7/7 tests OK
- **test_graph_qa.py** : 5/5 = 100% de réussite

## 📚 Outils MCP Disponibles

| Outil | Description |
|-------|-------------|
| `memory_create` | Crée une nouvelle mémoire (namespace) |
| `memory_delete` | Supprime une mémoire |
| `memory_list` | Liste les mémoires disponibles |
| `memory_stats` | Statistiques (docs, entités, relations) |
| `memory_ingest` | Ingère un document (S3 + extraction + graphe) |
| `memory_search` | Recherche dans le graphe |
| `memory_get_context` | Contexte complet d'une entité |
| `admin_create_token` | Crée un token d'accès |
| `admin_list_tokens` | Liste les tokens |
| `admin_revoke_token` | Révoque un token |
| `system_health` | État de santé des services |

## 📁 Structure du Projet

```
graph-memory/
├── src/mcp_memory/
│   ├── server.py           # Serveur MCP principal
│   ├── config.py           # Configuration centralisée
│   ├── core/
│   │   ├── extractor.py    # Extraction LLM
│   │   ├── graph.py        # Service Neo4j
│   │   ├── storage.py      # Service S3
│   │   └── models.py       # Modèles de données
│   └── auth/
│       ├── middleware.py   # Auth Bearer Token
│       └── token_manager.py
├── scripts/
│   ├── test_health.py
│   ├── test_auth.py
│   ├── test_s3.py
│   ├── test_memory_workflow.py
│   └── test_graph_qa.py
├── memory-bank/            # Documentation projet
├── DESIGN/                 # Specs techniques
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## ⚙️ Configuration Avancée

### Limite de Tokens LLM

Le modèle `gpt-oss:120b` fait du "chain-of-thought reasoning" qui consomme beaucoup de tokens. Configuration recommandée :

```python
# config.py
llmaas_max_tokens: int = 60000  # IMPORTANT
```

### Timeouts

```python
extraction_timeout_seconds: int = 120
s3_upload_timeout_seconds: int = 60
neo4j_query_timeout_seconds: int = 30
```

## 🔒 Sécurité

- **Authentification** : Bearer Token requis pour toutes les requêtes
- **Bootstrap** : Clé admin pour créer le premier token
- **Isolation** : Chaque mémoire est un namespace séparé

## 📈 Exemple d'Utilisation

### Via Python (client MCP)

```python
from mcp.client.sse import sse_client
from mcp import ClientSession
import base64

async def exemple():
    headers = {"Authorization": "Bearer votre_token"}
    
    async with sse_client("http://localhost:8002/sse", headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Créer une mémoire
            await session.call_tool("memory_create", {
                "memory_id": "ma-memoire",
                "name": "Ma Mémoire",
                "description": "Test"
            })
            
            # Ingérer un document
            content = base64.b64encode(b"Contenu du document...").decode()
            await session.call_tool("memory_ingest", {
                "memory_id": "ma-memoire",
                "content_base64": content,
                "filename": "document.txt"
            })
            
            # Rechercher
            result = await session.call_tool("memory_search", {
                "memory_id": "ma-memoire",
                "query": "ma recherche"
            })
```

## 🤝 Intégration

Ce service est conçu pour s'intégrer avec :
- **QuoteFlow** : Mémoire des documents juridiques
- **Agents IA** : Contexte persistant entre sessions
- **Applications métier** : Base de connaissances structurée

## 📄 Licence

Projet interne Cloud Temple.

---

**Développé par Cloud Temple** | [Documentation technique](DESIGN/)
