---
tags: [checku, decision, adr]
---

# ADR-001 — Cómo llamar al formato antiguo

**Fecha**: 17/09/2026 · **Estado**: aceptada

## Contexto

Había que nombrar el formato viejo de la cédula en el código, la interfaz
y la carpeta de muestras. En conversación se le decía "cédula vieja" o
"cédula amarilla", pero eso no es terminología oficial y el proyecto se
entrega a una universidad.

## Investigación

La **Registraduría Nacional del Estado Civil** llama a ese formato
**"cédula de ciudadanía amarilla con hologramas"**. Tiene páginas de
trámite propias con ese nombre exacto (primera vez, duplicado, renovación,
rectificación). El formato actual se llama **"cédula digital"**.

La Registraduría también aclara que la amarilla **sigue siendo válida**;
ambos formatos conviven.

## Decisión

Usar el nombre oficial en todas partes:

- Constante en código: `FORMATO_AMARILLA = "amarilla_hologramas"`
- En la interfaz: "Cédula amarilla con hologramas" / "Cédula digital"
- Carpeta de muestras: `test_samples/Cedulas_Amarillas_Hologramas/`

## Consecuencias

- Los informes y la sustentación usan el mismo vocabulario que la entidad
  que emite el documento
- Queda claro que no es un formato "vencido" sino uno de los dos vigentes
- La carpeta vieja `Cedulas_Amarillas/` queda obsoleta y hay que borrarla
  a mano
