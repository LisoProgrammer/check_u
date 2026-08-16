# test/test_agent.py

from ..core.agent import DocumentAgent


def test_agent():

    ocr = """
Vastitución Sducativa
By Oda Sfrancisco de Ask
Arroz Barato Carrera 3 No. 8-71
Cartagena de Indias, Bolivar
Dane: 213001007231 Nit. No 806011890-1
Acta individual de Graduación
En la ciudad de Cartagena, a los 03 días del mes diciembre del año 2021 se llevó
a cabo el acto de graduación presidido por la suscrita rectora y secretario en el
cual la institución educativa san francisco de asís confirió el título de: Sachiller Cécnico en.
- Odistemas y
o e A: ZAPATA PATERNINA LISANDRO ENAIQUE
Identificado(A) con D.1. No. 1.043.645,839 de Cartagena - Bol
Wi
(Es
ia
No
Quien cumplió con los requisitos académicos y las exigencias establecidos en los 6
1 pl
reglamentos y norimas vigentes, correspondiente al nivel de educación media
técnica de acuerdo al proyecto educativo institucional -P.E.1,
7 ZAS
SN
MS
A!
Esta institución reconocida oficialmente por la secretaría de educación y cultura
del distrito de Cartagena según resolución No.1448 del 11 de marzo del2013 E
Es fiel copia tomada del Acta ge
    """

    agent = DocumentAgent()

    result = agent.extract(
        ocr,
        "acta_grado"
    )

    print("\nResultado del agente:")
    print(result)


if __name__ == "__main__":
    test_agent()