"""BÉNIN JURIS-IA - Module LLM"""

from .prompt_templates import get_rag_prompt
from .rag_chain import query_rag

__all__ = ["get_rag_prompt", "query_rag"]