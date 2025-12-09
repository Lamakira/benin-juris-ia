"""
BÉNIN JURIS-IA - Metadata Enricher
Injection du contexte hiérarchique (Livre > Titre > Chapitre) pour chaque article.

Cette version utilise une MACHINE À ÉTATS qui parse le texte complet
pour construire dynamiquement la hiérarchie, au lieu de mappings statiques.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


# PATTERNS DE DÉTECTION (Regex strictes)
# Pattern pour détecter les lignes de sommaire
TOC_LINE_PATTERN = re.compile(r"\.{2,}\s*\d+\s*$")

# Patterns pour détecter les marqueurs de structure
# Ces patterns matchent seulement si la ligne ne finit PAS par des points + chiffre
LIVRE_PATTERN = re.compile(r"^(LIVRE\s+[IVX]+|LIVRE\s+PREMIER|LIVRE\s+PRELIMINAIRE)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
TITRE_PATTERN = re.compile(r"^(TITRE\s+[IVX]+|TITRE\s+PREMIER|TITRE\s+UNIQUE)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
CHAPITRE_PATTERN = re.compile(r"^(CHAPITRE\s+[IVX]+|CHAPITRE\s+PREMIER|CHAPITRE\s+UNIQUE)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(SECTION\s+\d+)\s*[:\-]?\s*(.*)$", re.IGNORECASE)

# Pattern pour détecter les Articles
ARTICLE_PATTERN = re.compile(r"^(Article\s+(\d+)(?:er)?)\s*[:\-\.]", re.IGNORECASE)

# Patterns pour détecter le vrai début du code après le sommaire
START_MARKERS = [
    re.compile(r"^LIVRE\s+PRELIMINAIRE\b", re.IGNORECASE),
    re.compile(r"^LIVRE\s+PREMIER\b", re.IGNORECASE),
    re.compile(r"^LIVRE\s+I\s*[:\-]\s*DISPOSITIONS", re.IGNORECASE),
]


def is_toc_line(line: str) -> bool:
    """
    Vérifie si une ligne fait partie du sommaire.
    
    Les lignes de sommaire se terminent par des points de suite et un numéro de page.
    Ex: "LIVRE I ....... 45"
    
    Args:
        line: Ligne à vérifier
    Returns:
        True si c'est une ligne de sommaire
    """
    return bool(TOC_LINE_PATTERN.search(line))


def is_start_of_content(line: str) -> bool:
    """
    Vérifie si une ligne marque le début du contenu réel après le sommaire.
    
    Args:
        line: Ligne à vérifier    
    Returns:
        True si c'est le début du contenu
    """
    # Ne pas considérer les lignes de sommaire comme début
    if is_toc_line(line):
        return False
    
    # Vérifier contre les marqueurs de début
    for pattern in START_MARKERS:
        if pattern.match(line):
            return True
    
    return False


# STATE MACHINE - Structure de données
@dataclass
class HierarchyState:
    """État courant de la hiérarchie lors du parsing."""
    livre: Optional[str] = None
    livre_title: Optional[str] = None
    titre: Optional[str] = None
    titre_title: Optional[str] = None
    chapitre: Optional[str] = None
    chapitre_title: Optional[str] = None
    section: Optional[str] = None
    section_title: Optional[str] = None
    
    def reset_below_livre(self):
        """Réinitialise titre, chapitre, section quand un nouveau LIVRE est détecté."""
        self.titre = None
        self.titre_title = None
        self.chapitre = None
        self.chapitre_title = None
        self.section = None
        self.section_title = None
    
    def reset_below_titre(self):
        """Réinitialise chapitre, section quand un nouveau TITRE est détecté."""
        self.chapitre = None
        self.chapitre_title = None
        self.section = None
        self.section_title = None
    
    def reset_below_chapitre(self):
        """Réinitialise section quand un nouveau CHAPITRE est détecté."""
        self.section = None
        self.section_title = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire."""
        return {
            "livre": self.livre,
            "livre_title": self.livre_title,
            "titre": self.titre,
            "titre_title": self.titre_title,
            "chapitre": self.chapitre,
            "chapitre_title": self.chapitre_title,
            "section": self.section,
            "section_title": self.section_title,
        }
    
    def copy(self) -> "HierarchyState":
        """Crée une copie de l'état courant."""
        return HierarchyState(
            livre=self.livre,
            livre_title=self.livre_title,
            titre=self.titre,
            titre_title=self.titre_title,
            chapitre=self.chapitre,
            chapitre_title=self.chapitre_title,
            section=self.section,
            section_title=self.section_title,
        )


