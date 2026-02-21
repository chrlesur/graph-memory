# Cahier de Spécification Technique — Graph Memory

> **Version** : 1.3.7 | **Date** : 21 février 2026
> **Auteur** : Christophe Lesur & Cloud Temple
> **Repository** : https://github.com/chrlesur/graph-memory

---

## Table des matières

1. [Vision & Objectifs](#1-vision--objectifs)
2. [Architecture](#2-architecture)
3. [Modèle de données](#3-modèle-de-données)
4. [Outils MCP](#4-outils-mcp--28-outils)
5. [Pipeline d'ingestion](#5-pipeline-dingestion)
6. [Pipeline de recherche & Q&A](#6-pipeline-de-recherche--qa)
7. [Système d'ontologies](#7-système-dontologies)
8. [Authentification & Sécurité](#8-authentification--sécurité)
9. [Backup & Restore](#9-backup--restore)
10. [Interface Web](#10-interface-web)
11. [CLI — Command Line Interface](#11-cli--command-line-interface)
12. [Intégration Live Memory](#12-intégration-live-memory)
13. [Configuration](#13-configuration)
14. [Déploiement](#14-déploiement)
15. [Structure du projet](#15-structure-du-projet)
16. [Évolutions futures](#16-évolutions-futures)

---

## 1. Vision & Objectifs

### 1.1 Le problème

Les systèmes RAG (Retrieval-Augmented Generation) traditionnels souffrent de limitations fondamentales :

| Limitation          | RAG vectoriel classique                            | Graph Memory                                    |
| ------------------- | -------------------------------------------------- | ----------------------------------------------- |
| **Structure**       | Perte des relations entre concepts (chunks isolés) | Relations explicites et typées entre entités    |
| **Précision**       | Similitude cosinus approximative                   | Requêtes Cypher précises sur le graphe          |
| **Traçabilité**     | Chunks anonymes                                    | Entités nommées liées à leurs documents sources |
| **Multi-documents** | Mélange de chunks hétérogènes                      | Relations inter-documents explicites            |
| **Exploration**     | Recherche unidirectionnelle                        | Navigation multi-hop dans le graphe             |
| **Visualisation**   | Difficile                                          | Graphe interactif natif                         |

### 1.2 La solution : Knowledge Graph as a Service

**Graph Memory** est un service de mémoire à long terme pour agents IA, exposé via le protocole **MCP (Model Context Protocol)** sur HTTP/SSE. Il extrait des **entités** et **relations** structurées via un LLM, guidé par des **ontologies** métier, pour construire un graphe de connaissances interrogeable en langage naturel.

### 1.3 Objectifs principaux

1. **Multi-tenant** — Chaque mémoire est un namespace isolé dans Neo4j (pas de fuite de données)
2. **Knowledge Graph First** — Neo4j comme source primaire, RAG vectoriel (Qdrant) en complément
3. **Ontologie-Driven** — L'extraction est guidée par des ontologies YAML métier (legal, cloud, presales…)
4. **Auto-maintenance** — Déduplication par hash, fusion d'entités, rétention de backups
5. **API MCP Standard** — Compatible avec tout client MCP (Claude Desktop, Cline, agents custom)
6. **Sécurité** — WAF OWASP CRS, tokens Bearer, contrôle d'accès par mémoire, rate limiting

### 1.4 Critères de succès

1. Un agent IA peut créer une mémoire, ingérer des documents, et poser des questions en langage naturel
2. Les entités et relations sont correctement extraites selon l'ontologie choisie
3. La recherche Graph-Guided RAG est plus précise que le RAG vectoriel seul
4. Plusieurs clients avec des tokens différents accèdent à leurs mémoires respectives sans interférence
5. Le cycle backup → suppression → restore fonctionne intégralement (Neo4j + Qdrant + S3)

### 1.5 Périmètre

**Inclus (v1.3.7)** :
- Serveur MCP HTTP/SSE (28 outils)
- 5 ontologies (legal, cloud, managed-services, presales, general)
- Interface web interactive (graphe vis-network, panneau Q&A)
- CLI complète (Click scriptable + Shell interactif)
- Backup/Restore 3 couches (Neo4j + Qdrant + S3)
- WAF Coraza avec rate limiting
- Intégration native avec Live Memory

**Exclus (v2)** :
- Clustering Neo4j
- Webhooks de notification
- API GraphQL
- Dashboard de monitoring avancé

### 1.6 Fondements théoriques — Positionnement dans les systèmes multi-agents

Graph Memory s'inscrit dans le cadre des **systèmes multi-agents à base de LLM** (LLM-based MAS) tels que formalisés par Tran et al. (2025) dans *"Multi-Agent Collaboration Mechanisms: A Survey of LLMs"* (arXiv:2501.06322).

#### 1.6.1 Graph Memory comme environnement partagé (E)

Dans le framework MAS, chaque agent est défini par `a = {m, o, e, x, y}` où `e` est l'environnement partagé. Le papier identifie explicitement les **bases de données vectorielles** et les **interfaces de messagerie** comme formes d'environnement partagé (§3.1).

Graph Memory joue ce rôle d'**environnement partagé E** pour les agents IA :
- **Neo4j** = base de connaissances structurée (entités, relations, documents)
- **Qdrant** = base vectorielle pour le RAG
- **S3** = stockage pérenne des documents originaux
- **MCP SSE** = interface de messagerie standardisée

Les agents (Cline, Claude Desktop, QuoteFlow, Vela) accèdent à cet environnement via le protocole MCP, conformément à la définition formelle : `y = m(o, E, x)`.

#### 1.6.2 Collaboration coopérative avec spécialisation par rôle

L'intégration Live Memory + Graph Memory implémente une **collaboration coopérative** (§4.2.1 du papier) où les agents alignent leurs objectifs individuels vers un but partagé : `O_collab = ∪ o_i`.

La stratégie est **role-based** (§4.3.2) avec division du travail :
- **Live Memory** = agent de mémoire de travail (notes, consolidation LLM)
- **Graph Memory** = agent de mémoire long terme (extraction, structuration, Q&A)
- **Agents IA** (Cline, etc.) = agents de tâche qui consomment et alimentent la mémoire

Le papier montre que cette approche role-based améliore l'efficacité en évitant les chevauchements et en permettant la modularité (MetaGPT, AgentVerse).

#### 1.6.3 Mémoire comme composant fondamental

Le papier identifie la **mémorisation des connaissances** comme un bénéfice transformatif des MAS (§1.1) :

> *"MASs excel in knowledge memorization, enabling distributed agents to retain and share diverse knowledge bases without overloading a single system."*

Graph Memory matérialise ce principe en offrant :
- **Knowledge memorization** : extraction et structuration permanente des connaissances dans un graphe
- **Long-term planning** : les connaissances persistent entre les sessions, permettant la planification sur le long terme
- **Effective generalization** : le Q&A Graph-Guided RAG permet de répondre à des questions transverses combinant plusieurs documents

#### 1.6.4 Canaux de collaboration et stades d'interaction

Le framework de Tran et al. distingue 3 stades de collaboration :

| Stade           | Description                                 | Implémentation Graph Memory                     |
| --------------- | ------------------------------------------- | ----------------------------------------------- |
| **Early-stage** | Partage de données, contexte, environnement | Documents ingérés dans S3, ontologies partagées |
| **Mid-stage**   | Échange de paramètres ou modèles            | Non applicable (pas de fine-tuning fédéré)      |
| **Late-stage**  | Agrégation d'outputs/actions                | Q&A = graphe + RAG fusionnés → réponse LLM      |

Le canal de collaboration `graph_push` entre Live Memory et Graph Memory est un canal coopératif de type **early-stage** (partage de données) avec une structure **centralisée** (Graph Memory = hub de connaissances).

#### 1.6.5 Défis identifiés par le papier et réponses de Graph Memory

| Défi MAS (Tran et al.)        | Réponse Graph Memory                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| **Hallucinations en cascade** | Extraction guidée par ontologie (types stricts), normalisation, "Other" tracking         |
| **Scalabilité**               | Multi-tenancy par namespace, isolation des mémoires                                      |
| **Gouvernance unifiée**       | Tokens avec permissions et contrôle d'accès par mémoire                                  |
| **Évaluation**                | `memory_query` retourne les données brutes pour audit, `storage_check` pour la cohérence |
| **Sécurité**                  | WAF OWASP CRS, rate limiting, validation backup_id, contrôle write                       |

## 2. Architecture

### 2.1 Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Clients MCP                                  │
│   (Claude Desktop, Cline, QuoteFlow, Vela, CLI, Interface Web)       │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP/SSE + Bearer Token
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Coraza WAF (Port 8080 — seul port exposé)               │
│  OWASP CRS · Rate Limiting · CSP · HSTS · Let's Encrypt (prod)       │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ réseau Docker interne (mcp-network)
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Graph Memory Service (Port 8002 interne)          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Middleware Layer (ASGI)                                       │  │
│  │  AuthMiddleware → LoggingMiddleware → StaticFilesMiddleware    │  │
│  │  → HostNormalizerMiddleware → mcp.sse_app()                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  MCP Tools Layer (28 outils)                                   │  │
│  │  • Memory CRUD (5)    • Documents (4)   • Recherche/Q&A (4)    │  │
│  │  • Ontologies (1)     • Storage S3 (2)  • Admin tokens (4)     │  │
│  │  • Backup/Restore (6) • System (2)                             │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Core Services                                                 │  │
│  │  • GraphService (Neo4j)       • StorageService (S3 boto3)      │  │
│  │  • ExtractorService (LLM)     • OntologyService (YAML)         │  │
│  │  • EmbeddingService (BGE-M3)  • VectorStoreService (Qdrant)    │  │
│  │  • SemanticChunker            • BackupService                  │  │
│  │  • TokenManager               • Models (Pydantic)              │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
        ┌────────────┬─────────┼─────────┬────────────┐
        ▼            ▼         ▼         ▼            ▼
┌───────────┐ ┌───────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│  Neo4j 5  │ │ S3 Cloud  │ │LLMaaS│ │ Qdrant  │ │Embedding │
│ Community │ │ Temple    │ │gpt-  │ │ v1.16.2 │ │BGE-M3    │
│ (graphe)  │ │ Dell ECS  │ │oss:  │ │(vecteur)│ │567m via  │
│ (interne) │ │           │ │120b  │ │(interne)│ │LLMaaS    │
└───────────┘ └───────────┘ └──────┘ └─────────┘ └──────────┘
```

### 2.2 Stack technique

| Composant       | Technologie                   | Version               |
| --------------- | ----------------------------- | --------------------- |
| Runtime         | Python                        | 3.11+                 |
| MCP SDK         | `mcp` (FastMCP)               | ≥ 1.0.0               |
| Web Framework   | FastAPI + Starlette           | ≥ 0.100.0             |
| ASGI Server     | Uvicorn                       | ≥ 0.20.0              |
| Graph Database  | Neo4j Community               | 5.x                   |
| Vector Database | Qdrant                        | v1.16.2 (épinglé)     |
| Object Storage  | S3 (Dell ECS / AWS)           | boto3 ≥ 1.28.0        |
| LLM             | gpt-oss:120b via LLMaaS       | API compatible OpenAI |
| Embedding       | BGE-M3 (bge-m3:567m)          | 1024 dimensions       |
| WAF             | Coraza + Caddy                | OWASP CRS             |
| Configuration   | pydantic-settings             | ≥ 2.0.0               |
| CLI             | Click + prompt_toolkit + Rich | —                     |

### 2.3 Services externes

#### S3 Cloud Temple (Dell ECS)
- **Endpoint** : `https://takinc5acc.s3.fr1.cloud-temple.com`
- **Bucket** : `quoteflow-memory`
- **Usage** : Documents originaux, ontologies, backups, health checks
- **Préfixes réservés** : `_backups/`, `_health_check/`, `_ontology_*`

#### LLMaaS Cloud Temple
- **Endpoint** : `https://api.ai.cloud-temple.com`
- **Modèle extraction** : `gpt-oss:120b` (chain-of-thought, 120K tokens contexte)
- **Modèle embedding** : `bge-m3:567m` (1024 dimensions, scoring cosinus)
- **Format** : API compatible OpenAI (`/v1/chat/completions`, `/v1/embeddings`)

### 2.4 Réseau Docker

```yaml
services:
  waf:          # Port 8080 exposé (seul point d'entrée)
  mcp-memory:   # Port 8002 interne uniquement
  neo4j:        # Ports 7474/7687 internes uniquement
  qdrant:       # Port 6333 interne uniquement

networks:
  mcp-network:  # Bridge isolé, tous les services connectés
```

**Principe** : seul le WAF est exposé. Neo4j, Qdrant et le service MCP ne sont accessibles que via le réseau Docker interne. Le container MCP tourne en utilisateur non-root (`USER mcp`).

### 2.5 Pile de middlewares ASGI

L'ordre d'exécution est critique :

```
Requête entrante
  │
  ▼ AuthMiddleware        — Vérifie Bearer Token, injecte current_auth
  ▼ LoggingMiddleware     — Log requêtes (si debug=true)
  ▼ StaticFilesMiddleware — Sert /graph, /static/*, /api/* (routes web)
  ▼ HostNormalizerMiddleware — Normalise Host header (reverse proxy)
  ▼ mcp.sse_app()         — Routes MCP: /sse, /messages/*
```

Les routes `/api/*` sont interceptées par `StaticFilesMiddleware` avant d'atteindre le SDK MCP. Les routes `/sse` et `/messages/*` traversent toute la pile jusqu'au MCP SDK (Starlette).

## 3. Modèle de données

### 3.1 Multi-Tenancy par Namespace Neo4j

Chaque mémoire (`memory_id`) crée un namespace isolé via des **labels préfixés** dans Neo4j. Aucun nœud n'est partagé entre mémoires.

```cypher
-- Mémoire "JURIDIQUE"
(:JURIDIQUE_Memory {id: "JURIDIQUE", name: "Corpus Juridique", ontology: "legal"})
(:JURIDIQUE_Document {uri: "s3://...", filename: "CGA.docx", hash: "abc123..."})
(:JURIDIQUE_Entity {name: "Cloud Temple SAS", type: "Organization"})

-- Mémoire "CLOUD"
(:CLOUD_Memory {id: "CLOUD", name: "Documentation Cloud", ontology: "cloud"})
(:CLOUD_Document {uri: "s3://...", filename: "iaas-vmware.md"})
(:CLOUD_Entity {name: "VMware vSphere", type: "Technology"})
```

### 3.2 Nœuds Neo4j

| Label           | Propriétés                                                                                                                             | Description                             |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `{ns}_Memory`   | `id`, `name`, `description`, `ontology`, `created_at`                                                                                  | Métadonnées de la mémoire               |
| `{ns}_Document` | `uri`, `filename`, `hash`, `ingested_at`, `metadata`, `source_path`, `source_modified_at`, `size_bytes`, `text_length`, `content_type` | Document source + métadonnées enrichies |
| `{ns}_Entity`   | `name`, `type`, `description`, `mention_count`, `source_docs`                                                                          | Entité extraite par le LLM              |
| `{ns}_Chunk`    | `text`, `index`, `embedding`                                                                                                           | Fragment textuel (pour RAG vectoriel)   |

### 3.3 Relations Neo4j

| Type         | From → To          | Propriétés                      | Description                   |
| ------------ | ------------------ | ------------------------------- | ----------------------------- |
| `CONTAINS`   | Document → Chunk   | `index`                         | Document contient un chunk    |
| `MENTIONS`   | Document → Entity  | `count`, `context`              | Document mentionne une entité |
| `DEFINES`    | Document → Concept | —                               | Document définit un concept   |
| `RELATED_TO` | Entity → Entity    | `type`, `weight`, `description` | Relation sémantique typée     |

> **Note** : Le type de relation `RELATED_TO` porte une propriété `type` qui contient le vrai type sémantique défini par l'ontologie (ex: `HAS_CERTIFICATION`, `COMPLIANT_WITH`, `IMPOSES`). Avec une bonne ontologie, aucun `RELATED_TO` générique ne devrait apparaître.

### 3.4 Index et contraintes Neo4j

```cypher
-- Index fulltext accent-insensitive (Lucene standard-folding)
CREATE FULLTEXT INDEX entity_fulltext FOR (e:Entity) ON EACH [e.name]
OPTIONS {indexConfig: {`fulltext.analyzer`: 'standard-folding'}}

-- Recherche : "réversibilité", "reversibilite", "REVERSIBILITE" matchent tous
```

### 3.5 Collections Qdrant

Chaque mémoire a sa propre collection Qdrant :
- **Nom** : `memory_{MEMORY_ID}` (ex: `memory_JURIDIQUE`)
- **Dimensions** : 1024 (BGE-M3)
- **Distance** : Cosinus
- **Payload** : `doc_id`, `chunk_index`, `text`, `filename`
- **Scores typiques BGE-M3** : ~0.55-0.63 pour les meilleurs chunks
- **Seuil de pertinence** : `RAG_SCORE_THRESHOLD=0.58` (en dessous = ignoré)

### 3.6 Stockage S3

```
{bucket}/
├── {memory_id}/
│   ├── {filename}                    # Documents originaux
│   └── ...
├── _ontology_{memory_id}.yaml        # Ontologie copiée à la création
├── _backups/
│   └── {memory_id}/
│       └── {timestamp}/
│           ├── manifest.json         # Métadonnées du backup
│           ├── graph_data.json       # Export Neo4j complet
│           ├── qdrant_vectors.jsonl  # Export Qdrant complet
│           └── document_keys.json    # Liste des clés S3
└── _health_check/                    # Fichier de test connectivité
```

## 4. Outils MCP — 28 outils

### 4.1 Gestion des mémoires (5 outils)

| Outil           | Paramètres                                      | Auth      | Description                                                 |
| --------------- | ----------------------------------------------- | --------- | ----------------------------------------------------------- |
| `memory_create` | `memory_id`, `name`, `ontology`, `description?` | 🔑 write | Crée une mémoire avec ontologie obligatoire (copiée sur S3) |
| `memory_delete` | `memory_id`                                     | 🔑 write | Supprime tout : Neo4j + Qdrant + S3 (cascade)               |
| `memory_list`   | —                                               | 🔑 read  | Liste les mémoires accessibles au token                     |
| `memory_stats`  | `memory_id`                                     | 🔑 read  | Stats : docs, entités, relations, types                     |
| `memory_graph`  | `memory_id`, `format?`                          | 🔑 read  | Graphe complet (nœuds, arêtes, documents)                   |

### 4.2 Documents (4 outils)

| Outil             | Paramètres                                                                                              | Auth      | Description                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------- |
| `memory_ingest`   | `memory_id`, `content_base64`, `filename`, `metadata?`, `force?`, `source_path?`, `source_modified_at?` | 🔑 write | Ingère un document : S3 + LLM extraction + Neo4j + Qdrant      |
| `document_list`   | `memory_id`                                                                                             | 🔑 read  | Liste les documents avec métadonnées                           |
| `document_get`    | `memory_id`, `filename`, `include_content?`                                                             | 🔑 read  | Métadonnées (+ contenu S3 si `include_content=true`)           |
| `document_delete` | `memory_id`, `document_id`                                                                              | 🔑 write | Supprime doc + entités orphelines + chunks Qdrant + fichier S3 |

### 4.3 Recherche et Q&A (4 outils)

| Outil                | Paramètres                        | Auth     | Description                                                 |
| -------------------- | --------------------------------- | -------- | ----------------------------------------------------------- |
| `memory_search`      | `memory_id`, `query`, `limit?`    | 🔑 read | Recherche d'entités dans le graphe (fulltext)               |
| `memory_get_context` | `memory_id`, `entity_name`        | 🔑 read | Contexte complet d'une entité (voisins, docs, relations)    |
| `question_answer`    | `memory_id`, `question`, `limit?` | 🔑 read | Question LN → réponse LLM avec Graph-Guided RAG + citations |
| `memory_query`       | `memory_id`, `query`, `limit?`    | 🔑 read | Données structurées brutes sans LLM (pour agents IA)        |

**Différence `question_answer` vs `memory_query`** :
- `question_answer` : appelle le LLM pour générer une réponse en langage naturel avec citations
- `memory_query` : même pipeline de recherche (graphe + RAG) mais retourne les données brutes (entités enrichies, chunks RAG avec scores, documents sources) — idéal pour les agents qui construisent leur propre réponse

### 4.4 Ontologies (1 outil)

| Outil           | Paramètres | Auth     | Description                                 |
| --------------- | ---------- | -------- | ------------------------------------------- |
| `ontology_list` | —          | 🔑 read | Liste les ontologies disponibles avec stats |

### 4.5 Stockage S3 (2 outils)

| Outil             | Paramètres   | Auth      | Description                                              |
| ----------------- | ------------ | --------- | -------------------------------------------------------- |
| `storage_check`   | `memory_id?` | 🔑 read  | Vérifie cohérence graphe ↔ S3 (accessibilité, orphelins) |
| `storage_cleanup` | `dry_run?`   | 🔑 write | Nettoie les fichiers S3 orphelins                        |

### 4.6 Administration tokens (4 outils)

| Outil                | Paramètres                                                                 | Auth      | Description                                             |
| -------------------- | -------------------------------------------------------------------------- | --------- | ------------------------------------------------------- |
| `admin_create_token` | `client_name`, `permissions?`, `memory_ids?`, `expires_in_days?`, `email?` | 👑 admin | Crée un token Bearer (affiché une seule fois !)         |
| `admin_list_tokens`  | —                                                                          | 👑 admin | Liste les tokens (métadonnées, pas les tokens en clair) |
| `admin_revoke_token` | `token_hash_prefix`                                                        | 👑 admin | Révoque un token par préfixe de hash                    |
| `admin_update_token` | `token_hash_prefix`, `add_memories?`, `remove_memories?`, `set_memories?`  | 👑 admin | Modifie les mémoires autorisées (add/remove/set)        |

### 4.7 Backup & Restore (6 outils)

| Outil                    | Paramètres                        | Auth      | Description                                             |
| ------------------------ | --------------------------------- | --------- | ------------------------------------------------------- |
| `backup_create`          | `memory_id`, `description?`       | 🔑 write | Backup complet sur S3 (Neo4j + Qdrant + manifest)       |
| `backup_list`            | `memory_id?`                      | 🔑 read  | Liste les backups avec statistiques                     |
| `backup_restore`         | `backup_id`                       | 🔑 write | Restaure depuis S3 (mémoire ne doit pas exister)        |
| `backup_download`        | `backup_id`, `include_documents?` | 🔑 read  | Archive tar.gz en base64 (+ docs originaux optionnels)  |
| `backup_delete`          | `backup_id`                       | 🔑 write | Supprime un backup de S3                                |
| `backup_restore_archive` | `archive_base64`                  | 🔑 write | Restaure depuis tar.gz local (re-upload S3 + checksums) |

### 4.8 Système (2 outils)

| Outil           | Paramètres | Auth | Description                                                         |
| --------------- | ---------- | ---- | ------------------------------------------------------------------- |
| `system_health` | —          | —    | État de santé des 5 services (Neo4j, S3, LLMaaS, Qdrant, Embedding) |
| `system_about`  | —          | —    | Carte d'identité complète (version, capacités, mémoires, config)    |

### 4.9 Légende des permissions

| Icône     | Permission           | Description                                        |
| --------- | -------------------- | -------------------------------------------------- |
| —         | Aucune               | Accès public (health, about)                       |
| 🔑 read  | `read`               | Token avec permission `read` + accès à la mémoire  |
| 🔑 write | `write`              | Token avec permission `write` + accès à la mémoire |
| 👑 admin | `admin` ou bootstrap | Token admin ou clé bootstrap uniquement            |

## 5. Pipeline d'ingestion

### 5.1 Vue d'ensemble

```
Document (PDF, DOCX, MD, TXT, HTML, CSV)
    │
    ├──▶ 1. Upload S3 (stockage pérenne, hash SHA-256)
    │
    ├──▶ 2. Extraction texte (selon format)
    │
    ├──▶ 3. Extraction LLM guidée par ontologie
    │    └── Chunked si > 25K chars (séquentiel avec contexte cumulatif)
    │    └──▶ Entités + Relations typées → MERGE Neo4j
    │
    └──▶ 4. Chunking sémantique + Embedding BGE-M3
         └──▶ Vecteurs 1024d → Qdrant
```

### 5.2 Étape 1 — Upload S3 et déduplication

1. Le document est encodé en base64 par le client
2. Calcul du hash SHA-256 sur le contenu décodé
3. Vérification de déduplication : si un document avec le même hash existe et `force=False`, retour `already_exists`
4. Si `force=True`, suppression de l'ancien document (cascade Neo4j + Qdrant + S3) avant ré-ingestion
5. Upload sur S3 : `{memory_id}/{filename}`
6. **Libération mémoire** : `del content_base64` + `del content` + `gc.collect()` (protection OOM)

### 5.3 Étape 2 — Extraction texte

| Format        | Méthode                                           |
| ------------- | ------------------------------------------------- |
| `.txt`, `.md` | Lecture directe UTF-8                             |
| `.html`       | Stripping des balises                             |
| `.csv`        | Conversion en texte tabulaire                     |
| `.pdf`        | Extraction via PyPDF2 / pdfplumber                |
| `.docx`       | Extraction via python-docx (paragraphes + tables) |

### 5.4 Étape 3 — Extraction LLM (ontologie-driven)

#### Chunking d'extraction (gros documents)

Si le texte dépasse `EXTRACTION_CHUNK_SIZE` (défaut: 25K chars ≈ 6K tokens) :
1. Découpe aux frontières de sections (double saut de ligne), jamais mid-paragraphe
2. Chaque chunk reçoit la liste compacte des entités/relations des chunks précédents (contexte cumulatif)
3. Fusion finale : déduplication par (nom+type) pour entités, (from+to+type) pour relations
4. Si un chunk timeout (600s), on continue avec les suivants (résilience)

#### Prompt LLM structuré

Le LLM reçoit un prompt construit par `ontology.build_prompt()` contenant :
- Le contexte de l'ontologie (types d'entités, types de relations, exemples)
- Les instructions spéciales (`special_instructions`)
- Les entités prioritaires
- Le texte du document (ou chunk)
- Le contexte cumulatif des chunks précédents (si extraction chunked)

Le LLM retourne du JSON structuré :
```json
{
  "entities": [
    {"name": "Cloud Temple", "type": "Organization", "description": "Opérateur cloud souverain"}
  ],
  "relations": [
    {"from": "Cloud Temple", "to": "SecNumCloud", "type": "HAS_CERTIFICATION", "description": "..."}
  ]
}
```

#### Normalisation des types

- Le type d'entité retourné par le LLM est comparé à l'ontologie (insensible à la casse)
- Si le type est dans l'ontologie → retourné avec la casse exacte de l'ontologie
- Si le type est hors ontologie → classé `"Other"`
- **L'ontologie est la seule source de vérité** (pas de mapping hardcodé en Python)

### 5.5 Étape 4 — Chunking sémantique + Embedding

#### SemanticChunker (3 passes)

**Passe 1 — DETECT** : Détection de la structure du document
- Articles numérotés (`Article 1`, `1.2.3`)
- Headers Markdown (`##`, `###`)
- Numérotation hiérarchique (`a)`, `i)`)
- Titres en majuscules

**Passe 2 — SPLIT** : Découpe en phrases
- Split au niveau des phrases (`.`, `!`, `?`)
- Ne coupe jamais au milieu d'une phrase

**Passe 3 — MERGE** : Fusion en chunks avec overlap
- Taille cible : `CHUNK_SIZE` tokens (défaut: 500)
- Overlap : `CHUNK_OVERLAP` tokens (défaut: 50) au niveau des phrases
- Préfixe contextuel `[Article X — Titre]` sur chaque chunk
- **Protection boucle infinie** : si overlap + phrase > chunk_size, vidage de l'overlap forcé

#### Embedding BGE-M3

- Modèle : `bge-m3:567m` via LLMaaS (`/v1/embeddings`)
- Dimensions : 1024
- Batch processing pour optimiser les appels API
- Stockage dans Qdrant avec payload (doc_id, chunk_index, text, filename)

### 5.6 Notifications temps réel

Chaque étape d'ingestion notifie le client via `ctx.info()` (MCP LoggingMessageNotification) :

```
📤 Upload S3...
📄 Extraction texte (135K chars)...
🔍 Extraction LLM chunk 1/7 (25K chars)...
🔍 Extraction LLM chunk 2/7 — 12 entités, 8 relations cumulées...
📊 Stockage Neo4j (45 entités, 52 relations)...
🧩 Chunking sémantique (23 chunks)...
🔢 Embedding batch 1/3 (BGE-M3)...
📦 Stockage Qdrant (23 vecteurs)...
✅ Terminé
```

### 5.7 Monitoring mémoire

Chaque étape loggue le RSS (Resident Set Size) : `[RSS=XXmb]`

## 6. Pipeline de recherche & Q&A

### 6.1 Stratégie Graph-Guided RAG

```
Question en langage naturel
    │
    ▼ 1. Tokenisation + normalisation accents + stop words français
    │
    ▼ 2. Recherche d'entités dans Neo4j
    │    ├── Fulltext Lucene (standard-folding, scoring)
    │    └── Fallback CONTAINS (raw + normalisé)
    │
    ├── Entités trouvées ? ──▶ Graph-Guided RAG
    │   │  Le graphe identifie les documents pertinents (doc_ids)
    │   │  Qdrant recherche les chunks DANS ces documents uniquement
    │   └──▶ Contexte ciblé (graphe + chunks filtrés)
    │
    └── 0 entités ? ──▶ RAG-only (fallback)
        │  Qdrant recherche dans TOUS les chunks de la mémoire
        └──▶ Contexte large (chunks seuls)
    │
    ▼ 3. Filtrage par seuil (score cosinus ≥ 0.58)
    │
    ▼ 4. Construction du contexte LLM
    │    ├── Entités + relations + voisins (depuis Neo4j)
    │    └── Chunks RAG pertinents (depuis Qdrant)
    │
    ▼ 5. Génération de réponse LLM avec citations [Source: fichier.pdf]
```

### 6.2 Recherche d'entités (2 niveaux)

**Niveau 1 — Fulltext Lucene** (principal) :
- Index `entity_fulltext` avec analyzer `standard-folding` (ASCII folding)
- Scoring par pertinence Lucene
- Insensible aux accents : `réversibilité` = `reversibilite` = `REVERSIBILITE`
- Caractères spéciaux Lucene échappés (`_escape_lucene()`)

**Niveau 2 — CONTAINS** (fallback) :
- Si fulltext retourne < `limit` résultats
- Envoie tokens raw (avec accents) ET normalisés (sans accents) à Neo4j
- Complémente les résultats fulltext

### 6.3 Tokenisation de recherche

```python
# 1. Extraction mots (lettres uniquement, pas de ponctuation)
tokens = re.findall(r'[a-zA-ZÀ-ÿ]+', query)

# 2. Filtrage stop words français (~45 mots)
tokens = [t for t in tokens if t.lower() not in STOP_WORDS_FR]

# 3. Normalisation accents pour fallback CONTAINS
normalized = unicodedata.normalize('NFKD', token)
normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
```

### 6.4 Q&A dual-mode

| Mode                  | Condition                        | Contexte LLM                                     | Précision        |
| --------------------- | -------------------------------- | ------------------------------------------------ | ---------------- |
| **Graph-Guided RAG**  | Entités trouvées dans le graphe  | Entités + relations + chunks filtrés par doc_ids | ⭐⭐⭐ Élevée    |
| **RAG-only fallback** | 0 entités dans le graphe         | Tous les chunks de la mémoire                    | ⭐⭐ Moyenne     |
| **Pas d'information** | 0 entités ET 0 chunks pertinents | —                                                | Retour explicite |

### 6.5 Prompt Q&A

Le prompt de réponse inclut :
- La question de l'utilisateur
- Les entités trouvées avec `[Source: filename]`
- Les chunks RAG pertinents avec scores
- Instruction : citer les documents sources dans la réponse

---

## 7. Système d'ontologies

### 7.1 Rôle des ontologies

L'ontologie est le **contrat** entre le développeur et le LLM : elle définit exactement quels types d'entités et de relations le LLM doit extraire. Sans ontologie, le LLM invente des types aléatoires. Avec une bonne ontologie, l'extraction est précise et cohérente.

### 7.2 Ontologies fournies

| Ontologie          | Fichier                            | Entités  | Relations | Usage                                                     |
| ------------------ | ---------------------------------- | -------- | --------- | --------------------------------------------------------- |
| `legal`            | `ONTOLOGIES/legal.yaml`            | 22 types | 22 types  | Contrats, CGV, CGVU, documents juridiques                 |
| `cloud`            | `ONTOLOGIES/cloud.yaml`            | 27 types | 19 types  | Infrastructure cloud, fiches produits, docs techniques    |
| `managed-services` | `ONTOLOGIES/managed-services.yaml` | 20 types | 16 types  | Services managés, infogérance, MCO/MCS                    |
| `presales`         | `ONTOLOGIES/presales.yaml`         | 28 types | 30 types  | Avant-vente, RFP/RFI, propositions commerciales           |
| `general`          | `ONTOLOGIES/general.yaml`          | 28 types | 24 types  | Générique : FAQ, référentiels, certifications, RSE, specs |

Toutes utilisent les limites d'extraction `max_entities: 60` / `max_relations: 80`.

### 7.3 Format YAML d'une ontologie

```yaml
name: legal
description: Ontologie pour documents juridiques
version: "1.0"

entity_types:
  - name: Article
    description: Article numéroté d'un contrat ou d'une loi
    priority: high
    examples:
      - "Article 15 – Résiliation"
      - "Article L.1111-1 du Code de la santé publique"
  - name: Organization
    description: Entreprise, institution, organisme
    examples:
      - "Cloud Temple SAS"
      - "ANSSI"
  # ... (22 types pour legal)

relation_types:
  - name: DEFINES
    description: Définit un concept ou une obligation
  - name: APPLIES_TO
    description: S'applique à une entité ou un secteur
  # ... (22 types pour legal)

extraction_rules:
  max_entities: 60
  max_relations: 80
  priority_entities:
    - Article
    - Certification

instructions: |
  Instructions générales pour le LLM lors de l'extraction.

special_instructions: |
  Règles spécifiques supplémentaires, mappings obligatoires,
  catégories d'exclusion, etc.

examples:
  - input: "Article 15.1 – Cloud Temple SAS s'engage..."
    output:
      entities:
        - {name: "Article 15.1", type: "Article"}
        - {name: "Cloud Temple SAS", type: "Organization"}
      relations:
        - {from: "Article 15.1", to: "Cloud Temple SAS", type: "APPLIES_TO"}
```

### 7.4 Champs clés

| Champ                                | Obligatoire | Description                              |
| ------------------------------------ | ----------- | ---------------------------------------- |
| `name`                               | ✅          | Identifiant unique de l'ontologie        |
| `entity_types[].name`                | ✅          | Nom du type d'entité (PascalCase)        |
| `entity_types[].description`         | ✅          | Description pour guider le LLM           |
| `entity_types[].priority`            | ❌          | `high` = extraction prioritaire          |
| `entity_types[].examples`            | ❌          | Exemples concrets pour le LLM            |
| `relation_types[].name`              | ✅          | Nom du type de relation (UPPER_SNAKE)    |
| `extraction_rules.max_entities`      | ❌          | Défaut: 60                               |
| `extraction_rules.max_relations`     | ❌          | Défaut: 80                               |
| `extraction_rules.priority_entities` | ❌          | Types à extraire en priorité             |
| `instructions`                       | ❌          | Instructions générales pour le LLM       |
| `special_instructions`               | ❌          | Règles spécifiques, mappings, exclusions |
| `examples`                           | ❌          | Exemples input/output pour few-shot      |

### 7.5 Bonnes pratiques ontologie

1. **Nommer précisément** les types d'entités (pas de `Thing` ou `Item`)
2. **Ajouter des exemples réels** dans `examples` (noms de produits, articles, personnes)
3. **Utiliser `special_instructions`** pour les mappings obligatoires : "Ne crée JAMAIS de type X, utilise Y à la place"
4. **Définir les exclusions** : "N'extrait PAS les variables d'environnement, les chemins de fichiers, les paramètres CLI"
5. **Tester avec `--force`** sur quelques documents et vérifier le taux de "Other" (objectif : 0%)
6. **Scripts d'analyse** : `analyze_entities.py` (distribution types) et `analyze_others.py` (détail des "Other")

### 7.6 Création d'une mémoire avec ontologie

```bash
# L'ontologie est OBLIGATOIRE à la création
python scripts/mcp_cli.py memory create JURIDIQUE -n "Corpus Juridique" -o legal

# L'ontologie est copiée sur S3 : _ontology_JURIDIQUE.yaml
# Elle est rechargée depuis S3 à chaque ingestion (versioning)
```

## 8. Authentification & Sécurité

### 8.1 Modèle d'authentification

```
Client → Header "Authorization: Bearer <token>" → AuthMiddleware → current_auth ContextVar → Outils MCP
```

**3 niveaux d'accès** :
1. **Bootstrap** — Clé `ADMIN_BOOTSTRAP_KEY` dans le `.env` (accès total, pour créer le premier token)
2. **Token client** — Créé via `admin_create_token`, avec permissions et mémoires autorisées
3. **Localhost** — Requêtes depuis 127.0.0.1 exemptées d'authentification (MCP/SSE uniquement)

### 8.2 Structure d'un token

```python
TokenInfo:
  token_hash: str          # SHA-256 du token (stocké, jamais le token en clair)
  client_name: str         # Ex: "quoteflow", "vela"
  permissions: List[str]   # ["read"], ["read", "write"], ["admin"]
  memory_ids: List[str]    # [] = toutes les mémoires, ["JURIDIQUE"] = restreint
  email: Optional[str]     # Adresse du propriétaire
  created_at: str          # ISO 8601
  expires_at: Optional[str]
```

Tokens stockés dans Neo4j (nœuds `:Token`).

### 8.3 Contrôle d'accès par mémoire

Propagation via `contextvars.ContextVar` :
```
AuthMiddleware → current_auth.set(auth_info) → check_memory_access(memory_id) dans chaque outil
```

Règles :
- Bootstrap/admin → accès à toutes les mémoires
- `memory_ids = []` → accès à toutes les mémoires
- `memory_ids = ["JURIDIQUE", "CLOUD"]` → accès restreint à ces deux mémoires

### 8.4 WAF Coraza (OWASP CRS)

| Protection        | Détail                                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| **OWASP CRS**     | Injection SQL/XSS, path traversal, SSRF, scanners                                              |
| **Headers**       | CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy |
| **Rate Limiting** | SSE: 10/min, Messages MCP: 60/min, API: 30/min, Global: 200/min                                |
| **TLS**           | Let's Encrypt automatique en production (`SITE_ADDRESS=domaine.com`)                           |

**Routage intelligent** :
- Routes SSE/MCP (`/sse*`, `/messages/*`) → reverse proxy direct (streaming incompatible avec WAF)
- Routes web (`/api/*`, `/graph`, `/static/*`) → WAF Coraza + OWASP CRS
- Timeouts : SSE=∞, ingestion=1800s, API=300s

### 8.5 Sécurité Backup

| Menace                     | Mitigation                                                                      |
| -------------------------- | ------------------------------------------------------------------------------- |
| **Path traversal S3**      | `_validate_backup_id()` : regex `^[A-Za-z0-9_-]+$` sur chaque composant         |
| **Path traversal archive** | Rejet `..` et `/` dans les noms de fichiers, normalisation `os.path.basename()` |
| **Cross-memory access**    | Extraction `memory_id` du `backup_id` + `check_memory_access()`                 |
| **Token read-only**        | `check_write_permission()` sur backup_create/restore/delete                     |
| **DoS archive**            | `MAX_ARCHIVE_SIZE_BYTES = 100 MB`, rejet avant extraction                       |

### 8.6 Sécurité Docker

- Container non-root : `USER mcp` dans le Dockerfile
- Neo4j/Qdrant sur réseau interne uniquement (pas de ports exposés)
- Seul le port 8080 (WAF) est accessible de l'extérieur

---

## 9. Backup & Restore

### 9.1 Architecture

```
BackupService (core/backup.py) — Orchestrateur
  │
  ├─ create_backup(memory_id)
  │   ├─ graph.export_full_graph()      → graph_data.json
  │   ├─ vector_store.export_all_vectors() → qdrant_vectors.jsonl
  │   ├─ storage.list_all_objects()     → document_keys.json
  │   ├─ Compile manifest.json (stats, metadata, checksums)
  │   ├─ Upload 4 fichiers sur S3: _backups/{memory_id}/{timestamp}/
  │   └─ apply_retention()              → supprime anciens backups
  │
  ├─ restore_backup(backup_id)         — Depuis S3
  │   ├─ Download manifest + graph_data + qdrant_vectors
  │   ├─ graph.import_full_graph()     → MERGE idempotent
  │   ├─ vector_store.import_vectors() → upsert batch
  │   └─ Vérifie existence docs S3
  │
  └─ restore_from_archive(tar.gz)      — Depuis fichier local
      ├─ Extrait tar.gz en mémoire
      ├─ Re-uploade documents sur S3 + checksum SHA-256
      ├─ graph.import_full_graph()     → MERGE idempotent
      └─ vector_store.import_vectors() → upsert batch
```

### 9.2 Format de backup S3

```
_backups/{memory_id}/{timestamp}/
├── manifest.json          # Version, memory_id, ontologie, stats, checksums
├── graph_data.json        # Export complet Neo4j (nœuds + relations)
├── qdrant_vectors.jsonl   # Export complet Qdrant (vecteurs + payloads)
└── document_keys.json     # Liste des clés S3 des documents
```

### 9.3 Format archive tar.gz (download)

```
{memory_id}_{timestamp}.tar.gz
├── manifest.json
├── graph_data.json
├── qdrant_vectors.jsonl
├── document_keys.json
└── documents/              # Optionnel (si --include-documents)
    ├── contrat.docx
    ├── guide.pdf
    └── ...
```

### 9.4 Principes

- **Restore idempotent** : `MERGE` Cypher (pas de doublons si re-exécuté)
- **Restore refuse si mémoire existe** : protection contre l'écrasement accidentel
- **Rétention automatique** : `BACKUP_RETENTION_COUNT=5` (les plus anciens sont supprimés)
- **Restore instantané** : pas de ré-extraction LLM (~0.3s pour un backup standard)
- **Checksums** : SHA-256 vérifié lors du restore depuis archive

### 9.5 Cycle complet validé

```
1. create mémoire + ingest documents → entités, relations, vecteurs
2. backup_create → backup sur S3
3. backup_download --include-documents → archive tar.gz locale
4. memory_delete → suppression complète serveur
5. backup_restore_archive → restore depuis fichier local
6. storage_check → tout intact ✅
```

---

## 10. Interface Web

### 10.1 Architecture

Accessible via `http://localhost:8080/graph` (à travers le WAF).

```
graph.html                  — Page principale
├── css/graph.css           — Styles (thème sombre, couleurs Cloud Temple)
├── js/config.js            — Configuration, couleurs, état de filtrage
├── js/api.js               — Appels API REST (/api/memories, /api/graph, /api/ask)
├── js/graph.js             — Rendu vis-network + mode Focus
├── js/sidebar.js           — Filtres, liste d'entités, recherche
├── js/ask.js               — Panneau Q&A + export HTML
└── js/app.js               — Orchestration et initialisation
```

8 fichiers, tous < 210 lignes. Token Bearer stocké en `localStorage`.

### 10.2 Fonctionnalités

**Graphe interactif (vis-network)** :
- Force-directed layout, zoom, drag, sélection de nœuds
- Entités colorées par type, documents en carrés rouges
- Clic sur un nœud → panneau détails (relations, docs, description)

**Filtrage avancé (sidebar gauche, 3 panneaux pliables)** :
- Types d'entités : checkboxes avec pastilles couleur, compteurs, Tous/Aucun/Inverser
- Types de relations : checkboxes avec barres couleur, compteurs
- Documents : masquer/afficher par document source (cascade entités exclusives)

**Toggle MENTIONS (📄)** : masque les nœuds Document + arêtes MENTIONS pour ne voir que les relations sémantiques

**Panneau ASK (💬)** :
- Question en langage naturel → réponse LLM avec Markdown (tableaux, code, listes)
- Entités cliquables → focus sur le nœud dans le graphe
- **Mode Focus (🔬)** : isole le sous-graphe (entités réponse + voisins 1 hop)
- **Export HTML (📥)** : fichier autonome avec branding Cloud Temple, compatible impression

**Panneau redimensionnable** : poignée de drag, body scrollable indépendant

### 10.3 API REST

| Méthode | Endpoint          | Auth | Description                  |
| ------- | ----------------- | ---- | ---------------------------- |
| `GET`   | `/health`         | —    | État du serveur              |
| `GET`   | `/graph`          | —    | Interface web                |
| `GET`   | `/api/memories`   | 🔑  | Liste des mémoires           |
| `GET`   | `/api/graph/{id}` | 🔑  | Graphe complet d'une mémoire |
| `POST`  | `/api/ask`        | 🔑  | Question/Réponse LLM         |
| `POST`  | `/api/query`      | 🔑  | Données structurées sans LLM |

## 11. CLI — Command Line Interface

### 11.1 Principe des 3 couches

**Règle fondamentale** : toute fonctionnalité doit être exposée dans les 3 couches simultanément.

```
API MCP (server.py) → CLI Click (commands.py) → Shell interactif (shell.py)
```

### 11.2 Architecture du package `scripts/cli/`

```
scripts/
├── mcp_cli.py              # Point d'entrée
└── cli/
    ├── __init__.py          # Configuration (MCP_URL, MCP_TOKEN)
    ├── client.py            # MCPClient HTTP/SSE (call_tool, on_progress)
    ├── display.py           # Affichage Rich partagé (tables, panels, format_size)
    ├── ingest_progress.py   # Progression ingestion temps réel (Rich Live + SSE)
    ├── commands.py          # Commandes Click (scriptable)
    └── shell.py             # Shell interactif (prompt_toolkit, 22+ commandes)
```

**Règle DRY** : ne JAMAIS dupliquer de code entre `commands.py` et `shell.py`. Toute logique partagée dans `display.py` (affichage) ou `ingest_progress.py` (progression).

### 11.3 Mode Click (scriptable)

```bash
python scripts/mcp_cli.py health
python scripts/mcp_cli.py memory list
python scripts/mcp_cli.py memory create JURIDIQUE -n "Corpus" -o legal
python scripts/mcp_cli.py document ingest JURIDIQUE /path/to/doc.pdf
python scripts/mcp_cli.py ask JURIDIQUE "Quelles sont les clauses de résiliation ?"
python scripts/mcp_cli.py backup create JURIDIQUE
python scripts/mcp_cli.py about
```

### 11.4 Mode Shell (interactif)

```bash
python scripts/mcp_cli.py shell

mcp> list
mcp> use JURIDIQUE
mcp[JURIDIQUE]> ingest /path/to/doc.pdf
mcp[JURIDIQUE]> entities
mcp[JURIDIQUE]> ask Quelles sont les obligations du client ?
mcp[JURIDIQUE]> backup-create
```

**Fonctionnalités shell** :
- Autocomplétion Tab (prompt_toolkit)
- Historique persistant `~/.mcp_memory_history`
- `use ID` pour sélectionner la mémoire courante
- Option `--json` sur toute commande de consultation
- Progression temps réel d'ingestion (barres ASCII, compteurs, phases)

### 11.5 Variables CLI

| Priorité | URL              | Token                 | Source                          |
| :------: | ---------------- | --------------------- | ------------------------------- |
|    1     | `MCP_URL`        | `MCP_TOKEN`           | Shell export                    |
|    2     | `MCP_SERVER_URL` | `ADMIN_BOOTSTRAP_KEY` | `.env` via `load_dotenv()`      |
|    3     | —                | —                     | Défaut: `http://localhost:8080` |

---

## 12. Intégration Live Memory

### 12.1 Architecture mémoire à deux niveaux

```
Agents IA (Cline, Claude, ...)
     │
     ▼
┌─────────────────────────┐
│  Live Memory            │  Notes temps réel → LLM → Memory Bank Markdown
│  (mémoire de travail)   │  S3-only, pas de BDD
└──────────┬──────────────┘
           │ graph_push (MCP SSE)
           │ delete + re-ingest → recalcul du graphe
           ▼
┌──────────────────────────┐
│  Graph Memory            │  Entités + Relations + RAG vectoriel
│  (mémoire long terme)    │  Neo4j + Qdrant + S3
└──────────────────────────┘
```

| Niveau                 | Service      | Durée            | Contenu                          |
| ---------------------- | ------------ | ---------------- | -------------------------------- |
| **Mémoire de travail** | Live Memory  | Session / projet | Notes brutes + bank Markdown     |
| **Mémoire long terme** | Graph Memory | Permanent        | Entités + relations + embeddings |

### 12.2 Outils MCP côté Live Memory

1. `graph_connect` — Connecte un space à une mémoire Graph Memory (crée si besoin)
2. `bank_consolidate` — Le LLM consolide les notes en fichiers bank Markdown
3. `graph_push` — Pousse les fichiers bank vers Graph Memory (delete ancien + re-ingest)
4. `graph_status` — Vérifie la connexion et affiche stats

### 12.3 Protocole de synchronisation

- Chaque `graph_push` supprime l'ancien document puis ré-ingère → recalcul complet
- Réutilise `document_delete` (cascade) + `memory_ingest` avec `force=True`
- Connexion via MCP SSE standard (même auth Bearer Token)

**Référence** : Tran et al., 2025 — *Multi-Agent Collaboration Mechanisms* (arxiv:2501.06322)

---

## 13. Configuration

### 13.1 Variables d'environnement complètes

#### S3
| Variable               | Défaut                                       | Description    |
| ---------------------- | -------------------------------------------- | -------------- |
| `S3_ENDPOINT_URL`      | `https://takinc5acc.s3.fr1.cloud-temple.com` | Endpoint S3    |
| `S3_ACCESS_KEY_ID`     | — (obligatoire)                              | Clé d'accès S3 |
| `S3_SECRET_ACCESS_KEY` | — (obligatoire)                              | Secret S3      |
| `S3_BUCKET_NAME`       | `quoteflow-memory`                           | Nom du bucket  |

#### LLMaaS
| Variable                      | Défaut                            | Description                        |
| ----------------------------- | --------------------------------- | ---------------------------------- |
| `LLMAAS_API_URL`              | `https://api.ai.cloud-temple.com` | Endpoint LLMaaS                    |
| `LLMAAS_API_KEY`              | — (obligatoire)                   | Clé API                            |
| `LLMAAS_MODEL`                | `gpt-oss:120b`                    | Modèle extraction/Q&A              |
| `LLMAAS_MAX_TOKENS`           | `60000`                           | Max tokens par réponse             |
| `LLMAAS_TEMPERATURE`          | `1.0`                             | Température (gpt-oss requiert 1.0) |
| `LLMAAS_EMBEDDING_MODEL`      | `bge-m3:567m`                     | Modèle embedding                   |
| `LLMAAS_EMBEDDING_DIMENSIONS` | `1024`                            | Dimensions vecteurs                |

#### Neo4j
| Variable         | Défaut              | Description  |
| ---------------- | ------------------- | ------------ |
| `NEO4J_URI`      | `bolt://neo4j:7687` | URI Neo4j    |
| `NEO4J_USER`     | `neo4j`             | Utilisateur  |
| `NEO4J_PASSWORD` | — (obligatoire)     | Mot de passe |

#### Qdrant
| Variable                   | Défaut               | Description             |
| -------------------------- | -------------------- | ----------------------- |
| `QDRANT_URL`               | `http://qdrant:6333` | URL Qdrant              |
| `QDRANT_COLLECTION_PREFIX` | `memory_`            | Préfixe des collections |

#### Extraction & Chunking
| Variable                     | Défaut   | Description                          |
| ---------------------------- | -------- | ------------------------------------ |
| `EXTRACTION_MAX_TEXT_LENGTH` | `950000` | Max chars envoyés au LLM             |
| `EXTRACTION_CHUNK_SIZE`      | `25000`  | Max chars par chunk d'extraction     |
| `EXTRACTION_TIMEOUT_SECONDS` | `600`    | Timeout par appel LLM (10 min)       |
| `CHUNK_SIZE`                 | `500`    | Taille cible en tokens par chunk RAG |
| `CHUNK_OVERLAP`              | `50`     | Tokens de chevauchement              |

#### RAG
| Variable              | Défaut | Description               |
| --------------------- | ------ | ------------------------- |
| `RAG_SCORE_THRESHOLD` | `0.58` | Score cosinus min. BGE-M3 |
| `RAG_CHUNK_LIMIT`     | `8`    | Max chunks retournés      |

#### Serveur & Auth
| Variable                 | Défaut    | Description                              |
| ------------------------ | --------- | ---------------------------------------- |
| `MCP_SERVER_PORT`        | `8002`    | Port d'écoute                            |
| `MCP_SERVER_HOST`        | `0.0.0.0` | Host (0.0.0.0 = désactive DNS rebinding) |
| `MCP_SERVER_DEBUG`       | `false`   | Logs détaillés                           |
| `ADMIN_BOOTSTRAP_KEY`    | —         | Clé pour créer le premier token          |
| `BACKUP_RETENTION_COUNT` | `5`       | Backups conservés par mémoire            |

---

## 14. Déploiement

### 14.1 Développement local

```bash
git clone https://github.com/chrlesur/graph-memory.git
cd graph-memory
cp .env.example .env
# Éditer .env avec vos credentials
docker compose up -d
curl http://localhost:8080/health
```

### 14.2 Production

1. Configurer `SITE_ADDRESS=votre-domaine.com` dans `.env`
2. Décommenter ports 80/443 dans `docker-compose.yml`
3. Caddy obtient automatiquement un certificat Let's Encrypt
4. Ou : reverse proxy nginx/traefik en amont, `SITE_ADDRESS=:8080` (HTTP)

**Déploiement Cloud Temple** :
- Serveur : `prod-docker02` (192.168.10.21)
- URL : `https://graph-mem.mcp.cloud-temple.app`
- TLS : reverse proxy nginx en amont
- WAF : mode HTTP `:8080`

### 14.3 Mise à jour

```bash
git pull
docker compose build mcp-memory
docker compose up -d mcp-memory
```

### 14.4 Intégration MCP (clients)

```json
{
  "mcpServers": {
    "graph-memory": {
      "url": "http://localhost:8080/sse",
      "headers": {
        "Authorization": "Bearer VOTRE_TOKEN"
      }
    }
  }
}
```

---

## 15. Structure du projet

```
graph-memory/
├── .env.example              # Template configuration
├── docker-compose.yml        # Orchestration (WAF + MCP + Neo4j + Qdrant)
├── Dockerfile                # Image service (non-root)
├── requirements.txt          # Dépendances Python
├── VERSION                   # Version courante
├── CHANGELOG.md              # Historique complet
├── README.md                 # Documentation utilisateur
│
├── DESIGN/                   # Documents de spécification
│   └── SPECIFICATION.md      # Ce document
│
├── waf/                      # WAF Coraza
│   ├── Dockerfile            # xcaddy + coraza + ratelimit
│   └── Caddyfile             # Config OWASP CRS + routes + TLS
│
├── ONTOLOGIES/               # Ontologies d'extraction
│   ├── legal.yaml            # 22 entités / 22 relations
│   ├── cloud.yaml            # 27 entités / 19 relations (v1.2)
│   ├── managed-services.yaml # 20 entités / 16 relations
│   ├── presales.yaml         # 28 entités / 30 relations
│   └── general.yaml          # 28 entités / 24 relations (v1.1)
│
├── scripts/                  # CLI et utilitaires
│   ├── mcp_cli.py            # Point d'entrée CLI
│   └── cli/                  # Package CLI
│       ├── __init__.py       # Config (MCP_URL, MCP_TOKEN)
│       ├── client.py         # MCPClient HTTP/SSE
│       ├── commands.py       # Commandes Click
│       ├── display.py        # Affichage Rich partagé
│       ├── ingest_progress.py # Progression temps réel
│       └── shell.py          # Shell interactif
│
├── starter-kit/              # Kit pour créer un nouveau service MCP
│
└── src/mcp_memory/           # Code source service
    ├── server.py             # Serveur MCP + 28 outils
    ├── config.py             # Configuration pydantic-settings
    ├── auth/                 # Authentification
    │   ├── context.py        # ContextVar + check_memory_access
    │   ├── middleware.py     # ASGI middlewares
    │   └── token_manager.py  # CRUD tokens Neo4j
    ├── core/                 # Services métier
    │   ├── graph.py          # Neo4j (Cypher, export/import)
    │   ├── storage.py        # S3 (boto3)
    │   ├── extractor.py      # LLM extraction
    │   ├── ontology.py       # Ontologies YAML
    │   ├── chunker.py        # SemanticChunker (3 passes)
    │   ├── embedder.py       # BGE-M3 embeddings
    │   ├── vector_store.py   # Qdrant CRUD
    │   ├── backup.py         # Backup/Restore orchestrateur
    │   └── models.py         # Pydantic models
    └── static/               # Interface web
        ├── graph.html
        ├── css/graph.css
        └── js/ (6 fichiers)
```

---

## 16. Évolutions futures

### Court terme
- [ ] Ré-ingérer REFERENTIEL avec general.yaml v1.1 (réduire 299 "Other" à ~0)
- [ ] Ré-ingérer DOCS entièrement avec cloud.yaml v1.2
- [ ] Ingérer plus de documents juridiques (CGVU, Contrat Cadre, Convention de Services)

### Moyen terme
- [ ] **Git-Sync** — Synchronisation automatique mémoire ↔ dépôt Git (design terminé : `DESIGN/GIT_SYNC_DESIGN.md`)
- [ ] Export du graphe (Cypher, JSON-LD, RDF)
- [ ] Diff sémantique CGA/CGV
- [ ] Amélioration extraction DOCX (tables converties en texte plat)

### Long terme
- [ ] Dashboard de monitoring web
- [ ] API de merge entre mémoires
- [ ] Clustering Neo4j
- [ ] Webhooks de notification
- [ ] Interface web d'administration des backups

---

*Graph Memory v1.3.7 — Cahier de Spécification — 21 février 2026*
*Développé par Cloud Temple — https://www.cloud-temple.com*
