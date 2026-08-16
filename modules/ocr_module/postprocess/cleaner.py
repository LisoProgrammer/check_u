# postprocess/cleaner.py

import re
from typing import List


class TextCleaner:
    """
    Limpia y normaliza texto producido por OCR.

    IMPORTANTE:
    Este módulo NO intenta corregir nombres, números de documento
    ni datos personales. Su objetivo es eliminar ruido estructural
    sin modificar información potencialmente importante.
    """

    def __init__(
        self,
        min_line_length: int = 2,
        remove_empty_lines: bool = True
    ):
        self.min_line_length = min_line_length
        self.remove_empty_lines = remove_empty_lines

    def clean(self, text: str) -> str:
        """
        Limpia el texto OCR conservando la mayor cantidad posible
        de información original.
        """

        if not text:
            return ""

        # 1. Normalizar saltos de línea y caracteres de control
        text = self._normalize_whitespace(text)

        # 2. Eliminar caracteres de control / basura
        text = self._remove_invalid_characters(text)

        # 3. Normalizar espacios
        text = self._remove_extra_spaces(text)

        # 4. Limpiar líneas
        text = self._clean_empty_lines(text)

        # 5. Normalizar algunos patrones OCR seguros
        text = self._normalize_ocr_patterns(text)

        return text.strip()

    # ---------------------------------------------------------
    # WHITESPACE
    # ---------------------------------------------------------

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normaliza saltos de línea, tabs y espacios.
        """

        # Normalizar diferentes tipos de salto de línea
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Tabs -> espacio
        text = text.replace("\t", " ")

        # Espacios no separables
        text = text.replace("\u00A0", " ")

        # Eliminar espacios al final de las líneas
        text = re.sub(r"[ \t]+\n", "\n", text)

        # Máximo dos saltos de línea consecutivos
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

    # ---------------------------------------------------------
    # INVALID CHARACTERS
    # ---------------------------------------------------------

    def _remove_invalid_characters(self, text: str) -> str:
        """
        Elimina caracteres de control y algunos símbolos de ruido.

        No elimina letras, números ni puntuación normal.
        """

        cleaned = []

        for char in text:

            # Conservar saltos de línea
            if char == "\n":
                cleaned.append(char)
                continue

            # Eliminar caracteres de control
            if ord(char) < 32:
                continue

            # Conservar caracteres imprimibles
            if char.isprintable():
                cleaned.append(char)

        text = "".join(cleaned)

        # Símbolos que suelen aparecer como ruido visual del OCR
        text = re.sub(
            r"[`´¡°§¶†‡™]",
            "",
            text
        )

        return text

    # ---------------------------------------------------------
    # SPACES
    # ---------------------------------------------------------

    def _remove_extra_spaces(self, text: str) -> str:
        """
        Reduce espacios innecesarios sin modificar el contenido.
        """

        # Múltiples espacios -> uno
        text = re.sub(r"[ ]{2,}", " ", text)

        # Espacios alrededor de saltos de línea
        lines = []

        for line in text.split("\n"):
            line = line.strip()
            lines.append(line)

        return "\n".join(lines)

    # ---------------------------------------------------------
    # LINES
    # ---------------------------------------------------------

    def _clean_empty_lines(self, text: str) -> str:
        """
        Elimina líneas vacías y líneas compuestas únicamente por ruido.
        """

        lines = text.split("\n")

        cleaned_lines = []

        for line in lines:

            line = line.strip()

            # Línea vacía
            if not line:
                if not self.remove_empty_lines:
                    cleaned_lines.append("")
                continue

            # Línea demasiado corta
            if len(line) < self.min_line_length:
                continue

            # Eliminar líneas formadas exclusivamente por símbolos
            if self._is_noise_line(line):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _is_noise_line(self, line: str) -> bool:
        """
        Determina si una línea parece estar compuesta únicamente
        por ruido OCR.
        """

        # Si contiene letras o números, NO eliminar
        if re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]", line):
            return False

        # Si solamente contiene símbolos, probablemente es ruido
        return True

    # ---------------------------------------------------------
    # OCR PATTERNS
    # ---------------------------------------------------------

    def _normalize_ocr_patterns(self, text: str) -> str:
        """
        Normalizaciones seguras.

        IMPORTANTE:
        No se realizan correcciones lingüísticas automáticas porque
        podrían modificar nombres o números.
        """

        # Normalizar guiones Unicode
        text = text.replace("–", "-")
        text = text.replace("—", "-")
        text = text.replace("−", "-")

        # Normalizar comillas
        text = text.replace("“", '"')
        text = text.replace("”", '"')
        text = text.replace("‘", "'")
        text = text.replace("’", "'")

        # Normalizar espacios alrededor de algunos separadores
        text = re.sub(r"\s*:\s*", ": ", text)

        return text

    # ---------------------------------------------------------
    # LINES API
    # ---------------------------------------------------------

    def clean_lines(self, text: str) -> List[str]:
        """
        Limpia el texto y devuelve una lista de líneas.
        """

        cleaned = self.clean(text)

        return [
            line
            for line in cleaned.split("\n")
            if line.strip()
        ]


def clean_ocr_text(
    text: str,
    min_line_length: int = 2
) -> str:
    """
    Función de conveniencia.
    """

    cleaner = TextCleaner(
        min_line_length=min_line_length
    )

    return cleaner.clean(text)