# STATE MACHINE - Parsing du texte complet
def build_article_hierarchy_map(full_text: str) -> Dict[int, HierarchyState]:
    """
    Parse le texte complet et construit un mapping article_num -> hiérarchie.
    
    Utilise une machine à états qui:
    1. IGNORE le sommaire (lignes avec "....... 45")
    2. Démarre le parsing uniquement après "LIVRE PRELIMINAIRE" ou "LIVRE PREMIER"
    3. Met à jour le contexte courant à chaque marqueur de structure
    4. Reset les sous-niveaux lors des transitions
    
    Args:
        full_text: Texte complet nettoyé et fusionné     
    Returns:
        Dictionnaire {numéro_article: état_hiérarchique}
    """
    article_hierarchy_map: Dict[int, HierarchyState] = {}
    current_state = HierarchyState()
    
    # Ne commence le parsing qu'après avoir passé le sommaire
    parsing_started = False
    
    stats = {
        "toc_lines_skipped": 0,
        "livres": 0,
        "titres": 0,
        "chapitres": 0,
        "sections": 0,
        "articles": 0,
    }
    
    for line in full_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Ignorer les lignes de sommaire
        if is_toc_line(line):
            stats["toc_lines_skipped"] += 1
            continue
        
        # Détecter le début du contenu réel après le sommaire
        if not parsing_started:
            if is_start_of_content(line):
                parsing_started = True
                logger.info(f"Debut du contenu detecte: {line[:60]}...")
            else:
                continue
        
        # Détecter LIVRE (priorité la plus haute)
        livre_match = LIVRE_PATTERN.match(line)
        if livre_match:
            current_state.livre = livre_match.group(1).upper()
            current_state.livre_title = livre_match.group(2).strip() if livre_match.group(2) else None
            current_state.reset_below_livre()  # reset titre, chapitre, section
            stats["livres"] += 1
            continue
        
        # Détecter TITRE
        titre_match = TITRE_PATTERN.match(line)
        if titre_match:
            current_state.titre = titre_match.group(1).upper()
            current_state.titre_title = titre_match.group(2).strip() if titre_match.group(2) else None
            current_state.reset_below_titre()  # reset chapitre, section
            stats["titres"] += 1
            continue
        
        # Détecter CHAPITRE
        chapitre_match = CHAPITRE_PATTERN.match(line)
        if chapitre_match:
            current_state.chapitre = chapitre_match.group(1).upper()
            current_state.chapitre_title = chapitre_match.group(2).strip() if chapitre_match.group(2) else None
            current_state.reset_below_chapitre()  # reset section
            stats["chapitres"] += 1
            continue
        
        # Détecter SECTION
        section_match = SECTION_PATTERN.match(line)
        if section_match:
            current_state.section = section_match.group(1).upper()
            current_state.section_title = section_match.group(2).strip() if section_match.group(2) else None
            stats["sections"] += 1
            continue
        
        # 6. Détecter ARTICLE
        article_match = ARTICLE_PATTERN.match(line)
        if article_match:
            article_num = int(article_match.group(2))
            # Sauvegarder une copie de l'état courant pour cet article
            article_hierarchy_map[article_num] = current_state.copy()
            stats["articles"] += 1
    
    logger.info("Parsing hiérarchique terminé:")
    logger.info(f"   - Lignes de sommaire ignorées: {stats['toc_lines_skipped']}")
    logger.info(f"   - Livres détectés: {stats['livres']}")
    logger.info(f"   - Titres détectés: {stats['titres']}")
    logger.info(f"   - Chapitres détectés: {stats['chapitres']}")
    logger.info(f"   - Sections détectées: {stats['sections']}")
    logger.info(f"   - Articles mappés: {stats['articles']}")
    
    return article_hierarchy_map


# FORMATTAGE ET ENRICHISSEMENT
def format_hierarchy_path(state: HierarchyState) -> str:
    """
    Formate le chemin hiérarchique en chaîne lisible.
    
    Args:
        state: État hiérarchique
    Returns:
        Chaîne formatée (ex: "LIVRE VI > TITRE I > CHAPITRE IX")
    """
    parts = []
    
    if state.livre:
        livre_str = state.livre
        if state.livre_title:
            title = state.livre_title[:50] + "..." if len(state.livre_title) > 50 else state.livre_title
            livre_str += f" ({title})"
        parts.append(livre_str)
    
    if state.titre:
        titre_str = state.titre
        if state.titre_title:
            title = state.titre_title[:50] + "..." if len(state.titre_title) > 50 else state.titre_title
            titre_str += f" ({title})"
        parts.append(titre_str)
    
    if state.chapitre:
        chapitre_str = state.chapitre
        if state.chapitre_title:
            title = state.chapitre_title[:50] + "..." if len(state.chapitre_title) > 50 else state.chapitre_title
            chapitre_str += f" ({title})"
        parts.append(chapitre_str)
    
    if state.section:
        section_str = state.section
        if state.section_title:
            title = state.section_title[:40] + "..." if len(state.section_title) > 40 else state.section_title
            section_str += f" ({title})"
        parts.append(section_str)
    
    return " > ".join(parts) if parts else "Structure non définie"


