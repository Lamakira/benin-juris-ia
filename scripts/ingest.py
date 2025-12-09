#!/usr/bin/env python3
"""
BÉNIN JURIS-IA - Script d'ingestion principal
Pipeline complet : Load -> Clean -> Chunk -> Enrich -> Embed -> Index
"""
import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import config first to initialize logger
from src.config import settings
from loguru import logger
from src.ingestion import load_pdf, clean_text, chunk_by_articles, enrich_metadata
from src.ingestion.metadata_enricher import set_full_text
from src.retrieval import generate_embeddings, index_to_chromadb


def ensure_directories():
    """Crée les répertoires nécessaires s'ils n'existent pas."""
    dirs = [
        settings.project_root / "data/raw",
        settings.project_root / "data/processed",
        settings.project_root / "data/vectorstore",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        logger.info(f"Repertoire: {d.relative_to(settings.project_root)}")


def save_processed_chunks(chunks, output_path: Path):
    """Sauvegarde les chunks traités en JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Chunks sauvegardes: {output_path}")


def load_processed_chunks(input_path: Path):
    """Charge les chunks depuis un fichier JSON."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Point d'entrée principal du pipeline d'ingestion."""
    logger.info("=" * 60)
    logger.info("BENIN JURIS-IA - Pipeline d'ingestion")
    logger.info("=" * 60)
    
    # 0. Vérifier les répertoires
    logger.info("Verification des repertoires...")
    ensure_directories()
    
    # 1. Vérifier que le PDF existe
    pdf_path = settings.pdf_path
    if not pdf_path.exists():
        logger.error(f"PDF non trouve!")
        logger.error(f"   Attendu: {pdf_path}")
        logger.error(f"   Placez le fichier CODE-DU-NUMERIQUE.pdf dans data/raw/")
        sys.exit(1)
    
    # 2. Charger le PDF
    logger.info("Etape 1/6 - Chargement du PDF...")
    raw_pages = load_pdf(pdf_path)
    
    # 3. Nettoyer le texte
    logger.info("Etape 2/6 - Nettoyage ligne par ligne...")
    cleaned_text = clean_text(raw_pages)
    
    # 4. Découper par Articles
    logger.info("Etape 3/6 - Segmentation par Articles...")
    chunks = chunk_by_articles(cleaned_text)
    
    if not chunks:
        logger.error("Aucun article extrait!")
        sys.exit(1)
    
    # 5. Enrichir les métadonnées (avec le texte complet pour le parsing hiérarchique)
    logger.info("Etape 4/6 - Enrichissement des metadonnees...")
    set_full_text(cleaned_text)  # Passer le texte complet pour la machine à états
    enriched_chunks = enrich_metadata(chunks)
    
    # 6. Sauvegarder les chunks traités
    logger.info("Etape 5/6 - Sauvegarde des chunks traites...")
    save_processed_chunks(enriched_chunks, settings.processed_path)
    
    # 7. Générer les embeddings et indexer
    logger.info("Etape 6/6 - Vectorisation et indexation...")
    embeddings = generate_embeddings(enriched_chunks)
    collection = index_to_chromadb(enriched_chunks, embeddings)
    
    # Résumé final
    logger.info("=" * 60)
    logger.success("INGESTION TERMINEE AVEC SUCCES!")
    logger.info("=" * 60)
    logger.info("Statistiques:")
    logger.info(f"   - Pages PDF traitees: {len(raw_pages)}")
    logger.info(f"   - Chunks generes: {len(enriched_chunks)}")
    logger.info(f"   - Embeddings crees: {len(embeddings)}")
    logger.info(f"   - Collection ChromaDB: {collection.name} ({collection.count()} documents)")
    logger.success("L'assistant est pret a repondre aux questions!")
    logger.info("   Lancez: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
