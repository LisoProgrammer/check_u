# Base de datos del backend (NestJS + PostgreSQL)

**Fecha:** 13/10/2026 · **Autor:** Héctor Cabarcas (backend) · **Rama:** `backend_base_de_datos` · **Revisa:** Lisandro Zapata (PR a `main`)

Resumen de la decisión en la bóveda: `Obsidian/Decisiones/ADR-006 Base de datos del backend.md`.

## 1. Contexto y objetivo

El backend en NestJS (`backend/`, creado por Lisandro el 09-10/10/2026) tiene `/api/health` y el login (`/api/auth/login`, `me`, `logout`), pero **no tiene base de datos**: los dos usuarios están escritos en el código y las sesiones viven en memoria. Todo lo que falta para el LIA necesita guardar datos: el login real, la preinscripción, la carga de documentos, el análisis, la revisión del personal y las estadísticas.

**Objetivo:** que el backend tenga una base PostgreSQL con el modelo del proyecto, migraciones, datos de ejemplo y pruebas, de modo que cualquier integrante la levante con pocos comandos.

**Éxito:**
- Con Docker Desktop abierto, `npm run db:up`, `npm run db:migrate` y `npm run db:seed` dejan la base con las 8 tablas y los datos de ejemplo.
- `npm run start:dev` conecta y `GET /api/health` responde `baseDeDatos: "conectada"`.
- Las pruebas de integración pasan contra la base `checku_test`.

## 2. Decisiones

| # | Tema | Decisión |
|---|---|---|
| 1 | Coordinación | Rama `backend_base_de_datos` desde `main` y **Pull Request que revisa Lisandro**. No se toca `main` directamente. |
| 2 | ORM | **TypeORM 1.x** con `@nestjs/typeorm` 12 (compatible con NestJS 12; pide Node 22.13+). |
| 3 | Dónde corre | **PostgreSQL 18 en Docker**, con `backend/docker-compose.yml`. Contenedor `checku-bd`, solo en el propio PC (`127.0.0.1:5433`). |
| 4 | Contenedor anterior | El `checku-bd` que existía en el PC de Héctor (con tablas de otra versión) **se reemplaza**. |
| 5 | Modelo | El **modelo ajustado de 8 tablas** (sección 4): archivos dentro de PostgreSQL (`bytea`) en vez de rutas en disco, versiones por reenvío, `campos_extraidos`, estado `borrador` y enums. |
| 6 | Cambios de esquema | **Migraciones versionadas** en el repo. `synchronize` apagado siempre. |
| 7 | Organización | Todo lo de la base en **`src/database/`**: entidades, migraciones, semilla y conexión. |
| 8 | Configuración | `backend/.env` (no se sube) y `backend/.env.example` (sí se sube). Se lee con **`@nestjs/config`**. |
| 9 | Sin base al arrancar | El backend **no arranca**: 3 intentos en unos 6 segundos y un mensaje claro que dice cómo levantar la base. |
| 10 | Salud | `GET /api/health` conserva su respuesta y agrega `baseDeDatos: "conectada"` o `"sin conexión"`. Siempre responde 200. |
| 11 | Datos de ejemplo | Las cuentas que ya usa el equipo (`lizapata`, `rmarriaga`, clave `12345`) **cifradas con argon2id**, una solicitud de `lizapata` y 40 solicitudes sintéticas más 3 borradores. |
| 12 | Pruebas | Vitest (ya está en el backend), contra la base `checku_test`. |
| 13 | Documentación | README del backend en español (reemplaza la plantilla de NestJS), este spec y el ADR-006 en Obsidian. |

## 3. Infraestructura y configuración

**`backend/docker-compose.yml`:**
- imagen `postgres:18`, contenedor `checku-bd`, puerto `127.0.0.1:5433:5432`, volumen `checku_pg` montado en `/var/lib/postgresql`;
- usuario, clave y base salen de `backend/.env`;
- `backend/docker/init/01-bd-pruebas.sql` crea la base `checku_test` la primera vez que arranca el contenedor.