def enrich_chunks_with_hierarchy(
    chunks: List[Dict[str, Any]], 
    full_text: str
) -> List[Dict[str, Any]]:
    """
    Enrichit les chunks avec la hiérarchie extraite dynamiquement du texte.
    
    Cette fonction:
    1. Parse le texte complet pour construire le mapping article->hiérarchie
    2. Applique ce mapping à chaque chunk
    
    Args:
        chunks: Liste des chunks à enrichir
        full_text: Texte complet nettoyé (pour le parsing de structure)
        
    Returns:
        Liste des chunks enrichis avec hierarchy_path correct
    """
    # Construire le mapping dynamique
    article_hierarchy_map = build_article_hierarchy_map(full_text)
    
    enriched_chunks: List[Dict[str, Any]] = []
    stats = {"enriched": 0, "unknown": 0}
    
    for chunk in chunks:
        enriched = chunk.copy()
        article_num = chunk.get("article_number")
        
        if article_num and article_num in article_hierarchy_map:
            # Récupérer la hiérarchie depuis le mapping
            state = article_hierarchy_map[article_num]
            hierarchy_path = format_hierarchy_path(state)
            
            enriched["metadata"] = {
                **chunk.get("metadata", {}),
                "hierarchy": state.to_dict(),
                "hierarchy_path": hierarchy_path,
                "source": "Code du Numérique du Bénin - Loi N°2017-20 du 20 avril 2018",
                "article_number": article_num,
            }
            
            # Préfixe contextuel pour l'embedding
            context_prefix = f"[Contexte: {hierarchy_path}]\n[{chunk['id']}]\n\n"
            enriched["content_with_context"] = context_prefix + chunk["content"]
            stats["enriched"] += 1
        else:
            # Article non trouvé dans le mapping
            enriched["metadata"] = {
                **chunk.get("metadata", {}),
                "source": "Code du Numérique du Bénin - Loi N°2017-20 du 20 avril 2018",
                "hierarchy_path": "Article 1 - Définitions" if chunk.get("type") == "definition" else "Non classifié",
            }
            enriched["content_with_context"] = chunk["content"]
            stats["unknown"] += 1
        
        enriched_chunks.append(enriched)
    
    logger.info("Enrichissement terminé:")
    logger.info(f"   - Chunks enrichis avec hiérarchie: {stats['enriched']}")
    logger.info(f"   - Chunks sans mapping (définitions, etc.): {stats['unknown']}")
    
    return enriched_chunks


# Variable globale pour stocker le texte complet
_full_text_cache: Optional[str] = None

def set_full_text(text: str):
    """
    Définit le texte complet pour l'enrichissement.
    Doit être appelé avant enrich_metadata().
    """
    global _full_text_cache
    _full_text_cache = text


def enrich_metadata(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Point d'entrée principal pour l'enrichissement des métadonnées.
    
    IMPORTANT: Appeler set_full_text(text) avant cette fonction,
    ou utiliser directement enrich_chunks_with_hierarchy(chunks, full_text).
    
    Args:
        chunks: Liste des chunks à enrichir  
    Returns:
        Liste des chunks enrichis
    """
    global _full_text_cache
    
    if _full_text_cache is None:
        logger.warning("Texte complet non defini. Utilisation du fallback.")
        # Fallback: reconstruire le texte depuis les chunks
        _full_text_cache = "\n".join(c.get("content", "") for c in chunks)
    
    return enrich_chunks_with_hierarchy(chunks, _full_text_cache)


# UTILITAIRES DE DEBUG
def debug_hierarchy_detection(full_text: str) -> None:
    """
    Affiche tous les marqueurs de structure détectés.
    """
    logger.debug("" + "=" * 60)
    logger.debug("DEBUG: Marqueurs de structure détectés")
    logger.debug("=" * 60)
    
    current_livre = None
    
    for i, line in enumerate(full_text.split("\n"), 1):
        line = line.strip()
        
        if LIVRE_PATTERN.match(line):
            current_livre = line
            logger.debug(f"[{i}] LIVRE: {line}")
        elif TITRE_PATTERN.match(line):
            logger.debug(f"  [{i}] TITRE: {line}")
        elif CHAPITRE_PATTERN.match(line):
            logger.debug(f"    [{i}] CHAPITRE: {line}")
        elif SECTION_PATTERN.match(line):
            logger.debug(f"      [{i}] SECTION: {line}")

