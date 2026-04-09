from fastapi import APIRouter, Header, HTTPException
from app.services.indexer import index_course
from app.config import settings

router = APIRouter()


@router.post("/index/{course_id}")
async def index_course_endpoint(
    course_id: int,
    x_api_token: str = Header(...)
):
    """
    Indexa el contenido de un curso de Moodle en ChromaDB.
    Requiere el mismo API_TOKEN del backend.
    """
    if x_api_token != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await index_course(course_id)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result
