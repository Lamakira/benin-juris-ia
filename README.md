# BÉNIN JURIS-IA

Assistant juridique conversationnel basé sur le Code du Numérique du Bénin (Loi N°2017-20).

## Architecture

Ce projet utilise une approche **Structure-Aware Chunking** où chaque article de loi est traité comme une unité atomique.

## Installation

```bash
# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Configurer variables d'environnement
cp .env.example .env
# Éditer .env avec votre clé OpenAI
```

## Utilisation

### 1. Ingestion du document

Placer le fichier PDF dans `data/raw/CODE-DU-NUMERIQUE.pdf` puis :

```bash
python scripts/ingest.py
```

### 2. Lancer l'application

```bash
streamlit run app/streamlit_app.py
```

## Structure du Projet

```
├── data/
│   ├── raw/              # PDF source
│   ├── processed/        # Articles JSON nettoyés
│   └── vectorstore/      # ChromaDB
├── src/
│   ├── ingestion/        # Pipeline ETL
│   ├── retrieval/        # Recherche vectorielle
│   └── llm/              # Intégration LLM
├── app/                  # Interface Streamlit
├── scripts/              # Scripts utilitaires
└── tests/                # Tests unitaires
```

## Licence

Projet ECP 2025
