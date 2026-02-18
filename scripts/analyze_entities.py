#!/usr/bin/env python3
"""Analyse des entités par type dans une mémoire."""
import sys
import json
import asyncio
from collections import Counter

sys.path.insert(0, ".")
from scripts.cli.client import MCPClient
from scripts.cli import BASE_URL, TOKEN


async def analyze(memory_id: str):
    client = MCPClient(BASE_URL, TOKEN)
    result = await client.get_graph(memory_id)
    
    if result.get("status") != "ok":
        print(f"Erreur: {result.get('message', 'unknown')}")
        return

    nodes = [n for n in result.get("nodes", []) if n.get("node_type") == "entity"]
    edges = [e for e in result.get("edges", []) if e.get("type") != "MENTIONS"]
    docs = result.get("documents", [])
    
    print(f"\n{'='*60}")
    print(f"  ANALYSE DE LA MÉMOIRE: {memory_id}")
    print(f"  Entités: {len(nodes)} | Relations: {len(edges)} | Documents: {len(docs)}")
    print(f"{'='*60}\n")
    
    # --- Entités par type ---
    # Le champ dans get_full_graph() est "type", pas "entity_type"
    type_counts = Counter(n.get("type", "UNKNOWN").lower() for n in nodes)
    print(f"{'TYPE':<30} {'COUNT':>6} {'%':>6}")
    print("-" * 44)
    for t, c in type_counts.most_common():
        pct = 100 * c / len(nodes)
        marker = " ⚠️" if t in ("other", "unknown", "") else ""
        print(f"{t:<30} {c:>6} {pct:>5.1f}%{marker}")
    print("-" * 44)
    print(f"{'TOTAL':<30} {len(nodes):>6}")
    
    # --- Focus sur les "other" ---
    others = [n for n in nodes if n.get("type", "").lower() in ("other", "unknown")]
    if others:
        print(f"\n{'='*60}")
        print(f"  DÉTAIL DES {len(others)} ENTITÉS 'other'")
        print(f"{'='*60}\n")
        
        # Afficher un échantillon
        for i, o in enumerate(others[:50]):
            name = o.get("name", "?")
            desc = (o.get("description") or "")[:80]
            print(f"  [{i+1:>3}] {name:<40} | {desc}")
        
        if len(others) > 50:
            print(f"\n  ... et {len(others) - 50} autres")
        
        # Analyser les patterns dans les noms des "other"
        print(f"\n--- Patterns dans les noms 'other' ---")
        name_words = Counter()
        for o in others:
            name = o.get("name", "").lower()
            for word in name.split():
                if len(word) > 3:
                    name_words[word] += 1
        print("Mots fréquents:")
        for w, c in name_words.most_common(20):
            print(f"  {w:<25} x{c}")
    
    # --- Relations par type ---
    rel_counts = Counter(e.get("type", "UNKNOWN") for e in edges)
    print(f"\n{'='*60}")
    print(f"  RELATIONS PAR TYPE")
    print(f"{'='*60}\n")
    print(f"{'TYPE':<30} {'COUNT':>6}")
    print("-" * 38)
    for t, c in rel_counts.most_common():
        print(f"{t:<30} {c:>6}")
    print("-" * 38)
    print(f"{'TOTAL':<30} {len(edges):>6}")


if __name__ == "__main__":
    mid = sys.argv[1] if len(sys.argv) > 1 else "PRESALES"
    asyncio.run(analyze(mid))
