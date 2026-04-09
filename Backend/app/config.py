from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str
    API_TOKEN: str
    CHROMA_DB_PATH: str = "./chroma_db"

    # Control de acceso piloto — IDs de cursos de Moodle habilitados
    ALLOWED_COURSE_IDS: List[int] = []
    # Nombres de carreras habilitadas (deben coincidir con el campo career del plugin)
    ALLOWED_CAREERS: List[str] = []

    # Moodle API (opcional — para obtener contenido del curso automáticamente)
    MOODLE_URL: Optional[str] = None
    MOODLE_API_TOKEN: Optional[str] = None
    # URL interna para descargas de archivos desde dentro del contenedor Docker
    # Si Moodle corre en el mismo host, usar http://172.17.0.1:8080
    MOODLE_INTERNAL_URL: Optional[str] = None

    # Intervalo de re-indexación automática en horas (0 = desactivado)
    INDEX_INTERVAL_HOURS: int = 6

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
