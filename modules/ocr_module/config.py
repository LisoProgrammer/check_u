# config.py
import os
from pathlib import Path

# Directorio raíz del módulo
MODULE_ROOT = Path(__file__).parent

# Parámetros de Tesseract
TESSERACT_CONFIG = {
    'lang': 'spa',  # Idioma: español
    'psm': 3,       # PSM 3: Automatic page segmentation with OCR
}

# Parámetros de preprocesamiento
PREPROCESS_CONFIG = {
    'resize_width': 1200,  # Ancho de redimensionamiento
    'blur_kernel': (5, 5),  # Kernel para desenfoque gaussiano
    'threshold_value': 127,  # Valor para binarización
    'dilation_kernel_size': 3,
    'erosion_kernel_size': 3,
    'max_skew_angle': 15,  # Ángulo máximo de inclinación en grados
}

# Parámetros de postprocesamiento
POSTPROCESS_CONFIG = {
    'remove_empty_lines': True,
    'normalize_whitespace': True,
    'min_line_length': 2,  # Líneas más cortas se descartan
}

# Rutas de prueba
TEST_DATA_DIR = MODULE_ROOT.parent / 'test_data'
TEST_PDF_PATH = TEST_DATA_DIR / 'cc3_escaneada.pdf'
TEST_IMAGE_PATH = TEST_DATA_DIR / 'images.png'

# Logging
LOG_LEVEL = 'INFO'