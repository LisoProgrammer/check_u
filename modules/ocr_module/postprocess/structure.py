# postprocess/structure.py
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class TextBlock:
    """Bloque de texto estructurado"""
    type: str  # 'paragraph', 'heading', 'list_item', 'table_row'
    content: str
    confidence: float = 1.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class TextStructurer:
    """Estructura el texto OCR en bloques lógicos"""
    
    def __init__(self):
        self.heading_patterns = [
            r'^[A-Z][A-Z\s]{2,}$',  # Todo mayúsculas
            r'^#{1,6}\s',  # Markdown style
        ]
        self.list_patterns = [
            r'^[\s]*[-•*]\s',  # Bullet points
            r'^[\s]*\d{1,2}[.)]\s',  # Numbered lists
        ]
    
    def structure(self, text: str) -> List[TextBlock]:
        """
        Estructura el texto en bloques lógicos
        
        Args:
            text: Texto limpiado
        
        Returns:
            Lista de TextBlock estructurados
        """
        blocks = []
        lines = text.split('\n')
        current_paragraph = []
        
        for line in lines:
            if not line.strip():
                # Línea vacía -> guardar párrafo actual
                if current_paragraph:
                    blocks.append(self._create_block(current_paragraph))
                    current_paragraph = []
            elif self._is_heading(line):
                # Guardar párrafo anterior
                if current_paragraph:
                    blocks.append(self._create_block(current_paragraph))
                    current_paragraph = []
                # Crear bloque de encabezado
                blocks.append(TextBlock(type='heading', content=line.strip()))
            elif self._is_list_item(line):
                # Guardar párrafo anterior
                if current_paragraph:
                    blocks.append(self._create_block(current_paragraph))
                    current_paragraph = []
                # Crear bloque de lista
                blocks.append(TextBlock(type='list_item', content=line.strip()))
            else:
                # Agregar a párrafo actual
                current_paragraph.append(line)
        
        # Guardar párrafo final
        if current_paragraph:
            blocks.append(self._create_block(current_paragraph))
        
        return blocks
    
    def _is_heading(self, line: str) -> bool:
        """Detecta si la línea es un encabezado"""
        line = line.strip()
        for pattern in self.heading_patterns:
            if re.match(pattern, line):
                return True
        return False
    
    def _is_list_item(self, line: str) -> bool:
        """Detecta si la línea es un elemento de lista"""
        for pattern in self.list_patterns:
            if re.match(pattern, line):
                return True
        return False
    
    def _create_block(self, lines: List[str]) -> TextBlock:
        """Crea un bloque de párrafo de múltiples líneas"""
        content = ' '.join(line.strip() for line in lines if line.strip())
        return TextBlock(type='paragraph', content=content)
    
    def extract_key_fields(self, text: str) -> Dict[str, Optional[str]]:
        """
        Intenta extraer campos clave de un documento (ej: cédula)
        
        Args:
            text: Texto extraído
        
        Returns:
            Diccionario con campos detectados
        """
        fields = {
            'fecha_nacimiento': self._extract_date(text),
            'lugar_nacimiento': self._extract_location(text),
            'sexo': self._extract_sex(text),
            'grupo_sangre': self._extract_blood_type(text),
            'fecha_expedicion': self._extract_date(text, position='expedicion'),
        }
        
        return {k: v for k, v in fields.items() if v}
    
    def _extract_date(self, text: str, position: str = 'nacimiento') -> Optional[str]:
        """Extrae fechas en formato DD-MM-YYYY"""
        pattern = r'\d{1,2}-\d{1,2}-\d{4}'
        matches = re.findall(pattern, text)
        return matches[0] if matches else None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extrae lugar de nacimiento"""
        pattern = r'LUGAR DE NACIMIENTO\s*(?:S)?\s*([A-Z\s]+?)(?=\n|SEXO)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_sex(self, text: str) -> Optional[str]:
        """Extrae sexo"""
        if re.search(r'\bSEXO.*?[MF]\b', text, re.IGNORECASE):
            if re.search(r'\bM\b', text):
                return 'M'
            elif re.search(r'\bF\b', text):
                return 'F'
        return None
    
    def _extract_blood_type(self, text: str) -> Optional[str]:
        """Extrae tipo de sangre"""
        pattern = r'(?:G\.?S\.?|GRUPO)\s*([ABO+-]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).upper() if match else None

def structure_text(text: str) -> List[TextBlock]:
    """Función de conveniencia para estructurar texto"""
    structurer = TextStructurer()
    return structurer.structure(text)

def extract_fields(text: str) -> Dict[str, Optional[str]]:
    """Función de conveniencia para extraer campos"""
    structurer = TextStructurer()
    return structurer.extract_key_fields(text)