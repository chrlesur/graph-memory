# Active Context

## Contexte actuel (11 mars 2026)

### Focus : Ontologie software-development v1.2

Nouvelle ontologie créée, testée, auditée et itérée pour l'ingestion de code source dans graph-memory.

**Ontologie v1.2** — `ONTOLOGIES/software-development.yaml` :
- 21 types d'entités (Package, Module, Layer, Class, Function, Middleware, DataModel, Enum, MCPTool, APIEndpoint, Protocol, ExternalService, Dependency, ConfigParameter, DesignPattern, Algorithm, TestCase, Documentation, Feature, InfraComponent, SecurityBoundary)
- 23 types de relations (CONTAINS, PART_OF, BELONGS_TO_LAYER, DEPENDS_ON, IMPORTS, USES, CALLS, INHERITS_FROM, IMPLEMENTS, RETURNS, ACCEPTS, PRODUCES, STORES_IN, EXPOSES, DELEGATES_TO, UPDATES, READS, CONFIGURED_BY, TESTED_BY, DOCUMENTED_IN, IMPLEMENTS_FEATURE, PROTECTS, ROUTES_TO)

### Évolutions v1.0 → v1.1 → v1.2

- **v1.0** : Création initiale (19 entités, 19 relations)
- **v1.1** : Post-audit — +UPDATES, +READS, 12 mappings obligatoires (EXECUTES→CALLS, etc.), nommage canonique pour fusion cross-docs, anti-hub rules, connectivité minimum ≥2, zéro "Other"
- **v1.2** : Post-analyse DESIGN — +InfraComponent, +SecurityBoundary, +PROTECTS, +ROUTES_TO pour couvrir l'architecture d'infrastructure et la sécurité (~95% de SPECIFICATION.md)

### Résultats du test sur QuoteFlow (backend Python/FastAPI)

Audit sur 10 documents ingérés (v1.1) :
- 965 entités, 910 relations
- 99% conformité entités (1 seul type "Other")
- 95% conformité relations (12 types inventés → corrigés en v1.1 avec mappings)
- 33% orphelins (objectif <20% avec v1.2)
- 0% fusion cross-docs (objectif >10% avec nommage canonique v1.1)

### Outils créés

- `scripts/audit_ontology.py` — Audit qualité du graphe (distribution types, hubs, orphelins, fusion, nommage)
- `scripts/ingest_quoteflow.sh` — Ingestion en masse d'un projet complet (189 fichiers QuoteFlow)
- `scripts/test_ontology.py` — Script de test MCP (non utilisé, remplacé par CLI)

### Documentation mise à jour

- VERSION bumpé 1.4.1 → 1.5.0
- CHANGELOG.md — Entrée v1.5.0 complète
- DESIGN/SPECIFICATION.md — Table ontologies §7.2, listing §15, "6 ontologies", footer v1.5.0
- README.md / README.en.md — Changelog factorisé → pointeur CHANGELOG.md, "6 ontologies"

### Ingestion en cours

L'ingestion v1.2 de QuoteFlow (189 fichiers) est en cours en arrière-plan.
Suivi : `tail -f scripts/ingest_quoteflow.log`

### Prochaines étapes

1. Attendre la fin de l'ingestion QuoteFlow et refaire un audit v1.2
2. Comparer les métriques v1.1 vs v1.2 (orphelins, fusion, types inventés)
3. Auto-ingérer graph-memory dans graph-memory (cas d'usage premier de l'ontologie)
4. Tester l'ingestion de code JavaScript/JSX (frontend QuoteFlow)

### Décisions importantes

- Le nommage canonique (format strict par type) est la clé de la fusion cross-documents
- Les mappings obligatoires dans `special_instructions` sont essentiels pour guider le LLM
- L'ontologie code source utilise des limites plus élevées (160/240 vs 60/80) car le code est plus dense
- Les types InfraComponent et SecurityBoundary couvrent l'architecture de déploiement manquante
