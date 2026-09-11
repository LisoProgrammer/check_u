# Check_U — Panel de pruebas locales

Backend Flask que conecta los módulos ya existentes del repo
(`modules/ocr_module`, `modules/mrz`, `modules/check_id`) en un solo
flujo de extremo a extremo, con una interfaz web para probarlo con
documentos y cédulas reales.

## Cómo correrlo

```
.\venv\Scripts\Activate.ps1      # o el equivalente en tu entorno
pip install flask requests       # si no se instalaron ya con setup_windows.ps1
python webapp\app.py
```

Abre `http://localhost:5000`.

## Qué hace

1. Subes un **Documento** (PDF — Acta de grado o ICFES) y una **Cédula**
   (PDF o imagen).
2. Al darle a **Procesar**, cada archivo pasa por 5 etapas visibles en
   tiempo real (vía Server-Sent Events): leyendo → convirtiendo →
   procesando (preprocesamiento de imagen) → corrigiendo inclinación →
   limpiando (OCR + limpieza de texto).
3. Para el **Documento** se usa `TextStructurer.extract_key_fields()`
   (ya existente en `modules/ocr_module/postprocess/structure.py`) con
   el tipo elegido (`acta_grado` o `icfes`).
4. Para la **Cédula** se busca el MRZ (franja de 3 líneas con `<`) dentro
   del texto OCR y se parsea con `modules/mrz` (nombre, número de
   documento, fecha de nacimiento, edad calculada, sexo), validando los
   dígitos de verificación.
5. Se comparan los campos del mismo tipo entre ambos documentos (nombre,
   número de documento) con una normalización simple (mayúsculas, sin
   tildes, solo dígitos).
6. Se consulta el RUI del DNP (`modules/check_id/rui/consultar.py`) con
   el número de documento obtenido, mostrando un spinner minimalista y
   luego un check/datos o un error.
7. Cada procesamiento queda guardado en `webapp/historial.json` y
   aparece en la pestaña **Historial**.

## Decisiones que tomé (avísenme si prefieren otra cosa)

- **Colores**: investigué en vivo `utb.edu.co` (no los tenía en mi
  conocimiento) y tomé el azul `#093AD8` (usado en el nav, enlaces y
  encabezados del sitio) como color primario, el cian `#0FC5EF` como
  acento, y el naranja `#FF4B2E` para el botón principal de "Procesar"
  (la UTB lo usa así en sus propios botones de llamada a la acción).
- **Bug corregido**: `modules/check_id/rui/consultar.py` tenía una
  llamada de prueba (`print(consultar(pre_data))`) *fuera* de
  `if __name__ == "__main__":`, así que se ejecutaba apenas alguien
  importara el módulo (rompía el arranque de la app). La envolví en el
  guard `__main__`, igual que ya hacen `mrz/validate.py` y otros
  archivos del repo.
- **Año de nacimiento del MRZ**: `mrz/get_info.py` siempre antepone
  "20" al año de 2 dígitos (asume nacidos en 2000+). Si eso da una
  fecha futura, en `webapp/app.py` la interpreto como 19xx para poder
  calcular la edad. No toqué `get_info.py` — si prefieren que la
  corrección viva ahí en vez de en el webapp, lo muevo.
- **Selector de tipo de documento**: agregué un desplegable
  (Acta de grado / ICFES) en la tarjeta "Documento", ya que
  `structure.py` ya soporta ambos tipos.
- **Campos comparados**: "Nombre completo" y "Número de documento" se
  comparan entre Documento y Cédula. "Fecha de nacimiento" y "Edad"
  solo los aporta la Cédula (el Acta/ICFES no trae fecha de
  nacimiento en el repo actual), así que se muestran sin comparación.

## Limitaciones conocidas

- Los dos archivos de prueba en `modules/test_data/` (`cc_escaneada.pdf`,
  `cedula_alexander_veha_rocha.png`) parecen ser una plantilla en blanco
  (sin datos reales ni MRZ real), así que con ellos el flujo corre
  completo pero no va a "encontrar" un MRZ ni un número de documento.
  Prueben con una cédula real (foto o escaneo) para ver el resultado
  completo, incluida la consulta al RUI.
- La consulta al RUI (`ventanillasocial.dnp.gov.co`) necesita salida a
  internet normal; en mi entorno de pruebas en la nube esa salida está
  bloqueada por el proxy, así que no pude verificar una respuesta real
  del DNP — sí verifiqué que el código arma la petición correctamente y
  que los errores de red se manejan sin tumbar el flujo.
- `preprocess/image_cleaner.py` (código ya existente) escribe un PDF de
  depuración en `test_image_cleaner/` cada vez que limpia una imagen —
  no lo desactivé porque no me pidieron tocar ese comportamiento.
