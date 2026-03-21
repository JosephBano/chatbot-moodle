from openai import AsyncOpenAI
from app.services.rag import search_knowledge_base
from app.config import settings

# DeepSeek usa una API compatible con OpenAI
client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

SYSTEM_PROMPT = """Eres un asistente académico virtual del Instituto Tecnológico Superior.
Tu función es ayudar a estudiantes y docentes a comprender los contenidos de sus materias
y el uso de la plataforma Moodle.

REGLAS ESTRICTAS DE COMPORTAMIENTO:
- Explica conceptos, genera ejemplos ilustrativos y aclara ejercicios ya resueltos del material del curso.
- NUNCA resuelvas tareas, trabajos, exámenes ni ejercicios nuevos presentados por el estudiante.
- NUNCA generes código, textos o respuestas listas para copiar y entregar.
- Si el estudiante pide que "hagas" algo para entregar, declina y ofrece explicar el concepto relacionado.
- Responde siempre en español, de forma clara y apropiada para el nivel universitario.
- Si no encuentras la respuesta en el material del curso, indícalo y sugiere consultar al docente.

Rol del usuario: {user_role}
Página actual en Moodle: {context}

Material relevante del curso:
{rag_context}
"""

async def generate_response(message: str, history: list, user_role: str, context: str) -> str:
    # Buscar contexto en la base de conocimiento
    rag_docs = search_knowledge_base(message)
    rag_context = "\n".join(rag_docs) if rag_docs else "No se encontró material específico del curso."

    system = SYSTEM_PROMPT.format(
        user_role=user_role,
        context=context,
        rag_context=rag_context
    )

    messages = [{"role": "system", "content": system}]
    messages += [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        model="deepseek-chat",   # deepseek-chat = DeepSeek V3.2
        max_tokens=1024,
        messages=messages,
        temperature=0.7,
    )

    return response.choices[0].message.content
