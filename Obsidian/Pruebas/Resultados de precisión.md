---
tags: [checku, pruebas, resultados]
---

# Resultados de precisión

Medido el 17/09/2026 con las 14 muestras reales.

## Cédulas amarillas con hologramas (11 muestras)

| Métrica | Antes | Después |
|---|---|---|
| Número de documento correcto | 4/11 (36 %) | **7/11 (64 %)** |
| Nombre con ≥85 % de similitud | 1/11 (9 %) | **6/11 (55 %)** |

Detalle por documento:

| Documento | Número | Nombre |
|---|---|---|
| 1100687349 ROMERO PARRA JUAN DIEGO | ✅ | 100 % |
| 1104698087 RODRIGUEZ SANCHEZ HUMBERTO | ✅ | ❌ |
| 17282271 URREGO CORTES CARLOS | ✅ | 79 % |
| 40048750 RIAÑO HIGUERA VICKY LILIANA | ✅ | 100 % |
| 63323985 LEON DIAZ ROSA DELIA | ✅ | 100 % |
| 72055079 BARRERA PEREZ ROY JAVIER | ✅ | 100 % |
| 91529559 GARCIA LEON CARLOS HUMBERTO | ✅ | 96 % |
| 17282259 LONDOÑO PANTOJA JOSE ELIAS | ❌ (17202259) | 94 % |
| 1022436889 BARBA ARIZA CRISTOPHER | ❌ | ❌ |
| 13848975 JOYA PARRA LUIS FERNANDO | ❌ (13040975) | ❌ |
| 14445931 ALONSO LOPEZ EDUARDO | ❌ | 67 % |

## Cédulas digitales (3 muestras)

| Documento | Número | Nombre |
|---|---|---|
| Juan David Ramos Olmos | ✅ 1128051329 | correcto |
| Héctor Manuel Cabarcas Cuadrado | ✅ 1043643394 | **completo** (antes truncado a "MANU") |
| Jorge Morales Blanco | ✅ 1043964337 | correcto |

**3/3 números correctos.**

## Lectura honesta de estos números

Un 64 % suena bajo, y lo es — pero hay que mirar con qué material:

- Las 11 amarillas son **capturas de internet de 277 a 472 px de ancho
  para las DOS caras juntas**. Una de ellas trae hasta la marca de agua de
  un anuncio
- Un escaneo o foto de celular real da 2.000-4.000 px
- El [[Código PDF417]] —la fuente más confiable, con corrección de
  errores— **no decodifica en ninguna** por falta de resolución. Se
  comprobó explícitamente
- Los errores que quedan son de tipo OCR puro: `17202259` por `17282259`
  (un 8 leído como 0), `GRACIA` por `GARCIA`. No son fallas de lógica

Con muestras de resolución real deberían subir bastante, y el PDF417
pasaría a resolver el número sin depender del OCR. Conseguir 2-3
escaneos reales está en [[Pendientes y próximos pasos]].

## Velocidad

~5,5 segundos por documento de una página, de punta a punta (carga,
preparación, dos pasadas de OCR, PDF417, extracción y consulta al RUI).
