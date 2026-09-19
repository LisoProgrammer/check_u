---
tags: [checku, arquitectura, frontend]
---

# Interfaz del panel

`webapp/templates/index.html` + `static/app.js` + `static/style.css`.
Sin frameworks: JavaScript plano.

## Flujo de trabajo

1. Se **suelta** un documento en cualquier parte de la ventana
2. Se abre su **pestaña** en la barra carrusel y empieza a procesarse sola
   (no hay botón "Procesar")
3. El documento se muestra **de fondo**, con **recuadros** sobre la región
   de donde salió cada dato y **líneas** que los unen con el panel de datos
4. Al soltar un segundo documento, se procesa al instante y al terminar
   aparece la pestaña **Comparación**: pantalla dividida, con líneas entre
   los datos equivalentes y el porcentaje encima

## Piezas

- **Carrusel de pestañas**: una por documento, más la de comparación. Cada
  una con un punto de color según su estado
- **Visor**: la imagen de la página con los recuadros posicionados en
  porcentaje (así funcionan a cualquier tamaño de pantalla)
- **Capa de líneas**: un SVG encima de todo, sin capturar clics, que se
  redibuja al cambiar el tamaño o al desplazar el visor
- **Panel de datos**: cada campo con su valor, su fuente y su recuadro
  asociado. Pasar el mouse resalta el dato y su recuadro a la vez
- **Aviso de formato**: burbuja flotante mientras procesa, se va al terminar
- **Cajón de historial**: lista de casos retomables, se abre con un botón

## Diseño

Glassmorphism minimalista sobre la paleta que ya tenía el proyecto:

```css
--azul: #093AD8;   --cian: #0FC5EF;
--naranja: #FF4B2E; --azul-oscuro: #011629; --morado: #3B0DC1;
```

El cristal necesita dos cosas para verse como cristal: algo de color
detrás que difuminar (las "manchas" del fondo) y un borde claro de 1 px.

**Tema**: sigue el del sistema por defecto. El botón impone claro u oscuro
y la elección se recuerda. Los colores se redefinen en tres lugares
(`:root`, `prefers-color-scheme`, `[data-tema]`) para que el botón pueda
imponerse en ambos sentidos.

## Agrupación de recuadros

Varios campos pueden salir de la misma región —en la cédula digital todo
lo que viene del [[MRZ]] sale de esa única franja—. Dibujar cuatro
recuadros idénticos encimados solo hace que sus etiquetas se pisen, así
que se agrupan en uno con la etiqueta combinada ("Fecha de nacimiento ·
Sexo") y cada campo tira su propia línea hacia él.

## Tres bugs de CSS que costaron caro

Ver [[Bugs encontrados]]. Los tres eran invisibles al ojo y aparecieron en
las pruebas automatizadas.
