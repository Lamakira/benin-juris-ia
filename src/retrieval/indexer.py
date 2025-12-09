"""
BÉNIN JURIS-IA - ChromaDB Indexer
Stockage et gestion du vector store avec métadonnées aplaties pour le filtrage.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from src.config import settings


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Initialise le client ChromaDB avec persistance.
    
    Returns:
        Client ChromaDB configuré
    """
    persist_path = Path(settings.vectorstore_path)
    persist_path.mkdir(parents=True, exist_ok=True)
    
    return chromadb.PersistentClient(
        path=str(persist_path),
        settings=ChromaSettings(anonymized_telemetry=False)
    )


def flatten_metadata_for_chroma(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplatit les métadonnées imbriquées pour compatibilité ChromaDB.
    
    ChromaDB ne supporte pas les dictionnaires imbriqués dans les métadonnées.
    Cette fonction extrait les champs de 'hierarchy' et les ajoute au niveau racine.
    
    Args:
        chunk: Chunk avec métadonnées potentiellement imbriquées        
    Returns:
        Dictionnaire de métadonnées aplaties (compatible ChromaDB)
    """
    meta = {
        "id": str(chunk.get("id", "")),
        "type": str(chunk.get("type", "article")),
        "article_number": int(chunk.get("article_number", 0)),
    }
    
    # Extraire les métadonnées du chunk
    chunk_meta = chunk.get("metadata", {})
    
    if "hierarchy_path" in chunk_meta:
        meta["hierarchy_path"] = str(chunk_meta["hierarchy_path"])
    
    if "source" in chunk_meta:
        meta["source"] = str(chunk_meta["source"])
    
    # Aplatir la hiérarchie 
    hierarchy = chunk_meta.get("hierarchy", {})
    if isinstance(hierarchy, dict):
        if hierarchy.get("livre"):
            meta["livre"] = str(hierarchy["livre"])
        if hierarchy.get("livre_title"):
            meta["livre_title"] = str(hierarchy["livre_title"])
        if hierarchy.get("titre"):
            meta["titre"] = str(hierarchy["titre"])
        if hierarchy.get("titre_title"):
            meta["titre_title"] = str(hierarchy["titre_title"])
        if hierarchy.get("chapitre"):
            meta["chapitre"] = str(hierarchy["chapitre"])
        if hierarchy.get("chapitre_title"):
            meta["chapitre_title"] = str(hierarchy["chapitre_title"])
        if hierarchy.get("section"):
            meta["section"] = str(hierarchy["section"])
      
    return meta


def index_to_chromadb(
    chunks: List[Dict[str, Any]], 
    embeddings: List[List[float]],
    collection_name: Optional[str] = None
) -> chromadb.Collection:
    """
    Indexe les chunks et leurs embeddings dans ChromaDB.
    
    Les métadonnées sont aplaties pour supporter le filtrage par:
    - livre: "LIVRE IV"
    - titre: "TITRE II"
    - chapitre: "CHAPITRE I"
    - type: "article" | "definition"
    
    Args:
        chunks: Liste des chunks enrichis
        embeddings: Liste des vecteurs d'embeddings
        collection_name: Nom de la collection (défaut: depuis config) 
    Returns:
        Collection ChromaDB créée
    """
    client = get_chroma_client()
    collection_name = collection_name or settings.chroma_collection_name
    
    try:
        client.delete_collection(collection_name)
        logger.info(f"Collection '{collection_name}' existante supprimee")
    except Exception:
        pass 
    
    # Créer nouvelle collection
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "Code du Numérique du Bénin - Articles"}
    )
    
    # Préparer les données pour l'indexation
    ids = [f"chunk_{i}_{chunk['id'].replace(' ', '_')}" for i, chunk in enumerate(chunks)]
    
    documents = [chunk.get("content_with_context", chunk["content"]) for chunk in chunks]
    
    # Aplatir les métadonnées pour chaque chunk
    metadatas = [flatten_metadata_for_chroma(chunk) for chunk in chunks]
    
    logger.info(f"Métadonnées aplaties pour {len(metadatas)} chunks")
    
    # Indexation par batches
    batch_size = 500
    for i in range(0, len(chunks), batch_size):
        end_idx = min(i + batch_size, len(chunks))
        
        collection.add(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )
        logger.info(f"   Batch {i // batch_size + 1}: {end_idx - i} chunks indexes")
    
    logger.success(f"{len(chunks)} chunks indexes dans '{collection_name}'")
    
    return collection


def load_vectorstore(collection_name: Optional[str] = None) -> chromadb.Collection:
    """
    Charge une collection ChromaDB existante.
    
    Args:
        collection_name: Nom de la collection
    Returns:
        Collection ChromaDB
    """
    client = get_chroma_client()
    collection_name = collection_name or settings.chroma_collection_name
    
    return client.get_collection(collection_name)


def get_collection_stats(collection: chromadb.Collection) -> Dict[str, Any]:
    """
    Retourne les statistiques d'une collection.
    
    Args:
        collection: Collection ChromaDB
    Returns:
        Dictionnaire de statistiques
    """
    return {
        "name": collection.name,
        "count": collection.count(),
        "metadata": collection.metadata,
    }
