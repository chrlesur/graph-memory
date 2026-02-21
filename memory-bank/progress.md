# Progress

## Ce qui fonctionne ✅

### Infrastructure
- Serveur MCP via HTTP/SSE (FastMCP + uvicorn)
- Docker Compose (WAF + MCP + Neo4j + Qdrant)
- **Coraza WAF** (v0.6.6) : reverse proxy OWASP CRS, seul port 8080 exposé
- **Rate Limiting** (v1.1.0) : `caddy-ratelimit` 4 zones par IP (SSE 10/min, messages 60/min, API 30/min, global 200/min). Testé : HTTP 429 au-delà des limites.
- **Analyse de Risques** (v1.1.0) : `DESIGN/ANALYSE_RISQUES_SECURITE.md` — matrice par route, vecteurs d'attaque, conformité OWASP/SecNumCloud/RGPD
- **TLS Let's Encrypt** (v0.6.6) : `SITE_ADDRESS` pour basculer dev/prod
- **Dockerfile non-root** (v0.6.6) : `USER mcp`, plus de container root
- **Réseau Docker isolé** (v0.6.6) : Neo4j/Qdrant internes uniquement
- Authentification Bearer Token + Bootstrap Admin Key
- Auth middleware : localhost (127.0.0.1) exempt d'authentification
- Stockage S3 Dell ECS (upload/download documents)
- `EXTRACTION_MAX_TEXT_LENGTH` refactorisé en garde-fou (v0.6.6) : rejette explicitement au lieu de tronquer

### Outil system_about + Starter Kit (v1.3.5)
- **`system_about`** : carte d'identité complète du service (identité, 28 outils/8 catégories, 5 ontologies, mémoires actives, état services, configuration LLM/RAG)
- Commande `about` dans CLI Click + shell interactif + affichage Rich `show_about()`
- **Starter Kit** (`starter-kit/`) : guide 4 étapes + boilerplate fonctionnel (Docker, WAF, CLI, auth)
- **`client.py` robustifié** : gestion `isError`, réponse vide, réponse non-JSON (plus de crash `json.loads`)

### CLI refactorisée et alignée (package `scripts/cli/`)
- 7 fichiers, tous < 500 lignes, bien commentés
- `client.py` — MCPClient REST + SSE
- `display.py` — Affichage Rich partagé (tables, panels, graphe, entités, Q&A, `format_size`, `show_ingest_preflight`, `show_entities_by_type`, `show_relations_by_type`)
- `ingest_progress.py` — Progression ingestion temps réel partagée (`create_progress_state`, `make_progress_bar`, `create_progress_callback`, `run_ingest_with_progress`)
- `commands.py` — Commandes Click (health, memory, document, storage, ask, ontologies)
- `shell.py` — Shell interactif prompt_toolkit (22 commandes)
- Point d'entrée : `python3 scripts/mcp_cli.py`
- **Règle d'alignement** : API MCP → CLI Click → Shell (toujours les 3 couches)
- **Factorisation v1.2.4** : ~300 lignes de duplication supprimées (entities, relations, ingest progress, format_size) — 0 changement fonctionnel
- **Variables CLI v1.2.1** : `MCP_URL` + `MCP_TOKEN` prioritaires sur `MCP_SERVER_URL` + `ADMIN_BOOTSTRAP_KEY` (évite conflit dev/prod avec `load_dotenv()`)

