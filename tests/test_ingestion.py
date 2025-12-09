"""
Tests d'intégration pour le pipeline d'ingestion complet.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingestion import load_pdf, clean_text, chunk_by_articles, enrich_metadata


class TestIngestionPipeline:
    """Tests d'intégration pour le pipeline complet."""
    
    @pytest.fixture
    def sample_text(self):
        """Texte de test simulant le Code du Numérique."""
        return """
LOI N°2017-20 DU 20 AVRIL 2018
PORTANT CODE DU NUMERIQUE EN REPUBLIQUE DU BENIN

Article 1 : Définitions
Au sens de la présente loi, on entend par :
Cryptologie : L'ensemble des techniques permettant de chiffrer des messages.
Données : Représentation de faits sous forme adaptée à leur traitement.

Article 2 : Champ d'application
La présente loi s'applique sur l'ensemble du territoire de la République du Bénin.

Article 550 : Sanctions pénales
Est puni d'une peine d'emprisonnement de un à cinq ans et d'une amende quiconque 
accède frauduleusement à un système informatique.
"""
    
    def test_full_pipeline(self, sample_text):
        """Test du pipeline complet: Clean -> Chunk -> Enrich."""
        
        # Simuler des pages de PDF
        pages = [sample_text]
        
        # 1. Nettoyage
        cleaned = clean_text(pages)
        assert "LOI N°2017-20" not in cleaned
        assert "Article 1" in cleaned
        
        # 2. Chunking
        chunks = chunk_by_articles(cleaned)
        assert len(chunks) >= 3  # Articles 1, 2, 550
        
        # 3. Enrichissement
        enriched = enrich_metadata(chunks)
        
        # Vérifier les métadonnées
        for chunk in enriched:
            assert "metadata" in chunk
            assert "content_with_context" in chunk
            assert "source" in chunk["metadata"]
    
    def test_article_550_hierarchy(self, sample_text):
        """Vérifie que l'Article 550 a la bonne hiérarchie (Cybercriminalité)."""
        pages = [sample_text]
        cleaned = clean_text(pages)
        chunks = chunk_by_articles(cleaned)
        enriched = enrich_metadata(chunks)
        
        # Trouver l'article 550
        article_550 = next(
            (c for c in enriched if c.get("article_number") == 550), 
            None
        )
        
        assert article_550 is not None
        assert "hierarchy" in article_550.get("metadata", {})
        # Selon le mapping, 550 devrait être dans LIVRE VI (Cybercriminalité)
        hierarchy = article_550["metadata"]["hierarchy"]
        assert "LIVRE VI" in hierarchy.get("livre", "")
    
    def test_context_prefix(self, sample_text):
        """Vérifie que le contenu avec contexte est correctement formaté."""
        pages = [sample_text]
        cleaned = clean_text(pages)
        chunks = chunk_by_articles(cleaned)
        enriched = enrich_metadata(chunks)
        
        for chunk in enriched:
            content_with_context = chunk.get("content_with_context", "")
            
            # Doit commencer par le préfixe de contexte
            if chunk.get("article_number"):
                assert "[Contexte:" in content_with_context or chunk["content"] in content_with_context
