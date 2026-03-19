from fastapi import APIRouter, Header, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import generate_response
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

    reply = await generate_response(
        message=request.message,
        history=request.history,
        user_role=request.user_role,
        context=request.context
    )
    return ChatResponse(reply=reply)