### Shell interactif
- Autocomplétion Tab (prompt_toolkit)
- Historique persistant ↑↓ (~/.mcp_memory_history)
- Édition avancée (Ctrl+A/E/W)
- Commandes : list, use, info, graph, docs, entities, entity, relations, ask, query, limit, delete, debug, clear, exit
- **Option `--json` globale** (v0.6.5) : utilisable sur toute commande de consultation (list, info, graph, docs, entities, entity, relations, ask, query). Affiche le JSON brut sans formatage Rich. Détection automatique n'importe où dans la ligne.
- `use` valide le memory_id, extrait l'ID si copié avec le nom
- `relations <TYPE>` deepdive par type
- `entities` avec colonne Document(s) source
- `limit [N]` configurable par session (passé à l'API)
- **Progression ingestion temps réel** (v1.2.3) : `cmd_ingest` utilise Rich Live + callback `on_progress` pour afficher barres ASCII extraction LLM/embedding, compteurs entités/relations, phases S3→texte→LLM→Neo4j→chunking→embedding→Qdrant — même affichage que la CLI Click
- **Progression temps réel pour ingestdir** (v1.3.4) : `cmd_ingestdir` et `document_ingest_dir` utilisent `run_ingest_with_progress()` pour chaque fichier (même UX que `ingest` unitaire). Header `[X/N] 📥 fichier (taille)`, barres LLM/embedding, résumé `new+merged entités/relations (durée)`.
- **Parser --exclude robuste** (v1.3.4) : `shlex.split()` dans le shell (gère guillemets, options inconnues détectées avec message d'erreur clair). CLI Click non affectée (Click gère nativement `multiple=True`).

### Gestion des mémoires
- Création avec ontologie obligatoire (copiée sur S3)
- Suppression (cascade : docs + entités + relations)
- Listing et statistiques
- Graphe complet (API REST + outil MCP)

### Ingestion de documents
- Formats : txt, md, html, docx, pdf, csv
- Déduplication par hash SHA-256
- Force re-ingestion : supprime l'ancien document + entités orphelines avant recréation
- Extraction LLM guidée par ontologie
- Réponse enrichie : entities/relations created/merged, types
- `--force` disponible en CLI

### Extraction (améliorée)
- Extraction guidée par ontologie
- `EXTRACTION_MAX_TEXT_LENGTH` configurable (fin du hardcodé 50K)
- `generate_answer` utilise `self._max_tokens` (plus de limite 1000)
- Ontologie legal.yaml : instruction exhaustivité des articles
- Instructions anti-hub dans le prompt
- 0 RELATED_TO sur corpus juridique (relations sémantiques spécifiques)

### Recherche et Q&A
- Recherche d'entités par texte (limit configurable)
- Contexte d'entité (voisins + documents)
- Question/Réponse via LLM avec contexte du graphe
- Documents sources affichés dans les réponses
- `limit` comme paramètre API optionnel
- **`memory_query`** (v0.6.5) — Interrogation structurée sans LLM. Même pipeline que `question_answer` (graphe + RAG) mais retourne données brutes : entités enrichies (relations, voisins, docs), chunks RAG avec scores, statistiques. Idéal pour agents IA.

### Ontologies
- 5 ontologies : legal, cloud, managed-services, technical, **presales** (v1.3.0)
- legal.yaml : 22 types entités, 22 types relations, instructions exhaustivité
- presales.yaml : 28 types entités (6 familles), 30 types relations (5 familles), max_entities=60, max_relations=80
  - Familles entités : Acteurs & Personnes, Sécurité & Conformité, Technique & Infrastructure, Gouvernance & Méthodologie, Commercial & Valeur, Contexte & Indicateurs
  - Entités prioritaires : Service, Certification, Differentiator, Requirement, SLA, ClientReference
  - Relations prioritaires : HAS_CERTIFICATION, GUARANTEES, TARGETS_PERSONA, ANSWERED_BY, PART_OF_DOMAIN, PROVEN_BY
- general.yaml **v1.1** : 28 types entités (5 familles), 24 types relations (6 familles), max_entities=60, max_relations=80
  - v1.0→v1.1 : +4 entités (LegalProvision, Sector, Sanction, Stakeholder), +2 relations (APPLIES_TO, IMPOSES)
  - ~50 lignes `special_instructions` additionnelles (textes réglementaires, RSE/matérialité, 15 mappings anti-"Other")
  - Couverture des 299 "Other" de REFERENTIEL : articles de loi, secteurs NIS2/DORA, stakeholders RSE, sanctions, deadlines, résolutions AG, rapports, zones PAMS, qualifications ANSSI
  - **En attente ré-ingestion** des 7 documents problématiques (NIS2, DORA, NEURONES, PAMS, SecNumCloud, HDS, DiagCarbone)
- cloud.yaml **v1.2** : 27 types entités, 19 types relations, max_entities=60, max_relations=80
  - v1.0→v1.1 : +4 entités (PricingModel, StorageClass, BackupSolution, AIModel), +5 relations
  - **v1.1→v1.2** : +2 entités (`Role` IAM/RBAC, `SLALevel` P1-P5/Impact/Criticité), +50 lignes `special_instructions`
  - 12 mappings obligatoires (Endpoint→API, Licence→PricingModel, HA→Technology, Feature→NetworkComponent, etc.)
  - 8 catégories d'exclusion (CLI flags, variables, erreurs, paramètres API, titres de sections)
  - Règle de qualité des noms descriptifs
  - **Tests ré-ingestion 4/4 = 0 "Other"** (forti.md, llmaas.md, quickstart.md, Références_client.md)
- presales.yaml **v1.1** : mapping MonetaryAmount/Duration → ClientReference/PricingModel
  - Test ré-ingestion 01_Références_client.md : 12 Other → **0 Other**

### Scripts d'analyse ontologie (v1.3.6)
- `scripts/analyze_entities.py` : distribution types entités/relations d'une mémoire (top N + détail "Other")
- `scripts/analyze_others.py` : détail des entités "Other" par document source + catégorisation
- `scripts/fix_other_entities.py` : reclassification Cypher des "Other" existants (dry-run + --apply)

### Vérification et nettoyage S3
- `storage_check(memory_id?)` — Vérifie cohérence graphe ↔ S3 (accessibilité, orphelins)
- `storage_cleanup(dry_run=True)` — Nettoie les fichiers orphelins S3
- `document_delete` supprime maintenant le fichier S3 associé
- `memory_delete` supprime tous les fichiers S3 du préfixe mémoire
- CLI : commandes `check` et `cleanup` (+ `cleanup --force`)
- Affichage Rich : panneau résumé, tableau docs/orphelins, tailles

### Gestion des tokens et contrôle d'accès mémoire (session 02/09/2026 après-midi)
- `admin_update_token` — Nouvel outil MCP pour modifier les memory_ids d'un token (add/remove/set)
- `auth/context.py` — `contextvars.ContextVar` pour propager l'auth du middleware aux outils MCP
- `check_memory_access()` — Vérification d'accès dans chaque outil mémoire (memory_create, _delete, _ingest, _search, question_answer, etc.)
- CLI Click : groupe `token` avec 6 sous-commandes (list, create, revoke, grant, ungrant, set-memories)
- Shell interactif : 6 nouvelles commandes (tokens, token-create, token-revoke, token-grant, token-ungrant, token-set)
- `display.py` : `show_tokens_table()`, `show_token_created()`, `show_token_updated()`
- Middleware injecte `current_auth.set()` pour bootstrap et tokens clients

### RAG Vectoriel Graph-Guided (session 02/09/2026 après-midi — 2e partie)
- **Qdrant** : base vectorielle (docker-compose, healthcheck, volume persistant)
- **Couplage strict** : Neo4j + Qdrant obligatoires (pas de mode dégradé)
- **SemanticChunker** (`core/chunker.py`) :
  - 3 passes : DETECT structure → SPLIT phrases → MERGE chunks avec overlap
  - Détecte articles numérotés, headers Markdown, numérotation hiérarchique, titres majuscules
  - Ne coupe jamais au milieu d'une phrase
  - Overlap au niveau des phrases (configurable)
  - Préfixe contextuel [Article X - Titre] sur chaque chunk
- **EmbeddingService** (`core/embedder.py`) : LLMaaS bge-m3:567m, 1024 dimensions, batch
- **VectorStoreService** (`core/vector_store.py`) : CRUD Qdrant, search filtré par doc_ids
- **Ingestion** : Graph + Chunk + Embed + Qdrant (synchrone strict, rollback si erreur)
- **Q&A Graph-Guided RAG** : graphe identifie doc_ids → Qdrant filtre chunks → double contexte LLM
- **Suppressions** : document_delete et memory_delete suppriment aussi dans Qdrant (strict)
- **system_health** : teste 5 services (S3, Neo4j, LLMaaS, Qdrant, Embedding)
- **Modèles** : Chunk + ChunkResult dans models.py

### Backup / Restore complet (v1.2.0)
- **BackupService** (`core/backup.py`) — Orchestrateur backup/restore/list/download/delete/restore_from_archive
- **3 couches sauvegardées** : Neo4j (graphe complet), Qdrant (vecteurs RAG), S3 (documents originaux)
- Stockage backups sur S3 : `_backups/{memory_id}/{timestamp}/` (graph_data.json + qdrant_vectors.jsonl + manifest.json + document_keys.json)
- `graph.py` : `export_full_graph()` (labels dynamiques) / `import_full_graph()` (MERGE idempotent)
- `vector_store.py` : `export_all_vectors()` (scroll complet) / `import_vectors()` (upsert batch)
- Config : `BACKUP_RETENTION_COUNT=5` (rotation automatique, supprime les plus anciens)
- **7 outils MCP** : `backup_create`, `backup_list`, `backup_restore`, `backup_download`, `backup_delete`, `backup_restore_archive`
- **`backup_restore_archive`** : restaure depuis un fichier tar.gz local (base64). Re-uploade les documents S3 inclus dans l'archive + restaure graphe Neo4j + vecteurs Qdrant. Vérifie checksums SHA-256.
- **CLI Click** : groupe `backup` avec 6 sous-commandes (create/list/restore/download/delete/restore-file)
- **Shell interactif** : commandes backup correspondantes
- **Display Rich** : `show_backup_result()`, `show_backups_table()`, `show_restore_result()`
- Restore vérifie que la mémoire n'existe pas (évite écrasement accidentel)
- Download génère une archive tar.gz (optionnel: `--include-documents` pour inclure les PDFs/DOCX originaux)
- **Cycle complet validé** : create → ingest → backup → download tar.gz → delete tout → restore depuis fichier local → verify OK (0.3s)

### Durcissement sécurité backup (v1.2.0)
- **`_validate_backup_id()`** : regex `^[A-Za-z0-9_-]+$` sur chaque composant du backup_id (anti path-traversal S3)
- **Path traversal `restore_from_archive`** : rejet `..` et `/`, normalisation `os.path.basename()`, log des rejets
- **`check_write_permission()`** : nouvelle fonction dans `auth/context.py`, vérifie permission `write` ou `admin`
- **Contrôle write** appliqué à : `backup_create`, `backup_restore`, `backup_delete`, `backup_restore_archive`
- **Cross-memory access control** : `backup_restore/download/delete` extraient `memory_id` du `backup_id` et appellent `check_memory_access()` AVANT l'opération
- **Limite taille archive** : `MAX_ARCHIVE_SIZE_BYTES = 100 MB`, rejet immédiat avant extraction tar.gz (anti DoS)

### Fix storage_check (v1.2.0)
- Les fichiers `_backups/` sont exclus de la détection d'orphelins (gérés par `backup_list`)
- Quand scopé à une mémoire, la détection d'orphelins charge les URIs de TOUTES les mémoires (pas de faux-positifs)

### Intégration Live Memory (2026-02-21)
- **Architecture mémoire à deux niveaux** documentée dans le README : Live Memory (mémoire de travail) ↔ Graph Memory (mémoire long terme)
- 4 outils MCP dans Live Memory pour l'intégration : `graph_connect`, `graph_push`, `graph_status`, `graph_disconnect`
- Flux : `bank_consolidate` → `graph_push` (delete + re-ingest → recalcul du graphe)
- Les fichiers Markdown de la memory bank Live Memory deviennent des entités et relations interrogeables en langage naturel
- Référence académique : Tran et al., 2025 — *Multi-Agent Collaboration Mechanisms*

### Branding & Q&A amélioré
- Logo Cloud Temple SVG en header + couleur accent `#41a890`
- Prompt ASK cite les documents sources (chaque entité inclut `[Source: filename]`)
- API REST `/api/ask` délègue à `question_answer()` (DRY, source unique de vérité)

### Client web modulaire (8 fichiers)
- Architecture : graph.html + css/graph.css + 6 fichiers JS
- vis-network pour le graphe (force-directed, zoom, drag, sélection)
- **Filtrage avancé (3 panneaux pliables)** :
  - Types d'entités : checkboxes avec pastilles couleur, compteurs, Tous/Aucun/Inverser
  - Types de relations : checkboxes avec barres couleur, compteurs, Tous/Aucun/Inverser
  - Documents : checkboxes individuelles, masquage cascade entités exclusives
- **Mode Focus Question (ASK)** :
  - Bouton "🔬 Isoler le sujet" après chaque réponse
  - Isole le sous-graphe : entités réponse + voisins 1 hop + arêtes entre eux
  - Bannière "Mode Focus" avec bouton "🔄 Graphe complet" pour restaurer
- Panneau détails nœud (relations, documents, description)
- ASK intégré : question en langage naturel → réponse LLM + highlight entités
- Entités cliquables dans la réponse → focus sur le nœud dans le graphe
- Rendu Markdown complet (marked.js CDN) : tableaux, listes, code, blockquotes
- Modale paramètres (distance, répulsion, taille nœuds/texte)
- Recherche locale d'entités dans la sidebar
- État de filtrage centralisé (`filterState` dans config.js, `applyFilters()`)
- API REST : GET /api/memories, GET /api/graph/{id}, POST /api/ask

### Métadonnées enrichies sur les documents (v0.6.0)
- Nœud Document enrichi dans Neo4j : `source_path`, `source_modified_at`, `size_bytes`, `text_length`, `content_type`
- `source_path` et `source_modified_at` passés optionnellement par le client à l'ingestion
- `size_bytes`, `text_length`, `content_type` calculés automatiquement côté serveur
- `get_document()` et `get_full_graph()` retournent les métadonnées enrichies
- Permet la détection de modifications (hash ≠, taille ≠, date source plus récente)
- **CLI enrichi** : `document ingest` (+ `--source-path`), `document ingest-dir`, `cmd_ingest`, `cmd_ingestdir` passent automatiquement `source_path` et `source_modified_at` (mtime fichier)
- **`document_get`** : paramètre `include_content=False` par défaut → métadonnées sans téléchargement S3 (rapide). `include_content=True` pour récupérer le contenu.

### Chunked Graph Extraction (v0.6.0 → v0.6.1)
- **Extraction chunked séquentielle** avec contexte cumulatif pour les gros documents
- `extract_with_ontology_chunked()` : découpe si texte > `EXTRACTION_CHUNK_SIZE`
- **v0.6.1** : `EXTRACTION_CHUNK_SIZE` réduit de 200K à **25K chars** (~6K tokens, laisse marge pour prompt+réponse dans les 120K tokens de gpt-oss:120b)
- Découpe aux frontières de sections (double saut de ligne), jamais mid-paragraphe
- Chaque chunk reçoit la liste compacte des entités/relations des chunks précédents
- Fusion : déduplication par (nom+type) pour entités, (from+to+type) pour relations
- Résilience : si un chunk timeout, on continue avec les suivants
- `build_prompt()` (ontology.py) accepte `cumulative_context` optionnel
- `memory_ingest()` utilise `extract_with_ontology_chunked()` (transparent pour les petits docs)
- **Timeout LLM** : 120s → **600s** (10 min par appel, gpt-oss:120b chain-of-thought)
- **Progress callback** : `extract_with_ontology_chunked()` notifie `extraction_start` et `extraction_chunk_done` → propagé via `ctx.info()` au client
- **Documentation** : `DESIGN/chunking_methodology.md` complète

### Stabilisation & Observabilité ingestion (v0.6.1)
- **Fix boucle infinie chunker** : `_split_group_with_overlap()` pouvait boucler infiniment quand overlap + phrase > chunk_size → vidage overlap forcé si nécessaire
- **Healthcheck Docker** : `python -c "import httpx"` → `curl` (économie ~50MB RAM par check)
- **Libération mémoire** : `del content_base64` + `del content` + `gc.collect()` dans `memory_ingest()`
- **Monitoring RSS** : chaque étape d'ingestion loggue `[RSS=XXmb]`
- **Logs chunker détaillés** : 3 passes avec section-par-section, flush immédiat
- **Progression CLI temps réel** : notifications MCP `ctx.info()` → monkey-patch `_received_notification` → Rich Live display avec barres % extraction + embedding

### Client web graphe amélioré (v0.6.1 → v0.6.4)
- **Toggle MENTIONS (📄)** : bouton toggle dans le header pour afficher/masquer les nœuds Document + arêtes MENTIONS. `displayOptions.showMentions` contrôle le filtrage dans `applyFilters()`. Permet de visualiser uniquement les relations sémantiques.
- **Exit isolation avant ASK** : `submitQuestion()` appelle `exitIsolation()` si mode Focus actif → plus de filtrage résiduel entre deux questions.
- **v0.6.4 Fix toggle Documents en isolation** : test `showMentions` placé AVANT le test d'isolation dans `applyFilters()` — les carrés rouges disparaissent toujours quand le toggle est OFF, même en mode Focus.
- **v0.6.4 Panneau ASK redimensionnable** : poignée de drag en haut du panneau, drag vers le haut = panneau grandit. Body scrollable indépendant (flex layout). `setupAskResize()` dans ask.js.
- **v0.6.4 Export HTML** : bouton "📥 Export HTML" après chaque réponse. Génère un fichier HTML autonome avec CSS inline, branding Cloud Temple, compatible impression. `exportAnswerHtml()` dans ask.js.
- **v0.6.4 Barre d'actions** : conteneur `.ask-actions` regroupe "Isoler" + "Export HTML" sous la réponse.

### Recherche accent-insensitive fulltext (v0.6.2)
- **Index fulltext Neo4j** avec analyzer `standard-folding` (ASCII folding : é→e, ç→c, ü→u)
- `search_entities()` refactorisé : fulltext Lucene (principal) + CONTAINS (fallback)
- `_search_fulltext()` : requête Lucene avec scoring par pertinence, filtre par memory_id
- `_search_contains()` amélioré : envoie tokens raw (avec accents) ET normalisés (sans accents)
- `ensure_fulltext_index()` : lazy init idempotent au premier appel
- `_escape_lucene()` : échappe les caractères spéciaux Lucene
- "réversibilité", "reversibilite", "REVERSIBILITE" → matchent tous les 3 ✅

### Recherche et Q&A (v0.5.2)
- Stop words français enrichis (~45 mots) filtrés dans search_entities
- Tokenisation robuste : `re.findall(r'[a-zA-ZÀ-ÿ]+', ...)` (ponctuation retirée)
- Normalisation des accents : `unicodedata.normalize('NFKD', ...)` → `"résiliation"` matche `"RESILIATION"`
- Recherche AND puis fallback OR dans Neo4j
- **Q&A dual-mode** :
  - **Graph-Guided RAG** : entités trouvées → RAG filtré par doc_ids (précis)
  - **RAG-only fallback** : 0 entités → RAG sur tous les chunks (exhaustif)
  - "Pas d'informations" seulement si NI graphe NI RAG ne trouvent de contexte
- Logs décisionnels complets : tokenisation → graphe → RAG → contexte LLM

## Ce qui reste à faire 🔧

### 🔴 Prioritaire
- [x] **Gestion de l'authentification MCP** — tokens avec memory_ids, enforcement, CLI complète ✅ (02/09/2026)

### Court terme
- [x] Git nettoyage complet + purge historique + force push (session 02/09/2026)
- [ ] Rebuild + ré-ingérer CGA/CGV avec nouvelles limites et ontologie
- [ ] Vérifier extraction exhaustive des articles (23.2 etc.)
- [ ] Ingérer plus de documents (CGVU, Contrat Cadre, Convention de Services)

### Moyen terme
- [x] Chunking sémantique pour les très gros documents ✅ (02/09/2026 — SemanticChunker)
- [ ] **Git-Sync** — Synchronisation automatique mémoire ↔ dépôt Git. Design terminé (`DESIGN/GIT_SYNC_DESIGN.md`). Clone initial auto, sync incrémental via `git diff`, full-sync, dry-run. Script client `scripts/git_sync.py` + intégration CLI Click + Shell. (2026-02-18)
- [ ] Comparer CGA/CGV (outil de diff sémantique)
- [ ] Export du graphe (Cypher, JSON-LD, RDF)
- [ ] Améliorer la visualisation graph.html (couleurs par type, filtres)

### Long terme
- [x] RAG hybride (graphe + embeddings vectoriels) ✅ (02/09/2026 — Graph-Guided RAG Qdrant)
- [ ] Multi-tenant avec isolation des données
- [ ] Dashboard de monitoring
- [ ] API de merge entre mémoires

## Bugs connus corrigés ✅
- **force=True créait des doublons** → supprime l'ancien avant de recréer
- **Hub "Cloud Temple SAS"** → ontologie + prompt anti-hub
- **default.yaml fallback** → supprimé, ontologie obligatoire
- **Shell use avec nom complet** → extrait l'ID, valide côté serveur
- **Documents tronqués à 50K** → configurable via EXTRACTION_MAX_TEXT_LENGTH
- **generate_answer limité à 1000 tokens** → utilise self._max_tokens (60K)
- **Auth 401 sur requêtes internes** → localhost exempt d'auth
- **Limites hardcodées** → tout configurable (limit API + shell + .env)
- **Page blanche client web** → balise `</title>` tronquée en `</titl` → tout le HTML interprété comme titre
- **Ponctuation dans tokens de recherche** (v0.5.2) → `"résiliation?"` avec `?` ne matchait jamais → `re.findall` extrait que les lettres
- **Accents non normalisés** (v0.5.2) → `"résiliation"` ne matchait pas `"RESILIATION"` → normalisation `unicodedata`
- **Q&A retournait "pas d'infos" sans chercher Qdrant** (v0.5.2) → 0 entités graphe = retour immédiat → ajout fallback RAG-only
- **Qdrant `latest` obsolète** (v0.5.2) → client 1.16.2 / serveur 1.14.1 → image épinglée `v1.16.2`
- **Boucle infinie chunker OOM** (v0.6.1) → `_split_group_with_overlap` : overlap + phrase > chunk_size → `i` n'avançait jamais → millions de chunks → 7.47GB RAM → SIGKILL (exit 137) → vidage overlap forcé si nécessaire
- **Healthcheck Docker fork Python** (v0.6.1) → `python -c "import httpx"` forkait un processus Python complet (~50MB) toutes les 30s → remplacé par `curl`
- **EXTRACTION_CHUNK_SIZE trop grand** (v0.6.1) → 200K chars envoyé en 1 appel LLM saturait le contexte gpt-oss:120b (120K tokens) → réduit à 25K chars
- **Recherche "réversibilité" → 0 résultats** (v0.6.2) → Python normalisait les accents (`reversibilite`) mais `toLower()` de Neo4j les conservait (`réversibilité`) → `CONTAINS` échouait → ajout index fulltext `standard-folding` (ASCII folding) + fallback CONTAINS avec double tokens (raw+normalized)
- **RAG quasi inactif seuil 0.65** (v0.6.3) → BGE-M3 produit des scores cosinus ~0.55-0.63 pour les meilleurs chunks → seuil 0.65 éliminait 93% des chunks pertinents → abaissé à **0.58** après benchmark comparatif (`scripts/test_rag_thresholds.py`)
- **Toggle Documents inefficace en mode isolation** (v0.6.4) → `applyFilters()` : `filterState.isolatedNodes.has(n.id)` retournait `true` avant le test `showMentions` → carrés rouges Document visibles même avec toggle OFF → test `showMentions` déplacé avant le test d'isolation
- **CLI 401 sur serveur de production** (v1.2.1) → `scripts/cli/__init__.py` lisait `MCP_SERVER_URL` (pas `MCP_URL`), et Click `envvar="ADMIN_BOOTSTRAP_KEY"` capturait la valeur dev du `.env` local (`admin_bootstrap_key_change_me`) au lieu du token prod → ajout `MCP_URL`/`MCP_TOKEN` prioritaires dans `__init__.py` + Click `envvar` en liste ordonnée
