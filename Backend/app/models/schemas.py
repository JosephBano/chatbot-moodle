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

class ChatResponse(BaseModel):
    reply: str
