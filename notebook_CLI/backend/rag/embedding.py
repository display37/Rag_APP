from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings

_embeddings = None

def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
    return _embeddings


class _LazyEmbeddings(Embeddings):
    """Proxy that loads the HuggingFace model on first use.
    Inherits from langchain Embeddings so Qdrant vectorstore
    recognizes it as a proper embeddings object (not a callable).
    """

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return _get_embeddings().embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return _get_embeddings().embed_query(text)

    def __getattr__(self, name):
        return getattr(_get_embeddings(), name)


embeddings = _LazyEmbeddings()