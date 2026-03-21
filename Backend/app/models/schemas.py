from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str       # "user" o "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    user_role: Optional[str] = "student"   # rol en Moodle
    context: Optional[str] = ""            # página actual en Moodle
    course_id: Optional[int] = None        # ID del curso activo en Moodle
    career: Optional[str] = ""             # carrera del estudiante

class ChatResponse(BaseModel):
    reply: str

class AccessDeniedResponse(BaseModel):
    reply: str = "El asistente no está disponible para esta materia o carrera en este momento."
