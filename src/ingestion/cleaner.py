"""
BÉNIN JURIS-IA - Text Cleaner
Nettoyage ligne par ligne avant fusion pour éliminer le bruit récurrent.
Inclut le fix pour l'encodage CID (Mojibake) spécifique à ce PDF.
"""
import re
from typing import List, Pattern
from loguru import logger


# =============================================================================
# CID ENCODING FIX (Critique pour ce PDF)
# =============================================================================
# Le PDF utilise une police avec un décalage ASCII.
# Pattern: (cid:XX) où XX est un code numérique
# Formule de décodage: chr(int(XX) + 29)

CID_PATTERN = re.compile(r"\(cid:(\d+)\)")

def fix_cid_encoding(text: str) -> str:
    """
    Répare l'encodage CID (Mojibake) spécifique à ce PDF.
    
    Le PDF utilise une police personnalisée qui encode les caractères
    sous forme (cid:XX). La formule de décodage est: chr(code + 29).
    
    Exemples:
        (cid:79) -> chr(79+29) = chr(108) = 'l'
        (cid:76) -> chr(76+29) = chr(105) = 'i'
        (cid:70) -> chr(70+29) = chr(99)  = 'c'
    
    Args:
        text: Texte brut avec potentiels (cid:XX) 
    Returns:
        Texte avec les CID décodés en caractères lisibles
    """
    def decode_cid(match: re.Match) -> str:
        code = int(match.group(1))
        try:
            # Appliquer le décalage ASCII (+29)
            decoded_char = chr(code + 29)
            return decoded_char
        except (ValueError, OverflowError):
            # En cas d'erreur, retourner le match original
            return match.group(0)
    
    return CID_PATTERN.sub(decode_cid, text)


# =============================================================================
# MOJIBAKE FIX - SPÉCIFIQUE AU CODE DU NUMÉRIQUE
# =============================================================================
# Ce mappage est spécifique à la police utilisée dans le PDF du Code du Numérique.
# Les caractères ont été identifiés par analyse directe du document.

# Mappage spécifique au PDF du Code du Numérique du Bénin
# Après le décodage CID (+29), certains caractères spéciaux restent mal encodés
SPECIFIC_CODE_NUMERIQUE_MAPPING = [
    # 1. Ponctuation critique
    ("\u0352", "'"),      # ͒ -> ' (Apostrophe très fréquente)
    
    # 2. Accents et caractères spéciaux (Mapping observé)
    ("¿", "à"),           # à
    ("È", "é"),           # é
    ("Ç", "è"),           # è
    ("Ú", "û"),           # û
    ("Á", "â"),           # â
    ("Ø", "ù"),           # ù
    ("¨", "É"),           # ¨ -> É (ex: l'¨tat)
    ("Ĳ", "œ"),           # œ (ligature)
    
    # 3. Nouveaux caractères identifiés
    ("Ó", "ô"),           # ô (ex: contrôle)
    ("Æ", "ç"),           # ç (ex: façon, reçoit)
    ("Í", "î"),           # î (ex: maîtrise, connaître)
    
    # 4. Cas contextuels (À appliquer prudemment)
    # Le PDF utilise parfois "É" pour "ê" (ex: intérÉt, arrÉt, prÉt).
    # Mais "É" est aussi utilisé pour É majuscule (Élaboration).
    # On remplace les cas les plus fréquents de "É" -> "ê" manuellement
    ("intérÉt", "intérêt"),
    ("arrÉt", "arrêt"),
    ("prÉt", "prêt"),
    ("bientÉt", "bientôt"),
    ("sûretÉ", "sûreté"),
    ("forÉt", "forêt"),
    ("enquÉte", "enquête"),
    ("Étre", "être"),      # Erreur fréquente en début de phrase ou milieu
]

