# ocr/__init__.py
from .engine import OCREngine
from .tesseract_engine import TesseractEngine

__all__ = ['OCREngine', 'TesseractEngine']