from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from rag.embedding import embeddings

COLLECTION_NAME = "rag_collection"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 outputs 384-dim vectors

# Lazy initialization — connect on first use, not on import
_client = None
_vectorstore = None
_retriever = None


def _init_qdrant():
    """Connect to Qdrant and create collection if it doesn't exist."""
    global _client, _vectorstore, _retriever
    if _client is None:
        _client = QdrantClient(host="localhost", port=6333)

        # Auto-create collection if missing
        existing = [c.name for c in _client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            _client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
            print(f"[Qdrant] Created collection '{COLLECTION_NAME}'")

        _vectorstore = Qdrant(
            client=_client,
            collection_name=COLLECTION_NAME,
            embeddings=embeddings
        )
        _retriever = _vectorstore.as_retriever(search_kwargs={"k": 12})


class _LazyRetriever:
    """Proxy that initializes Qdrant on first method call."""
    def invoke(self, *args, **kwargs):
        _init_qdrant()
        try:
            return _retriever.invoke(*args, **kwargs)
        except Exception as e:
            print(f"[Qdrant] Retriever error (no docs yet?): {e}")
            return []

    def __getattr__(self, name):
        _init_qdrant()
        return getattr(_retriever, name)


class _LazyVectorstore:
    """Proxy that initializes Qdrant on first method call."""
    def add_documents(self, *args, **kwargs):
        _init_qdrant()
        return _vectorstore.add_documents(*args, **kwargs)

    def __getattr__(self, name):
        _init_qdrant()
        return getattr(_vectorstore, name)


vectorstore = _LazyVectorstore()
retriever = _LazyRetriever()