#  Active Context

## Focus actuel (mis à jour 2026-02-19)

### Ontologie general.yaml v1.1 — Réduction "Other" REFERENTIEL v1.3.7 (SESSION COURANTE — 2026-02-19)

**Problème identifié** : La mémoire REFERENTIEL (2727 entités, 20 docs, ontologie `general`) contenait **299 entités "Other" (11%)**, principalement issues de textes réglementaires : NIS2 (107), rapport NEURONES (90), DORA (67), PAMS ANSSI (20), SecNumCloud (7), HDS (6).

**Analyse** : Script `analyze_entities.py` + `analyze_others.py` + script REST ad hoc pour examiner les 299 "Other" par document source. Catégorisation en **14 patterns** : articles de loi (~120), secteurs réglementés (~30), stakeholders RSE (~20), sanctions (~15), deadlines/durées (~20), résolutions AG (~15), impacts RSE (~12), rapports (~8), zones sécurité PAMS (~14), qualifications ANSSI (~4), rôles (~3), acronymes (~8), gouvernance (~10), composants infra (~2).

**Corrections ontologie `general.yaml` v1.0 → v1.1** :
- **+4 types d'entités** (24→28) : `LegalProvision` (articles, considérants, annexes), `Sector` (secteurs NIS2/DORA/NACE), `Sanction` (amendes, astreintes, suspensions), `Stakeholder` (parties prenantes RSE)
- **+2 types de relations** (22→24) : `APPLIES_TO` (réglementation→secteur), `IMPOSES` (provision→sanction)
- **~50 lignes de `special_instructions`** : règles textes réglementaires, règles RSE/matérialité, 15 mappings obligatoires additionnels (qualif ANSSI→Certification, rapports→Evidence, zones→Topic, comités→Organization, réunions→Action, rôles non nommés→ignorer, acronymes→Definition, deadlines/durées/fréquences→intégrés, status→ignorer)
- **+1 exemple d'extraction** réglementaire, `priority_entities` +LegalProvision +Sanction

**Action requise** : Redéployer en production (`git pull && docker compose build mcp-memory && docker compose up -d`) puis ré-ingérer les 7 documents problématiques avec `--force`.

---

### Qualité ontologies — Réduction "Other" à 0% (SESSION COURANTE — 2026-02-18)

**Problème identifié** : L'ingestion de `docs/` (110 docs) produisait **159 entités "Other"** (11.6% de 1376), et PRESALES avait 71 "Other". Le LLM inventait des types non définis dans les ontologies (MonetaryAmount, Duration, Endpoint, Licence, Feature, Priority, etc.) qui tombaient en "Other".

**Analyse** : Script `analyze_others.py` catégorise les 159 "Other" de DOCS en :
- **À ajouter** (~13%): Role (RBAC), SLALevel (P1-P5, Impact, Criticité) — types utiles absents
- **À mapper** (~38%): Endpoint→API, Licence→PricingModel, HA→Technology, Feature→NetworkComponent
- **À exclure** (~25%): CLI flags, variables, erreurs, chemins, paramètres API
- **À intégrer** (~24%): Durées, langues → dans le nom de l'entité parente

**Corrections ontologie `cloud.yaml` v1.1 → v1.2** :
- **+2 entity types** : `Role` (IAM/RBAC), `SLALevel` (P1-P5, Impact I1-I3, Criticité C1-C3)
- **+50 lignes de `special_instructions`** avec : 12 mappings obligatoires (⚠️ "Ne crée JAMAIS de type X"), 8 catégories d'exclusion, règle de qualité des noms

**Corrections ontologie `presales.yaml` v1.0 → v1.1** :
- Mapping MonetaryAmount/Duration → ClientReference/PricingModel dans special_instructions

**Nouveaux scripts d'analyse** (`scripts/`) :
- `analyze_entities.py` : distribution types/relations d'une mémoire
- `analyze_others.py` : détail des "Other" par document source + patterns
- `fix_other_entities.py` : reclassification Cypher des "Other" existants

**Tests de ré-ingestion : 4/4 = 0 Other** :
| Document | Other avant | Other après |
|---|---|---|
| presales/01_Références_client.md | 12 | **0** |
| docs/network/forti.md | 9 | **0** |
| docs/llmaas/llmaas.md | 11 | **0** |
| docs/iaas_bare-metal/quickstart.md | ~5 | **0** |