**`backend/.env.example`** (se copia como `.env`):

```
DB_HOST=localhost
DB_PORT=5433
DB_USER=checku
DB_PASSWORD=cambia-esta-clave
DB_NAME=checku
DB_NAME_TEST=checku_test
```

- `backend/.gitignore` agrega `.env` (hoy no lo ignora).
- `docker compose` lee `backend/.env` solo porque el archivo está en la misma carpeta.

**Comandos** (desde `backend/`):

| Comando | Qué hace |
|---|---|
| `npm run db:up` | Levanta el contenedor. |
| `npm run db:down` | Lo apaga; los datos quedan en el volumen. |
| `npm run db:migrate` | Aplica las migraciones pendientes. |
| `npm run db:migration:generate -- <Nombre>` | Crea una migración a partir de los cambios en las entidades. |
| `npm run db:seed` | Vacía las tablas y carga los datos de ejemplo (ver sección 6). |

## 4. Modelo de datos

**Convenciones:**
- tablas y columnas en snake_case, como en el diagrama del equipo; propiedades de TypeScript en camelCase (`@Column({ name: 'id_usuario' })`);
- claves primarias `serial`;
- fechas en `timestamptz`, porque Colombia es UTC-5 y el servidor puede estar en UTC;
- llaves foráneas `ON DELETE RESTRICT`: nada se borra en cascada, porque es un trámite oficial y debe quedar el rastro.

**Enums de PostgreSQL** (en `src/database/entities/enums.ts`):

| Enum | Valores |
|---|---|
| `rol_usuario` | `estudiante`, `funcionario` |
| `tipo_solicitud` | `pregrado`, `posgrado` |
| `estado_solicitud` | `borrador`, `por_revisar`, `valida`, `no_valida`, `inconsistente` |
| `tipo_documento` | `cedula`, `evaluacion_banner`, `estampilla_procultura`, `saber_pro`, `paz_y_salvo` |
| `estado_documento` | `procesando`, `valido`, `no_valido`, `inconsistente`, `por_revisar`, `error` |
| `tipo_validacion` | `lectura`, `rui_nombre`, `rui_numero`, `cruce_documentos`, `firma_digital` |
| `resultado_validacion` | `aprobada`, `fallida`, `advertencia` |
| `fuente_campo` | `mrz`, `pdf417`, `ocr` |

**Tablas:**

| Tabla | Columnas | Restricciones e índices |
|---|---|---|
| `usuarios` | `id_usuario` · `nombres` varchar(100) · `apellidos` varchar(100) · `correo` varchar(255) · `contrasena_hash` varchar(255) **NULL** (las cuentas de Microsoft no tienen clave) · `rol` · `programa` varchar(150) NULL · `activo` (true) · `fecha_creacion` · `fecha_actualizacion` | `correo` único; se guarda en minúsculas |
| `solicitud_grado` | `id_solicitud` · `id_estudiante` → usuarios · `tipo_solicitud` · `estado` (`borrador`) · `fecha_creacion` · `fecha_actualizacion` | índice (`estado`, `fecha_creacion`) para la cola |
| `documentos` | `id_documento` · `id_solicitud` → solicitud_grado · `tipo_documento` · `version` (1) · `estado` (`procesando`) · `fecha_carga` | único (`id_solicitud`, `tipo_documento`), que también sirve de índice por solicitud |
| `archivos` | `id_archivo` · `id_documento` → documentos · `nombre_original` varchar(255) · `mime_type` varchar(100) · `tamano_bytes` int · `hash_archivo` char(64) (SHA-256) · `contenido` **bytea** · `activa` (true) · `fecha_creacion` | índice (`id_documento`). Cada reenvío agrega una fila y desactiva la anterior. |
| `campos_extraidos` | `id_campo` · `id_documento` · `id_archivo` · `campo` varchar(60) · `valor` text · `fuente` · `pagina` int · `x`, `y`, `ancho`, `alto` numeric(6,3) NULL (en % de la página) · `fecha_creacion` | índice (`id_archivo`) |
| `validaciones` | `id_validacion` · `id_documento` · `id_archivo` · `tipo_validacion` · `resultado` · `mensaje` text · `confianza` numeric(5,2) NULL · `fecha_validacion` | índice (`id_archivo`) |
| `historial_validaciones` | `id_historial` · `id_validacion` → validaciones · `estado_anterior` NULL · `estado_nuevo` (`resultado_validacion`) · `observacion` text NULL · `fecha_cambio` | — |
| `revisiones` | `id_revision` · `id_solicitud` → solicitud_grado · `id_funcionario` → usuarios · `resultado` (`estado_solicitud`) · `comentario` text **NOT NULL** · `fecha_revision` | `CHECK` que el comentario no quede en blanco |

