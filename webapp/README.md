# Check_U — Panel de pruebas locales

Backend Flask que conecta los módulos ya existentes del repo
(`modules/ocr_module`, `modules/mrz`, `modules/check_id`) en un solo
flujo de extremo a extremo, con una interfaz web para probar el
procesamiento de una **cédula** con documentos reales.

## Cómo correrlo

```
.\venv\Scripts\Activate.ps1      # o el equivalente en tu entorno
pip install flask requests pymupdf   # si no se instalaron ya con setup_windows.ps1
python webapp\app.py
```

Abre `http://localhost:5000`.

Antes de arrancar, `app.py` corre un verificador de entorno
(`webapp/entorno.py`): revisa que Tesseract OCR esté instalado y en el
PATH (con el paquete de idioma español), que haya alguna forma de leer
PDF (PyMuPDF o poppler), y que los paquetes de Python necesarios estén
instalados. Si falta algo, el servidor **no arranca** — se imprime en
la terminal exactamente qué falta y cómo instalarlo, en vez de dejar
que el error aparezca a mitad de un procesamiento real. También se
puede correr aparte, sin levantar el servidor, para diagnosticar:

```
python webapp\entorno.py
```

El panel web también consulta esto por su cuenta (`GET /api/salud`) y
muestra un banner naranja arriba de todo si algo quedó mal configurado.

## Qué hace

1. Subes una **Cédula** (PDF o imagen).
2. Al darle a **Procesar**, el archivo pasa por 5 etapas visibles en
   tiempo real (vía Server-Sent Events), y cada casilla de la lista se
   va marcando como completada a medida que el proceso avanza (la
   barra de progreso refleja el porcentaje: 1/5, 2/5, ... 5/5):
   leyendo → convirtiendo → procesando (preprocesamiento de imagen) →
   corrigiendo inclinación → limpiando (OCR + limpieza de texto).
3. Se busca el MRZ (franja de 3 líneas con `<`) dentro del texto OCR y
   se parsea con `modules/mrz` (nombre, número de documento, fecha de
   nacimiento, edad calculada, sexo), validando los dígitos de
   verificación. Los datos extraídos se muestran en la tarjeta
   "Datos extraídos" apenas termina el proceso.
4. Se consulta el RUI del DNP (`modules/check_id/rui/consultar.py`) con
   el número de documento obtenido, mostrando un spinner minimalista y
   luego **un solo** estado final: check + datos, o un error — nunca
   los tres a la vez (ver bug corregido más abajo).
5. Cada procesamiento queda guardado en `webapp/historial.json` y
   aparece en la pestaña **Historial** (fecha, nombre, documento, edad
   y resultado del RUI).
6. Hay una fila de "próximamente" (Acta de grado, Resultado ICFES,
   Otros requisitos) reservada para cuando se agreguen esos documentos
   más adelante — de momento no hacen nada, son solo espacio reservado
   en el diseño.

## Cambios recientes (simplificación a solo-cédula)

Se quitó por completo la tarjeta de "Documento" (Acta de
grado/ICFES) y la tabla de comparación Documento↔Cédula que tenía la
primera versión, a pedido explícito: ahora el panel solo lee la
cédula y muestra sus datos extraídos directamente, con las casillas
de progreso llenándose según el porcentaje del proceso.

## Bugs corregidos (avísenme si prefieren otra cosa)

- **`modules/check_id/rui/consultar.py`**: tenía una llamada de prueba
  (`print(consultar(pre_data))`) *fuera* de `if __name__ == "__main__":`,
  así que se ejecutaba apenas alguien importara el módulo (rompía el
  arranque de la app). La envolví en el guard `__main__`, igual que ya
  hacen `mrz/validate.py` y otros archivos del repo.

- **Poppler no instalado/en el PATH (el error que reportaron:
  "Unable to get page count. Is poppler installed and in PATH?")**:
  ahora la carga de PDFs usa **PyMuPDF primero** (no depende de ningún
  binario externo) y solo intenta con poppler (`pdf2image`) como
  respaldo si PyMuPDF falla. Lo probé quitando físicamente los
  binarios de poppler del sistema y confirmé que el flujo completo
  sigue funcionando igual — así que ya no debería depender de que
  poppler esté instalado en Windows. **Importante:** para que esto
  funcione hace falta tener `pymupdf` instalado en el venv
  (`pip install pymupdf`, ya está agregado a `setup_windows.ps1`) — si
  ya habían creado el venv antes de este cambio, hay que instalarlo a
  mano una vez.