**Action** : ré-ingérer entièrement DOCS avec `ingestdir` pour appliquer la nouvelle ontologie.

---

### Outil system_about + Starter Kit + Robustification client v1.3.5 (SESSION COURANTE — 2026-02-18)

**Nouvel outil `system_about`** — Carte d'identité complète du service MCP Memory :
- Identité, capacités (28 outils / 8 catégories), 5 ontologies, formats supportés
- Mémoires actives avec compteurs, état des 5 services, configuration LLM/RAG
- Commande `about` dans CLI Click + shell interactif + affichage Rich (`show_about`)
- 28 outils MCP exposés (27 → 28)

**Starter Kit développeur** (`starter-kit/`) :
- Guide `README.md` : processus en 4 étapes pour ajouter un outil MCP
- Boilerplate fonctionnel dans `starter-kit/boilerplate/` (Docker, WAF, CLI, auth)

**Robustification `client.py`** :
- `call_tool()` gère `isError=True`, réponse vide, réponse non-JSON
- Plus de crash `json.loads` sur erreurs serveur → messages exploitables

**Bug identifié et documenté** : `scripts/.env` charge `MCP_URL` pointant vers production via `load_dotenv()`. Le serveur de production n'a pas encore `system_about` → "Unknown tool". Fonctionne sur localhost après `--url http://localhost:8080`. **Action** : redéployer en production.

---

### CLI ingestdir — Progression temps réel + Fix --exclude v1.3.4 (SESSION COURANTE — 2026-02-18)

**Alignement UX** : `ingestdir` (batch) utilise maintenant `run_ingest_with_progress()` pour chaque fichier, identique à `ingest` (unitaire). Appliqué dans les deux interfaces (Shell interactif et CLI Click).

**Bug corrigé** — Parser `--exclude` cassé dans le shell :
- L'ancien parser artisanal (recherche de sous-chaîne) avait 3 bugs : typos non détectées (`--excluse` collé au chemin), guillemets non strippés (`fnmatch` échouait), options inconnues silencieuses
- **Fix** : réécriture avec `shlex.split()` (parsing POSIX) + itération par tokens + détection d'options inconnues
- CLI Click non affectée (Click gère nativement `@click.option("--exclude", multiple=True)`)

**Améliorations** :
- Progression temps réel par fichier : barres ASCII LLM/embedding, compteurs, timer
- Header enrichi : `[3/15] 📥 bastion/concepts.md (12.4 KB)`
- Résumé par fichier : `✅ concepts.md: 12+3 entités, 8+2 relations (45.2s)`
- Autocomplétion : `--exclude` et `--confirm` ajoutés

**Fichiers modifiés** : `scripts/cli/shell.py`, `scripts/cli/commands.py`

---

### Ontologie cloud.yaml v1.1 (SESSION COURANTE — 2026-02-18)

**Audit et amélioration** de l'ontologie `cloud.yaml` après confrontation avec le contenu réel de ~30 documents `DOCS/` et ~15 fiches `PRODUCT/`.

**Analyse** :
- Lecture de 12 documents échantillons (IaaS VMware, Block Storage, Managed K8s, Bastion, LLMaaS, Housing, IAM, SLA, Network)
- Comparaison avec les 4 autres ontologies (legal, technical, managed-services, presales)
- Audit du code `ontology.py` et `extractor.py` pour vérifier la compatibilité technique

**Modifications v1.0 → v1.1** :
- **+4 entity types** : `PricingModel` (tarification omniprésente dans PRODUCT), `StorageClass` (5 classes IOPS), `BackupSolution` (IBM SPP, VMware Replication), `AIModel` (LLMaaS)
- **+5 relation types** : `COMPATIBLE_WITH`, `SUPPORTS`, `PART_OF`, `DEPENDS_ON`, `HAS_PRICING` (14→19 relations, aligné avec les autres ontologies)
- **`priority: high`** ajouté sur `CloudService` et `Technology` (en plus de `Certification` et `SLA`)
- **`priority_entities`** enrichi : +`StorageClass`, +`PricingModel`
- **Nettoyage `extraction_rules`** : suppression de 4 champs non reconnus par le code (`include_metrics`, `include_durations`, `include_amounts`, `extract_implicit_relations`)
- **+1 exemple d'extraction** basé fiche produit (Bastion, StorageClass, pricing, backup)
- **Contexte LLM enrichi** : consignes pour fiches produits (tarification, compatibilités, modèles IA)
- **Exemples d'entités enrichis** : ajout noms réels (PAR7S, TH3S, Cisco UCS B200, Intel Xeon Gold, Thales Luna, ISAE 3402, etc.)

