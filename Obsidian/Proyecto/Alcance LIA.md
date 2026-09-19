---
tags: [checku, proyecto, alcance]
---

# Alcance según el formato LIA

Lo que el proyecto se comprometió a entregar ante la universidad.

## Documentos que recibe

**Pregrado (5):**
1. Cédula de ciudadanía
2. Evaluación de Grado expedida por Banner
3. Comprobante de pago de la estampilla Pro-Cultura
4. Resultados de las Pruebas Saber Pro
5. Paz y Salvo de Biblioteca

**Posgrado (3):** Cédula, Paz y Salvo de Biblioteca, estampilla Pro-Cultura.

> Hoy solo está implementada la **cédula**. Ver [[Estado actual]].

## Estados de una solicitud

`Válida` · `No válida` · `Inconsistente` · `Por revisar`

Son los mismos nombres que usa el panel, a propósito: ver
[[Backend del panel#Estados]].

## Entregables comprometidos

- Login básico (estudiantes y personal de grados)
- Vista de estudiante: preinscripción, carga documental, seguimiento
- Vista de personal de grados: gestión, filtros por estado, retroalimentación
- Estadísticas con gráficos de barras y circulares
- **Software de Biblioteca**: firma criptográfica del Paz y Salvo, que
  CheckU debe poder verificar después

## Objetivos específicos del formato

1. Analizar el proceso actual de recepción y validación
2. Diseñar el flujo de preinscripción
3. **Implementar OCR para extraer la información** ← lo que cubre esta bóveda
4. **Implementar reglas de validación** ← lo que cubre esta bóveda
5. Subsistema de firma criptográfica del Paz y Salvo
6. Evaluar el funcionamiento con pruebas

## Cierre

Se presenta en la feria de proyectos y se entrega a la universidad por
acta. El equipo no pide derechos sobre el producto, solo que se reconozca
su autoría.
