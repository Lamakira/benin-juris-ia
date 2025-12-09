"""
BÉNIN JURIS-IA - Embedder
Génération des embeddings avec OpenAI text-embedding-3-small.
"""
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from src.config import settings


def get_embedding_model() -> OpenAIEmbeddings:
    """
    Initialise le modèle d'embeddings OpenAI.
    
    Returns:
        Instance OpenAIEmbeddings configurée
    """
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[List[float]]:
    """
    Génère les embeddings pour tous les chunks.
    
    Utilise le contenu enrichi avec contexte pour de meilleurs résultats.
    
    Args:
        chunks: Liste des chunks avec content_with_context    
    Returns:
        Liste des vecteurs d'embeddings
    """
    embeddings_model = get_embedding_model()
    
    # Utiliser le contenu avec contexte si disponible
    texts = [
        chunk.get("content_with_context", chunk["content"])
        for chunk in chunks
    ]
    
    logger.info(f"Génération des embeddings pour {len(texts)} chunks...")
    
    # Batch processing 
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = embeddings_model.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        logger.info(f"   Batch {i // batch_size + 1}: {len(batch)} embeddings générés")
    
    logger.success(f"{len(all_embeddings)} embeddings générés au total")
    
    return all_embeddings


def embed_query(query: str) -> List[float]:
    """
    Génère l'embedding pour une requête utilisateur.
    
    Args:
        query: Question de l'utilisateur
    Returns:
        Vecteur d'embedding
    """
    embeddings_model = get_embedding_model()
    return embeddings_model.embed_query(query)