**Cómo se lee el modelo:**
- `campos_extraidos` y `validaciones` guardan `id_archivo` porque un documento puede tener varias versiones de archivo; así se sabe de cuál salió cada dato.
- La regla de longitud del comentario y el tamaño máximo de archivo los validará la API cuando exista; la base solo garantiza lo esencial.
- Los campos personales del formulario de preinscripción, que define Javier, se agregan después con su propia migración.

## 5. Código en NestJS

```
backend/src/database/
├── opciones.ts            # configuración de conexión a partir del .env (una sola fuente)
├── database.module.ts     # TypeOrmModule.forRootAsync con ConfigService
├── data-source.ts         # DataSource para el CLI de TypeORM (migraciones)
├── entities/
│   ├── enums.ts
│   ├── usuario.entity.ts … revision.entity.ts   # las 8 entidades
│   └── index.ts           # ENTIDADES: la lista que se registra en la conexión
├── migrations/
│   └── <timestamp>-Inicial.ts                    # generada desde las entidades
└── semilla/
    ├── semilla.ts         # sembrar(dataSource, { ahora }): datos deterministas
    └── ejecutar.ts        # lo que corre npm run db:seed
```

- **`AppModule`:**
  - importa `ConfigModule.forRoot({ isGlobal: true })` y `DatabaseModule`;
  - el módulo `auth` de Lisandro **no cambia** (sigue en memoria hasta el siguiente paso);
  - `ObserveModule` tampoco se toca.
- **`opciones.ts`:**
  - `type: 'postgres'`, la lista `ENTIDADES`, las migraciones de `src/database/migrations` y `synchronize: false`;
  - `retryAttempts: 3` y `retryDelay: 2000`.
- **Sin base al arrancar:** si la conexión falla después de los reintentos, el arranque termina con este mensaje: *"No hay conexión con PostgreSQL en localhost:5433. ¿Docker Desktop está abierto? Corre `npm run db:up` en la carpeta backend."*
- **`/api/health`:** `AppController` recibe el `DataSource` y hace `SELECT 1`. La respuesta agrega `baseDeDatos: "conectada" | "sin conexión"` sin cambiar los campos actuales (`status`, `service`, `message`), así la página `/connect` del frontend sigue funcionando.
- **Riesgo a validar en el plan:** el backend es ESM (`"type": "module"`, `nodenext`). Hay que confirmar con una prueba corta cómo corre el CLI de TypeORM sobre `data-source.ts` en ese modo. Si hace falta, puede correr sobre el JavaScript ya compilado.

## 6. Datos de ejemplo (`npm run db:seed`)

- **Resguardo:**
  - antes de vaciar, la semilla cuenta los archivos que **no** llevan la marca `documento sintético de prueba (CheckU)`;
  - si hay alguno (un documento real), se detiene sin borrar nada;
  - después vacía las tablas con `TRUNCATE … RESTART IDENTITY` para que los ids sean siempre los mismos.
