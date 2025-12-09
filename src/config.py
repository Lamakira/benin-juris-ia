"""
BÉNIN JURIS-IA - Configuration centralisée
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    # Paths
    project_root: Path = Path(__file__).parent.parent
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    openai_llm_model: str = Field(default="gpt-4o-mini", env="OPENAI_LLM_MODEL")
    
    # ChromaDB
    chroma_persist_directory: str = Field(default="data/vectorstore", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="benin_code_numerique", env="CHROMA_COLLECTION_NAME")
    
    # Ingestion
    pdf_source_path: str = Field(default="data/raw/CODE-DU-NUMERIQUE.pdf", env="PDF_SOURCE_PATH")
    processed_output_path: str = Field(default="data/processed/articles.json", env="PROCESSED_OUTPUT_PATH")
    
    # Application
    app_title: str = Field(default="BÉNIN JURIS-IA", env="APP_TITLE")
    app_description: str = Field(
        default="Assistant juridique basé sur le Code du Numérique du Bénin",
        env="APP_DESCRIPTION"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def pdf_path(self) -> Path:
        return self.project_root / self.pdf_source_path
    
    @property
    def processed_path(self) -> Path:
        return self.project_root / self.processed_output_path
    
    @property
    def vectorstore_path(self) -> Path:
        return self.project_root / self.chroma_persist_directory


# Singleton
settings = Settings()
