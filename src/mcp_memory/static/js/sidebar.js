/**
 * MCP Memory - Sidebar : stats, légende, liste d'entités, filtres, documents
 */

function updateStats(nodeCount, edgeCount) {
    document.getElementById('nodeCount').textContent = nodeCount;
    document.getElementById('edgeCount').textContent = edgeCount;
}

function updateLegend(nodes) {
    const types = [...new Set(nodes.map(n => n.type))];
    document.getElementById('legend').innerHTML = types.map(t => `
        <div class="legend-item">
            <div class="legend-color" style="background:${TYPE_COLORS[t] || TYPE_COLORS.Unknown}"></div>
            <span>${t}</span>
        </div>`).join('');

    // Peupler le select de filtrage par type
    const select = document.getElementById('typeFilter');
    select.innerHTML = '<option value="">Tous les types</option>' +
        types.sort().map(t => `<option value="${t}">${t} (${nodes.filter(n => n.type === t).length})</option>`).join('');
}

function updateEntityList(nodes) {
    const list = document.getElementById('entityList');
    const sorted = [...nodes].sort((a, b) => (b.mentions || 0) - (a.mentions || 0));
    list.innerHTML = sorted.slice(0, 50).map(n => `
        <div class="entity-item" onclick="focusNode('${n.id}')"
             style="border-left:3px solid ${TYPE_COLORS[n.type] || TYPE_COLORS.Unknown}">
            ${n.label.substring(0, 30)}${n.label.length > 30 ? '…' : ''}
            <div class="type">${n.type}</div>
        </div>`).join('');
}

function updateDocumentList(documents) {
    if (!documents.length) return;
    const sidebar = document.querySelector('.sidebar');
    let section = document.getElementById('docSection');
    if (!section) {
        section = document.createElement('div');
        section.id = 'docSection';
        sidebar.appendChild(section);
    }
    section.innerHTML = '<h3>📄 Documents</h3><div class="entity-list">' +
        documents.map(d => `
            <div class="entity-item" style="border-left:3px solid #e74c3c">
                <strong>${d.filename}</strong>
                <div class="type" style="word-break:break-all;font-size:0.65rem">${d.uri || ''}</div>
            </div>`).join('') + '</div>';
}

/** Filtre local d'entités dans la sidebar */
function setupSearchFilter() {
    document.getElementById('searchInput').addEventListener('input', function () {
        const q = this.value.toLowerCase().trim();
        if (!appState.currentData || !appState.network) return;
        if (!q) {
            appState.network.unselectAll();
            updateEntityList(appState.currentData.nodes);
            return;
        }
        const matches = appState.currentData.nodes.filter(n =>
            n.label.toLowerCase().includes(q) ||
            (n.description || '').toLowerCase().includes(q) ||
            (n.type || '').toLowerCase().includes(q)
        );
        updateEntityList(matches);
        if (matches.length > 0 && matches.length <= 20) {
            const ids = matches.map(n => n.id);
            appState.network.selectNodes(ids);
            if (matches.length === 1) appState.network.focus(ids[0], { scale: 1.5, animation: true });
        }
    });
}

/** Filtre par type dans la sidebar */
function setupTypeFilter() {
    document.getElementById('typeFilter').addEventListener('change', function () {
        const type = this.value;
        if (!appState.currentData) return;
        if (!type) {
            renderGraph(appState.currentData.nodes, appState.currentData.edges);
            updateEntityList(appState.currentData.nodes);
            return;
        }
        const filteredNodes = appState.currentData.nodes.filter(n => n.type === type);
        const filteredIds = new Set(filteredNodes.map(n => n.id));
        const filteredEdges = appState.currentData.edges.filter(e => filteredIds.has(e.from) || filteredIds.has(e.to));
        const connectedIds = new Set(filteredIds);
        filteredEdges.forEach(e => { connectedIds.add(e.from); connectedIds.add(e.to); });
        const allVisible = appState.currentData.nodes.filter(n => connectedIds.has(n.id));
        renderGraph(allVisible, filteredEdges);
        updateEntityList(filteredNodes);
    });
}
