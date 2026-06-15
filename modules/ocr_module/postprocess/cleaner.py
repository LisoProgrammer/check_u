# postprocess/cleaner.py
import re
from typing import List

class TextCleaner:
    """Limpia texto extraído por OCR eliminando ruido y normalizando"""
    
    def __init__(self, min_line_length: int = 2, remove_empty_lines: bool = True):
        self.min_line_length = min_line_length
        self.remove_empty_lines = remove_empty_lines
    
    def clean(self, text: str) -> str:
        """
        Limpia el texto completo aplicando múltiples técnicas
        
        Args:
            text: Texto sin procesar de OCR
        
        Returns:
            Texto limpiado
        """
        # Limpiar saltos de línea extra
        text = self._normalize_whitespace(text)
        
        # Limpiar caracteres inválidos
        text = self._remove_invalid_characters(text)
        
        # Limpiar espacios extra
        text = self._remove_extra_spaces(text)
        
        # Limpiar líneas cortas/vacías
        text = self._clean_empty_lines(text)
        
        # Corregir errores comunes de OCR
        text = self._fix_common_ocr_errors(text)
        
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normaliza espacios en blanco"""
        # Reemplazar múltiples saltos de línea con máximo 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Reemplazar tabs con espacios
        text = text.replace('\t', '    ')
        return text
    
    def _remove_invalid_characters(self, text: str) -> str:
        """Elimina caracteres inválidos/ruido"""
        # Eliminar caracteres de control excepto newline y tab
        text = ''.join(char for char in text if char.isprintable() or char == '\n')
        # Eliminar símbolos raros muy comunes en OCR
        text = re.sub(r'[`´¡°§¶†‡§™]', '', text)
        return text
    
    def _remove_extra_spaces(self, text: str) -> str:
        """Elimina espacios extra dentro de líneas"""
        # Múltiples espacios -> un espacio
        text = re.sub(r' {2,}', ' ', text)
        # Espacios al inicio/final de líneas
        text = '\n'.join(line.strip() for line in text.split('\n'))
        return text
    
    def _clean_empty_lines(self, text: str) -> str:
        """Limpia líneas vacías o muy cortas"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Eliminar líneas vacías si está configurado
            if self.remove_empty_lines and not line:
                continue
            
            # Eliminar líneas muy cortas
            if len(line) >= self.min_line_length:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _fix_common_ocr_errors(self, text: str) -> str:
        """Corrige errores comunes de OCR en español"""
        # Errores comunes por confusión de caracteres
        replacements = {
            r'\bl\b': 'I',  # letra 'l' minúscula -> 'I'
            r'\b0\b': 'O',  # '0' -> 'O' en palabras aisladas
            r'\b1\b': 'I',  # '1' -> 'I' en palabras aisladas
            r'rn': 'm',     # 'rn' -> 'm' (a menudo confundido)
            r'ln': 'm',     # 'ln' -> 'm'
            r'RH': 'Rh',    # Estandarizar notación de sangre
            r'DD-MM-YYYY': 'DD-MM-YYYY',  # Mantener formato de fecha
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def clean_lines(self, text: str) -> List[str]:
        """
        Limpia el texto y lo retorna como lista de líneas
        
        Args:
            text: Texto de entrada
        
        Returns:
            Lista de líneas limpias
        """
        cleaned = self.clean(text)
        return [line for line in cleaned.split('\n') if line.strip()]

def clean_ocr_text(text: str, min_line_length: int = 2) -> str:
    """Función de conveniencia para limpiar texto OCR"""
    cleaner = TextCleaner(min_line_length=min_line_length)
    return cleaner.clean(text)