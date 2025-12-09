"""
BÉNIN JURIS-IA - RAG Chain
Pipeline RAG complet utilisant ChromaDB et OpenAI.
Adapté à la structure de données avec métadonnées aplaties.
"""
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.retrieval.indexer import load_vectorstore


# PROMPT SYSTÈME STRICT POUR L'ASSISTANT JURIDIQUE

SYSTEM_PROMPT = """Tu es un assistant juridique béninois spécialisé dans le Code du Numérique du Bénin (Loi N°2017-20 du 20 avril 2018).

RÈGLES STRICTES:
1. Tu réponds UNIQUEMENT en te basant sur le contexte fourni ci-dessous.
2. Si la réponse n'est pas dans le contexte, dis clairement: "Je n'ai pas trouvé d'information sur ce sujet dans le Code du Numérique."
3. Cite TOUJOURS les articles pertinents (ex: "Selon l'Article 45...").
4. Utilise un langage juridique précis mais accessible.
5. Structure tes réponses de manière claire avec des puces si nécessaire.

AVERTISSEMENT: Tes réponses sont à titre informatif uniquement et ne constituent pas un avis juridique professionnel."""


RAG_PROMPT_TEMPLATE = """CONTEXTE JURIDIQUE (Articles du Code du Numérique):
{context}

QUESTION DE L'UTILISATEUR:
{question}

RÉPONSE (basée uniquement sur le contexte ci-dessus):"""


# CONFIGURATION DU LLM ET EMBEDDINGS

def get_llm() -> ChatOpenAI:
    """
    Initialise le modèle de langage avec temperature=0 pour rigueur juridique.
    """
    return ChatOpenAI(
        model=settings.openai_llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0,  # 0 pour maximiser la précision juridique
    )


def get_embedding_model() -> OpenAIEmbeddings:
    """
    Initialise le modèle d'embedding (doit être le même que celui utilisé pour l'indexation).
    """
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,  # text-embedding-3-small
        openai_api_key=settings.openai_api_key,
    )


# RECHERCHE DANS CHROMADB

def search_vectorstore(
    query: str, 
    n_results: int = 5,
    filter_livre: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Recherche sémantique dans ChromaDB avec le bon modèle d'embedding.
    
    Args:
        query: Question de l'utilisateur
        n_results: Nombre de résultats à retourner
        filter_livre: Optionnel - filtrer par livre (ex: "LIVRE IV")
    Returns:
        Liste de documents avec contenu et métadonnées
    """
    collection = load_vectorstore()
    embedding_model = get_embedding_model()
    
    # Générer l'embedding de la query avec le même modèle
    query_embedding = embedding_model.embed_query(query)
    
    # Construire le filtre si spécifié
    where_filter = None
    if filter_livre:
        where_filter = {"livre": filter_livre}
    
    # Recherche dans ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    # Formater les résultats
    formatted_results = []
    
    if results and results.get("documents"):
        documents = results["documents"][0]
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
        distances = results["distances"][0] if results.get("distances") else [0] * len(documents)
        
        for doc, meta, distance in zip(documents, metadatas, distances):
            formatted_results.append({
                "content": doc,
                "metadata": meta,
                "distance": distance,
                "relevance_score": 1 - distance,  # Convertir distance en score
            })
    
    return formatted_results


def format_context(search_results: List[Dict[str, Any]]) -> str:
    """
    Formate les résultats de recherche en contexte pour le LLM.
    """
    context_parts = []
    
    for i, result in enumerate(search_results, 1):
        meta = result.get("metadata", {})
        article_num = meta.get("article_number", "?")
        hierarchy = meta.get("hierarchy_path", "")
        content = result.get("content", "")
        
        # Formater chaque source
        context_parts.append(
            f"[Source {i} - Article {article_num}]\n"
            f"Position: {hierarchy}\n"
            f"Contenu:\n{content}\n"
        )
    
    return "\n---\n".join(context_parts)


# CHAÎNE RAG PRINCIPALE

def get_rag_chain():
    """
    Crée et retourne une fonction RAG prête à l'emploi.
    
    Returns:
        Fonction callable(question, n_results) -> Dict
    """
    llm = get_llm()
    
    def rag_chain(
        question: str, 
        n_results: int = 5,
        filter_livre: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exécute la chaîne RAG complète.
        
        Args:
            question: Question juridique de l'utilisateur
            n_results: Nombre de sources à considérer
            filter_livre: Optionnel - filtrer par livre 
        Returns:
            Dict avec answer, sources, context_used
        """
        # Recherche sémantique
        search_results = search_vectorstore(
            query=question,
            n_results=n_results,
            filter_livre=filter_livre
        )
        
        # Formatage du contexte
        context = format_context(search_results)
        
        # Construction du prompt
        user_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=question
        )
        
        # Génération de la réponse
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        
        response = llm.invoke(messages)
        
        # Formater les sources pour l'affichage
        sources = []
        for r in search_results:
            meta = r.get("metadata", {})
            sources.append({
                "article_number": meta.get("article_number", 0),
                "article_id": meta.get("id", "Unknown"),
                "livre": meta.get("livre", ""),
                "titre": meta.get("titre", ""),
                "chapitre": meta.get("chapitre", ""),
                "hierarchy_path": meta.get("hierarchy_path", ""),
                "relevance_score": r.get("relevance_score", 0),
                "content_preview": r.get("content", "")[:300] + "...",
            })
        
        return {
            "question": question,
            "answer": response.content,
            "sources": sources,
            "context_used": context,
            "n_sources": len(sources),
        }
    
    return rag_chain


def query_rag(
    question: str, 
    n_results: int = 5,
    filter_livre: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Point d'entrée simple pour interroger le RAG.
    
    Args:
        question: Question juridique
        n_results: Nombre de sources à considérer
        filter_livre: Optionnel - filtrer par livre spécifique
        verbose: Afficher les détails de recherche   
    Returns:
        Dictionnaire avec réponse et sources
    """
    chain = get_rag_chain()
    result = chain(question, n_results=n_results, filter_livre=filter_livre)
    
    if verbose:
        print(f"\n Sources utilisées ({len(result['sources'])})")
        for source in result["sources"]:
            print(f"      Article {source['article_number']} - {source['hierarchy_path']}")
            print(f"      Pertinence: {source['relevance_score']:.2%}")
    
    return result
