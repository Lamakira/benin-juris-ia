"""
BÉNIN JURIS-IA - Interface Streamlit
Assistant juridique RAG pour le Code du Numérique du Bénin.
"""
import streamlit as st
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.rag_chain import query_rag


# =============================================================================
# CONFIGURATION DE LA PAGE
# =============================================================================

st.set_page_config(
    page_title="Bénin Juris-IA",
    page_icon="🇧🇯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a5f2a;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .disclaimer {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 1.5rem;
        font-size: 0.9rem;
        color: #000000;
    }
    .source-card {
        background-color: #f8f9fa;
        border-left: 4px solid #1a5f2a;
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
        color: #000000;
    }
    .source-title {
        font-weight: bold;
        color: #1a5f2a;
        margin-bottom: 4px;
    }
    .source-path {
        font-size: 0.85rem;
        color: #333333;
        margin-bottom: 8px;
    }
    .source-preview {
        font-size: 0.9rem;
        color: #000000;
        font-style: italic;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: #000000;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        color: #000000;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #1a5f2a;
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# INITIALISATION DE LA SESSION
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "sources_history" not in st.session_state:
    st.session_state.sources_history = []


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/0/0a/Flag_of_Benin.svg", width=100)
    st.markdown("## ⚙️ Paramètres")
    
    n_sources = st.slider(
        "Nombre de sources à consulter",
        min_value=3,
        max_value=10,
        value=5,
        help="Plus de sources = réponse plus complète mais plus lente"
    )
    
    # Filtre par Livre
    livre_options = [
        "Tous les Livres",
        "LIVRE I",
        "LIVRE II", 
        "LIVRE III",
        "LIVRE IV",
        "LIVRE V",
        "LIVRE VI",
        "LIVRE VII"
    ]
    selected_livre = st.selectbox(
        "Filtrer par Livre",
        options=livre_options,
        index=0,
        help="Restreindre la recherche à un livre spécifique"
    )
    
    filter_livre = None if selected_livre == "Tous les Livres" else selected_livre
    
    st.markdown("---")
    st.markdown("### 📖 À propos")
    st.markdown("""
    Cet assistant utilise le **Code du Numérique du Bénin** 
    (Loi N°2017-20 du 20 avril 2018) pour répondre à vos questions.
    
    **Livres couverts:**
    - 📕 Livre I: Dispositions Générales
    - 📘 Livre II: Communications Électroniques
    - 📗 Livre III: Transactions Électroniques
    - 📙 Livre IV: Protection des Données
    - 📓 Livre V: Cybersécurité
    - 📔 Livre VI: Cybercriminalité
    - 📒 Livre VII: Dispositions Finales
    """)
    
    if st.button("🗑️ Effacer l'historique"):
        st.session_state.messages = []
        st.session_state.sources_history = []
        st.rerun()


# =============================================================================
# CONTENU PRINCIPAL
# =============================================================================

# Header
st.markdown('<div class="main-header">🇧🇯 Bénin Juris-IA</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Assistant juridique intelligent pour le Code du Numérique</div>', unsafe_allow_html=True)

# Disclaimer
st.markdown("""
<div class="disclaimer">
    ⚠️ <strong>Avertissement:</strong> Cet assistant est fourni à titre informatif uniquement. 
    Les réponses ne constituent pas un avis juridique professionnel. 
    Pour toute question juridique sérieuse, consultez un avocat qualifié.
</div>
""", unsafe_allow_html=True)

# Afficher l'historique des messages
for i, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 Vous:</strong><br>{message["content"]}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Juris-IA:</strong><br>{message["content"]}
        </div>
        """, unsafe_allow_html=True)
        
        # Afficher les sources si disponibles
        if i < len(st.session_state.sources_history) and st.session_state.sources_history[i]:
            sources = st.session_state.sources_history[i]
            with st.expander(f"📚 Voir les {len(sources)} sources utilisées"):
                for source in sources:
                    article_num = source.get("article_number", "?")
                    livre = source.get("livre", "")
                    titre = source.get("titre", "")
                    hierarchy = source.get("hierarchy_path", "Non classifié")
                    preview = source.get("content_preview", "")
                    relevance = source.get("relevance_score", 0)
                    
                    # Construire le fil d'ariane
                    breadcrumb_parts = [livre]
                    if titre:
                        breadcrumb_parts.append(titre)
                    breadcrumb = " > ".join(filter(None, breadcrumb_parts))
                    
                    st.markdown(f"""
                    <div class="source-card">
                        <div class="source-title">📄 Article {article_num}</div>
                        <div class="source-path">📍 {breadcrumb or hierarchy}</div>
                        <div class="source-preview">"{preview[:200]}..."</div>
                        <small>Pertinence: {relevance:.0%}</small>
                    </div>
                    """, unsafe_allow_html=True)


# =============================================================================
# INPUT UTILISATEUR
# =============================================================================

# Zone de saisie
user_question = st.chat_input("Posez votre question sur le Code du Numérique...")

if user_question:
    # Ajouter la question à l'historique
    st.session_state.messages.append({"role": "user", "content": user_question})
    st.session_state.sources_history.append(None)  # Placeholder
    
    # Afficher la question
    st.markdown(f"""
    <div class="chat-message user-message">
        <strong>👤 Vous:</strong><br>{user_question}
    </div>
    """, unsafe_allow_html=True)
    
    # Indicateur de chargement
    with st.spinner("🔍 Recherche dans le Code du Numérique..."):
        try:
            # Appeler le RAG
            result = query_rag(
                question=user_question,
                n_results=n_sources,
                filter_livre=filter_livre,
                verbose=False
            )
            
            answer = result["answer"]
            sources = result["sources"]
            
            # Ajouter la réponse à l'historique
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.session_state.sources_history[-1] = sources
            
            # Afficher la réponse
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Juris-IA:</strong><br>{answer}
            </div>
            """, unsafe_allow_html=True)
            
            # Afficher les sources
            if sources:
                with st.expander(f"📚 Voir les {len(sources)} sources utilisées"):
                    for source in sources:
                        article_num = source.get("article_number", "?")
                        livre = source.get("livre", "")
                        titre = source.get("titre", "")
                        hierarchy = source.get("hierarchy_path", "Non classifié")
                        preview = source.get("content_preview", "")
                        relevance = source.get("relevance_score", 0)
                        
                        # Construire le fil d'ariane
                        breadcrumb_parts = [livre]
                        if titre:
                            breadcrumb_parts.append(titre)
                        breadcrumb = " > ".join(filter(None, breadcrumb_parts))
                        
                        st.markdown(f"""
                        <div class="source-card">
                            <div class="source-title">📄 Article {article_num}</div>
                            <div class="source-path">📍 {breadcrumb or hierarchy}</div>
                            <div class="source-preview">"{preview[:200]}..."</div>
                            <small>Pertinence: {relevance:.0%}</small>
                        </div>
                        """, unsafe_allow_html=True)
        
        except Exception as e:
            error_msg = f"Une erreur s'est produite: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": f"❌ {error_msg}"})


# =============================================================================
# EXEMPLES DE QUESTIONS
# =============================================================================

if not st.session_state.messages:
    st.markdown("### 💡 Exemples de questions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        - Quelles sont les sanctions prévues pour la cybercriminalité ?
        - Comment sont protégées les données personnelles au Bénin ?
        - Quelles sont les obligations des fournisseurs de services en ligne ?
        """)
    
    with col2:
        st.markdown("""
        - Qu'est-ce que la signature électronique selon le Code ?
        - Quels sont les droits des consommateurs en matière de commerce électronique ?
        - Que dit l'Article 45 sur le consentement ?
        """)


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.85rem;">
    🇧🇯 Bénin Juris-IA | Basé sur la Loi N°2017-20 du 20 avril 2018<br>
    Développé avec ❤️ pour la diffusion du droit numérique béninois
</div>
""", unsafe_allow_html=True)
