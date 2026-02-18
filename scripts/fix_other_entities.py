#!/usr/bin/env python3
"""
Script de reclassification des entités "Other" dans une mémoire.

Analyse les 71 entités de type "Other" identifiées et les reclassifie
vers le type correct en fonction de patterns dans leurs noms/descriptions.

Usage: python scripts/fix_other_entities.py [MEMORY_ID] [--dry-run|--apply]
"""
import sys
import re
import asyncio

sys.path.insert(0, ".")
from scripts.cli.client import MCPClient
from scripts.cli import BASE_URL, TOKEN


# =============================================================================
# Règles de reclassification (ordre = priorité)
# =============================================================================
# Note: tous les patterns sont case-insensitive via re.IGNORECASE dans le code
RECLASSIFICATION_RULES = [
    # --- Modèles IA → Technology ---
    {
        "name_patterns": [
            r"llama", r"deepcoder", r"foundation.sec",
            r"gemma", r"mistral", r"granite",
            r"gpt", r"claude", r"qwen",
        ],
        "new_type": "Technology",
        "reason": "Modèle d'IA → Technology",
    },
    # --- Sécurité physique → SecurityPolicy ---
    {
        "name_patterns": [
            r"destruction certifi", r"transport s[eé]curis",
            r"journaux d.acc[eè]s", r"revue.*journaux",
            r"phishing", r"\bSETA\b",
            r"supervision.*siem",
        ],
        "new_type": "SecurityPolicy",
        "reason": "Mesure de sécurité → SecurityPolicy",
    },
    # --- Budgets dans les références clients → ClientReference ---
    {
        "name_patterns": [
            r"budget annuel", r"valeur.*contrat",
        ],
        "new_type": "ClientReference",
        "reason": "Budget/contrat client → ClientReference",
    },
    # --- Durées de relations client → ClientReference ---
    {
        "name_patterns": [
            r"dur[eé]e relation", r"dur[eé]e projet",
            r"dur[eé]e contrat", r"p[eé]riode.*contrat",
            r"p[eé]riode.*march[eé]",
        ],
        "new_type": "ClientReference",
        "reason": "Durée relation client → ClientReference",
    },
    # --- Fréquences isolées → Governance ---
    {
        "name_patterns": [
            r"^mensuelle$", r"^hebdomadaire$",
            r"^semestrielle$", r"^trimestrielle$",
            r"^unique$", r"^fin de phase$",
            r"r[eé]unions? hebdomadaire",
        ],
        "new_type": "Governance",
        "reason": "Fréquence de comité → Governance",
    },
    # --- Durées/fréquences opérationnelles → KPI ---
    {
        "name_patterns": [
            r"^dur[eé]e\b", r"^duration",
            r"fr[eé]quence de tests", r"fr[eé]quence annuelle",
        ],
        "new_type": "KPI",
        "reason": "Durée/fréquence opérationnelle → KPI",
    },
    # --- Domaines → PresalesDomain ---
    {
        "name_patterns": [
            r"secnumcloud.*s[eé]curit[eé].*conformit[eé]",
            r"HDS.*s[eé]curit[eé].*conformit[eé]",
            r"infrastructure et plateforme",
            r"processus op[eé]rationnels",
        ],
        "new_type": "PresalesDomain",
        "reason": "Domaine thématique → PresalesDomain",
    },
    # --- Programme nommé → Methodology ---
    {
        "name_patterns": [
            r"programme CESAR",
        ],
        "new_type": "Methodology",
        "reason": "Programme structuré → Methodology",
    },
    # --- Activités RACI → ProjectPhase ---
    {
        "name_patterns": [
            r"definition of needs", r"validation of deliverables",
            r"acceptance.*recette", r"service provision",
            r"contracts? and financial",
            r"operational aspects",
            r"transition and transformation",
        ],
        "new_type": "ProjectPhase",
        "reason": "Activité RACI → ProjectPhase",
    },
    # --- Processus de gestion → Methodology ---
    {
        "name_patterns": [
            r"gestion de la qualit[eé]",
            r"gestion des configurations",
            r"gestion des risques",
            r"tableaux de bord",
        ],
        "new_type": "Methodology",
        "reason": "Processus de gestion → Methodology",
    },
    # --- Besoins clients → Requirement ---
    {
        "name_patterns": [
            r"visibilit[eé] compl[eè]te",
            r"suivi en temps r[eé]el",
            r"communication en fran[cç]ais",
            r"interventions sur site",
        ],
        "new_type": "Requirement",
        "reason": "Besoin client → Requirement",
    },
    # --- SLA → SLA ---
    {
        "name_patterns": [
            r"SLA.*REX",
        ],
        "new_type": "SLA",
        "reason": "Engagement de service → SLA",
    },
    # --- Périmètres de service → Service ---
    {
        "name_patterns": [
            r"^syst[eè]mes$",
            r"^stockage$",
            r"middlewares? et bases",
        ],
        "new_type": "Service",
        "reason": "Périmètre de service → Service",
    },
]

