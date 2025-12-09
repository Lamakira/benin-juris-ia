"""
BÉNIN JURIS-IA - Semantic Searcher
Recherche sémantique dans le vector store.
"""
from typing import List, Dict, Any, Optional
import chromadb

from src.retrieval.embedder import embed_query
from src.retrieval.indexer import load_vectorstore


def semantic_search(
    query: str,
    n_results: int = 5,
    collection: Optional[chromadb.Collection] = None,
    filter_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Effectue une recherche sémantique dans le vector store.
    
    Args:
        query: Question de l'utilisateur
        n_results: Nombre de résultats à retourner
        collection: Collection ChromaDB (charge depuis config si None)
        filter_type: Filtrer par type de chunk ("article", "definition", etc.)
        
    Returns:
        Liste des résultats avec documents, métadonnées et distances
    """
    # Charger la collection si non fournie
    if collection is None:
        collection = load_vectorstore()
    
    # Générer l'embedding de la requête
    query_embedding = embed_query(query)
    
    # Construire le filtre si spécifié
    where_filter = None
    if filter_type:
        where_filter = {"type": filter_type}
    
    # Effectuer la recherche
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    # Formater les résultats
    formatted_results = []
    
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            formatted_results.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
                "relevance_score": 1 - (results["distances"][0][i] if results["distances"] else 0),
            })
    
    return formatted_results


def search_by_article_number(
    article_num: int,
    collection: Optional[chromadb.Collection] = None,
) -> Optional[Dict[str, Any]]:
    """
    Recherche un article spécifique par son numéro.
    
    Args:
        article_num: Numéro de l'article recherché
        collection: Collection ChromaDB
        
    Returns:
        Article trouvé ou None
    """
    if collection is None:
        collection = load_vectorstore()
    
    results = collection.get(
        where={"article_number": article_num},
        include=["documents", "metadatas"]
    )
    
    if results["documents"]:
        return {
            "content": results["documents"][0],
            "metadata": results["metadatas"][0] if results["metadatas"] else {},
        }
    
    return None


def format_search_context(results: List[Dict[str, Any]]) -> str:
    """
    Formate les résultats de recherche en contexte pour le LLM.
    
    Args:
        results: Résultats de la recherche sémantique
        
    Returns:
        Contexte formaté pour le prompt
    """
    context_parts = []
    
    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        hierarchy = metadata.get("hierarchy_path", "")
        article_id = metadata.get("id", f"Source {i}")
        
        context_parts.append(f"--- {article_id} ---")
        if hierarchy:
            context_parts.append(f"[{hierarchy}]")
        context_parts.append(result["content"])
        context_parts.append("")  # Ligne vide entre articles
    
    return "\n".join(context_parts)
