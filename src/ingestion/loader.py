"""
BÉNIN JURIS-IA - PDF Loader
Extraction du texte PDF avec pdfplumber pour une meilleure gestion de l'encodage.
"""
import pdfplumber
from pathlib import Path
from typing import List


def load_pdf(pdf_path: str | Path) -> List[str]:
    """
    Charge toutes les pages d'un fichier PDF et retourne le texte de chaque page.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
    Returns:
        Liste de chaînes, une par page du PDF 
    Raises:
        FileNotFoundError: Si le fichier PDF n'existe pas
        Exception: Si erreur lors de l'extraction
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"Fichier PDF non trouvé: {pdf_path}")
    
    pages_text: List[str] = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                pages_text.append(text)
            else:
                # Page vide ou non extractible
                pages_text.append("")
                print(f"⚠️  Page {page_num}: aucun texte extrait")
    
    print(f"✅ {len(pages_text)} pages chargées depuis {pdf_path.name}")
    return pages_text


def get_pdf_metadata(pdf_path: str | Path) -> dict:
    """
    Extrait les métadonnées du PDF.
    
    Args:
        pdf_path: Chemin vers le fichier PDF  
    Returns:
        Dictionnaire des métadonnées
    """
    pdf_path = Path(pdf_path)
    
    with pdfplumber.open(pdf_path) as pdf:
        return {
            "num_pages": len(pdf.pages),
            "metadata": pdf.metadata or {},
        }
