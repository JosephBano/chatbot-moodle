# Moodle Local — Entorno de desarrollo

Moodle **4.2.10** corriendo en Docker con MariaDB **10.6** — versión idéntica a producción.

---

## Levantar el entorno

```bash
cd moodle-docker
docker compose up -d
```

> Primera vez: tarda ~2 min porque MariaDB necesita inicializarse antes de que Apache arranque.

---

## Acceso

| Recurso | URL / Valor |
|---|---|
| Moodle | http://localhost |
| Usuario admin | `admin` |
| Contraseña admin | `Admin1234!` |
| Email admin | `admin@local.dev` |

---

## Base de datos (MariaDB)

| Parámetro | Valor |
|---|---|
| Host (interno Docker) | `moodle_db` |
| Puerto | `3306` (no expuesto al host) |
| Base de datos | `moodle_db` |
| Usuario | `moodle_user` |
| Contraseña | `moodle_pass` |
| Root password | `root_pass` |

Conectar desde el host (si se necesita inspeccionar):

```bash
docker exec -it moodle_db mariadb -u moodle_user -pmoodle_pass moodle_db
```

---

## Archivos del entorno

```
moodle-docker/
├── docker-compose.yml   # Servicios: MariaDB + Moodle
├── Dockerfile           # PHP 8.2 + Apache + Moodle 4.5
├── config.php           # Configuración de Moodle (conexión a BD, rutas)
└── README.md            # Este archivo
```

---

## Comandos utiles

```bash
# Ver logs en tiempo real
docker compose logs -f moodle

# Detener sin borrar datos
docker compose stop

# Detener y borrar contenedores (los volúmenes persisten)
docker compose down

# Borrar todo incluyendo datos de BD y moodledata
docker compose down -v
```

---

## IMPORTANTE: config.php tras recrear el contenedor

El archivo `config.php` vive dentro del contenedor. Si haces `docker compose down && docker compose up`
(no solo `stop/start` o `restart`), el contenedor se recrea desde la imagen y el archivo se pierde.

Después de cualquier recreación, restaurarlo con:

```bash
docker cp moodle-docker/config.php moodle:/var/www/moodle/config.php
docker exec moodle chown www-data:www-data /var/www/moodle/config.php
```

> `restart` y `stop/start` NO recrean el contenedor, así que no requieren este paso.

---

## Próximos pasos — configurar para el chatbot

Una vez que Moodle carga correctamente, hacer estos pasos en el panel admin antes de instalar el plugin:

1. **Crear campo de perfil `carrera`**
   - Ir a: `Administración del sitio → Usuarios → Campos de perfil de usuario → Crear nuevo campo`
   - Tipo: Texto
   - Nombre corto (shortname): `carrera` (exacto, minúsculas, sin tilde)

2. **Crear curso de prueba**
   - Anotar el ID que aparece en la URL del curso (`?id=X`)

3. **Crear usuario alumno**
   - Usuario: `alumno_prueba` / Contraseña: `Alumno1234!`
   - Llenar el campo `carrera` con el valor exacto que se usará en el `.env` del backend

4. **Crear usuario docente**
   - Usuario: `docente_prueba` / Contraseña: `Docente1234!`

5. **Inscribir ambos al curso** con sus roles correspondientes (Estudiante / Profesor)
