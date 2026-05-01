# ocr/engine.py
from abc import ABC, abstractmethod

class OCREngine(ABC):
    @abstractmethod
    def extract_text(self, image) -> str:
        pass