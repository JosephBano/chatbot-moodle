# DEPLOY.md — Guía de Despliegue del Chatbot Moodle

> Documento generado a partir del despliegue real en el entorno de stage.
> Fecha: 2026-04-08
> Entorno validado: Moodle 4.2.10 + FastAPI (Docker) + Tailscale

---

## Arquitectura

```
[Usuario en Moodle] → [Plugin block_chatbot (PHP/JS)] → [Backend FastAPI] → [DeepSeek V3.2]
```

- Moodle corre en Docker (PHP 8.1 + Apache + MariaDB 10.6)
- Backend corre en Docker (Python 3.11 + FastAPI)
- Comunicación entre Moodle y Backend vía IP Tailscale
- Control de acceso por curso y carrera configurado en el Backend

---

## Requisitos previos

- Docker y Docker Compose v2+ instalados
- Tailscale instalado y activo en el servidor
- API Key de DeepSeek con saldo disponible
- Acceso de administrador a Moodle

---

## PARTE 1 — Backend (FastAPI)

### 1.1 Configurar el .env

```bash
cd Backend/
cp .env.example .env
nano .env
```

Valores requeridos:

```env
DEEPSEEK_API_KEY=sk-TU_CLAVE_REAL

# Generar con: python3 -c "import secrets; print(secrets.token_hex(32))"
API_TOKEN=token_generado

CHROMA_DB_PATH=./chroma_db

# IDs de cursos habilitados (ver URL del curso: ?id=N)
ALLOWED_COURSE_IDS=[630]

# Carreras habilitadas — lista vacía = cualquier carrera pasa
ALLOWED_CAREERS=[]
```

> **Nota:** No incluir MOODLE_URL ni MOODLE_API_TOKEN — el backend no los necesita y Pydantic los rechaza si no están declarados en config.py (ya corregido con `extra = "ignore"`).

### 1.2 Levantar el Backend

```bash
docker compose up -d --build
```

### 1.3 Verificar que responde

```bash
curl http://[IP-TAILSCALE]:8000/docs
```

Respuesta esperada: HTML de Swagger UI.

### 1.4 Test de acceso completo

```bash
curl -X POST http://[IP-TAILSCALE]:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Token: TU_API_TOKEN" \
  -d '{"message":"Hola","history":[],"user_role":"student","context":"course-view","course_id":630,"career":""}'
```

---

## PARTE 2 — Moodle Docker

### 2.1 Configurar config.php

Editar `moodle-docker/config.php` y poner la IP Tailscale del servidor:

```php
$CFG->wwwroot = 'http://[IP-TAILSCALE]:8080';
```

### 2.2 Levantar Moodle

```bash
cd moodle-docker/
docker compose up -d
```

### 2.3 Restaurar config.php (obligatorio tras cada recreación del contenedor)

```bash
docker cp config.php moodle:/var/www/moodle/config.php
docker exec moodle chown www-data:www-data /var/www/moodle/config.php
```

> `restart` y `stop/start` NO requieren este paso. Solo `down/up` (recreación).

---

## PARTE 3 — Plugin block_chatbot

### 3.1 Copiar el plugin al contenedor

```bash
docker cp moodle/blocks/chatbot moodle:/var/www/moodle/blocks/chatbot
docker exec moodle chown -R www-data:www-data /var/www/moodle/blocks/chatbot
```

### 3.2 Instalar el plugin

Ir al navegador:
```
http://[IP-TAILSCALE]:8080/admin/index.php
```

Moodle detectará el plugin y mostrará la pantalla de upgrade. Hacer clic en **Continuar** → **Upgrade**.

### 3.3 Configurar la URL del backend en la base de datos

Moodle Admin → Site administration → Server → Web services tiene plugins rotos del backup que impiden usar la UI. Configurar directamente en la BD:

```bash
docker exec moodle_db mariadb -u moodle_user -pmoodle_pass moodle_db -e \
  "INSERT INTO mdl_config_plugins (plugin, name, value)
   VALUES ('block_chatbot', 'backend_url', 'http://[IP-TAILSCALE]:8000/api')
   ON DUPLICATE KEY UPDATE value='http://[IP-TAILSCALE]:8000/api';"

docker exec moodle_db mariadb -u moodle_user -pmoodle_pass moodle_db -e \
  "INSERT INTO mdl_config_plugins (plugin, name, value)
   VALUES ('block_chatbot', 'api_token', 'TU_API_TOKEN')
   ON DUPLICATE KEY UPDATE value='TU_API_TOKEN';"
```

Limpiar caché:

```bash
docker exec -u www-data moodle php /var/www/moodle/admin/cli/purge_caches.php
```

### 3.4 Agregar el bloque a un curso

1. Ir al curso en Moodle
2. Activar edición (botón **Edit mode**)
3. Panel lateral → **Add a block** → **Chatbot**
4. Desactivar edición
5. El widget flotante azul aparece en la esquina inferior derecha

---

## PARTE 4 — Control de acceso

El backend controla quién puede usar el chatbot mediante dos listas en `.env`:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `ALLOWED_COURSE_IDS` | IDs de cursos habilitados | `[630, 145]` |
| `ALLOWED_CAREERS` | Nombres exactos de carreras | `["Sistemas","Industrial"]` |

**Lógica AND:** el curso debe estar en la lista Y la carrera también.
- Si `ALLOWED_CAREERS=[]` → cualquier carrera pasa
- Si `ALLOWED_COURSE_IDS=[]` → sin cursos habilitados (acceso denegado)
- Si ambas vacías → acceso denegado a todos (por seguridad)

