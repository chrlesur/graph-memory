# -*- coding: utf-8 -*-
"""
ExtractorService - Extraction d'entités et relations via LLMaaS.

Utilise l'API LLMaaS Cloud Temple (compatible OpenAI) pour extraire
les entités, relations et concepts à partir de texte.
"""

import sys
import json
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import AsyncOpenAI
from openai import APIError, APITimeoutError

from ..config import get_settings
from .models import (
    ExtractionResult, ExtractedEntity, ExtractedRelation,
    EntityType, RelationType
)
from .ontology import Ontology, get_ontology_manager


# Prompt d'extraction structuré - Version améliorée avec métriques et durées
EXTRACTION_PROMPT = """Tu es un expert en extraction d'information pour documents contractuels et juridiques. Analyse le document suivant et extrait TOUTES les entités importantes, y compris les valeurs numériques, métriques et durées.

DOCUMENT:
---
{document_text}
---

INSTRUCTIONS:
1. Identifie TOUTES les entités nommées (personnes, organisations, lieux, concepts)
2. Identifie TOUTES les métriques et valeurs numériques importantes (SLA, pourcentages, taux)
3. Identifie TOUTES les durées et délais (durée de contrat, préavis, périodes)
4. Identifie TOUS les montants financiers (prix, tarifs, pénalités)
5. Identifie les relations entre ces entités
6. Fournis un bref résumé du document

TYPES D'ENTITÉS (avec exemples):
- Person: Personne physique → "Jean Dupont", "Marie Martin (DSI)"
- Organization: Entreprise, institution → "Cloud Temple SAS", "ANSSI"
- Concept: Idée abstraite, terme technique → "SecNumCloud", "Infrastructure IaaS"
- Location: Lieu géographique → "Paris", "Nanterre"
- Date: Date précise → "1er janvier 2026", "Q1 2026"
- Product: Produit ou technologie → "VMware", "Neo4j"
- Service: Service proposé → "Support 24/7", "Infogérance"
- Clause: Clause contractuelle → "Clause de réversibilité", "Confidentialité"
- Certification: Certification ou norme → "ISO 27001", "HDS", "SOC 2 Type II"
- Metric: Valeur numérique, SLA, pourcentage → "SLA 99.95%", "GTI 15 minutes", "Disponibilité 99.9%"
- Duration: Durée ou délai → "36 mois", "3 ans", "préavis 6 mois", "rétention 30 jours"
- Amount: Montant financier → "50 000 EUR/mois", "2 500 EUR HT", "pénalité 10%"
- Other: Autre type important

EXEMPLES D'EXTRACTION:
Document: "Le SLA de disponibilité est de 99.95% avec un GTI de 15 minutes."
→ Entités: {{"name": "SLA Disponibilité 99.95%", "type": "Metric", "description": "Niveau de service garanti"}}
→ Entités: {{"name": "GTI 15 minutes", "type": "Metric", "description": "Garantie de temps d'intervention"}}

Document: "Contrat de 36 mois renouvelable par tacite reconduction."
→ Entités: {{"name": "Durée 36 mois", "type": "Duration", "description": "Durée initiale du contrat"}}

Document: "Prix mensuel: 3 150 EUR HT."
→ Entités: {{"name": "Prix 3 150 EUR HT/mois", "type": "Amount", "description": "Tarification mensuelle"}}

TYPES DE RELATIONS:
- MENTIONS: Le document mentionne l'entité
- DEFINES: Le document définit/spécifie une valeur
- RELATED_TO: Relation générique entre entités
- BELONGS_TO: Appartenance
- SIGNED_BY: Signature/validation
- CREATED_BY: Création/auteur
- REFERENCES: Référence à un autre document/concept
- HAS_VALUE: Associe une métrique/durée/montant à un concept
- GUARANTEES: Garantie de service (SLA)
- CERTIFIES: Certification obtenue

Réponds UNIQUEMENT avec un JSON valide:
```json
{{
  "entities": [
    {{"name": "Nom de l'entité", "type": "Person|Organization|Metric|Duration|Amount|...", "description": "Description courte"}}
  ],
  "relations": [
    {{"from_entity": "Nom entité source", "to_entity": "Nom entité cible", "type": "RELATED_TO|HAS_VALUE|...", "description": "Description de la relation"}}
  ],
  "summary": "Résumé du document en 2-3 phrases",
  "key_topics": ["sujet1", "sujet2", "sujet3"]
}}
```

IMPORTANT: 
- Extrais au maximum 30 entités et 40 relations
- NE PAS OUBLIER les métriques (SLA, %), durées (mois, jours) et montants (EUR, USD)
- Les noms d'entités doivent être explicites et inclure la valeur (ex: "SLA 99.95%" pas juste "SLA")
- Privilégie l'exhaustivité pour les données chiffrées
"""


