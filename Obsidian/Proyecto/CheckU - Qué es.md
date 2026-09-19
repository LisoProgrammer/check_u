---
tags: [checku, proyecto]
---

# CheckU — Qué es

Sistema de **preinscripción automatizada para solicitudes de grado** de la
Universidad Tecnológica de Bolívar. Proyecto de grado del [[Equipo y roles|equipo]],
inscrito en el Laboratorio de Ingeniería Aplicada (LIA).

Repositorio: `github.com/LisoProgrammer/check_u`

## El problema

Hoy la validación de los documentos de una solicitud de grado es manual.
Alguien abre cada documento y revisa si cumple. Eso genera:

- Tiempo dedicado a revisar solicitudes que no pueden avanzar.
- Reprocesos cuando el estudiante debe corregir o volver a presentar.
- Mayor carga para el personal encargado.
- Errores humanos durante la revisión.
- Dificultad para detectar inconsistencias entre documentos.

## La idea

Que el estudiante suba sus documentos ANTES de la inscripción formal, y
que el sistema los lea, los valide y marque la solicitud como **válida**,
**no válida**, **inconsistente** o **por revisar**. Así la revisión
manual solo recibe lo que ya pasó el filtro.

Los cinco puntos del problema se atacan concretamente así:

| Problema | Cómo lo ataca el sistema |
|---|---|
| Tiempo en solicitudes que no avanzan | El estado se calcula solo; lo inconsistente ni llega a revisión |
| Reprocesos | El estudiante ve la alerta y corrige antes de radicar |
| Carga del personal | Solo revisan "por revisar", no todo |
| Errores humanos | El cruce contra el [[RUI - Ventanilla Social DNP|RUI]] es automático y siempre igual |
| Inconsistencias entre documentos | Se comparan campo por campo y se muestran unidos con una línea |

Ver [[Alcance LIA]] para el compromiso formal completo, y [[Estado actual]]
para lo que realmente está construido.
