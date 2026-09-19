---
tags: [checku, pruebas, bugs]
---

# Bugs encontrados y corregidos

Los tres primeros los encontró la prueba automatizada del navegador, no la
revisión del código. Ninguno se veía en una captura de pantalla.

## 1. `[hidden]` anulado por el `display` del CSS

**Síntoma**: no se podía hacer clic en ninguna pestaña. Playwright:
"`<div hidden id="soltar-aqui">` intercepts pointer events".

**Causa**: cualquier regla propia con `display` (flex, grid) le gana en la
cascada al `[hidden] { display: none }` que trae el navegador. La capa de
"soltar aquí" estaba `hidden` pero seguía ocupando toda la pantalla,
invisible, tapando todos los clics. Y los avisos se mostraban vacíos.

**Arreglo**:
```css
[hidden] { display: none !important; }
```

> **Este proyecto ya había caído en el mismo error antes**, con los tres
> estados del RUI que se mostraban a la vez. Vale la pena recordarlo.

## 2. Desborde horizontal en móvil

**Síntoma**: a 420 px de ancho la página se desplazaba 62 px hacia los
lados.

**Causa**: los hijos de un grid traen `min-width: auto`, así que **no
encogen por debajo de su contenido**. Un nombre largo o el detalle de la
validación empujaban la página entera.

**Arreglo**: `min-width: 0` en los items del grid y
`grid-template-columns: minmax(0, 1fr)` en vez de `1fr`.

## 3. Recuadros dibujados 37 % más arriba del dato

**Síntoma**: los recuadros no caían sobre el texto que señalaban. Medido:
el navegador ponía el recuadro en y=0.096 donde el backend decía y=0.153.

**Causa**: `.visor-paginas` es un flex en columna con alto limitado, así
que sus hijos **se encogen** (`flex-shrink: 1` por defecto). La imagen
conservaba su alto real pero el contenedor quedaba más bajo, y como los
recuadros se posicionan en porcentaje del contenedor, terminaban arriba.

**Arreglo**: `.visor-pagina { flex: none; }`

Verificado después: coordenadas del navegador idénticas a las del backend
hasta el cuarto decimal.

## 4. Casos vacíos llenando el historial

**Síntoma**: cada vez que se abría el panel aparecía un caso más
"(sin identificar) · 0 documentos".

**Causa**: al iniciar se creaba un caso en el servidor aunque no se subiera
nada.

**Arreglo**: el caso se crea recién cuando entra el primer documento, y el
historial no lista casos sin documentos.

## 5. Etiquetas de recuadros encimadas

**Síntoma**: sobre la franja [[MRZ]] se leía "Sexo de nacimiento" —dos
etiquetas pisándose.

**Causa**: los cuatro campos que salen del MRZ comparten exactamente la
misma región, así que se dibujaban cuatro recuadros idénticos.

**Arreglo**: se agrupan en uno solo con la etiqueta combinada ("Fecha de
nacimiento · Sexo"), y cada campo tira su propia línea hacia él. Además,
para la [[Cédula digital]] se prefiere la caja del texto impreso del frente
cuando dice lo mismo que el MRZ: señalar una franja de código no le dice
nada a quien revisa.

## Bugs de sesiones anteriores, para no repetirlos

- **Tesseract "desaparecía" del PATH** entre `setup_windows.ps1` y
  `run_webapp.ps1`. Causa doble: winget no registra el PATH permanente, y
  reactivar el venv reseteaba el PATH del proceso. Se arregló escribiendo
  el PATH de Usuario y, de paso, **fusionando los dos scripts en uno**
- **`KeyError: 'JPEG'`** al procesar: `Image.frombytes()` (que usa PyMuPDF)
  no registra los plugins de Pillow, a diferencia de `Image.open()`. Hace
  falta un `Image.init()` explícito
- **El MRZ desaparecía por el filtro de confianza**: Tesseract califica la
  franja con confianza baja aunque lea bien. Hay una pasada dedicada sin
  filtro
- **Ruido de 2 letras pegado al nombre** ("HECTOR MANUEL **TA** CABARCAS"):
  un fragmento de "ESTATURA". Se subió el mínimo a 3 letras
