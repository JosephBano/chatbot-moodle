from fastapi import APIRouter, Header, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import generate_response
from app.services.access import is_access_allowed
from app.config import settings

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_token: str = Header(...)
):
    # Validar token
    if x_api_token != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Validar acceso por carrera y materia (piloto controlado)
    if not is_access_allowed(career=request.career, course_id=request.course_id):
        return ChatResponse(
            reply="El asistente aún no está disponible para esta materia o carrera. "
                  "Consulta con tu coordinador académico sobre el programa piloto."
        )

    reply = await generate_response(
        message=request.message,
        history=request.history,
        user_role=request.user_role,
        context=request.context
    )
    return ChatResponse(reply=reply)
