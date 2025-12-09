"""BÉNIN JURIS-IA - Module de retrieval"""

from .embedder import generate_embeddings
from .indexer import index_to_chromadb, load_vectorstore
from .searcher import semantic_search

__all__ = ["generate_embeddings", "index_to_chromadb", "load_vectorstore", "semantic_search"]
