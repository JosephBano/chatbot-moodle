import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.chat import router as chat_router
from app.routes.admin import router as admin_router
from app.services.indexer import index_course
from app.config import settings

logger = logging.getLogger("indexer.scheduler")


async def _auto_index_loop():
    """Re-indexa todos los cursos habilitados cada INDEX_INTERVAL_HOURS horas."""
    interval_seconds = settings.INDEX_INTERVAL_HOURS * 3600
    # Espera inicial para no bloquear el arranque
    await asyncio.sleep(60)
    while True:
        if settings.MOODLE_URL and settings.MOODLE_API_TOKEN and settings.ALLOWED_COURSE_IDS:
            logger.info(
                "Auto-indexación iniciada para cursos: %s",
                settings.ALLOWED_COURSE_IDS,
            )
            for course_id in settings.ALLOWED_COURSE_IDS:
                try:
                    result = await index_course(course_id)
                    logger.info("Curso %s indexado: %s", course_id, result)
                except Exception as e:
                    logger.error("Error indexando curso %s: %s", course_id, e)
        else:
            logger.debug(
                "Auto-indexación omitida: MOODLE_URL, MOODLE_API_TOKEN o "
                "ALLOWED_COURSE_IDS no configurados."
            )
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.INDEX_INTERVAL_HOURS > 0:
        task = asyncio.create_task(_auto_index_loop())
        logger.info(
            "Auto-indexación activada cada %s horas.",
            settings.INDEX_INTERVAL_HOURS,
        )
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="chatbot-moodle API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir al dominio de Moodle en producción
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
