/**
 * MCP Memory - Rendu vis-network et détails de nœuds
 */

/** Rend le graphe dans le conteneur #graph */
function renderGraph(nodes, edges) {
    const container = document.getElementById('graph');
    const showMentions = document.getElementById('showMentions').checked;
    const showLabels = document.getElementById('showLabels').checked;

    let filteredNodes = showMentions ? nodes : nodes.filter(n => n.node_type !== 'document');
    let filteredEdges = showMentions ? edges : edges.filter(e => e.type !== 'MENTIONS');

    const visNodes = filteredNodes.map(n => {
        const label = n.label.length > 40 ? n.label.substring(0, 39) + '…' : n.label;
        const bgColor = TYPE_COLORS[n.type] || TYPE_COLORS.Unknown;
        const base = currentParams.nodeSize;
        return {
            id: n.id, label,
            title: `${n.label}\n━━━━━━━━━━━━━━\nType: ${n.type}\n${n.description || ''}`,
            color: {
                background: bgColor, border: bgColor,
                highlight: { background: '#fff', border: bgColor },
                hover: { background: bgColor, border: '#fff' }
            },
            font: { color: '#fff', size: currentParams.fontSize, face: 'Arial', strokeWidth: 2, strokeColor: '#000' },
            size: n.node_type === 'document' ? base * 1.5 : base + Math.min(n.mentions || 0, 10) * 2,
            shape: n.node_type === 'document' ? 'square' : 'dot',
            data: n
        };
    });

    const visEdges = filteredEdges.map((e, i) => ({
        id: i, from: e.from, to: e.to,
        label: showLabels ? (e.type || '').replace(/_/g, ' ') : '',
        title: `${e.type}\n${e.description || ''}`,
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        color: { color: EDGE_COLORS[e.type] || '#556', highlight: '#fff', hover: '#aaa' },
        font: { color: '#bbb', size: Math.max(currentParams.fontSize - 2, 8), strokeWidth: 2, strokeColor: '#000', align: 'top' },
        width: e.type === 'MENTIONS' ? 1 : 2,
        smooth: { type: 'continuous', roundness: 0.2 }
    }));

    const data = { nodes: new vis.DataSet(visNodes), edges: new vis.DataSet(visEdges) };

    const options = {
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -currentParams.gravity, centralGravity: 0.1,
                springLength: currentParams.springLength, springConstant: 0.02,
                damping: 0.9, avoidOverlap: 0.5
            },
            stabilization: { iterations: 300, fit: true }, maxVelocity: 30, minVelocity: 0.75
        },
        interaction: { hover: true, tooltipDelay: 100, zoomView: true, dragView: true, navigationButtons: true, keyboard: true },
        nodes: { borderWidth: 2, shadow: { enabled: true, size: 5 } },
        edges: { width: 1.5, selectionWidth: 3, shadow: false },
        layout: { improvedLayout: true }
    };

    appState.network = new vis.Network(container, data, options);

    // Geler après stabilisation
    appState.network.on('stabilizationIterationsDone', function () {
        appState.network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
        setTimeout(() => appState.network.setOptions({ physics: { enabled: false } }), 600);
    });
    appState.network.on('dragStart', () => appState.network.setOptions({ physics: { enabled: true, stabilization: false } }));
    appState.network.on('dragEnd', () => setTimeout(() => appState.network.setOptions({ physics: { enabled: false } }), 1000));

    // Clic nœud → détails
    appState.network.on('click', function (params) {
        if (params.nodes.length > 0) {
            const node = appState.currentData.nodes.find(n => n.id === params.nodes[0]);
            if (node) showNodeDetails(node);
        } else {
            hideNodeDetails();
        }
    });

    updateStats(filteredNodes.length, filteredEdges.length);
}

/** Affiche les détails riches d'un nœud */
function showNodeDetails(node) {
    const details = document.getElementById('nodeDetails');
    const content = document.getElementById('detailContent');
    const color = TYPE_COLORS[node.type] || TYPE_COLORS.Unknown;
    const data = appState.currentData;

    const connectedEdges = data ? data.edges.filter(e => (e.from === node.id || e.to === node.id) && e.type !== 'MENTIONS') : [];
    const sourceDocs = (node.source_docs || []).map(docId => {
        const doc = data ? data.documents.find(d => d.id === docId) : null;
        return doc ? doc.filename : docId;
    });

    let html = `<h4>${node.label}</h4>
        <span class="type-badge" style="background:${color}">${node.type}</span>
        ${node.mentions > 1 ? `<span style="font-size:0.7rem;color:#4CAF50;margin-left:0.3rem">×${node.mentions}</span>` : ''}`;

    if (node.description) {
        const descriptions = node.description.split(' | ');
        html += `<div class="detail-section"><div class="detail-label">📝 Description</div>
            ${descriptions.map(d => `<p>${d.trim()}</p>`).join('')}</div>`;
    }
    if (sourceDocs.length > 0) {
        html += `<div class="detail-section"><div class="detail-label">📄 Documents (${sourceDocs.length})</div>
            <div>${sourceDocs.map(d => `<span class="doc-tag">📄 ${d}</span>`).join('')}</div></div>`;
    }
    if (connectedEdges.length > 0) {
        html += `<div class="detail-section"><div class="detail-label">🔗 Relations (${connectedEdges.length})</div>`;
        connectedEdges.slice(0, 15).forEach(e => {
            const other = e.from === node.id ? e.to : e.from;
            const dir = e.from === node.id ? '→' : '←';
            html += `<div class="relation-item" style="cursor:pointer" onclick="focusNode('${other}')">
                <span class="relation-type">${(e.type || 'RELATED').replace(/_/g, ' ')}</span>
                <span>${dir} ${other.length > 28 ? other.substring(0, 26) + '…' : other}</span></div>`;
        });
        if (connectedEdges.length > 15) html += `<p style="font-size:0.7rem;color:#888">… +${connectedEdges.length - 15}</p>`;
        html += `</div>`;
    }

    content.innerHTML = html;
    details.classList.add('visible');
}

function hideNodeDetails() {
    document.getElementById('nodeDetails').classList.remove('visible');
}

/** Focus et sélection d'un nœud par ID */
function focusNode(nodeId) {
    if (appState.network) {
        appState.network.focus(nodeId, { scale: 1.5, animation: true });
        appState.network.selectNodes([nodeId]);
        const node = appState.currentData.nodes.find(n => n.id === nodeId);
        if (node) showNodeDetails(node);
    }
}

/**
 * Met en évidence des nœuds par nom (pour ASK).
 * Les nœuds matchés ont un halo blanc, les autres sont dimmed.
 */
function highlightEntities(entityNames) {
    if (!appState.network || !appState.currentData) return;

    const namesLower = entityNames.map(n => n.toLowerCase());
    const matchingIds = appState.currentData.nodes
        .filter(n => namesLower.includes(n.label.toLowerCase()))
        .map(n => n.id);

    if (matchingIds.length > 0) {
        appState.network.selectNodes(matchingIds);
        // Zoom pour voir tous les nœuds sélectionnés
        if (matchingIds.length <= 5) {
            appState.network.fit({ nodes: matchingIds, animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
        }
    }
}

/** Efface la mise en évidence */
function clearHighlight() {
    if (appState.network) appState.network.unselectAll();
}