# Entités à supprimer (sections de document sans valeur métier)
DELETE_PATTERNS = [
    r"^introduction$",
    r"^pr[eé]sentation g[eé]n[eé]rale$",
    r"^organisation$",
]


async def fix_others(memory_id: str, dry_run: bool = True):
    """Reclassifie les entités 'Other' dans une mémoire."""
    client = MCPClient(BASE_URL, TOKEN)
    result = await client.get_graph(memory_id)
    
    if result.get("status") != "ok":
        print(f"Erreur: {result.get('message')}")
        return
    
    nodes = [n for n in result.get("nodes", []) if n.get("node_type") == "entity"]
    others = [n for n in nodes if n.get("type", "").lower() == "other"]
    
    print(f"\n{'='*70}")
    print(f"  RECLASSIFICATION DES ENTITÉS 'Other' — {'DRY RUN' if dry_run else '⚡ APPLICATION'}")
    print(f"  Mémoire: {memory_id}")
    print(f"  Entités 'Other': {len(others)}")
    print(f"{'='*70}\n")
    
    reclassified = []
    to_delete = []
    unmatched = []
    
    for n in others:
        name = n.get("id", "")
        matched = False
        
        # Vérifier les patterns de suppression
        for pattern in DELETE_PATTERNS:
            if re.match(pattern, name, re.IGNORECASE):
                to_delete.append(n)
                matched = True
                break
        
        if matched:
            continue
        
        # Vérifier les règles de reclassification
        for rule in RECLASSIFICATION_RULES:
            for pattern in rule["name_patterns"]:
                if re.search(pattern, name, re.IGNORECASE):
                    reclassified.append({
                        "name": name,
                        "old_type": "Other",
                        "new_type": rule["new_type"],
                        "reason": rule["reason"],
                    })
                    matched = True
                    break
            if matched:
                break
        
        if not matched:
            unmatched.append(n)
    
    # --- Afficher le plan ---
    print(f"📊 PLAN DE RECLASSIFICATION:")
    print(f"   ✅ Reclassifiés: {len(reclassified)}")
    print(f"   🗑️ À supprimer:  {len(to_delete)}")
    print(f"   ❓ Non matchés:  {len(unmatched)}")
    print()
    
    if reclassified:
        print(f"--- Reclassifications ({len(reclassified)}) ---")
        for r in reclassified:
            print(f"  ✅ '{r['name'][:45]:<45}' Other → {r['new_type']:<20} ({r['reason']})")
    
    if to_delete:
        print(f"\n--- Suppressions ({len(to_delete)}) ---")
        for d in to_delete:
            print(f"  🗑️ '{d.get('id', '?')}'")
    
    if unmatched:
        print(f"\n--- Non matchés ({len(unmatched)}) ---")
        for u in unmatched:
            print(f"  ❓ '{u.get('id', '?')[:50]}' | {(u.get('description') or '')[:60]}")
    
    if dry_run:
        print(f"\n💡 Pour appliquer: python scripts/fix_other_entities.py {memory_id} --apply")
        return
    
    # --- Appliquer via Neo4j ---
    print(f"\n⚡ APPLICATION EN COURS...")
    
    # On va construire un script Cypher exécuté via une connexion directe
    from neo4j import AsyncGraphDatabase
    from src.mcp_memory.config import get_settings
    
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    
    async with driver.session(database=settings.neo4j_database) as session:
        # Reclassifications
        reclass_count = 0
        for r in reclassified:
            result = await session.run(
                """
                MATCH (e:Entity {name: $name, memory_id: $memory_id, type: 'Other'})
                SET e.type = $new_type, e.updated_at = datetime()
                RETURN count(e) as updated
                """,
                name=r["name"],
                memory_id=memory_id,
                new_type=r["new_type"],
            )
            record = await result.single()
            if record and record["updated"] > 0:
                reclass_count += 1
                print(f"  ✅ {r['name'][:40]} → {r['new_type']}")
        
        # Suppressions
        delete_count = 0
        for d in to_delete:
            name = d.get("id", "")
            result = await session.run(
                """
                MATCH (e:Entity {name: $name, memory_id: $memory_id, type: 'Other'})
                DETACH DELETE e
                RETURN count(e) as deleted
                """,
                name=name,
                memory_id=memory_id,
            )
            record = await result.single()
            if record and record["deleted"] > 0:
                delete_count += 1
                print(f"  🗑️ Supprimé: {name}")
    
    await driver.close()
    
    print(f"\n{'='*70}")
    print(f"  RÉSULTAT:")
    print(f"  ✅ Reclassifiés: {reclass_count}/{len(reclassified)}")
    print(f"  🗑️ Supprimés:    {delete_count}/{len(to_delete)}")
    print(f"  ❓ Non traités:  {len(unmatched)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    mid = sys.argv[1] if len(sys.argv) > 1 else "PRESALES"
    apply = "--apply" in sys.argv
    asyncio.run(fix_others(mid, dry_run=not apply))