# Remplacements génériques pour le Mojibake UTF-8 standard
GENERIC_MOJIBAKE_REPLACEMENTS = [
    # UTF-8 mal interprété comme Latin-1 (accents français)
    ("Ã©", "é"),
    ("Ã¨", "è"),
    ("Ã ", "à"),
    ("Ã¢", "â"),
    ("Ãª", "ê"),
    ("Ã®", "î"),
    ("Ã´", "ô"),
    ("Ã»", "û"),
    ("Ã§", "ç"),
    ("Ã¹", "ù"),
    ("Ã‰", "É"),
    ("Ã€", "À"),
    # Guillemets et apostrophes
    ("Â«", "«"),
    ("Â»", "»"),
    ("Â ", " "),
]


def fix_specific_mojibake(text: str) -> str:
    """
    Répare le Mojibake spécifique au PDF du Code du Numérique.
    
    Applique le mappage de caractères identifié par analyse du document.
    Doit être appelé APRÈS fix_cid_encoding().
    
    Args:
        text: Texte après décodage CID
        
    Returns:
        Texte avec accents et apostrophes corrigés
    """
    for corrupted, correct in SPECIFIC_CODE_NUMERIQUE_MAPPING:
        text = text.replace(corrupted, correct)
    return text


def fix_common_mojibake(text: str) -> str:
    """
    Répare les caractères français courants mal encodés (UTF-8/Latin-1).
    
    Args:
        text: Texte potentiellement corrompu
        
    Returns:
        Texte avec les caractères français réparés
    """
    for corrupted, correct in GENERIC_MOJIBAKE_REPLACEMENTS:
        text = text.replace(corrupted, correct)
    return text


# =============================================================================
# NOISE PATTERNS (Bruit à supprimer)
# =============================================================================

NOISE_PATTERNS: List[Pattern] = [
    # En-tête de la loi (variations possibles)
    re.compile(r"LOI\s+N°?\s*2017-20.*", re.IGNORECASE),
    re.compile(r"LOI\s+N°?\s*2017.*20\s+AVRIL\s+2018.*", re.IGNORECASE),
    
    # Sous-titre récurrent
    re.compile(r"PORTANT\s+CODE\s+DU\s+NUM[EÉ]RIQUE.*", re.IGNORECASE),
    re.compile(r"EN\s+R[EÉ]PUBLIQUE\s+DU\s+B[EÉ]NIN", re.IGNORECASE),
    
    # Numéros de page isolés - différents formats
    re.compile(r"^\s*\[?\d{1,3}\]?\s*$"),  # [4], 4, [ 12 ]
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),  # Page 12
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),  # - 12 -
    
    # Lignes de sommaire avec points de suspension
    re.compile(r"^.*\.{3,}\s*\d+\s*$"),  # Chapitre I ....... 45
    
    # Footer récurrent (Autorité de Protection des Données)
    re.compile(r"Impression\s+réalisée\s+par\s+l['']?Autorité\s+de\s+Protection\s+des\s+Données.*", re.IGNORECASE),
    
    # Lignes vides ou whitespace uniquement
    re.compile(r"^\s*$"),
]


def is_noise_line(line: str) -> bool:
    """
    Vérifie si une ligne correspond à du bruit à supprimer.
    
    Args:
        line: Ligne de texte à vérifier 
    Returns:
        True si la ligne est du bruit, False sinon
    """
    line = line.strip()
    
    # Ligne vide
    if not line:
        return True
    
    # Vérification contre les patterns de bruit
    for pattern in NOISE_PATTERNS:
        if pattern.match(line):
            return True
    
    return False


def normalize_whitespace(text: str) -> str:
    """
    Normalise les espaces multiples et caractères spéciaux.
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte normalisé
    """
    # Remplacer les espaces multiples par un seul
    text = re.sub(r"[ \t]+", " ", text)
    
    # Normaliser les tirets et apostrophes
    text = text.replace("'", "'")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    
    # Supprimer les caractères de contrôle
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    
    return text.strip()


