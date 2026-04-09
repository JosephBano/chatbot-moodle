from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str
    API_TOKEN: str
    CHROMA_DB_PATH: str = "./chroma_db"

    # Control de acceso piloto — IDs de cursos de Moodle habilitados
    ALLOWED_COURSE_IDS: List[int] = []
    # Nombres de carreras habilitadas (deben coincidir con el campo career del plugin)
    ALLOWED_CAREERS: List[str] = []

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
