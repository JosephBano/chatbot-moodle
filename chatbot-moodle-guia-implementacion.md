# Guía de Implementación — chatbot-moodle

> Documento técnico para el equipo de desarrollo.  
> Versión: 1.0 | Fecha: 19/03/2026 | Área: Gestión Académica

---

## Índice

1. [Resumen de la arquitectura](#1-resumen-de-la-arquitectura)
2. [Requisitos previos](#2-requisitos-previos)
3. [Backend — FastAPI + IA](#3-backend--fastapi--ia)
4. [Configuración del LLM y base de conocimiento](#4-configuración-del-llm-y-base-de-conocimiento)
5. [Plugin de Moodle (Frontend)](#5-plugin-de-moodle-frontend)
6. [Configuración en Moodle — cuentas y permisos](#6-configuración-en-moodle--cuentas-y-permisos)
7. [Conexión Plugin ↔ Backend](#7-conexión-plugin--backend)
8. [Deployment](#8-deployment)
9. [Variables de entorno de referencia](#9-variables-de-entorno-de-referencia)

---

## 1. Resumen de la arquitectura

```
[Usuario en Moodle]
       │
       ▼
[Plugin PHP (block_chatbot)]  ←→  [Moodle Web Services API]
       │
       │  POST /chat  (token auth)
       ▼
[Backend FastAPI (Python)]
       │
       ├──► [LLM — DeepSeek API]
       │
       └──► [ChromaDB — Base vectorial RAG]
```

El plugin de Moodle es un cliente liviano. Toda la lógica de IA vive en el backend externo.

---

## 2. Requisitos previos

### Servidor del backend
- Ubuntu 22.04 LTS (recomendado) o compatible
- Python 3.11+
- Docker y Docker Compose v2+
- 2 GB RAM mínimo (4 GB recomendado)
- Acceso a internet para llamar a la API de DeepSeek

### Servidor de Moodle
- Moodle 3.9 o superior
- PHP 7.4+ (8.x recomendado)
- Acceso de administrador a la instancia
- Web Services habilitados (se configura en la sección 6)

### Cuentas y claves necesarias (solicitar antes de empezar)
| Recurso | Para qué sirve | Dónde obtener |
|---|---|---|
| API Key de Deepseek | Llamar al LLM Deepseek | chat-deepseek.com |
| Cuenta admin de Moodle | Instalar plugin y configurar Web Services | Administrador del instituto |
| Acceso SSH al servidor | Desplegar el backend | Sysadmin del instituto |
| Token de servicio Moodle | Autenticar llamadas a la API de Moodle | Se genera en Moodle (sección 6) |

---

## 3. Backend — FastAPI + IA

### 3.1 Estructura del proyecto

```
chatbot-backend/
├── app/
│   ├── main.py              # Entrada de FastAPI
│   ├── routes/
│   │   └── chat.py          # Endpoint POST /chat
│   ├── services/
│   │   ├── llm.py           # Lógica de llamada a DeepSeek
│   │   └── rag.py           # Consulta a ChromaDB
│   ├── models/
│   │   └── schemas.py       # Modelos Pydantic
│   └── config.py            # Variables de entorno
├── knowledge/
│   └── docs/                # Aquí van los PDFs y TXTs de manuales
├── scripts/
│   └── index_docs.py        # Script para indexar documentos
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### 3.2 Dependencias (requirements.txt)

```txt
fastapi==0.111.0
uvicorn==0.29.0
openai==1.12.0
langchain==0.1.20
langchain-community==0.0.38
chromadb==0.5.0
python-dotenv==1.0.1
pydantic==2.7.0
httpx==0.27.0
```

### 3.3 Archivo principal (app/main.py)

```python
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
```

### 3.4 Esquemas (app/models/schemas.py)

```python
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
```

### 3.5 Endpoint de chat (app/routes/chat.py)

```python
from fastapi import APIRouter, Header, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import generate_response
from app.config import settings

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_token: str = Header(...)
):
    # Validar token
    if x_api_token != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    reply = await generate_response(
        message=request.message,
        history=request.history,
        user_role=request.user_role,
        context=request.context
    )
    return ChatResponse(reply=reply)
```

### 3.6 Servicio LLM (app/services/llm.py)

```python
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
```

### 3.7 Configuración (app/config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str
    API_TOKEN: str
    CHROMA_DB_PATH: str = "./chroma_db"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 4. Configuración del LLM y base de conocimiento

### 4.1 Cómo funciona el RAG

Cuando un usuario hace una pregunta, el sistema:
1. Convierte la pregunta en un vector numérico (embedding).
2. Busca en ChromaDB los fragmentos de documentación más similares.
3. Inyecta esos fragmentos en el prompt del sistema antes de llamar a DeepSeek.
4. DeepSeek responde usando tanto su conocimiento como la documentación del instituto.

### 4.2 Servicio RAG (app/services/rag.py)

```python
import chromadb
from app.config import settings

# ChromaDB usará embeddings por defecto (no requiere dependencias adicionales)
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection("moodle_docs")

def search_knowledge_base(query: str, n_results: int = 3) -> list[str]:
    """Busca los fragmentos más relevantes para la consulta del usuario."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []
```

### 4.3 Indexar documentos (scripts/index_docs.py)

Este script lee los archivos de la carpeta `knowledge/docs/` y los indexa en ChromaDB.
Ejecutarlo cada vez que se actualice la documentación.

```python
import os
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

DOCS_PATH = "./knowledge/docs"
CHROMA_PATH = "./chroma_db"

def index_documents():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection("moodle_docs")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs_added = 0

    for filename in os.listdir(DOCS_PATH):
        filepath = os.path.join(DOCS_PATH, filename)

        if filename.endswith(".pdf"):
            loader = PyPDFLoader(filepath)
        elif filename.endswith(".txt") or filename.endswith(".md"):
            loader = TextLoader(filepath, encoding="utf-8")
        else:
            continue

        documents = loader.load()
        chunks = splitter.split_documents(documents)

        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_{i}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk.page_content],
                metadatas=[{"source": filename}]
            )
            docs_added += 1

    print(f"Indexación completa. {docs_added} fragmentos añadidos.")

if __name__ == "__main__":
    index_documents()
```

### 4.4 Cómo agregar documentación al chatbot

1. Colocar el archivo (PDF, TXT o MD) en la carpeta `knowledge/docs/`.
2. Ejecutar el script de indexación:
   ```bash
   python scripts/index_docs.py
   ```
3. No es necesario reiniciar el backend. ChromaDB persiste los datos en disco.

**Formatos soportados:** PDF, TXT, Markdown.

**Tipos de documentos recomendados:**
- Manual de uso de Moodle para estudiantes
- Manual de uso de Moodle para docentes
- Preguntas frecuentes del soporte técnico
- Guías de actividades (foros, tareas, cuestionarios)
- Políticas académicas relevantes

### 4.5 Ajustar el comportamiento del chatbot

El comportamiento del bot se controla desde el `SYSTEM_PROMPT` en `app/services/llm.py`.
Para modificarlo no se necesita tocar el código estructural, solo editar ese texto.

Ejemplos de ajustes comunes:
- Cambiar el nombre del instituto en el saludo
- Restringir temas adicionales que no debe responder
- Cambiar el tono (más formal, más amigable)
- Agregar instrucciones específicas por rol

---

## 5. Plugin de Moodle (Frontend)

### 5.1 Estructura del plugin

```
moodle/blocks/chatbot/
├── block_chatbot.php        # Clase principal del bloque
├── version.php              # Metadatos del plugin
├── settings.php             # Pantalla de configuración en admin
├── lang/
│   └── es/
│       └── block_chatbot.php  # Traducciones
└── amd/
    └── src/
        └── chat.js          # Lógica del widget de chat
```

### 5.2 Versión y metadatos (version.php)

```php
<?php
defined('MOODLE_INTERNAL') || die();

$plugin->component = 'block_chatbot';
$plugin->version   = 2026031900;
$plugin->requires  = 2020061500; // Moodle 3.9
$plugin->maturity  = MATURITY_STABLE;
$plugin->release   = '1.0.0';
```

### 5.3 Clase principal (block_chatbot.php)

```php
<?php
defined('MOODLE_INTERNAL') || die();

class block_chatbot extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_chatbot');
    }

    public function get_content() {
        global $USER, $COURSE, $PAGE;

        if ($this->content !== null) {
            return $this->content;
        }

        $this->content = new stdClass();

        // Obtener rol del usuario en el curso actual
        $context = context_course::instance($COURSE->id);
        $roles   = get_user_roles($context, $USER->id);
        $role    = !empty($roles) ? reset($roles)->shortname : 'student';

        // Pasar datos al widget JS
        $this->page->requires->js_call_amd('block_chatbot/chat', 'init', [
            get_config('block_chatbot', 'backend_url'),
            get_config('block_chatbot', 'api_token'),
            $role,
            $PAGE->pagetype
        ]);

        $this->content->text   = '<div id="chatbot-widget"></div>';
        $this->content->footer = '';

        return $this->content;
    }

    public function applicable_formats() {
        return ['all' => true]; // Disponible en todas las páginas
    }
}
```

### 5.4 Configuración admin (settings.php)

```php
<?php
defined('MOODLE_INTERNAL') || die();

if ($ADMIN->fulltree) {
    $settings->add(new admin_setting_configtext(
        'block_chatbot/backend_url',
        'URL del backend',
        'Ejemplo: https://chatbot.miinstituto.edu/api',
        '',
        PARAM_URL
    ));

    $settings->add(new admin_setting_configtext(
        'block_chatbot/api_token',
        'Token de autenticación',
        'Token secreto para autenticar con el backend',
        '',
        PARAM_RAW
    ));
}
```

### 5.5 Widget de chat (amd/src/chat.js)

```javascript
export const init = (backendUrl, apiToken, userRole, currentPage) => {
    // Crear el widget flotante
    const widget = document.createElement('div');
    widget.innerHTML = `
        <div id="cb-toggle" style="position:fixed;bottom:24px;right:24px;z-index:9999;
             width:56px;height:56px;border-radius:50%;background:#0066cc;
             cursor:pointer;display:flex;align-items:center;justify-content:center;
             box-shadow:0 4px 12px rgba(0,0,0,0.2);">
            <span style="color:white;font-size:24px;">💬</span>
        </div>
        <div id="cb-panel" style="display:none;position:fixed;bottom:96px;right:24px;
             z-index:9999;width:360px;height:480px;background:white;border-radius:12px;
             box-shadow:0 8px 24px rgba(0,0,0,0.15);display:flex;flex-direction:column;">
            <div style="background:#0066cc;color:white;padding:16px;border-radius:12px 12px 0 0;
                 font-weight:600;">Asistente Moodle</div>
            <div id="cb-messages" style="flex:1;overflow-y:auto;padding:16px;
                 display:flex;flex-direction:column;gap:8px;"></div>
            <div style="padding:12px;border-top:1px solid #eee;display:flex;gap:8px;">
                <input id="cb-input" type="text" placeholder="Escribe tu pregunta..."
                    style="flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:8px;
                    font-size:14px;outline:none;" />
                <button id="cb-send" style="padding:8px 16px;background:#0066cc;color:white;
                    border:none;border-radius:8px;cursor:pointer;font-size:14px;">Enviar</button>
            </div>
        </div>
    `;
    document.body.appendChild(widget);

    let history = [];
    let panelOpen = false;

    // Toggle del panel
    document.getElementById('cb-toggle').addEventListener('click', () => {
        panelOpen = !panelOpen;
        document.getElementById('cb-panel').style.display = panelOpen ? 'flex' : 'none';
    });

    // Enviar mensaje
    const sendMessage = async () => {
        const input   = document.getElementById('cb-input');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        appendMessage('user', message);

        try {
            const response = await fetch(`${backendUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Token': apiToken
                },
                body: JSON.stringify({ message, history, user_role: userRole, context: currentPage })
            });

            const data = await response.json();
            appendMessage('assistant', data.reply);
            history.push({ role: 'user', content: message });
            history.push({ role: 'assistant', content: data.reply });

            // Mantener historial en máximo 10 turnos
            if (history.length > 20) history = history.slice(-20);

        } catch (error) {
            appendMessage('assistant', 'Ocurrió un error. Por favor intenta de nuevo.');
        }
    };

    document.getElementById('cb-send').addEventListener('click', sendMessage);
    document.getElementById('cb-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    const appendMessage = (role, text) => {
        const messages = document.getElementById('cb-messages');
        const div      = document.createElement('div');
        div.style.cssText = `
            padding:10px 14px;border-radius:10px;font-size:14px;max-width:85%;line-height:1.5;
            ${role === 'user'
                ? 'background:#0066cc;color:white;align-self:flex-end;'
                : 'background:#f0f0f0;color:#333;align-self:flex-start;'}
        `;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    };
};
```

---

## 6. Configuración en Moodle — cuentas y permisos

### 6.1 Cuentas que debes solicitar

| Cuenta | Nivel de acceso | Para qué se usa |
|---|---|---|
| Administrador de Moodle | Acceso total al panel de administración | Instalar el plugin, habilitar Web Services, crear token |
| Usuario de servicio (API user) | Cuenta de sistema sin rol docente/estudiante | Autenticar llamadas de la API de Moodle desde el backend |

### 6.2 Habilitar Web Services en Moodle

1. Ir a **Administración del sitio → Características avanzadas**
2. Activar **Habilitar servicios web**
3. Ir a **Administración del sitio → Plugins → Servicios web → Protocolos**
4. Habilitar el protocolo **REST**

### 6.3 Crear el usuario de servicio

1. Ir a **Administración del sitio → Usuarios → Agregar usuario**
2. Crear usuario con nombre `chatbot_service`
3. Asignar rol **Gestor** a nivel de sistema (o un rol personalizado con permisos mínimos)

**Permisos mínimos necesarios para el usuario de servicio:**
- `moodle/user:viewdetails` — ver datos del usuario autenticado
- `moodle/course:view` — ver cursos en los que está inscrito

### 6.4 Crear el token de servicio

1. Ir a **Administración del sitio → Plugins → Servicios web → Gestionar tokens**
2. Crear un token para el usuario `chatbot_service`
3. Guardar el token generado — se usará en la variable `MOODLE_API_TOKEN` del backend

### 6.5 Instalar el plugin

1. Comprimir la carpeta `blocks/chatbot/` en un archivo ZIP
2. Ir a **Administración del sitio → Plugins → Instalar plugin**
3. Subir el ZIP y seguir el proceso de instalación
4. Una vez instalado, ir a **Administración del sitio → Plugins → Bloques → Chatbot**
5. Ingresar la URL del backend y el token de autenticación

### 6.6 Agregar el bloque a las páginas

1. Activar la edición en cualquier curso
2. En el panel lateral, seleccionar **Agregar un bloque**
3. Elegir **Chatbot**
4. Para que aparezca en todas las páginas del sitio, configurarlo desde **Administración del sitio → Apariencia → Página principal**

---

## 7. Conexión Plugin ↔ Backend

### 7.1 Flujo de una solicitud

```
1. Usuario escribe mensaje en el widget (JS)
2. JS hace POST a {BACKEND_URL}/api/chat con:
   - Header: X-API-Token: {token}
   - Body: { message, history, user_role, context }
3. Backend valida el token
4. Backend consulta ChromaDB con el mensaje
5. Backend llama a DeepSeek con el system prompt + RAG + historial
6. Backend responde con { reply: "..." }
7. JS muestra la respuesta en el widget
```

### 7.2 Probar la conexión manualmente

Antes de instalar el plugin, verificar que el backend responde correctamente:

```bash
curl -X POST https://tu-backend.com/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Token: tu_token_secreto" \
  -d '{
    "message": "¿Cómo subo una tarea en Moodle?",
    "history": [],
    "user_role": "student",
    "context": "course-view"
  }'
```

Respuesta esperada:
```json
{
  "reply": "Para subir una tarea en Moodle, debes..."
}
```

---

## 8. Deployment

Esta sección cubre dos escenarios. Evalúa cuál aplica según la infraestructura del instituto.

---

### Opción A — Servidor físico o VPS propio

**Cuándo usar esta opción:** El instituto tiene un servidor propio (físico o virtual) con acceso SSH, y prefiere que los datos no salgan de su infraestructura.

#### Paso 1 — Instalar Docker en el servidor

```bash
# Ubuntu 22.04
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

#### Paso 2 — Subir el proyecto al servidor

```bash
# Desde tu máquina local
scp -r chatbot-backend/ usuario@ip-servidor:/opt/chatbot/
```

#### Paso 3 — Crear el archivo .env

```bash
cd /opt/chatbot
cp .env.example .env
nano .env   # Llenar con los valores reales (ver sección 9)
```

#### Paso 4 — Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Paso 5 — docker-compose.yml

```yaml
version: "3.9"

services:
  chatbot:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./knowledge:/app/knowledge
    env_file:
      - .env
    restart: unless-stopped
```

#### Paso 6 — Iniciar el servicio

```bash
# Indexar documentos primero
docker compose run --rm chatbot python scripts/index_docs.py

# Levantar el backend
docker compose up -d

# Verificar que está corriendo
docker compose logs -f
```

#### Paso 7 — Configurar Nginx como proxy inverso (recomendado)

```nginx
server {
    listen 443 ssl;
    server_name chatbot.miinstituto.edu;

    ssl_certificate     /etc/letsencrypt/live/chatbot.miinstituto.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chatbot.miinstituto.edu/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }
}
```

Obtener certificado SSL gratuito con Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d chatbot.miinstituto.edu
```

---

### Opción B — Servicio cloud (Railway, Render o DigitalOcean App Platform)

**Cuándo usar esta opción:** El instituto no tiene servidor propio o quiere evitar la administración de infraestructura. Es la opción más rápida para comenzar.

#### Railway (recomendado para proyectos pequeños)

1. Crear cuenta en [railway.app](https://railway.app)
2. Crear nuevo proyecto → **Deploy from GitHub repo**
3. Conectar el repositorio del backend
4. Agregar las variables de entorno desde el panel (ver sección 9)
5. Railway genera automáticamente una URL pública tipo `https://chatbot-xxx.railway.app`
6. Usar esa URL como `BACKEND_URL` en la configuración del plugin de Moodle

**Nota sobre ChromaDB en cloud:** Los servicios cloud no tienen almacenamiento persistente por defecto. Para ChromaDB en cloud, agregar un volumen persistente o usar un servicio de base de datos vectorial externo como Qdrant Cloud (tiene plan gratuito).

#### DigitalOcean App Platform

1. Crear cuenta en [digitalocean.com](https://digitalocean.com)
2. Crear una **App** desde el repositorio de GitHub
3. Seleccionar el plan **Basic** ($5/mes es suficiente para comenzar)
4. Agregar las variables de entorno
5. Crear un **Space** (almacenamiento) para persistir el volumen de ChromaDB

---

### Comparativa rápida

| Criterio | Servidor propio | Cloud (Railway/DO) |
|---|---|---|
| Costo | Solo hardware/VPS | Desde $0–$5/mes |
| Privacidad de datos | Total | Datos en servidores externos |
| Mantenimiento | Manual (sysadmin) | Automático |
| Escalabilidad | Limitada por hardware | Elástica |
| Tiempo de setup | 2–4 horas | 30–60 minutos |
| Recomendado si... | Instituto con sysadmin y datos sensibles | Inicio rápido o sin sysadmin disponible |

---

## 9. Variables de entorno de referencia

Crear el archivo `.env` en la raíz del backend con estos valores:

```env
# ── LLM ──────────────────────────────────────────────
DEEPSEEK_API_KEY=sk-deepseek-xxxxxxxxxxxxxxxxxxxx

# ── Seguridad ─────────────────────────────────────────
# Token secreto que el plugin de Moodle enviará en cada petición
# Generar con: python -c "import secrets; print(secrets.token_hex(32))"
API_TOKEN=genera_un_token_aleatorio_aqui

# ── Base de conocimiento ──────────────────────────────
CHROMA_DB_PATH=./chroma_db

# ── Moodle (opcional, si el backend consulta la API de Moodle) ──
MOODLE_URL=https://moodle.miinstituto.edu
MOODLE_API_TOKEN=token_generado_en_moodle
```

> ⚠️ **Nunca subir el archivo `.env` al repositorio.** Agregar `.env` al `.gitignore`.

---

*Documento generado para el proyecto chatbot-moodle v1.0 — Instituto Tecnológico Superior*
