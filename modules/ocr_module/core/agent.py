# core/agent.py

import json
import requests


class DocumentAgent:

    def __init__(self, model="gemma3:1b"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"

    def extract(self, text: str, document_type: str) -> dict:

        prompt = self._build_prompt(text, document_type)

        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0
                }
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        return json.loads(result["response"])

    def _build_prompt(self, text: str, document_type: str) -> str:

        return f"""
Eres un sistema automático de extracción de información documental.

NO eres un asistente conversacional.
NO debes explicar.
NO debes conversar.
NO debes responder preguntas.
NO debes agregar información que no esté en el texto.

Tu única tarea es:

TEXTO OCR → INFORMACIÓN ESTRUCTURADA

TIPO DE DOCUMENTO:
{document_type}


========================
REGLAS PRINCIPALES
========================

1. UTILIZA EXCLUSIVAMENTE EL TEXTO OCR.

2. NO utilices conocimiento externo.

3. NO completes información faltante.

4. NO inventes información.

5. Si un campo no puede determinarse con suficiente evidencia,
   devuelve null.

6. Cada valor devuelto debe poder justificarse mediante una parte
   concreta del texto OCR.

7. NO corrijas nombres utilizando conocimiento externo.

8. NO confundas información perteneciente a distintas personas,
   instituciones o secciones del documento.

9. Las palabras del OCR pueden contener errores. Puedes interpretar
   errores evidentes de OCR solamente cuando el texto proporciona
   suficiente evidencia para hacerlo.

10. Si existen varias posibles respuestas para un campo y no puedes
    determinar cuál es correcta, devuelve null.


========================
REGLA DE EVIDENCIA
========================

Antes de extraer cada campo, busca primero su evidencia en el texto.

Si no encuentras evidencia suficiente:

campo = null

Nunca hagas esto:

OCR:
"JUAN PEREZ"

Resultado:
"Juan Carlos Pérez"

Eso está PROHIBIDO.

Nunca agregues palabras que no tengan respaldo en el OCR.


========================
NOMBRE COMPLETO
========================

El nombre completo debe corresponder a la persona principal
del documento.

Da prioridad a nombres asociados con expresiones como:

- Identificado
- Identificada
- Identificado(A)
- C.C.
- D.I.
- Documento de identidad
- Titular
- Graduado
- Graduada
- Se identifica
- Quien

En documentos académicos, si aparece:

"JUAN PEREZ GOMEZ
Identificado con D.I. No. 123456789"

el nombre es:

"JUAN PEREZ GOMEZ"

NO incluyas en el nombre:

- nombre de la institución
- título académico
- dirección
- ciudad
- texto del encabezado
- cargos
- nombres de funcionarios
- nombres de rectores
- nombres de secretarios
- texto perteneciente a otra persona


========================
NÚMERO DE DOCUMENTO
========================

El número de documento debe estar asociado directamente con una
expresión de identificación.

Ejemplos válidos:

"C.C. No. 123456789"
"D.I. No. 123456789"
"Identificado con C.C. 123456789"
"Identificada con D.I. 123456789"
"Documento de identidad 123456789"

NO utilices números aislados.

NO confundas el documento con:

- fechas
- números de actas
- números de resolución
- códigos DANE
- números NIT
- teléfonos
- códigos de barras
- códigos internos
- números de registro


========================
ERRORES DE OCR EN DOCUMENTOS
========================

El OCR puede confundir caracteres.

Ejemplo:

"D.I. No. I.043.645,839"

puede representar:

"1043645839"

Cuando el número está claramente asociado a D.I. o C.C.,
puedes eliminar separadores de formato como:

.
,
espacios

pero NO puedes:

- agregar dígitos
- eliminar dígitos reales
- cambiar arbitrariamente un dígito
- inventar números

Si la interpretación no es suficientemente clara:

numero_documento = null


========================
INSTITUCIÓN EDUCATIVA
========================

Solo extrae una institución educativa si su nombre aparece realmente
en el OCR.

Ejemplos:

"Institución Educativa San Francisco de Asís"
→ "San Francisco de Asís"

"Universidad Tecnológica de Bolívar"
→ "Universidad Tecnológica de Bolívar"

"Colegio San José"
→ "Colegio San José"

Pero:

"Institución Educativa"
→ null

"Universidad"
→ null

"Colegio"
→ null

Las expresiones genéricas no son nombres de instituciones.

NO inventes una institución.

NO utilices una institución conocida por el modelo.

NO supongas que una institución pertenece al documento.

Si aparecen varias instituciones, selecciona únicamente la que
corresponda al tipo de documento y a su contexto.

Si no puede determinarse:

institucion_educativa = null


========================
REGLA ESPECIAL PARA ACTAS DE GRADO
========================

En un acta de grado, normalmente interesa:

- institución educativa
- nombre completo del graduado
- número de documento del graduado

El nombre del graduado debe estar relacionado con expresiones como:

"Identificado..."
"Identificada..."
"con D.I..."
"con C.C..."
"quien cumplió..."
"confirió el título..."

NO confundas al graduado con:

- rector
- secretaria
- secretario
- funcionarios
- profesores
- representantes
- nombres que aparecen en firmas


========================
REGLA ESPECIAL PARA CÉDULAS
========================

En una cédula, el nombre completo corresponde al titular del documento.

El número de documento corresponde al número de identificación
principal de la cédula.

No utilices códigos inferiores, números de registro o códigos OCR.


========================
SALIDA
========================

Devuelve ÚNICAMENTE un objeto JSON.

No escribas:

- explicaciones
- comentarios
- markdown
- texto antes del JSON
- texto después del JSON

Los campos que no puedan determinarse deben tener valor null.

CAMPOS A EXTRAER:

{self._get_fields(document_type)}


========================
TEXTO OCR
========================

{text}
"""

    def _get_fields(self, document_type: str) -> str:

        fields = {

            "cedula": """
{
    "nombre_completo": null,
    "numero_documento": null,
    "fecha_nacimiento": null,
    "lugar_nacimiento": null,
    "fecha_expedicion": null
}
""",

            "acta_grado": """
{
    "institucion_educativa": null,
    "nombre_completo": null,
    "numero_documento": null
}
""",

            "icfes": """
{
    "institucion_educativa": null,
    "nombre_completo": null,
    "numero_documento": null
}
"""
        }

        return fields.get(
            document_type,
            """
{
    "nombre_completo": null,
    "numero_documento": null
}
"""
        )