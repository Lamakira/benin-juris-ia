"""
Tests unitaires pour le module cleaner.
"""
import pytest
from src.ingestion.cleaner import is_noise_line, clean_text, normalize_whitespace


class TestIsNoiseLine:
    """Tests pour la détection de bruit."""
    
    def test_empty_line_is_noise(self):
        assert is_noise_line("") is True
        assert is_noise_line("   ") is True
        assert is_noise_line("\t\n") is True
    
    def test_law_header_is_noise(self):
        assert is_noise_line("LOI N°2017-20 DU 20 AVRIL 2018") is True
        assert is_noise_line("loi n°2017-20 du 20 avril 2018") is True
    
    def test_code_title_is_noise(self):
        assert is_noise_line("PORTANT CODE DU NUMERIQUE EN REPUBLIQUE DU BENIN") is True
        assert is_noise_line("PORTANT CODE DU NUMÉRIQUE EN RÉPUBLIQUE DU BÉNIN") is True
    
    def test_page_numbers_are_noise(self):
        assert is_noise_line("[4]") is True
        assert is_noise_line("42") is True
        assert is_noise_line("Page 12") is True
        assert is_noise_line("- 15 -") is True
    
    def test_toc_lines_are_noise(self):
        assert is_noise_line("Chapitre I ....... 45") is True
        assert is_noise_line("Section 2 .................. 78") is True
    
    def test_valid_content_is_not_noise(self):
        assert is_noise_line("Article 550 : Les peines applicables...") is False
        assert is_noise_line("La cryptologie est définie comme...") is False


class TestNormalizeWhitespace:
    """Tests pour la normalisation des espaces."""
    
    def test_multiple_spaces(self):
        assert normalize_whitespace("Hello    World") == "Hello World"
    
    def test_special_characters(self):
        assert normalize_whitespace("L'article") == "L'article"
        assert normalize_whitespace("avant–après") == "avant-après"


class TestCleanText:
    """Tests pour le nettoyage complet."""
    
    def test_empty_pages(self):
        result = clean_text(["", "", ""])
        assert result == ""
    
    def test_noise_removal(self):
        pages = [
            "LOI N°2017-20 DU 20 AVRIL 2018\nArticle 1 : Définitions\n[1]",
            "PORTANT CODE DU NUMERIQUE EN REPUBLIQUE DU BENIN\nLa présente loi..."
        ]
        result = clean_text(pages)
        
        assert "LOI N°2017-20" not in result
        assert "PORTANT CODE" not in result
        assert "[1]" not in result
        assert "Article 1" in result
        assert "La présente loi" in result
    
    def test_merge_across_pages(self):
        # Simule un article coupé entre deux pages
        pages = [
            "Article 10 : Ceci est le début de l'article",
            "et voici la suite qui était sur la page suivante."
        ]
        result = clean_text(pages)
        
        # Le texte doit être fusionné avec un \n entre les lignes
        assert "début de l'article" in result
        assert "suite qui était" in result
