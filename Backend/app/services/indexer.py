import re
import io
import httpx
import pdfplumber
from typing import Optional
from app.config import settings
from app.services.rag import collection


def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Divide texto en fragmentos con solapamiento."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 20]


def _clean_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


async def _download_file(url: str, token: str) -> Optional[bytes]:
    """Descarga un archivo desde Moodle usando el token."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params={"token": token})
            if response.status_code == 200:
                return response.content
    except Exception:
        pass
    return None


def _extract_pdf_text(content: bytes) -> str:
    """Extrae texto de un PDF en memoria."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n".join(pages)
    except Exception:
        return ""


async def index_course(course_id: int) -> dict:
    """
    Indexa el contenido completo de un curso en ChromaDB.
    Incluye texto de secciones, actividades y PDFs.
    Retorna un resumen del proceso.
    """
    if not settings.MOODLE_URL or not settings.MOODLE_API_TOKEN:
        return {"error": "MOODLE_URL o MOODLE_API_TOKEN no configurados"}

    url = f"{settings.MOODLE_URL.rstrip('/')}/webservice/rest/server.php"
    params = {
        "wstoken":            settings.MOODLE_API_TOKEN,
        "wsfunction":         "core_course_get_contents",
        "moodlewsrestformat": "json",
        "courseid":           course_id,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            data = response.json()
    except Exception as e:
        return {"error": f"No se pudo conectar a Moodle: {e}"}

    if isinstance(data, dict) and "exception" in data:
        return {"error": data.get("message", "Error de Moodle API")}

    # Eliminar documentos anteriores de este curso
    try:
        existing = collection.get(where={"course_id": course_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    docs, metas, ids = [], [], []
    indexed_files = 0
    indexed_modules = 0

    for section in data:
        section_name = _clean_html(section.get("name", "") or "")

        for module in section.get("modules", []):
            mod_id   = module.get("id", 0)
            mod_name = module.get("name", "").strip()
            mod_type = module.get("modname", "")
            summary  = _clean_html(module.get("summary", "") or "")

            # Texto descriptivo del módulo
            text_parts = []
            if section_name:
                text_parts.append(f"Sección: {section_name}")
            if mod_name:
                text_parts.append(f"Actividad: {mod_name} (tipo: {mod_type})")
            if summary:
                text_parts.append(f"Descripción: {summary}")

            if text_parts:
                full_text = "\n".join(text_parts)
                for i, chunk in enumerate(_chunk_text(full_text)):
                    docs.append(chunk)
                    metas.append({"course_id": course_id, "module_id": mod_id,
                                  "module_name": mod_name, "type": mod_type})
                    ids.append(f"course_{course_id}_mod_{mod_id}_chunk_{i}")
                indexed_modules += 1

            # Archivos adjuntos (PDFs, etc.)
            for content_item in module.get("contents", []):
                if content_item.get("type") != "file":
                    continue
                filename = content_item.get("filename", "")
                file_url = content_item.get("fileurl", "")
                mimetype = content_item.get("mimetype", "")
                if not file_url:
                    continue

                is_pdf = filename.lower().endswith(".pdf") or "pdf" in mimetype.lower()
                is_txt = filename.lower().endswith(".txt") or mimetype.lower() == "text/plain"

                if is_pdf:
                    file_bytes = await _download_file(file_url, settings.MOODLE_API_TOKEN)
                    if file_bytes:
                        pdf_text = _extract_pdf_text(file_bytes)
                        if pdf_text:
                            for i, chunk in enumerate(_chunk_text(pdf_text)):
                                docs.append(chunk)
                                metas.append({"course_id": course_id, "module_id": mod_id,
                                              "module_name": filename, "type": "pdf"})
                                ids.append(f"course_{course_id}_mod_{mod_id}_pdf_{i}")
                            indexed_files += 1

                elif is_txt:
                    file_bytes = await _download_file(file_url, settings.MOODLE_API_TOKEN)
                    if file_bytes:
                        txt = file_bytes.decode("utf-8", errors="ignore")
                        for i, chunk in enumerate(_chunk_text(txt)):
                            docs.append(chunk)
                            metas.append({"course_id": course_id, "module_id": mod_id,
                                          "module_name": filename, "type": "txt"})
                            ids.append(f"course_{course_id}_mod_{mod_id}_txt_{i}")
                        indexed_files += 1

    if docs:
        # Insertar en lotes de 100
        for i in range(0, len(docs), 100):
            collection.upsert(
                documents=docs[i:i+100],
                metadatas=metas[i:i+100],
                ids=ids[i:i+100]
            )

    return {
        "course_id":       course_id,
        "modules_indexed": indexed_modules,
        "files_indexed":   indexed_files,
        "chunks_total":    len(docs),
    }
