import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TextBlock:
    """Bloque de texto estructurado"""
    
    type: str
    content: str
    confidence: float = 1.0
    metadata: Dict = None


    def __post_init__(self):

        if self.metadata is None:
            self.metadata = {}

class TextStructurer:
    """
    Convierte texto OCR en información estructurada
    dependiendo del tipo de documento
    """

    def __init__(self):

        self.heading_patterns = [
            r'^[A-Z][A-Z\s]{2,}$',
            r'^#{1,6}\s'
        ]

    # -------------------------------------------------
    # ESTRUCTURA GENERAL DE TEXTO
    # -------------------------------------------------

    def structure(self, text: str) -> List[TextBlock]:

        blocks = []

        lines = text.split("\n")

        current = []


        for line in lines:


            if not line.strip():

                if current:

                    blocks.append(
                        self._create_block(current)
                    )

                    current = []


            elif self._is_heading(line):

                if current:

                    blocks.append(
                        self._create_block(current)
                    )

                    current = []


                blocks.append(
                    TextBlock(
                        type="heading",
                        content=line.strip()
                    )
                )


            else:

                current.append(line)



        if current:

            blocks.append(
                self._create_block(current)
            )


        return blocks




    def _create_block(self, lines):

        content = " ".join(
            x.strip()
            for x in lines
            if x.strip()
        )


        return TextBlock(
            type="paragraph",
            content=content
        )




    def _is_heading(self,line):

        return any(
            re.match(
                pattern,
                line.strip()
            )
            for pattern in self.heading_patterns
        )



    # -------------------------------------------------
    # EXTRACTOR DE DOCUMENTOS
    # -------------------------------------------------


    def extract_key_fields(
        self,
        text: str,
        document_type: str
    ) -> Dict:


        if document_type == "acta_grado":

            return self._extract_acta_grado(text)



        elif document_type == "icfes":

            return self._extract_icfes(text)


 
        return {

            "document_type": "unknown",

            "fields": {}

        }





    # -------------------------------------------------
    # ACTA DE GRADO
    # -------------------------------------------------


    def _extract_acta_grado(self,text):


        return {


            "document_type": "acta_grado",


            "fields": {


                "institucion_educativa":
                    self._extract_institution(text),


                "nombre_completo":
                    self._extract_name(text),


                "numero_documento":
                    self._extract_document(text)

            }

        }





    # -------------------------------------------------
    # ICFES
    # -------------------------------------------------


    def _extract_icfes(self,text):


        return {


            "document_type": "icfes",


            "fields": {


                "institucion_educativa":
                    self._extract_institution(text),


                "nombre_completo":
                    self._extract_name(text),


                "numero_documento":
                    self._extract_document(text),


                "puntaje_global":
                    self._extract_score(text)

            }

        }





    # -------------------------------------------------
    # EXTRACTORES GENERALES
    # -------------------------------------------------


    def _extract_document(self,text):


        match = re.search(

            r'(?:D\.?I\.?|DOCUMENTO|IDENTIFICADO).*?(\d{6,12})',

            text,

            re.IGNORECASE

        )


        return (
            match.group(1)
            if match
            else None
        )




    def _extract_name(self,text):


        lines = text.split("\n")


        for line in lines:


            clean = line.strip()


            if len(clean.split()) >= 3:


                if clean.isupper():

                    return clean



        return None




    def _extract_institution(self,text):


        match = re.search(

            r'(?:INSTITUCIÓN|INSTITUCION|COLEGIO).*',

            text,

            re.IGNORECASE

        )


        if match:

            return match.group(0).strip()



        return None





    def _extract_score(self,text):


        match = re.search(

            r'(?:puntaje|global).*?(\d{2,3})',

            text,

            re.IGNORECASE

        )


        return (

            match.group(1)

            if match

            else None

        )





# funciones existentes para no romper imports

def structure_text(text):

    structurer = TextStructurer()

    return structurer.structure(text)



def extract_fields(text, document_type):

    structurer = TextStructurer()

    return structurer.extract_key_fields(
        text,
        document_type
    )