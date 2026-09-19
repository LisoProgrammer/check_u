---
tags: [checku, decision, adr]
---

# ADR-005 — Casos en archivos JSON, sin base de datos

**Fecha**: 17/09/2026 · **Estado**: aceptada

## Contexto

Los casos deben poder retomarse en cualquier momento: el usuario cierra el
navegador y vuelve mañana a agregar un documento que faltaba.

## Decisión

Guardar cada caso como una **carpeta autocontenida** en `webapp/data/`:

```
webapp/data/casos/<id>/
├── caso.json                    ← documentos, comparaciones, estado
└── documentos/<doc_id>/
    ├── pagina_0.jpg             ← la imagen que ve el usuario
    └── resultado.json           ← campos, cajas, RUI, validación
```

Sin base de datos. El panel corre en local, en la máquina de quien revisa;
meter SQLite o Postgres solo para esto agregaría una dependencia más que
instalar, migrar y respaldar.

Una carpeta por caso se puede copiar, respaldar o borrar a mano sin romper
nada, y se puede abrir con cualquier editor para depurar.

## Privacidad

`webapp/data/` está en `.gitignore`. Son documentos de identidad de
personas reales: nombre, número de cédula, fecha de nacimiento y la imagen
del documento. **Nunca deben subirse al repositorio.**

Lo mismo aplica a `test_samples/`, agregado al `.gitignore` por la misma
razón.

> Antecedente real: `webapp/historial.json` llegó a quedar dentro de tres
> commits del historial de git porque una línea rota del `.gitignore`
> ("modules/ocr_module/config.pywebapp/historial.json", sin salto de
> línea) hacía que ninguno de los dos patrones funcionara. Se reescribió
> el historial para sacarlo por completo antes de publicar la rama.

## Consecuencias

- Si en el futuro el panel deja de ser local y pasa a ser un servicio
  compartido, esto hay que cambiarlo. Queda anotado en
  [[Pendientes y próximos pasos]]
- Los casos vacíos no se listan en el historial, y el caso ni siquiera se
  crea en el servidor hasta que entra el primer documento
