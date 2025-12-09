"""
BÉNIN JURIS-IA - Article Chunker
Segmentation Structure-Aware par Article avec gestion du cas spécial Article 1.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger


# Pattern principal pour détecter le début d'un article
# Captures: "Article 1 :", "Article 10 :", "Article 1er :", etc.
ARTICLE_PATTERN = re.compile(
    r"^(Article\s+(\d+)(?:er)?)\s*[:\-\.]\s*",
    re.MULTILINE | re.IGNORECASE
)

# Pattern pour les termes définis dans l'Article 1 (Définitions)
# Capture les termes qui commencent une définition
DEFINITION_TERM_PATTERN = re.compile(
    r"^([A-ZÉÈÀÙÂÊÎÔÛÇŒÆ][a-zéèàùâêîôûçœæ'\-\s]+)\s*:\s*",
    re.MULTILINE
)


def chunk_by_articles(full_text: str) -> List[Dict[str, Any]]:
    """
    Découpe le texte complet en chunks, un par Article.
   
    Args:
        full_text: Texte complet nettoyé et fusionné      
    Returns:
        Liste de chunks avec id, content et metadata
    """
    chunks: List[Dict[str, Any]] = []
    
    # Trouver tous les articles
    matches = list(ARTICLE_PATTERN.finditer(full_text))
    
    if not matches:
        logger.warning("Aucun article trouve dans le texte!")
        return chunks
    
    logger.info(f"{len(matches)} articles detectes")
    
    for i, match in enumerate(matches):
        start_pos = match.start()
        
        # Fin = début de l'article suivant ou fin du texte
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(full_text)
        
        article_id = match.group(1).strip() 
        article_num = match.group(2)
        article_content = full_text[start_pos:end_pos].strip()
        
        # Cas spécial pour Article 1 
        if article_num == "1":
            definition_chunks = sub_chunk_definitions(article_content, article_id)
            chunks.extend(definition_chunks)
            logger.info(f"   {article_id} (Definitions) -> {len(definition_chunks)} sous-chunks")
        else:
            chunks.append({
                "id": article_id,
                "article_number": int(article_num),
                "content": article_content,
                "type": "article",
                "metadata": {}
            })
    
    # Stats
    article_count = len([c for c in chunks if c["type"] == "article"])
    definition_count = len([c for c in chunks if c["type"] == "definition"])
    
    logger.success("Chunking termine:")
    logger.info(f"   - Articles standards: {article_count}")
    logger.info(f"   - Definitions (Article 1): {definition_count}")
    logger.info(f"   - Total chunks: {len(chunks)}")
    
    return chunks


def sub_chunk_definitions(article_1_text: str, article_id: str) -> List[Dict[str, Any]]:
    """
    Sous-découpe l'Article 1 (Définitions) par terme défini.
    
    L'Article 1 du Code du Numérique contient des dizaines de définitions
    (Cryptologie, Données personnelles, etc.). Chaque terme devient un chunk.
    
    Args:
        article_1_text: Contenu complet de l'Article 1
        article_id: ID de l'article ("Article 1")
        
    Returns:
        Liste de chunks, un par terme défini
    """
    chunks: List[Dict[str, Any]] = []
    
    # Trouver tous les termes définis
    matches = list(DEFINITION_TERM_PATTERN.finditer(article_1_text))
    
    if not matches:
        # Fallback: garder l'article entier si pas de pattern reconnu
        return [{
            "id": article_id,
            "article_number": 1,
            "content": article_1_text,
            "type": "article",
            "metadata": {}
        }]
    
    # Extraire le préambule
    preamble_end = matches[0].start()
    preamble = article_1_text[:preamble_end].strip()
    
    if preamble:
        chunks.append({
            "id": f"{article_id} - Préambule",
            "article_number": 1,
            "content": preamble,
            "type": "definition_preamble",
            "metadata": {"parent_article": article_id}
        })
    
    # Extraire chaque définition
    for i, match in enumerate(matches):
        start_pos = match.start()
        
        # Fin = début du terme suivant ou fin de l'article
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(article_1_text)
        
        term_name = match.group(1).strip()
        term_content = article_1_text[start_pos:end_pos].strip()
        
        chunks.append({
            "id": f"{article_id} - {term_name}",
            "article_number": 1,
            "content": term_content,
            "type": "definition",
            "term": term_name,
            "metadata": {"parent_article": article_id}
        })
    
    return chunks


def extract_article_number(article_id: str) -> Optional[int]:
    """
    Extrait le numéro d'article depuis son ID.
    
    Args:
        article_id: ID de l'article (ex: "Article 550")
    Returns:
        Numéro de l'article ou None
    """
    match = re.search(r"Article\s+(\d+)", article_id, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def get_article_stats(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Génère des statistiques sur les chunks extraits.
    
    Args:
        chunks: Liste des chunks   
    Returns:
        Dictionnaire de statistiques
    """
    article_numbers = [
        c["article_number"] 
        for c in chunks 
        if c.get("article_number")
    ]
    
    unique_articles = sorted(set(article_numbers))
    
    # Détecter les gaps dans la séquence
    expected = set(range(min(unique_articles), max(unique_articles) + 1))
    missing = expected - set(unique_articles)
    
    content_lengths = [len(c["content"]) for c in chunks]
    
    return {
        "total_chunks": len(chunks),
        "unique_articles": len(unique_articles),
        "article_range": (min(unique_articles), max(unique_articles)),
        "missing_articles": sorted(missing),
        "avg_content_length": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
        "min_content_length": min(content_lengths) if content_lengths else 0,
        "max_content_length": max(content_lengths) if content_lengths else 0,
    }
