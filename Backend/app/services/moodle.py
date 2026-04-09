import re
import httpx
from typing import Optional
from app.config import settings


async def get_course_context(course_id: int) -> Optional[str]:
    """
    Obtiene el contenido del curso desde la API de Moodle y lo formatea
    como contexto para el LLM.
    Retorna None si no hay credenciales configuradas o si ocurre un error.
    """
    if not settings.MOODLE_URL or not settings.MOODLE_API_TOKEN:
        return None

    url = f"{settings.MOODLE_URL.rstrip('/')}/webservice/rest/server.php"
    params = {
        "wstoken":            settings.MOODLE_API_TOKEN,
        "wsfunction":         "core_course_get_contents",
        "moodlewsrestformat": "json",
        "courseid":           course_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            data = response.json()

        # Moodle devuelve un dict con "exception" si hay error
        if isinstance(data, dict) and "exception" in data:
            return None

        lines = []
        for section in data:
            section_name = section.get("name", "").strip()
            if section_name and section_name != "General":
                lines.append(f"\n### Sección: {section_name}")

            for module in section.get("modules", []):
                mod_name = module.get("name", "").strip()
                mod_type = module.get("modname", "")
                summary  = module.get("summary", "").strip()

                if not mod_name:
                    continue

                lines.append(f"- [{mod_type}] {mod_name}")

                if summary:
                    clean = re.sub(r"<[^>]+>", " ", summary)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    if clean:
                        lines.append(f"  → {clean[:400]}")

        if not lines:
            return None

        header = "Contenido actual del curso en Moodle:\n"
        return header + "\n".join(lines)

    except Exception:
        return None