- **Cuentas del equipo** (las que hoy usa el login en memoria), con la clave `12345` guardada con **argon2id** (`@node-rs/argon2`):
  - `lizapata@utb.edu.co`: Lisandro Zapata, estudiante, Ingeniería de Sistemas;
  - `rmarriaga@utb.edu.co`: Rosana Marriaga, funcionaria.
- **Solicitud de `lizapata`:** pregrado, `por_revisar`, con sus 5 documentos.
- **40 solicitudes sintéticas:**
  - 12 `por_revisar`, 4 `inconsistente`, 3 `no_valida` y 21 `valida`, más 3 `borrador` (sin documentos);
  - cada una de un estudiante inventado, sin clave y con programa;
  - el 75 % son de pregrado (5 documentos) y el 25 % de posgrado (3).
- **Documentos:**
  - cada uno lleva un PDF mínimo con la marca sintética y una validación;
  - en las solicitudes que no son válidas, un documento tiene la validación que explica el estado; por ejemplo, Saber Pro con "imagen borrosa, no se leyó el puntaje".
- **Revisiones:** dos solicitudes válidas tienen una revisión de `rmarriaga`.
- **Determinista:** generador pseudoaleatorio con semilla fija; las fechas se reparten en los últimos 6 días.
- **Nunca** usa nada de `test_samples/` ni de `webapp/data/` (documentos reales).

## 7. Pruebas

Las pruebas de integración van en `backend/test/database/*.e2e-spec.ts` y corren con la configuración e2e que ya existe (`npm run test:e2e`). Usan la base `checku_test`:
- antes de cada archivo de prueba se reinicia el esquema y se aplican las migraciones;
- solo se reinicia una base cuyo nombre termine en `_test`.

Qué comprueban:
1. **Migraciones:** desde una base vacía crean las 8 tablas y los 8 enums; aplicarlas de nuevo no hace nada.
2. **Semilla:**
   - conteos por estado;
   - las dos cuentas existen y su clave verifica con argon2;
   - toda solicitud enviada tiene todos los documentos de su tipo, cada uno con un archivo activo y una validación de ese archivo;
   - correrla dos veces deja los mismos datos y los mismos ids.
3. **Reglas:** la base rechaza:
   - un correo repetido;
   - dos documentos del mismo tipo en una solicitud;
   - una revisión sin comentario o con el comentario en blanco;
   - borrar una solicitud que tiene documentos.
4. **Resguardo:** con un archivo no sintético, la semilla falla y no borra nada.
5. **Salud:** `GET /api/health` responde 200 con `baseDeDatos: "conectada"` (con supertest, que ya está en el backend).

Las pruebas unitarias que ya existen (`auth`, `app`) siguen pasando.

## 8. Documentación y entrega

- **`backend/README.md`** en español:
  - requisitos (Node 22.13+, Docker Desktop);
  - la primera vez: copiar `.env.example` como `.env`, `npm ci`, `db:up`, `db:migrate`, `db:seed` y `start:dev`;
  - los comandos, las cuentas de prueba y cómo crear una migración;
  - el aviso de que **el backend ahora necesita la base encendida**.
- **`Obsidian/Decisiones/ADR-006 Base de datos del backend.md`** y su enlace en `Obsidian/00 - Índice.md`.
- **Entrega:** commits pequeños en `backend_base_de_datos`. Antes de subir la rama y abrir el PR se le pregunta a Héctor.

## 9. Fuera de alcance

- Pasar el login a la base: es el siguiente paso y usará la entidad `Usuario`.
- La API de solicitudes, el inicio de sesión con Microsoft y la carga de documentos.
- Conectar el servicio de Python.
- Los campos personales de Javier.
- Cambios en el frontend.
- Configurar `ObserveModule`, que tiene claves de relleno: es decisión de Lisandro.