class ExtractorService:
    """
    Service d'extraction via LLMaaS.
    
    Utilise le modèle gpt-oss:120b de Cloud Temple pour extraire
    les entités et relations structurées depuis un texte.
    """
    
    def __init__(self):
        """Initialise le client OpenAI compatible."""
        settings = get_settings()
        
        self._client = AsyncOpenAI(
            base_url=settings.llmaas_base_url,
            api_key=settings.llmaas_api_key,
            timeout=settings.extraction_timeout_seconds
        )
        self._model = settings.llmaas_model
        self._max_tokens = settings.llmaas_max_tokens
        self._temperature = settings.llmaas_temperature
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def extract_from_text(
        self,
        text: str,
        max_text_length: int = 50000
    ) -> ExtractionResult:
        """
        Extrait les entités et relations d'un texte.
        
        Args:
            text: Texte à analyser
            max_text_length: Longueur max du texte (tronqué sinon)
            
        Returns:
            ExtractionResult avec entités, relations, résumé
        """
        # Tronquer si nécessaire
        if len(text) > max_text_length:
            text = text[:max_text_length] + "\n\n[Document tronqué...]"
        
        prompt = EXTRACTION_PROMPT.format(document_text=text)
        
        try:
            print(f"🔍 [Extractor] Extraction en cours ({len(text)} chars)...", file=sys.stderr)
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un assistant spécialisé dans l'extraction d'information structurée. Tu réponds uniquement en JSON valide."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self._max_tokens,
                temperature=self._temperature
                # Note: response_format non supporté par LLMaaS Cloud Temple
            )
            
            # Parser la réponse - DEBUG COMPLET
            print(f"🔍 [Extractor] DEBUG response type: {type(response)}", file=sys.stderr)
            print(f"🔍 [Extractor] DEBUG choices count: {len(response.choices)}", file=sys.stderr)
            if response.choices:
                print(f"🔍 [Extractor] DEBUG message: {response.choices[0].message}", file=sys.stderr)
                print(f"🔍 [Extractor] DEBUG finish_reason: {response.choices[0].finish_reason}", file=sys.stderr)
            
            content = response.choices[0].message.content
            if content is None:
                print(f"⚠️ [Extractor] Réponse LLM vide - message complet: {response.choices[0].message}", file=sys.stderr)
                return ExtractionResult()
            
            print(f"🔍 [Extractor] DEBUG content length: {len(content)}", file=sys.stderr)
            result = self._parse_extraction(content)
            
            print(f"✅ [Extractor] Extrait: {len(result.entities)} entités, {len(result.relations)} relations", file=sys.stderr)
            
            return result
            
        except APITimeoutError:
            print(f"⏰ [Extractor] Timeout - le document est peut-être trop long", file=sys.stderr)
            raise
        except APIError as e:
            print(f"❌ [Extractor] Erreur API: {e}", file=sys.stderr)
            raise
    
    def _parse_extraction(self, content: str) -> ExtractionResult:
        """Parse la réponse JSON du LLM."""
        try:
            # Nettoyer le contenu (parfois le LLM ajoute des ```json)
            content = content.strip()
            if content.startswith("```"):
                # Trouver le premier { et le dernier }
                start = content.find("{")
                end = content.rfind("}") + 1
                content = content[start:end]
            
            data = json.loads(content)
            
            # Parser les entités
            entities = []
            for e in data.get("entities", []):
                entity_type = self._parse_entity_type(e.get("type", "Other"))
                entities.append(ExtractedEntity(
                    name=e.get("name", "").strip(),
                    type=entity_type,
                    description=e.get("description")
                ))
            
            # Parser les relations
            relations = []
            for r in data.get("relations", []):
                rel_type = self._parse_relation_type(r.get("type", "RELATED_TO"))
                relations.append(ExtractedRelation(
                    from_entity=r.get("from_entity", "").strip(),
                    to_entity=r.get("to_entity", "").strip(),
                    type=rel_type,
                    description=r.get("description")
                ))
            
            return ExtractionResult(
                entities=entities,
                relations=relations,
                summary=data.get("summary"),
                key_topics=data.get("key_topics", [])
            )
            
        except json.JSONDecodeError as e:
            print(f"⚠️ [Extractor] Erreur parsing JSON: {e}", file=sys.stderr)
            print(f"   Contenu reçu: {content[:200]}...", file=sys.stderr)
            # Retourner un résultat vide plutôt que crasher
            return ExtractionResult()
    
    @staticmethod
    def _parse_entity_type(type_str: str) -> EntityType:
        """Convertit une string en EntityType."""
        type_map = {
            "person": EntityType.PERSON,
            "organization": EntityType.ORGANIZATION,
            "concept": EntityType.CONCEPT,
            "location": EntityType.LOCATION,
            "date": EntityType.DATE,
            "product": EntityType.PRODUCT,
            "service": EntityType.SERVICE,
            "clause": EntityType.CLAUSE,
            "certification": EntityType.CERTIFICATION,
            "metric": EntityType.METRIC,
            "duration": EntityType.DURATION,
            "amount": EntityType.AMOUNT,
        }
        return type_map.get(type_str.lower(), EntityType.OTHER)
    
    @staticmethod
    def _parse_relation_type(type_str: str) -> RelationType:
        """Convertit une string en RelationType."""
        type_map = {
            "mentions": RelationType.MENTIONS,
            "defines": RelationType.DEFINES,
            "related_to": RelationType.RELATED_TO,
            "belongs_to": RelationType.BELONGS_TO,
            "signed_by": RelationType.SIGNED_BY,
            "created_by": RelationType.CREATED_BY,
            "references": RelationType.REFERENCES,
            "contains": RelationType.CONTAINS,
        }
        return type_map.get(type_str.lower(), RelationType.RELATED_TO)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def extract_with_ontology(
        self,
        text: str,
        ontology_name: str = "default",
        max_text_length: int = 50000
    ) -> ExtractionResult:
        """
        Extrait les entités et relations d'un texte en utilisant une ontologie.
        
        Args:
            text: Texte à analyser
            ontology_name: Nom de l'ontologie à utiliser (ex: "legal", "cloud")
            max_text_length: Longueur max du texte (tronqué sinon)
            
        Returns:
            ExtractionResult avec entités, relations, résumé
        """
        # Charger l'ontologie
        ontology_manager = get_ontology_manager()
        ontology = ontology_manager.get_ontology(ontology_name)
        
        if not ontology:
            print(f"⚠️ [Extractor] Ontologie '{ontology_name}' non trouvée, utilisation de 'default'", file=sys.stderr)
            ontology = ontology_manager.get_default_ontology()
        
        # Tronquer si nécessaire
        if len(text) > max_text_length:
            text = text[:max_text_length] + "\n\n[Document tronqué...]"
        
        # Construire le prompt avec l'ontologie
        prompt = ontology.build_prompt(text)
        
        try:
            print(f"🔍 [Extractor] Extraction avec ontologie '{ontology.name}' ({len(text)} chars)...", file=sys.stderr)
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un assistant spécialisé dans l'extraction d'information structurée. Tu réponds uniquement en JSON valide."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self._max_tokens,
                temperature=self._temperature
            )
            
            content = response.choices[0].message.content
            if content is None:
                print(f"⚠️ [Extractor] Réponse LLM vide", file=sys.stderr)
                return ExtractionResult()
            
            result = self._parse_extraction(content)
            
            print(f"✅ [Extractor] Extrait ({ontology.name}): {len(result.entities)} entités, {len(result.relations)} relations", file=sys.stderr)
            
            return result
            
        except APITimeoutError:
            print(f"⏰ [Extractor] Timeout - le document est peut-être trop long", file=sys.stderr)
            raise
        except APIError as e:
            print(f"❌ [Extractor] Erreur API: {e}", file=sys.stderr)
            raise

    async def test_connection(self) -> dict:
        """Teste la connexion au LLMaaS."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "Réponds juste 'OK'"}],
                max_tokens=10
            )
            
            return {
                "status": "ok",
                "model": self._model,
                "message": "Connexion LLMaaS réussie"
            }
            
        except APIError as e:
            return {
                "status": "error",
                "model": self._model,
                "message": f"Erreur LLMaaS: {str(e)}"
            }


# Singleton pour usage global
_extractor_service: Optional[ExtractorService] = None


def get_extractor_service() -> ExtractorService:
    """Retourne l'instance singleton du ExtractorService."""
    global _extractor_service
    if _extractor_service is None:
        _extractor_service = ExtractorService()
    return _extractor_service
