---
tags: [checku, estado]
---

# Estado actual

Actualizado: **17 de septiembre de 2026**. Rama de trabajo:
`Validacion-Webapp-Local`.

## Lo que funciona

- Lectura de **[[Cédula digital]]** (con MRZ) — número correcto en 3/3 muestras
- Lectura de **[[Cédula amarilla con hologramas]]** (sin MRZ) — número
  correcto en 7/11 muestras, nombre ≥85 % en 6/11. Ver [[Resultados de precisión]]
- **Detección automática de formato**: si no hay MRZ, cambia solo y avisa
- **Validación contra el [[RUI - Ventanilla Social DNP|RUI]]** con umbral de
  [[ADR-004 Umbral de similitud 85|85 % de similitud]]
- **Comparación entre documentos** campo por campo, en pantalla dividida
- **Panel web** con pestañas, recuadros sobre el origen de cada dato,
  historial de casos retomables, modo claro/oscuro
- Instalación en un solo paso con `iniciar.ps1`

## Lo que NO existe todavía

- Login / autenticación de ningún tipo
- Los otros 4 documentos del [[Alcance LIA]] (Banner, estampilla, Saber Pro, Paz y Salvo)
- Firma criptográfica del Paz y Salvo (subsistema de Biblioteca)
- Estadísticas con gráficos
- Conexión del `frontend/` (maquetas HTML estáticas) con el backend
- `modules/check_id/orquestador.py` está vacío

## Aviso importante sobre las muestras

Las 11 cédulas amarillas de prueba son capturas de internet de **277 a
472 px de ancho para las dos caras juntas**. Un escaneo o foto de celular
real da 2.000-4.000 px. Los números de [[Resultados de precisión]] son un
piso, no un techo: el [[Código PDF417]] ni siquiera se puede decodificar a
esa resolución.
