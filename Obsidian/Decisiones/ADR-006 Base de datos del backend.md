---
tags: [checku, decision, adr]
---

# ADR-006 — Base de datos del backend: PostgreSQL con TypeORM

**Fecha**: 13/10/2026 · **Estado**: aceptada, en implementación (rama `backend_base_de_datos`)

Diseño completo: `docs/superpowers/specs/2026-10-13-base-de-datos-nestjs-design.md`.

## Contexto

El backend en NestJS no tiene base de datos: los usuarios están escritos en
el código y las sesiones viven en memoria. El login real, la preinscripción,
la carga de documentos y la revisión del personal necesitan guardar datos.
[[ADR-005 Casos en archivos JSON]] servía para el panel local de Python, no
para un servicio con varias personas y documentos de identidad.

## Decisión

- **PostgreSQL 18 en Docker** (`backend/docker-compose.yml`), solo en el
  propio PC (`127.0.0.1:5433`)
- **TypeORM** con `@nestjs/typeorm`; todo en `backend/src/database/`
- **Migraciones versionadas** en el repo; nunca `synchronize`
- **8 tablas**: el diagrama del equipo con estos ajustes:
  - los archivos se guardan dentro de la base (`archivos.contenido`, bytea)
    en vez de rutas en disco: una sola copia de seguridad cubre datos y
    documentos, y no quedan archivos huérfanos;
  - cada reenvío agrega una versión del archivo;
  - `campos_extraidos` guarda de dónde salió cada dato, para el comparador;
  - estado `borrador` y enums de PostgreSQL;
  - `revisiones.comentario` es obligatorio.
- Nada se borra en cascada: es un trámite oficial y debe quedar el rastro
- **Datos de ejemplo** 100 % sintéticos, con las cuentas que ya usa el equipo
  (clave cifrada con argon2id). La semilla se niega a vaciar una base que
  tenga documentos reales.

## Consecuencias

- El backend **necesita la base encendida**: si Docker está apagado no
  arranca, y dice cómo levantarla (`npm run db:up`)
- `GET /api/health` informa si la base está conectada
- El login pasa a la base en el siguiente paso
- Los campos personales del formulario (los define Javier) llegan con su
  propia migración
- Privacidad: con documentos reales en la base, las copias de seguridad de
  PostgreSQL son tan sensibles como los documentos. Nunca se suben al
  repositorio. Ver [[Pendientes y próximos pasos]]
