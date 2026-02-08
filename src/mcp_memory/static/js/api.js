/**
 * MCP Memory - Appels API REST
 */

async function apiLoadMemories() {
    const response = await fetch('/api/memories');
    return await response.json();
}

async function apiLoadGraph(memoryId) {
    const response = await fetch(`/api/graph/${encodeURIComponent(memoryId)}`);
    return await response.json();
}

async function apiAsk(memoryId, question, limit = 10) {
    const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ memory_id: memoryId, question, limit })
    });
    return await response.json();
}
