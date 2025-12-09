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

from src.config import settings
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
        print(f"📁 {d.relative_to(settings.project_root)}")


def save_processed_chunks(chunks, output_path: Path):
    """Sauvegarde les chunks traités en JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Chunks sauvegardés: {output_path}")


def load_processed_chunks(input_path: Path):
    """Charge les chunks depuis un fichier JSON."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Point d'entrée principal du pipeline d'ingestion."""
    print("=" * 60)
    print("🚀 BÉNIN JURIS-IA - Pipeline d'ingestion")
    print("=" * 60)
    
    # 0. Vérifier les répertoires
    print("\n📂 Vérification des répertoires...")
    ensure_directories()
    
    # 1. Vérifier que le PDF existe
    pdf_path = settings.pdf_path
    if not pdf_path.exists():
        print(f"\n❌ ERREUR: PDF non trouvé!")
        print(f"   Attendu: {pdf_path}")
        print(f"   Placez le fichier CODE-DU-NUMERIQUE.pdf dans data/raw/")
        sys.exit(1)
    
    # 2. Charger le PDF
    print("\n📄 Étape 1/6 - Chargement du PDF...")
    raw_pages = load_pdf(pdf_path)
    
    # 3. Nettoyer le texte
    print("\n🧹 Étape 2/6 - Nettoyage ligne par ligne...")
    cleaned_text = clean_text(raw_pages)
    
    # 4. Découper par Articles
    print("\n✂️  Étape 3/6 - Segmentation par Articles...")
    chunks = chunk_by_articles(cleaned_text)
    
    if not chunks:
        print("❌ ERREUR: Aucun article extrait!")
        sys.exit(1)
    
    # 5. Enrichir les métadonnées (avec le texte complet pour le parsing hiérarchique)
    print("\n📋 Étape 4/6 - Enrichissement des métadonnées...")
    set_full_text(cleaned_text)  # Passer le texte complet pour la machine à états
    enriched_chunks = enrich_metadata(chunks)
    
    # 6. Sauvegarder les chunks traités
    print("\n💾 Étape 5/6 - Sauvegarde des chunks traités...")
    save_processed_chunks(enriched_chunks, settings.processed_path)
    
    # 7. Générer les embeddings et indexer
    print("\n🔢 Étape 6/6 - Vectorisation et indexation...")
    embeddings = generate_embeddings(enriched_chunks)
    collection = index_to_chromadb(enriched_chunks, embeddings)
    
    # Résumé final
    print("\n" + "=" * 60)
    print("✅ INGESTION TERMINÉE AVEC SUCCÈS!")
    print("=" * 60)
    print(f"📊 Statistiques:")
    print(f"   - Pages PDF traitées: {len(raw_pages)}")
    print(f"   - Chunks générés: {len(enriched_chunks)}")
    print(f"   - Embeddings créés: {len(embeddings)}")
    print(f"   - Collection ChromaDB: {collection.name} ({collection.count()} documents)")
    print(f"\n🎉 L'assistant est prêt à répondre aux questions!")
    print(f"   Lancez: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()

