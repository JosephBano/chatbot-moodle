import chromadb
from typing import Optional
from app.config import settings

chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection("moodle_docs")


def search_knowledge_base(query: str, course_id: Optional[int] = None, n_results: int = 5) -> list[str]:
    """
    Busca fragmentos relevantes para la consulta.
    Si se pasa course_id, filtra solo por ese curso.
    Si no hay resultados del curso, hace búsqueda general como fallback.
    """
    try:
        # Búsqueda filtrada por curso
        if course_id:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"course_id": course_id}
            )
            docs = results["documents"][0] if results["documents"] else []
            if docs:
                return docs

        # Fallback: búsqueda general (documentos manuales indexados)
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results["documents"][0] if results["documents"] else []

    except Exception:
        return []
