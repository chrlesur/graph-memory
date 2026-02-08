/**
 * MCP Memory - Configuration et constantes
 * Couleurs par type d'entité et de relation, paramètres par défaut.
 */

// Couleurs des nœuds par type d'entité
const TYPE_COLORS = {
    Organization: '#3498db', Person: '#2ecc71', Party: '#2980b9',
    LegalRepresentative: '#27ae60', Clause: '#1abc9c', Obligation: '#16a085',
    ContractType: '#8e44ad', Annex: '#6c3483', Reference: '#5b2c6f',
    Amount: '#f39c12', Duration: '#e67e22', Date: '#d35400',
    SLA: '#e74c3c', Metric: '#c0392b', Certification: '#9b59b6',
    Regulation: '#8e44ad', Location: '#1abc9c', Jurisdiction: '#17a589',
    Concept: '#3498db', Product: '#2e86c1', Service: '#2874a6',
    Document: '#e74c3c', Other: '#95a5a6', Unknown: '#7f8c8d'
};

// Couleurs des arêtes par type de relation
const EDGE_COLORS = {
    RELATED_TO: '#667eea', DEFINES: '#e74c3c', SIGNED_BY: '#2ecc71',
    REPRESENTS: '#27ae60', MENTIONS: '#555', PARTY_TO: '#3498db',
    INCLUDES_ANNEX: '#8e44ad', HAS_DURATION: '#e67e22', HAS_AMOUNT: '#f39c12',
    HAS_SLA: '#e74c3c', HAS_CERTIFICATION: '#9b59b6', GUARANTEES: '#9b59b6',
    GOVERNED_BY: '#1abc9c', OBLIGATES: '#c0392b', REQUIRES_CERTIFICATION: '#8e44ad',
    AMENDS: '#d35400', SUPERSEDES: '#c0392b', LOCATED_AT: '#1abc9c',
    JURISDICTION: '#17a589', EFFECTIVE_DATE: '#d35400', CERTIFIES: '#9b59b6',
    REFERENCES: '#95a5a6', BELONGS_TO: '#2980b9', CREATED_BY: '#2ecc71',
    CONTAINS: '#34495e', HAS_VALUE: '#f39c12'
};

// Paramètres d'affichage du graphe
const DEFAULT_PARAMS = { springLength: 400, gravity: 15000, nodeSize: 20, fontSize: 11 };
let currentParams = { ...DEFAULT_PARAMS };

// État global de l'application
const appState = {
    network: null,      // Instance vis-network
    currentData: null,  // Données du graphe chargé
    currentMemory: null // ID de la mémoire sélectionnée
};
