"""BÉNIN JURIS-IA - Module d'ingestion"""

from .loader import load_pdf
from .cleaner import clean_text
from .chunker import chunk_by_articles
from .metadata_enricher import enrich_metadata

__all__ = ["load_pdf", "clean_text", "chunk_by_articles", "enrich_metadata"]
