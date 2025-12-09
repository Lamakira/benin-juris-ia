"""
Tests unitaires pour le module chunker.
"""
import pytest
from src.ingestion.chunker import chunk_by_articles, sub_chunk_definitions, extract_article_number


class TestChunkByArticles:
    """Tests pour le découpage par articles."""
    
    def test_single_article(self):
        text = "Article 10 : Ceci est le contenu de l'article dix."
        chunks = chunk_by_articles(text)
        
        assert len(chunks) == 1
        assert chunks[0]["id"] == "Article 10"
        assert "Ceci est le contenu" in chunks[0]["content"]
    
    def test_multiple_articles(self):
        text = """Article 10 : Premier article.
Article 11 : Deuxième article.
Article 12 : Troisième article."""
        
        chunks = chunk_by_articles(text)
        
        assert len(chunks) == 3
        assert chunks[0]["id"] == "Article 10"
        assert chunks[1]["id"] == "Article 11"
        assert chunks[2]["id"] == "Article 12"
    
    def test_article_premier(self):
        # L'Article 1er doit être reconnu
        text = "Article 1er : Au sens de la présente loi..."
        chunks = chunk_by_articles(text)
        
        # Note: Article 1 déclenche le sous-découpage
        assert len(chunks) >= 1
    
    def test_article_boundaries(self):
        # Chaque article contient exactement son contenu jusqu'au suivant
        text = """Article 5 : Contenu de l'article cinq.
Suite du texte de l'article cinq.
Article 6 : Contenu de l'article six."""
        
        chunks = chunk_by_articles(text)
        
        assert len(chunks) == 2
        assert "Suite du texte" in chunks[0]["content"]
        assert "Suite du texte" not in chunks[1]["content"]


class TestSubChunkDefinitions:
    """Tests pour le sous-découpage de l'Article 1."""
    
    def test_definition_extraction(self):
        article_1 = """Article 1 : Définitions
Au sens de la présente loi, on entend par :
Cryptologie : Science du chiffrement.
Données personnelles : Toute information relative à une personne."""
        
        chunks = sub_chunk_definitions(article_1, "Article 1")
        
        # Devrait extraire au moins le préambule et les définitions
        assert len(chunks) >= 2
        
        # Vérifier qu'on a des définitions
        definition_chunks = [c for c in chunks if c["type"] == "definition"]
        assert len(definition_chunks) >= 1


class TestExtractArticleNumber:
    """Tests pour l'extraction du numéro d'article."""
    
    def test_simple_number(self):
        assert extract_article_number("Article 42") == 42
        assert extract_article_number("Article 1") == 1
        assert extract_article_number("Article 550") == 550
    
    def test_invalid_format(self):
        assert extract_article_number("Chapitre 1") is None
        assert extract_article_number("Livre III") is None
