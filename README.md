# Dependencias del sistema (Linux / WSL)

Primero, instala las dependencias necesarias a nivel de sistema (raíz del proyecto):

sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils python3.12-venv


# Configuración del entorno virtual

Crea y activa un entorno virtual para aislar las dependencias del proyecto:

python3 -m venv venv
source venv/bin/activate

Instala las librerías de Python necesarias:

pip install pdf2image pytesseract pillow opencv-python


# Prueba del módulo OCR

Ejecuta el módulo de prueba con el siguiente comando:

python -m modules.ocr_module.test.test_ocr


Resultado de OCR (sin preprocesamiento)

===== TEXTO EXTRAÍDO =====

FECHA DE NACIMIENTO DD-MM-YYYY $

CIUDAD

(DEPARTAMENTO) S

LUGAR DE NACIMIENTO S
XX G.S. RH SEXO a

ESTATURA G.S. RH SEXO

DD-MM-YYYY CIUDAD
FECHA Y LUGAR DE EXPEDICION

III IOIIOO000 0000 OOOO AAA AAAAAIACOOA OAK


# Explicación

El módulo de OCR se ejecuta dentro de un entorno virtual con el fin de aislar dependencias y garantizar consistencia en el entorno de desarrollo.

El resultado mostrado corresponde a una ejecución sin aplicar técnicas de preprocesamiento de imagen, lo cual explica la presencia de ruido y errores en el texto extraído. Para mejorar la calidad del reconocimiento, es necesario incorporar etapas de limpieza y transformación de la imagen antes de aplicar OCR.