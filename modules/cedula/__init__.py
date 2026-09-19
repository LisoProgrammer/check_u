"""
modules.cedula
==============

Lectura y validacion de cedulas de ciudadania colombianas, en sus dos
formatos vigentes:

- **Cedula digital** (policarbonato, desde 2020): trae MRZ de 3 lineas en
  el reverso. Es la que ya sabia leer el proyecto (modules/mrz).
- **Cedula amarilla con hologramas** (2000-2020): NO tiene MRZ. Trae un
  codigo de barras PDF417 en el reverso y una linea de produccion
  impresa debajo, ademas del texto normal del frente.

El nombre "amarilla con hologramas" es el nombre oficial que usa la
Registraduria Nacional del Estado Civil para ese formato; se usa ese
mismo nombre en todo el codigo y en la interfaz para no inventar
terminologia propia.

Este paquete NO reemplaza a modules/mrz ni a modules/ocr_module: los
usa. Lo que agrega es (1) deteccion automatica de cual de los dos
formatos es, (2) la lectura del formato amarillo, y (3) las coordenadas
de donde salio cada dato, para poder dibujarlas sobre el documento.
"""

from .lectura import leer_cedula, FORMATO_AMARILLA, FORMATO_DIGITAL, FORMATO_DESCONOCIDO
from .similitud import comparar_nombres, UMBRAL_SIMILITUD

__all__ = [
    "leer_cedula",
    "comparar_nombres",
    "FORMATO_AMARILLA",
    "FORMATO_DIGITAL",
    "FORMATO_DESCONOCIDO",
    "UMBRAL_SIMILITUD",
]
