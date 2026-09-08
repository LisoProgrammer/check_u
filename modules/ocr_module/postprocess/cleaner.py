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
        remove_empty_lines: bool = True,
        KNOWN_SHORT_TOKENS: list = []
    ):
        self.min_line_length = min_line_length
        self.remove_empty_lines = remove_empty_lines
        self.KNOWN_SHORT_TOKENS = ["NIT", "N.I.T","TI", "T.I", "T.I.", "DI", "D.I", "D.I.", "CC", "C.C.", "C.C","NO", "PEI"]

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

            # Eliminar líneas formadas exclusivamente por símbolos no permitidos
            if self._looks_like_mrz(line):
                cleaned_lines.append(line)
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)
    def _looks_like_mrz(self, line: str) -> bool:
        """
        Detecta líneas que podrían pertenecer a una MRZ.
        No valida la MRZ; solamente evita eliminarlas como ruido.
        """

        line = line.strip()

        if not line:
            return False

        # Caracteres permitidos típicos de MRZ
        if not re.fullmatch(r"[A-Z0-9<]+", line):
            return False

        # Una MRZ normalmente es considerablemente larga
        if len(line) < 15:
            return False

        # Presencia del separador MRZ
        if "<" in line:
            return True

        # Línea larga con combinación de letras y números
        has_letters = bool(re.search(r"[A-Z]", line))
        has_numbers = bool(re.search(r"[0-9]", line))

        return has_letters and has_numbers and len(line) >= 20
    def _is_noise_line(self, line: str) -> bool:
        # Solo símbolos → ruido
        if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", line):
            return True

        letters_only = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", line)

        if not letters_only:
            return True

        # Línea muy corta sin ser una sigla conocida (Nit., D.I., etc.)
        if len(letters_only) <= 3 and letters_only.upper() not in self.KNOWN_SHORT_TOKENS:
            return True

        # Sin ninguna vocal y teniendo en cuenta el ratio → casi seguro basura ("SN", "MS", "ZAS")
        vowels = re.findall(r"[aeiouáéíóúAEIOUÁÉÍÓÚ]", letters_only)
        if len(vowels) / len(letters_only) < 0.15 and len(letters_only) < 8:
            return True

        # Palabra "aislada" corta en mayúsculas sin contexto de espacio
        words = line.split()
        if len(words) == 1 and len(line) <= 4 and line.isupper():
            return True

        return False

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