- **Bug nuevo que encontré y corregí probando este mismo cambio:**
  al cambiar a "PyMuPDF primero", la imagen llega a
  `preprocess/image_cleaner.py` sin haber pasado nunca por
  `PIL.Image.open()` (PyMuPDF entrega la imagen con
  `Image.frombytes()`), y esa función interna de Pillow no registra
  sus codecs de guardado. Como `image_cleaner.py` genera un PDF de
  depuración en cada corrida (`create_image_stage_pdf`), eso
  reventaba con `KeyError: 'JPEG'` justo en la etapa "Procesando" —
  **esto explica el "no se mueve de ahí, no realiza nada"**: con
  poppler ausente, cualquier corrida caía en PyMuPDF y luego se
  rompía silenciosamente ahí. Lo arreglé con un `PIL.Image.init()`
  explícito al arrancar `webapp/app.py`.

- **El MRZ podía "desaparecer" por el filtro de confianza del OCR:**
  `procesar_cedula` usa `min_confidence=40` para limpiar ruido del
  OCR, pero Tesseract suele calificar la franja del MRZ (una cadena
  rara de letras/dígitos/`<`) con confianza baja por palabra aunque
  lea bien los caracteres — así que el filtro podía borrar la línea
  completa *antes* de que `buscar_lineas_mrz()` la viera. Agregué una
  segunda pasada de OCR sin filtro de confianza, usada únicamente como
  respaldo para localizar el MRZ si la primera pasada no lo encuentra
  (el texto "limpio" que se muestra sigue usando el filtro normal).
  Lo verifiqué con una cédula sintética con MRZ válido generada para
  la prueba: encontró nombre, número de documento, fecha de
  nacimiento, edad y sexo correctamente, y disparó la consulta al RUI
  con el número correcto.

- **RUI mostrando los 3 estados a la vez (spinner + check + error)**:
  era un bug de CSS — `.rui-estado { display: flex; }` (en la hoja de
  estilos del autor) le ganaba en la cascada al `[hidden] { display:
  none }` por defecto del navegador, sin importar que el atributo
  `hidden` se pusiera bien por JavaScript. Se corrigió agregando
  `.rui-estado[hidden] { display: none; }` explícitamente, más un
  ajuste en `app.js` (`mostrarSoloEstadoRui`) que apaga los tres
  estados y solo prende el que corresponde. Verificado con una prueba
  automatizada (Playwright) leyendo el atributo `hidden` y el
  `display` calculado de cada uno de los tres divs, antes y después de
  la consulta: solo uno queda visible en cada momento.

- **Año de nacimiento del MRZ**: `mrz/get_info.py` siempre antepone
  "20" al año de 2 dígitos (asume nacidos en 2000+). Si eso da una
  fecha futura, en `webapp/app.py` la interpreto como 19xx para poder
  calcular la edad. No toqué `get_info.py` — si prefieren que la
  corrección viva ahí en vez de en el webapp, lo muevo.

## Cómo lo probé

Todo lo anterior se probó de extremo a extremo en un entorno de
pruebas (no en Windows, donde no tengo forma de ejecutar comandos
directamente): subiendo los dos archivos de ejemplo del repo
(`modules/test_data/cc_escaneada.pdf` y
`cedula_alexander_veha_rocha.png`, ambos plantillas en blanco sin MRZ
real, para confirmar que el flujo completa las 5 etapas y termina en
"RUI omitido" quedan sin datos), quitando físicamente los binarios de
poppler para confirmar que PyMuPDF los reemplaza sin errores, y con
una cédula sintética con un MRZ válido (generada solo para esta
prueba) para confirmar que sí se extraen nombre/documento/fecha/edad/
sexo y que se dispara la consulta al RUI con el número correcto.

## Limitaciones conocidas

- Los dos archivos de prueba en `modules/test_data/` (`cc_escaneada.pdf`,
  `cedula_alexander_veha_rocha.png`) parecen ser una plantilla en blanco
  (sin datos reales ni MRZ real), así que con ellos el flujo corre
  completo pero no va a "encontrar" un MRZ ni un número de documento.
  Prueben con una cédula real (foto o escaneo) para ver el resultado
  completo, incluida la consulta al RUI.
- La consulta al RUI (`ventanillasocial.dnp.gov.co`) necesita salida a
  internet normal; en mi entorno de pruebas esa salida está bloqueada
  por el proxy (confirmé que sí arma la petición correctamente, con el
  número de documento correcto, y que el error de red se maneja sin
  tumbar el flujo ni dejar el RUI en un estado inconsistente). Debería
  funcionar sin problema en una PC normal con internet.
- `preprocess/image_cleaner.py` (código ya existente) escribe un PDF de
  depuración en `test_image_cleaner/` cada vez que limpia una imagen —
  no lo desactivé porque no me pidieron tocar ese comportamiento.
