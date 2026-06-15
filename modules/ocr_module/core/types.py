# core/types.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class OCRResult:
    """Resultado de un proceso OCR"""
    text: str
    confidence: float
    language: str = 'spa'
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DocumentPage:
    """Página de un documento con su contenido OCR"""
    page_number: int
    image_path: Optional[str]
    raw_text: str
    cleaned_text: Optional[str] = None
    skew_angle: Optional[float] = None
    confidence: Optional[float] = None

@dataclass
class OCRPipelineResult:
    """Resultado final del pipeline OCR"""
    pages: List[DocumentPage]
    full_text: str
    total_confidence: float
    processing_time: float
    timestamp: datetime
    document_type: Optional[str] = None

    def to_dict(self):
        """Convierte el resultado a diccionario"""
        return {
            'pages_count': len(self.pages),
            'full_text': self.full_text,
            'average_confidence': self.total_confidence / len(self.pages) if self.pages else 0,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat(),
            'document_type': self.document_type,
        }

@dataclass
class PreprocessConfig:
    """Configuración de preprocesamiento"""
    resize_width: int = 1200
    blur_kernel: tuple = (5, 5)
    threshold_value: int = 127
    dilation_kernel_size: int = 3
    erosion_kernel_size: int = 3
    max_skew_angle: float = 15

@dataclass
class PostprocessConfig:
    """Configuración de postprocesamiento"""
    remove_empty_lines: bool = True
    normalize_whitespace: bool = True
    min_line_length: int = 2