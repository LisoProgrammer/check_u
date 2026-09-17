---
tags: [checku, pruebas]
---

# Metodología de pruebas

Tres niveles, cada uno buscando una clase distinta de error.

## 1. Precisión de extracción

`modules/cedula/test_precision.py`

Los archivos de prueba se llaman `<numero>_<APELLIDOS>_<NOMBRES>.pdf`, así
que **el nombre del archivo es la respuesta correcta** y la precisión se
mide sola, sin revisar a mano.

```
python -m modules.cedula.test_precision test_samples/Cedulas_Amarillas_Hologramas
```

Sale una tabla por documento y el porcentaje global. Resultados en
[[Resultados de precisión]].

## 2. Lógica de validación, con un RUI simulado

El [[RUI - Ventanilla Social DNP|RUI]] está bloqueado por el proxy en el
entorno de desarrollo, así que todo terminaría en `por_revisar` y los
caminos `valida` / `inconsistente` no se probarían nunca.

Se reemplaza `consultar_rui` por una función que devuelve un nombre
controlado y se verifican los siete casos de la tabla en
[[ADR-004 Umbral de similitud 85]].

## 3. Panel completo, en un navegador real

Playwright, headless, **24 comprobaciones**:

- Carga inicial y título
- Subida de la cédula digital: pestaña inmediata, procesamiento, imagen de
  fondo, recuadros, formato reconocido, líneas, número correcto
- Subida de la amarilla: **el aviso de cambio de formato aparece durante
  el proceso y desaparece al terminar**
- Pestaña de comparación: pantalla dividida, tabla, campos en rojo, líneas
- Modo oscuro: el atributo cambia **y el color de fondo cambia de verdad**
- Historial: lista casos, reabrir uno recupera documentos y recuadros
- Persistencia: tras recargar sigue abierto el mismo caso
- Responsive: **sin desborde horizontal a 420 px**
- **Cero errores de JavaScript en consola**

## 4. Verificación geométrica de los recuadros

Aparte, se comprueba que la posición del recuadro en pantalla coincide con
la coordenada que calculó el backend:

```
campo                    x navegador  x backend  y navegador  y backend
N° documento                  0.6685     0.6685       0.1530     0.1530  OK
Nombre completo               0.4785     0.4785       0.1661     0.1661  OK
Fecha de nacimiento · Sexo    0.3105     0.3105       0.6596     0.6596  OK
```

Esta prueba es la que encontró el tercer bug de [[Bugs encontrados]].

## Por qué vale la pena el nivel 3 y 4

Los tres bugs de CSS que se encontraron eran **invisibles**: la página se
veía bien en una captura. Uno tapaba todos los clics con una capa
transparente, otro desbordaba solo en móvil, y el tercero dibujaba los
recuadros 37 % más arriba del dato. Ninguno se habría visto revisando el
código ni mirando una captura de pantalla.
