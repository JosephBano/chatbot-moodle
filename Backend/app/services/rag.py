import chromadb
from app.config import settings

# ChromaDB usará embeddings por defecto (no requiere dependencias adicionales)
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection("moodle_docs")

def search_knowledge_base(query: str, n_results: int = 3) -> list[str]:
    """Busca los fragmentos más relevantes para la consulta del usuario."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []
