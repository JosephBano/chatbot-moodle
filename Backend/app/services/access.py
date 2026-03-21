from app.config import settings
from typing import Optional

def is_access_allowed(career: Optional[str], course_id: Optional[int]) -> bool:
    """
    Retorna True si el usuario tiene acceso al chatbot según el piloto.
    Lógica AND: la carrera debe estar habilitada Y el curso también.
    Si ambas listas están vacías, se deniega todo acceso por defecto.
    """
    allowed_careers    = settings.ALLOWED_CAREERS
    allowed_course_ids = settings.ALLOWED_COURSE_IDS

    # Si no hay nada configurado, denegar por defecto (seguridad)
    if not allowed_careers and not allowed_course_ids:
        return False

    career_ok = (not allowed_careers) or (career in allowed_careers)
    course_ok  = (not allowed_course_ids) or (course_id in allowed_course_ids)

    return career_ok and course_ok
