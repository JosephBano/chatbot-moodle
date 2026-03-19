from openai import OpenAI
from app.services.rag import search_knowledge_base
from app.config import settings

# DeepSeek es compatible con la API de OpenAI
client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = """Eres un asistente virtual del Instituto Tecnológico Superior, 
especializado en ayudar a estudiantes y docentes con el uso de la plataforma Moodle.

Responde siempre en español, de forma clara y concisa.
Si no conoces la respuesta con certeza, indica que el usuario puede contactar 
al soporte técnico del instituto.
No respondas preguntas fuera del ámbito del uso de Moodle o la plataforma académica.

Contexto del usuario: {user_role}
Página actual en Moodle: {context}

Información relevante de la documentación del instituto:
{rag_context}
"""

async def generate_response(message: str, history: list, user_role: str, context: str) -> str:
    # Buscar contexto en la base de conocimiento
    rag_docs = search_knowledge_base(message)
    rag_context = "\n".join(rag_docs) if rag_docs else "No se encontró documentación específica."

    # Construir system prompt con contexto
    system = SYSTEM_PROMPT.format(
        user_role=user_role,
        context=context,
        rag_context=rag_context
    )

    # Construir historial de mensajes para Chat Completion
    messages = [{"role": "system", "content": system}]
    for m in history:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=1024,
        messages=messages
    )

    return response.choices[0].message.content