**Script utilitaire** : `scripts/validate_ontology.py` créé puis supprimé (utilitaire ponctuel, validation terminée).

**Résultat validation structurelle** : ✅ 24 entity types, 19 relation types, 2 exemples, 0 erreur, 0 avertissement.

**Validation en conditions réelles (v1.3.3)** — Ingestion de 2 fiches produits avec ontologie cloud v1.1 :
- IaaS VMware (13.6 KB) : **40 entités, 52 relations, 0 "Other"** — StorageClass:6, PricingModel:1, BackupSolution:1
- LLMaaS (19.5 KB) : **33 entités, 36 relations, 2 "Other" (6%)** — AIModel:6, PricingModel:4
- **Total : 73 entités, 97.3% correctement typées**, 18/24 types utilisés, 88 relations
- Les 2 "Other" sont des cas marginaux (préavis contractuel + doublon SLA déjà capturé)

---

### Design Git-Sync (SESSION COURANTE — 2026-02-18)

**Nouveau module conçu** : synchronisation automatique d'une mémoire MCP avec un dépôt Git distant.

**Document de design** : `DESIGN/GIT_SYNC_DESIGN.md`

**Principe** :
1. Un script client autonome (`scripts/git_sync.py`) lancé par cron ou manuellement
2. Clone le repo si nécessaire, puis `git pull` à chaque exécution
3. Analyse le delta via `git diff --name-status <last_commit>..HEAD`
4. Applique les changements à la mémoire MCP :
   - **A (added)** → `memory_ingest` (nouveau fichier)
   - **M (modified)** → `memory_ingest(force=True)` (ré-extraction complète)
   - **D (deleted)** → `document_delete` (suppression cascade Neo4j + Qdrant + S3)
   - **R (renamed)** → delete ancien + ingest nouveau
5. Maintient un fichier d'état `.git-sync-state.json` (dernier commit synchronisé)

**Décisions prises** :
- Clone initial automatique si le repo n'existe pas localement
- Support `--subdir` pour synchroniser un sous-dossier vers une mémoire spécifique
- Pas de mapping multi-mémoires (un repo = une mémoire)
- Script client uniquement (pas d'outil MCP côté serveur pour l'instant)
- Mapping fichier ↔ document via `source_path` (chemin relatif dans le repo)

**Modes** :
- **Incrémental** (défaut) : delta git depuis le dernier commit synchro
- **Full sync** (`--full-sync`) : réconciliation complète fichiers locaux vs documents en mémoire
- **Dry run** (`--dry-run`) : simulation sans modification

