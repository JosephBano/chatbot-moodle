# Chatbot Moodle

> Asistente académico virtual con IA para la plataforma Moodle del Instituto Tecnológico Superior.  
> Responde preguntas sobre el contenido específico de cada curso usando RAG (ChromaDB + DeepSeek V3.2).

---

## Arquitectura

```
[Usuario en Moodle]
       │
       ▼
[Plugin PHP block_chatbot]  ←── JS Widget (chat.js)
       │ fetch /api/chat
       ▼
[Backend FastAPI]
       ├── Control de acceso (curso + carrera)
       ├── RAG: ChromaDB (búsqueda semántica por curso)
       └── DeepSeek V3.2 (generación de respuesta)

[Auto-indexación periódica]
       └── Moodle Web Services API → pdfplumber → ChromaDB
```

- Moodle y Backend corren en Docker en el mismo servidor
- Comunicación cliente↔backend vía IP Tailscale
- Indexación automática cada N horas (configurable)

---

## Estructura del proyecto

```
chatbot-moodle/
├── Backend/
│   ├── app/
│   │   ├── routes/
│   │   │   ├── chat.py          # POST /api/chat
│   │   │   └── admin.py         # POST /api/admin/index/{course_id}
│   │   ├── services/
│   │   │   ├── llm.py           # Integración DeepSeek + construcción de prompt
│   │   │   ├── rag.py           # Búsqueda semántica en ChromaDB
│   │   │   ├── indexer.py       # Indexación de cursos desde Moodle API
│   │   │   └── access.py        # Control de acceso por curso y carrera
│   │   ├── models/schemas.py    # Esquemas Pydantic
│   │   ├── config.py            # Variables de entorno
│   │   └── main.py              # App FastAPI + auto-indexación periódica
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── moodle/
│   └── blocks/chatbot/
│       ├── block_chatbot.php    # Bloque Moodle principal
│       ├── chat.js              # Widget JS flotante
│       ├── settings.php         # Configuración del plugin
│       ├── version.php
│       ├── db/access.php        # Capacidades del bloque
│       └── lang/en/             # Traducciones
│
└── DEPLOY.md                    # Guía completa de despliegue
```

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| LLM | DeepSeek V3.2 (API compatible con OpenAI) |
| RAG | ChromaDB + embeddings all-MiniLM-L6-v2 |
| Backend | FastAPI (Python 3.11) |
| Plugin | PHP 8.1 + JavaScript (ES5, sin AMD) |
| Plataforma | Moodle 4.2 |
| Infraestructura | Docker + Tailscale |
| Extracción PDF | pdfplumber |

---

## Configuración rápida

### Variables de entorno del backend (`.env`)

```env
DEEPSEEK_API_KEY=sk-...
API_TOKEN=token_hex_generado

CHROMA_DB_PATH=./chroma_db

# Cursos habilitados (IDs de Moodle)
ALLOWED_COURSE_IDS=[531, 630]
# Carreras habilitadas (vacío = todas)
ALLOWED_CAREERS=[]

# Moodle Web Services (para indexación)
MOODLE_URL=http://[IP]:8080
MOODLE_API_TOKEN=token_moodle
# URL interna Docker para descargar archivos
MOODLE_INTERNAL_URL=http://172.17.0.1:8080

# Auto-indexación periódica (0 = desactivado)
INDEX_INTERVAL_HOURS=6
```

### Levantar el backend

```bash
cd Backend/
docker compose up -d --build
```

### Indexar un curso manualmente

```bash
curl -X POST http://[IP]:8000/api/admin/index/[COURSE_ID] \
  -H "x-api-token: TU_API_TOKEN"
```

Respuesta esperada:
```json
{
  "course_id": 531,
  "modules_indexed": 7,
  "files_indexed": 2,
  "chunks_total": 45
}
```

---

## Flujo de indexación

1. El endpoint (o el scheduler automático) llama a `core_course_get_contents` en la API de Moodle
2. Se extraen nombres, descripciones y archivos de cada módulo
3. Los PDFs se descargan vía `pluginfile.php` y se procesan con pdfplumber
4. El texto se divide en chunks de 600 caracteres con solapamiento de 100
5. Se almacena en ChromaDB con metadatos `{course_id, module_id, type}`
6. En cada consulta del chat, se buscan los 5 fragmentos más relevantes filtrados por `course_id`

---

## Despliegue completo

Ver **[DEPLOY.md](./DEPLOY.md)** para instrucciones paso a paso incluyendo:
- Configuración de Moodle Web Services
- Instalación del plugin block_chatbot
- Control de acceso por piloto
- Auto-indexación periódica (Fase 2)
- Notas para producción (HTTPS, plugins rotos, persistencia ChromaDB)

---

*Desarrollado para el Instituto Tecnológico Superior — Stage validado: Moodle 4.2.10 + FastAPI + Docker + Tailscale*
