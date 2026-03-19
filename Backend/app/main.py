from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.chat import router as chat_router

app = FastAPI(title="chatbot-moodle API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir al dominio de Moodle en producción
    allow_methods=["POST"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