**Briques existantes réutilisées** :
- Déduplication par hash SHA-256 (skip automatique des fichiers inchangés)
- `force=True` sur `memory_ingest` (supprime l'ancien + recréé)
- `document_delete` (cascade: Neo4j + Qdrant + S3)
- `source_path` dans les métadonnées du nœud Document
- `MCPClient` de `scripts/cli/client.py` pour la communication HTTP/SSE

**Statut** : Design terminé, prêt pour implémentation future.

**Intégration CLI prévue** :
- `document git-sync` (CLI Click)
- `git-sync` (shell interactif)
- Fonctions display dans `display.py`

---

### Intégration ontologie presales v1.2.5 ✅

**Nouvelle ontologie `presales.yaml`** ajoutée dans `ONTOLOGIES/` pour les usages avant-vente et génération de propositions commerciales (RFP/RFI) Cloud Temple.

**Contenu de l'ontologie** :
- **28 types d'entités** répartis en 6 familles : Acteurs & Personnes, Sécurité & Conformité, Technique & Infrastructure, Gouvernance & Méthodologie, Commercial & Valeur, Contexte & Indicateurs
- **30 types de relations** répartis en 5 familles : Capacité & Conformité, Technique, Gouvernance, Commerciale, Structurelle & Contexte
- Entités prioritaires : `Service`, `Certification`, `Differentiator`, `Requirement`, `SLA`, `ClientReference`
- Relations prioritaires : `HAS_CERTIFICATION`, `GUARANTEES`, `TARGETS_PERSONA`, `ANSWERED_BY`, `PART_OF_DOMAIN`, `PROVEN_BY`
- Limites adaptées : `max_entities: 60`, `max_relations: 80` (ontologie plus riche que les autres)

**Correction YAML** : le fichier d'origine contenait des patterns YAML invalides (`- "Texte" (annotation)`) corrigés en `- "Texte (annotation)"` sur 8 blocs (Organization, Person, Persona, Methodology, Technology, KPI, PresalesDomain).

**Défauts Python relevés à 60/80** (`src/mcp_memory/core/ontology.py`) :
- Dataclass `ExtractionRules` : `max_entities: int = 60`, `max_relations: int = 80`
- Loader `_load_ontology_file` : `rules_data.get('max_entities', 60)`, `rules_data.get('max_relations', 80)`
- Impact : toutes les ontologies sans valeur explicite (legal, cloud, technical, managed-services) bénéficient maintenant des limites 60/80. `presales.yaml` conserve ses valeurs explicites identiques.

**Déployé en local** : rebuild + redémarrage. Vérification : `python3 scripts/mcp_cli.py ontologies` → 5 ontologies disponibles.

**⚠️ Production** : sur le serveur `prod-docker02`, faire `git pull && docker compose build mcp-memory && docker compose up -d mcp-memory`.

---

### Factorisation CLI Click / Shell interactif v1.2.4 ✅ (SESSION COURANTE)

Le code dupliqué entre `commands.py` (CLI Click) et `shell.py` (shell interactif) a été factorisé :

**Nouveau module `scripts/cli/ingest_progress.py`** :
- `create_progress_state()`, `make_progress_bar()`, `create_progress_callback()`, `run_ingest_with_progress()`
- Toute la mécanique Rich Live + parsing SSE en un seul endroit

**Fonctions partagées ajoutées dans `display.py`** :
- `format_size()` publique (3 copies → 1)
- `show_ingest_preflight()`, `show_entities_by_type()`, `show_relations_by_type()`

**Résultat** : ~300 lignes de duplication supprimées, 0 changement fonctionnel.
Architecture CLI : `__init__.py` → `client.py` → `display.py` → `ingest_progress.py` → `commands.py` / `shell.py`

### Alignement Shell interactif — Progression ingestion temps réel v1.2.3 ✅

**Problème** : La commande `ingest` dans le shell interactif (`shell.py`) n'affichait qu'un simple spinner pendant l'ingestion, alors que la commande Click (`commands.py`) affichait une progression riche en temps réel avec barres ASCII, compteurs d'entités/relations et phases détaillées.

**Écart constaté** :
| Fonctionnalité | CLI Click (`commands.py`) | Shell (`shell.py`) avant |
|---|---|---|
| Callback `on_progress` | ✅ Parse notifications serveur | ❌ Non utilisé |
| Barres ASCII `█████░░░` | ✅ Extraction LLM + Embedding | ❌ Absent |
| Phases détaillées | ✅ S3→texte→LLM→Neo4j→chunking→embedding→Qdrant | ❌ Spinner unique |
| Compteurs temps réel | ✅ Entités/Relations pendant extraction | ❌ Absent |
| Rich Live display | ✅ 4 rafraîchissements/seconde | ❌ Non |

**Correction** : Copie du mécanisme complet de progression dans `cmd_ingest` du shell :
- `_progress_state` dict pour tracker les phases et compteurs
- `_on_progress()` async callback qui parse les messages serveur via regex
- `_make_bar()` pour les barres ASCII avec pourcentage
- `_update_display()` coroutine avec `Rich Live` (refresh 4x/s)
- Passage de `on_progress=_on_progress` à `client.call_tool()`

**Résultat** : Le shell interactif affiche maintenant la même progression temps réel que la CLI Click pour l'ingestion de documents.

### Fix HTTP 421 — HostNormalizerMiddleware pour reverse proxy v1.2.2 ✅

**Problème** : Les clients MCP (Cline, CLI, agents IA) ne pouvaient pas se connecter au serveur de production via SSE. Les endpoints `/sse` et `/messages/*` retournaient **HTTP 421 "Invalid Host header"**.

**Cause racine** :
- Le reverse proxy (nginx → Caddy → MCP) transmet le `Host` header public (`graph-mem.mcp.cloud-temple.app`)
- Le MCP SDK (Starlette) valide le Host header et rejette toute valeur autre que `localhost:8002`
- Les routes `/api/*` fonctionnaient car interceptées par `StaticFilesMiddleware` (notre code) avant d'atteindre Starlette
- Seules les routes `/sse` et `/messages/*` (gérées par `mcp.sse_app()` = Starlette) étaient affectées

**Correction (double fix)** :
1. **Fix principal** : `FastMCP(host=settings.mcp_server_host)` → `host="0.0.0.0"` désactive la protection DNS rebinding du SDK MCP v1.26+ (`TransportSecurityMiddleware`). Le SDK ne vérifie le Host header QUE si `host` est dans `("127.0.0.1", "localhost", "::1")`.
   - Ref: `mcp/server/fastmcp/server.py` ligne 166 + `mcp/server/transport_security.py`
2. **Ceinture de sécurité** : `HostNormalizerMiddleware` ASGI entre `StaticFilesMiddleware` et `mcp.sse_app()` — normalise le Host header vers `localhost` comme protection supplémentaire.

**Pile de middlewares (ordre d'exécution)** :
```
AuthMiddleware → LoggingMiddleware → StaticFilesMiddleware → HostNormalizerMiddleware → mcp.sse_app()
```

**Amélioration client** :
- Nouvelle méthode `_extract_root_cause()` dans `scripts/cli/client.py`
- Descend récursivement dans les `ExceptionGroup`/`TaskGroup` pour extraire le vrai message d'erreur
- Suggestion de diagnostic si erreur Host détectée

**⚠️ Action requise** : Rebuild Docker sur le serveur Cloud Temple (`git pull && docker compose build mcp-memory && docker compose up -d mcp-memory`)

### Fix CLI production — Variables MCP_URL / MCP_TOKEN v1.2.1 ✅

**Problème** : Le CLI (`mcp_cli.py`) ne pouvait pas se connecter au serveur de production déployé sur `https://graph-mem.mcp.cloud-temple.app`.

**Cause racine** (double conflit de variables d'environnement) :
1. `scripts/cli/__init__.py` lisait `MCP_SERVER_URL` (pas `MCP_URL`) comme variable d'env
2. `scripts/cli/commands.py` : les options Click déclaraient `envvar="ADMIN_BOOTSTRAP_KEY"` → `load_dotenv()` chargeait le `.env` local dev (`ADMIN_BOOTSTRAP_KEY=admin_bootstrap_key_change_me`) qui **écrasait** le default calculé depuis `MCP_TOKEN`

**Corrections** :
- `__init__.py` : `MCP_URL` et `MCP_TOKEN` prioritaires (fallback `MCP_SERVER_URL` / `ADMIN_BOOTSTRAP_KEY`)
- `commands.py` : Click `envvar=["MCP_URL", "MCP_SERVER_URL"]` et `["MCP_TOKEN", "ADMIN_BOOTSTRAP_KEY"]` — première trouvée gagne
- Documentation complète : `scripts/README.md`, `DESIGN/DEPLOIEMENT_PRODUCTION.md` §15, `.env.example`

**Règle** : `.env` = config **serveur** (S3, Neo4j, etc.) / `MCP_URL` + `MCP_TOKEN` = config **client CLI** (pas dans le .env)

### Déploiement production v1.2.0 ✅

- Serveur déployé sur `prod-docker02` (192.168.10.21)
- URL : `https://graph-mem.mcp.cloud-temple.app`
- TLS géré par reverse proxy nginx en amont (pas par Caddy)
- WAF en mode HTTP `:8080` (`SITE_ADDRESS=:8080`)
- Guide complet : `DESIGN/DEPLOIEMENT_PRODUCTION.md`

### Backup / Restore complet v1.2.0 ✅

**Système de backup/restore** implémenté et testé pour les 3 couches de données :
- **Neo4j** (graphe : Memory, Documents, Entités, Relations, Mentions)
- **Qdrant** (vecteurs RAG : chunks embeddings avec payloads)
- **S3** (documents originaux : vérification d'existence + re-upload depuis archive)

**Architecture** :
- `core/backup.py` — `BackupService` : orchestrateur backup/restore/list/download/delete/restore_from_archive
- Stockage des backups sur S3 : `_backups/{memory_id}/{timestamp}/` (graph_data.json + qdrant_vectors.jsonl + manifest.json + document_keys.json)
- `graph.py` : `export_full_graph()` / `import_full_graph()` (Cypher MERGE idempotent)
- `vector_store.py` : `export_all_vectors()` / `import_vectors()` (scroll Qdrant complet)
- Config : `BACKUP_RETENTION_COUNT=5` (rotation automatique)

**7 outils MCP** ajoutés dans `server.py` :
1. `backup_create` — Backup complet (graphe + vecteurs + manifest + document_keys)
2. `backup_list` — Liste les backups (optionnel: par memory_id)
3. `backup_restore` — Restaure graphe + vecteurs depuis backup S3 (mémoire ne doit pas exister)
4. `backup_download` — Archive tar.gz en base64 (optionnel: `include_documents` pour inclure les PDFs/DOCX)
5. `backup_delete` — Supprime un backup de S3
6. `backup_restore_archive` — **Restaure depuis une archive tar.gz locale** (base64) :
   - Extrait le tar.gz en mémoire
   - Vérifie les checksums SHA-256 des documents inclus
   - Re-uploade les documents sur S3 avec leurs clés originales
   - Restaure le graphe Neo4j + vecteurs Qdrant

**Cycle complet validé** :
1. ✅ Create mémoire + ingest document → 8 entités, 10 relations, 4 vecteurs
2. ✅ Backup + download tar.gz avec `--include-documents` → 23.2 KB (contient `documents/test-doc-backup.md`)
3. ✅ Suppression TOTALE (mémoire + backup S3 = plus rien côté serveur)
4. ✅ **Restore depuis fichier tar.gz local** en 0.3s → graphe + vecteurs + document S3 tous restaurés
5. ✅ Vérification `storage check` : 1/1 docs accessibles sur S3, 8 entités intactes

**CLI complète** (3 couches alignées) :
- Click : `backup create/list/restore/download/delete/restore-file`
- Shell : commandes correspondantes dans shell interactif
- Display : `show_backup_result()`, `show_backups_table()`, `show_restore_result()`

### Fix storage_check v1.2.0 ✅

Deux bugs corrigés dans `storage_check` (server.py) :
1. **Exclusion `_backups/`** — Les fichiers du préfixe `_backups/` étaient signalés comme orphelins. Ajout d'un filtre au même titre que `_health_check/` et `_ontology_`.
2. **Scope multi-mémoires pour orphelins** — Quand scopé à une mémoire (`storage check JURIDIQUE`), les orphelins étaient calculés en ne considérant que les docs de cette mémoire, donc les 38 docs des autres mémoires apparaissaient comme faux-positifs. Maintenant, la détection d'orphelins charge TOUTES les mémoires même quand scopé.

Résultat : `storage check JURIDIQUE` passe de 42 faux orphelins à **1 seul vrai orphelin** (177 KB).

### Sécurité WAF v1.1.0 — Rate Limiting + Analyse de Risques

**Rate Limiting** implémenté et testé ✅ :
- Module `caddy-ratelimit` compilé dans l'image WAF (`waf/Dockerfile` via `xcaddy`)
- 4 zones par IP dans `waf/Caddyfile` : SSE 10/min, messages 60/min, API 30/min, global 200/min
- Testé : 30 requêtes passent, 31e → HTTP 429 (exact)
- Script de test : `scripts/test_rate_limit.sh`

**Analyse de Risques Sécurité** créée (`DESIGN/ANALYSE_RISQUES_SECURITE.md`) :
- Matrice complète par route (/sse, /messages, /api, /public)
- Conformité OWASP Top 10, SecNumCloud, RGPD

### Infrastructure sécurisée (v0.6.6 → v1.0.0)

- **Coraza WAF** : reverse proxy OWASP CRS, seul port 8080 exposé
- **TLS Let's Encrypt natif** : `SITE_ADDRESS` pour basculer dev/prod
- **Container non-root** : `USER mcp`
- **Réseau Docker isolé** : Neo4j/Qdrant internes uniquement

## Règle d'alignement — TOUJOURS RESPECTER

```
API MCP → CLI Click (commands.py) → Shell interactif (shell.py)
```

**Toute nouvelle fonctionnalité doit être ajoutée dans les TROIS couches.**

## Décisions architecturales
- **28 outils MCP** exposés via HTTP/SSE (v1.3.5)
- Client web modulaire : 8 fichiers < 210 lignes
- CLI Click = interface scriptable, Shell = interface interactive
- Même affichage Rich (fonctions display.py partagées)
- Couplage strict : Neo4j + Qdrant obligatoires
- Extraction graph : séquentielle avec contexte cumulatif (pas de parallélisme)
- Chunks d'extraction : ~25K chars (~6K tokens)
- Notifications MCP : `ctx.info()` côté serveur → `_received_notification` côté client
- Backups stockés sur S3 (même bucket, préfixe `_backups/`)
- Restore depuis archive : re-upload docs S3 + checksum SHA-256

### Durcissement sécurité backup v1.2.0 ✅ (SESSION COURANTE)

**5 failles corrigées** dans le système de backup :

1. **🔴 Path traversal dans `restore_from_archive`** — Un nom de fichier malveillant dans l'archive (`../../etc/passwd`) pouvait être injecté. Ajout de :
   - Rejet des noms contenant `..` ou commençant par `/`
   - Normalisation via `os.path.basename()`
   - Log des rejets et normalisations dans stderr

2. **🔴 Injection dans `backup_id`** — Le `backup_id` (format `memory_id/timestamp`) était utilisé sans validation pour construire des clés S3. Ajout de `_validate_backup_id()` :
   - Regex `^[A-Za-z0-9_-]+$` sur chaque composant
   - Bloque `../secrets/config` et similaires
   - Appliqué dans `restore_backup`, `download_backup`, `delete_backup`

3. **🟡 Contrôle permission `write`** — Les outils backup destructeurs n'exigeaient aucune permission spécifique. Ajout de `check_write_permission()` dans `auth/context.py` :
   - Vérifie que le token a la permission `write` ou `admin`
   - Appliqué à `backup_create`, `backup_restore`, `backup_delete`, `backup_restore_archive`
   - Token read-only ne peut plus modifier les backups

4. **🟡 Cross-memory access control** — Un token autorisé pour JURIDIQUE pouvait accéder aux backups de CLOUD. Maintenant :
   - `backup_restore/download/delete` extraient le `memory_id` du `backup_id` via `_validate_backup_id()`
   - Appel `check_memory_access(memory_id)` AVANT l'opération

5. **🟡 Limite taille archive** — `restore_from_archive` acceptait des archives de taille illimitée (DoS). Ajout de :
   - `MAX_ARCHIVE_SIZE_BYTES = 100 MB`
   - Rejet immédiat avant extraction tar.gz

**Fichiers modifiés** : `core/backup.py`, `auth/context.py`, `server.py`

### Fix UX CLI v1.2.0 ✅

- **Backup ID non tronqué** : colonne `no_wrap=True` + `min_width=35` dans `show_backups_table()` (display.py)
- **Date non tronquée** : colonne `no_wrap=True` + `min_width=19`
- **`backup-download --include-documents`** : option ajoutée dans le shell (détection, passage à l'API, aide contextuelle)
- **Autocomplétion** : `--include-documents` et `--force` ajoutés à `SHELL_COMMANDS`
- **Table d'aide** : backup-download mentionne `--include-documents`
- **README CLI** (`scripts/README.md`) : section Backup/Restore complète ajoutée (Click + Shell), option `--include-documents` documentée
- **README principal** : noms de commandes shell corrigés (`backup-create` au lieu de `backup create`)

## Prochaines étapes
- [ ] Ingérer plus de documents juridiques (CGVU, Contrat Cadre, Convention de Services)
- [ ] Améliorer la détection de sections DOCX (tables converties en texte plat)
- [ ] Export du graphe (JSON-LD, RDF, Cypher)
- [ ] Dashboard de monitoring
- [ ] Comparer CGA/CGV (outil de diff sémantique)
- [ ] Backup/restore via interface web (pas seulement CLI)
