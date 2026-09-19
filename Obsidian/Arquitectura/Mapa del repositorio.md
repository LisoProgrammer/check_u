---
tags: [checku, arquitectura]
---

# Mapa del repositorio

```
check_u/
├── iniciar.ps1              ← un solo script: instala todo y abre el panel
├── README.md
├── .gitignore               ← ignora venv, __pycache__, test_samples/, webapp/data/
│
├── modules/
│   ├── cedula/              ← NUEVO. Ver [[modules.cedula]]
│   ├── mrz/                 ← parseo del [[MRZ]] por posiciones fijas
│   │   ├── get_info.py      ← extrae los campos
│   │   ├── normalize.py     ← corrige confusiones de OCR (L→1, O→0...)
│   │   └── validate.py      ← dígitos de chequeo, estructura
│   ├── ocr_module/
│   │   ├── loaders/         ← carga de PDF (poppler)
│   │   ├── preprocess/      ← ImageCleaner, SkewDetector, divide_faces
│   │   ├── ocr/             ← TesseractEngine
│   │   └── postprocess/     ← limpieza y estructuración de texto
│   ├── check_id/
│   │   ├── rui/consultar.py ← [[RUI - Ventanilla Social DNP]]
│   │   └── orquestador.py   ← VACÍO (placeholder)
│   └── test_data/           ← dos plantillas en blanco, sin datos reales
│
├── webapp/                  ← el panel. Ver [[Backend del panel]]
│   ├── app.py               ← Flask + SSE
│   ├── entorno.py           ← verifica Tesseract/PyMuPDF/paquetes antes de arrancar
│   ├── templates/index.html
│   ├── static/{app.js, style.css}
│   └── data/                ← casos guardados (NO se sube a git)
│
├── frontend/                ← maquetas HTML estáticas, sin conectar
│   ├── public/icons/
│   └── src/views/{aspirantes, auxiliares}/
│
├── test_samples/            ← cédulas reales de prueba (NO se sube a git)
│   ├── Cedulas_MRZ/
│   └── Cedulas_Amarillas_Hologramas/
│
└── Obsidian/                ← esta bóveda
```

## Qué es de quién

`modules/ocr_module`, `modules/mrz` y `modules/check_id` son de otros
integrantes del equipo. `modules/cedula` y `webapp` son el aporte
documentado en esta bóveda.

**Regla que se siguió**: no se modificó código ajeno. Cuando hizo falta un
comportamiento distinto (ver [[ADR-002 Preprocesamiento propio]]), se
escribió aparte en `modules/cedula` en vez de tocar el módulo del
compañero.