def repair_encoding(text: str) -> str:
    """
    Répare tous les problèmes d'encodage du texte.
    
    Applique dans l'ordre:
    1. Fix CID encoding (cid:XX) -> caractère ASCII (+29 offset)
    2. Fix Mojibake spécifique au Code du Numérique (͒ -> ', È -> é, etc.)
    3. Fix Mojibake UTF-8 générique (Ã© -> é)
    
    Args:
        text: Texte brut potentiellement corrompu
    Returns:
        Texte avec encodage réparé
    """
    # Décoder les CID
    text = fix_cid_encoding(text)
    
    # Réparer le Mojibake SPÉCIFIQUE au Code du Numérique
    text = fix_specific_mojibake(text)
    
    # Réparer le Mojibake UTF-8 générique restant
    text = fix_common_mojibake(text)
    
    return text


def clean_text(raw_pages: List[str]) -> str:
    """
    Nettoie ligne par ligne puis fusionne en un seul bloc de texte.
    
    Pipeline de nettoyage:
    1. Réparation encodage (CID + Mojibake) sur TOUT le texte fusionné
    2. Découpage en lignes
    3. Suppression des lignes de bruit
    4. Normalisation des espaces
    5. Re-fusion  
 
    Args:
        raw_pages: Liste des textes bruts par page 
    Returns:
        Texte complet nettoyé et fusionné
    """
    # Fusionner toutes les pages pour le repair global
    full_raw_text = "\n".join(page for page in raw_pages if page)
    
    # Réparer l'encodage avant tout autre traitement
    repaired_text = repair_encoding(full_raw_text)
    
    # Compter les CID réparés pour stats
    cid_count_before = len(CID_PATTERN.findall(full_raw_text))
    cid_count_after = len(CID_PATTERN.findall(repaired_text))
    cid_fixed = cid_count_before - cid_count_after
    
    clean_lines: List[str] = []
    
    stats = {
        "total_lines": 0,
        "removed_lines": 0,
        "pages_processed": len(raw_pages),
        "cid_fixed": cid_fixed,
    }
    
    # Nettoyer ligne par ligne
    for line in repaired_text.split("\n"):
        stats["total_lines"] += 1
        
        if is_noise_line(line):
            stats["removed_lines"] += 1
            continue
        
        # Normaliser et conserver la ligne
        cleaned_line = normalize_whitespace(line)
        if cleaned_line:
            clean_lines.append(cleaned_line)
    
    # Fusion en un seul bloc
    merged_text = "\n".join(clean_lines)
    
    # Statistiques de nettoyage
    logger.info("Nettoyage termine:")
    logger.info(f"   - Pages traitees: {stats['pages_processed']}")
    logger.info(f"   - Lignes analysees: {stats['total_lines']}")
    logger.info(f"   - Lignes supprimees (bruit): {stats['removed_lines']}")
    logger.info(f"   - CID repares: {stats['cid_fixed']}")
    logger.info(f"   - Reduction: {stats['removed_lines']/max(1, stats['total_lines'])*100:.1f}%")
    
    return merged_text


def detect_remaining_noise(text: str) -> List[str]:
    """
    Détecte du bruit potentiel qui aurait échappé au nettoyage.
    Utile pour affiner les patterns.
    
    Args:
        text: Texte nettoyé
    Returns:
        Liste des lignes suspectes
    """
    suspicious: List[str] = []
    
    for line in text.split("\n"):
        line = line.strip()
        
        # Lignes très courtes qui ne sont pas des articles
        if len(line) < 10 and not line.startswith("Article"):
            suspicious.append(line)
        
        # Lignes qui ressemblent à des en-têtes/pieds de page
        if re.match(r"^\d+/\d+$", line):  # Format 1/50
            suspicious.append(line)
        
        # CID non réparés (pour debug)
        if "(cid:" in line:
            suspicious.append(f"[CID NON RÉPARÉ] {line[:100]}")
    
    return suspicious


def detect_remaining_cid(text: str) -> int:
    """
    Compte les CID restants non réparés (pour diagnostic).
    
    Args:
        text: Texte après nettoyage   
    Returns:
        Nombre de CID non réparés
    """
    return len(CID_PATTERN.findall(text))

