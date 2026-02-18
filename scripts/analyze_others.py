#!/usr/bin/env python3
"""Analyse détaillée des entités 'other' et 'name=?' dans une mémoire."""
import sys
import asyncio
from collections import Counter

sys.path.insert(0, ".")
from scripts.cli.client import MCPClient
from scripts.cli import BASE_URL, TOKEN


async def analyze_others(memory_id: str):
    client = MCPClient(BASE_URL, TOKEN)
    result = await client.get_graph(memory_id)
    
    if result.get("status") != "ok":
        print(f"Erreur: {result.get('message', 'unknown')}")
        return

    nodes = [n for n in result.get("nodes", []) if n.get("node_type") == "entity"]
    
    # Trouver les entités problématiques
    problematic = [n for n in nodes if (
        n.get("type", "").lower() in ("other", "unknown")
        or n.get("label", "").strip() in ("", "?")
        or n.get("id", "").strip() in ("", "?")
    )]
    
    # Trouver TOUTES les entités avec name="?" indépendamment du type
    question_mark = [n for n in nodes if n.get("id", "").strip() == "?"]
    
    print(f"\n{'='*70}")
    print(f"  ANALYSE DES ENTITÉS PROBLÉMATIQUES: {memory_id}")
    print(f"  Total entités: {len(nodes)}")
    print(f"  Entités 'other'/'unknown': {len([n for n in nodes if n.get('type', '').lower() in ('other', 'unknown')])}")
    print(f"  Entités avec name='?': {len(question_mark)}")
    print(f"  Entités problématiques (union): {len(problematic)}")
    print(f"{'='*70}\n")
    
    # Analyser les documents sources des entités "?"
    source_doc_counter = Counter()
    for n in problematic:
        for doc_id in n.get("source_docs", []):
            source_doc_counter[doc_id] += 1
    
    # Map doc_id -> filename
    docs = result.get("documents", [])
    doc_map = {d["id"]: d.get("filename", d["id"]) for d in docs}
    
    print(f"--- Documents produisant des entités problématiques ---")
    print(f"{'DOCUMENT':<50} {'COUNT':>5}")
    print("-" * 57)
    for doc_id, count in source_doc_counter.most_common(30):
        filename = doc_map.get(doc_id, doc_id[:20])
        print(f"{filename:<50} {count:>5}")
    
    # Détail complet des entités "other" avec description
    print(f"\n--- Détail des entités problématiques (type + description) ---")
    type_counter = Counter()
    for i, n in enumerate(problematic):
        name = n.get("id", "?")
        etype = n.get("type", "?")
        desc = (n.get("description") or "")[:100]
        srcs = n.get("source_docs", [])
        src_names = [doc_map.get(s, s[:12]) for s in srcs[:2]]
        type_counter[etype] += 1
        if i < 80:
            print(f"  [{i+1:>3}] type={etype:<15} name='{name}' | {desc}")
            if src_names:
                print(f"        docs: {', '.join(src_names)}")
    
    if len(problematic) > 80:
        print(f"\n  ... et {len(problematic) - 80} autres")
    
    # Vérifier s'il y a des entités avec des noms vides ou très courts
    short_names = [n for n in nodes if len(n.get("id", "").strip()) <= 2]
    print(f"\n--- Entités avec noms très courts (≤2 chars) ---")
    print(f"Total: {len(short_names)}")
    for n in short_names[:20]:
        print(f"  name='{n.get('id', '?')}' type={n.get('type', '?')} desc='{(n.get('description') or '')[:60]}'")


if __name__ == "__main__":
    mid = sys.argv[1] if len(sys.argv) > 1 else "PRESALES"
    asyncio.run(analyze_others(mid))
