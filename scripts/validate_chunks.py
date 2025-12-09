#!/usr/bin/env python3
"""
BÉNIN JURIS-IA - Script de validation des chunks
Vérifie la qualité du chunking et détecte les anomalies.
"""
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from loguru import logger


def load_chunks(input_path: Path) -> List[Dict[str, Any]]:
    """Charge les chunks depuis un fichier JSON."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_chunk_count(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Vérifie que le nombre de chunks est dans la plage attendue."""
    count = len(chunks)
    
    # Le Code du Numérique a environ 600+ articles
    expected_min = 500
    expected_max = 800
    
    status = "OK" if expected_min <= count <= expected_max else "WARN"
    
    return {
        "name": "Nombre de chunks",
        "status": status,
        "value": count,
        "expected": f"{expected_min}-{expected_max}",
        "message": f"{count} chunks extraits" if status == "OK" else f"Nombre inhabituel: {count}",
    }


def validate_empty_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Détecte les chunks avec contenu vide."""
    empty = [c["id"] for c in chunks if not c.get("content", "").strip()]
    
    status = "OK" if len(empty) == 0 else "ERROR"
    
    return {
        "name": "Chunks vides",
        "status": status,
        "value": len(empty),
        "expected": 0,
        "details": empty[:10] if empty else None,
        "message": "Aucun chunk vide" if status == "OK" else f"{len(empty)} chunks vides detectes",
    }


def validate_article_sequence(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Vérifie la continuité de la séquence d'articles."""
    article_nums = sorted([
        c["article_number"] 
        for c in chunks 
        if c.get("article_number") and c.get("type") == "article"
    ])
    
    if not article_nums:
        return {
            "name": "Sequence d'articles",
            "status": "ERROR",
            "message": "Aucun article trouve",
        }
    
    # Trouver les gaps
    expected = set(range(min(article_nums), max(article_nums) + 1))
    actual = set(article_nums)
    missing = sorted(expected - actual)
    
    status = "OK" if len(missing) <= 5 else "WARN"
    
    return {
        "name": "Sequence d'articles",
        "status": status,
        "value": f"{min(article_nums)}-{max(article_nums)}",
        "missing_count": len(missing),
        "missing_articles": missing[:20] if missing else None,
        "message": f"Plage {min(article_nums)}-{max(article_nums)}, {len(missing)} manquants",
    }


def validate_hierarchy_coverage(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Vérifie que les métadonnées hiérarchiques sont présentes."""
    with_hierarchy = sum(
        1 for c in chunks 
        if c.get("metadata", {}).get("hierarchy_path")
    )
    
    coverage = with_hierarchy / len(chunks) * 100 if chunks else 0
    status = "OK" if coverage >= 95 else "WARN" if coverage >= 80 else "ERROR"
    
    return {
        "name": "Couverture hierarchique",
        "status": status,
        "value": f"{coverage:.1f}%",
        "expected": ">=95%",
        "message": f"{with_hierarchy}/{len(chunks)} chunks ont une hierarchie",
    }


def detect_truncated_words(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Détecte les mots potentiellement coupés en fin de chunk."""
    suspects = []
    
    for chunk in chunks:
        content = chunk.get("content", "").strip()
        if not content:
            continue
        
        # Dernier mot
        words = content.split()
        if not words:
            continue
            
        last_word = words[-1]
        
        # Heuristiques: mot trop court, ne finit pas par ponctuation normale
        if (
            len(last_word) < 3 
            and not last_word.endswith((".", ":", ";", ")", "»", '"', "'"))
            and last_word.isalpha()
        ):
            suspects.append({
                "id": chunk["id"],
                "last_word": last_word,
            })
    
    status = "OK" if len(suspects) <= 3 else "WARN"
    
    return {
        "name": "Mots tronques",
        "status": status,
        "value": len(suspects),
        "expected": "<=3",
        "details": suspects[:10] if suspects else None,
        "message": f"{len(suspects)} chunks suspects" if suspects else "Aucune troncation detectee",
    }


def validate_content_length_distribution(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyse la distribution des longueurs de contenu."""
    lengths = [len(c.get("content", "")) for c in chunks]
    
    if not lengths:
        return {"name": "Distribution longueurs", "status": "ERROR", "message": "Pas de donnees"}
    
    avg_len = sum(lengths) / len(lengths)
    min_len = min(lengths)
    max_len = max(lengths)
    
    # Chunks très courts (<50 chars) peuvent indiquer un problème
    very_short = sum(1 for l in lengths if l < 50)
    
    status = "OK" if very_short <= 5 else "WARN"
    
    return {
        "name": "Distribution longueurs",
        "status": status,
        "value": f"moy={avg_len:.0f}, min={min_len}, max={max_len}",
        "very_short_count": very_short,
        "message": f"{very_short} chunks tres courts (<50 chars)",
    }


def validate_type_distribution(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyse la distribution des types de chunks."""
    types = Counter(c.get("type", "unknown") for c in chunks)
    
    return {
        "name": "Types de chunks",
        "status": "INFO",
        "distribution": dict(types),
        "message": ", ".join(f"{t}: {n}" for t, n in types.items()),
    }


def run_all_validations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Exécute toutes les validations."""
    return [
        validate_chunk_count(chunks),
        validate_empty_chunks(chunks),
        validate_article_sequence(chunks),
        validate_hierarchy_coverage(chunks),
        detect_truncated_words(chunks),
        validate_content_length_distribution(chunks),
        validate_type_distribution(chunks),
    ]


def print_report(results: List[Dict[str, Any]]):
    """Affiche le rapport de validation."""
    logger.info("=" * 60)
    logger.info("RAPPORT DE VALIDATION DES CHUNKS")
    logger.info("=" * 60)
    
    for result in results:
        status = result.get("status", "?")
        name = result.get("name", "Unknown")
        message = result.get("message", "")
        
        if status == "OK":
            logger.success(f"{name}: {message}")
        elif status == "WARN":
            logger.warning(f"{name}: {message}")
        elif status == "ERROR":
            logger.error(f"{name}: {message}")
        else:
            logger.info(f"{name}: {message}")
        
        if result.get("details"):
            logger.debug(f"   Details: {result['details'][:5]}...")
    
    # Résumé
    statuses = [r.get("status") for r in results]
    errors = statuses.count("ERROR")
    warnings = statuses.count("WARN")
    
    logger.info("-" * 60)
    if errors:
        logger.error(f"{errors} erreur(s) detectee(s)")
    elif warnings:
        logger.warning(f"{warnings} avertissement(s)")
    else:
        logger.success("Toutes les validations passees!")


def main():
    parser = argparse.ArgumentParser(description="Validation des chunks BENIN JURIS-IA")
    parser.add_argument(
        "--input", 
        type=str, 
        default=None,
        help="Chemin vers le fichier JSON des chunks"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sortie au format JSON"
    )
    
    args = parser.parse_args()
    
    # Chemin par défaut
    input_path = Path(args.input) if args.input else settings.processed_path
    
    if not input_path.exists():
        logger.error(f"Fichier non trouve: {input_path}")
        logger.error("   Executez d'abord: python scripts/ingest.py")
        sys.exit(1)
    
    # Charger et valider
    chunks = load_chunks(input_path)
    results = run_all_validations(chunks)
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results)


if __name__ == "__main__":
    main()
