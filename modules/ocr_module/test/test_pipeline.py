# test/test_pipeline.py

import os
import time
from datetime import datetime
from PIL import Image

from ..core.orchestrator import OCRPipeline
from ..config import TEST_PDF_PATH


pipeline_stages = []


def create_pipeline_pdf(stages, filename):

    os.makedirs(
        "test_outputs",
        exist_ok=True
    )


    pages = []


    for name, img in stages:

        if not isinstance(img, Image.Image):
            img = Image.fromarray(img)


        img = img.convert("RGB")


        pages.append(img)



    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    output = (
        f"test_outputs/{filename}_{timestamp}.pdf"
    )


    pages[0].save(
        output,
        save_all=True,
        append_images=pages[1:]
    )


    print(
        f"PDF del pipeline generado: {output}"
    )




def test_complete_pipeline():


    print("\n" + "="*60)
    print(
        "TEST COMPLETO: OCR Pipeline"
    )
    print("="*60)



    if not os.path.exists(TEST_PDF_PATH):

        print(
            f"No existe: {TEST_PDF_PATH}"
        )

        return



    print(
        f"\n📄 Archivo: {TEST_PDF_PATH}"
    )



    try:

        pipeline = OCRPipeline()



        with open(TEST_PDF_PATH, "rb") as f:

            pdf_bytes = f.read()



        start = time.time()


        result = pipeline.process(
            pdf_bytes
        )


        elapsed = time.time() - start



        print("\n" + "-"*60)
        print("RESULTADO OCR")
        print("-"*60)



        print(
            f"Tiempo: {elapsed:.2f}s"
        )


        print(
            f"Caracteres: {len(result['text'])}"
        )



        print("\nTexto extraído:\n")

        print(
            result["text"][:1000]
        )



        print("\n" + "-"*60)
        print("CAMPOS EXTRAÍDOS")
        print("-"*60)



        if result["fields"]:

            for key, value in result["fields"].items():

                print(
                    f"{key}: {value}"
                )

        else:

            print(
                "No se encontraron campos"
            )




        print("\n" + "-"*60)
        print("ESTRUCTURA")
        print("-"*60)



        print(
            f"Bloques: {len(result['blocks'])}"
        )



        for block in result["blocks"]:

            print(
                f"- {block.type}"
            )



        # -------------------------
        # PDF DE ETAPAS
        # -------------------------


        for index, img in enumerate(result["images"]):

            pipeline_stages.append(
                (
                    f"pagina_{index+1}",
                    img
                )
            )



        create_pipeline_pdf(
            pipeline_stages,
            "resultado_pipeline"
        )



    except Exception as e:

        print(
            f"Error: {e}"
        )

        import traceback

        traceback.print_exc()




if __name__ == "__main__":

    test_complete_pipeline()