Para habilitar un curso nuevo:

```bash
# 1. Editar .env y agregar el ID del curso
ALLOWED_COURSE_IDS=[630, 531, 145]

# 2. Reconstruir el contenedor (obligatorio — restart solo NO aplica los cambios del .env)
docker compose up -d --build

# 3. Verificar que los cambios se aplicaron
docker exec backend-chatbot-1 env | grep ALLOWED
```

> **Importante:** `docker compose restart` NO actualiza las variables del `.env` porque el archivo fue copiado dentro de la imagen durante el build. Siempre usar `docker compose up -d --build` al cambiar el `.env`.

Además, agregar el bloque en Moodle para cada curso nuevo:
1. Ir al curso como admin
2. Activar edición → **Add a block** → **Chatbot**
3. Desactivar edición

---

## PARTE 5 — Indexación de contenidos (RAG por curso)

El chatbot usa RAG (Retrieval-Augmented Generation) con ChromaDB para responder preguntas sobre el contenido específico de cada curso. Antes de que el chatbot pueda responder con información del curso, es necesario indexarlo.

### 5.1 Configurar credenciales de Moodle Web Services

El backend necesita conectarse a la API de Moodle para leer los contenidos. Agregar al `.env`:

```env
MOODLE_URL=http://[IP-TAILSCALE]:8080
MOODLE_API_TOKEN=TU_TOKEN_DE_MOODLE
```

Para obtener el `MOODLE_API_TOKEN`:

1. Admin → Site administration → Server → **Web services** → **Manage tokens**
2. Crear un token para el usuario administrador y el servicio **Chatbot Service**
3. El servicio debe tener habilitada la función `core_course_get_contents`

Después de modificar el `.env`, reconstruir el contenedor:

```bash
docker compose up -d --build
```

### 5.2 Indexar un curso

```bash
curl -X POST http://[IP-TAILSCALE]:8000/api/admin/index/[COURSE_ID] \
  -H "x-api-token: TU_API_TOKEN"
```

Respuesta esperada:

```json
{
  "course_id": 531,
  "modules_indexed": 5,
  "files_indexed": 0,
  "chunks_total": 5
}
```

- `modules_indexed`: secciones y actividades indexadas como texto
- `files_indexed`: PDFs y TXTs descargados e indexados
- `chunks_total`: fragmentos totales almacenados en ChromaDB

### 5.3 ¿Qué se indexa?

| Tipo | Qué extrae |
|---|---|
| Secciones y módulos | Nombre de la sección, nombre de la actividad, tipo, descripción |
| Archivos PDF | Texto completo extraído con pdfplumber |
| Archivos TXT | Contenido completo en texto plano |

Los fragmentos se almacenan con metadatos `{course_id, module_id, module_name, type}` para que las búsquedas RAG estén filtradas por curso.

### 5.4 Re-indexar un curso

Re-ejecutar el mismo comando. El endpoint elimina los chunks anteriores del curso antes de volver a indexar, por lo que es seguro ejecutarlo múltiples veces.

### 5.5 Persistencia de ChromaDB

Verificar que el `docker-compose.yml` del backend monte un volumen para `CHROMA_DB_PATH`:

```yaml
volumes:
  - ./chroma_db:/app/chroma_db
```

Si no hay volumen, los datos indexados se pierden al recrear el contenedor.

### 5.6 Cursos habilitados vs. indexados

Son dos controles independientes:

| Control | Dónde | Efecto |
|---|---|---|
| `ALLOWED_COURSE_IDS` en `.env` | Backend | Permite o bloquea el acceso al chat |
| Indexación vía `/api/admin/index/` | ChromaDB | Habilita respuestas con contexto del curso |

Un curso puede estar habilitado pero no indexado (el chatbot responde sin contexto RAG) o indexado pero no habilitado (el acceso es bloqueado antes de llegar al RAG). Lo correcto es tener ambos configurados.

---

## PARTE 6 — Notas para producción

### Plugin roto block_smowl
El backup de producción tiene `block_smowl` y `format_popups` registrados en la BD pero sin archivos. Desinstalarlos desde:
**Admin → Plugins → Plugins overview → buscar "smowl" / "popups" → Uninstall**

### JavaScript AMD
El plugin usa `chat.js` como script directo (no AMD compilado). Para producción con Moodle en modo normal (no developer), esto funciona correctamente porque se carga vía `$PAGE->requires->js()`.

### HTTPS en producción
El backend debe estar detrás de Nginx con SSL. Ver `PASOS-FALTANTES-DESPLIEGUE.md` → PASO 4.

### Extensión PHP xsl
La imagen Docker base no incluye `php-xsl`. Para instalarla:
```bash
docker exec -it moodle bash -c "apt-get update -qq && apt-get install -y libxslt1-dev && docker-php-ext-install xsl"
docker restart moodle
docker cp moodle-docker/config.php moodle:/var/www/moodle/config.php
docker exec moodle chown www-data:www-data /var/www/moodle/config.php
```

---

## Verificación final

```bash
# Backend corriendo
docker ps | grep chatbot

# Test directo al backend
curl -X POST http://[IP-TAILSCALE]:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Token: TU_API_TOKEN" \
  -d '{"message":"Hola","history":[],"user_role":"student","context":"course-view","course_id":630,"career":""}'

# Logs del backend
docker logs backend-chatbot-1 --tail 20
```

---

*Validado en stage el 2026-04-08 — Joseph Bano*
