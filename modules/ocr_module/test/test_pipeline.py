# test/test_pipeline.py
import os
from PIL import Image
import time
from datetime import datetime
from ..core.orchestrator import OCRPipeline
from ..preprocess.image_cleaner import ImageCleaner
from ..preprocess.check_inclination import SkewDetector
from ..postprocess.cleaner import TextCleaner
from ..postprocess.structure import TextStructurer
from ..config import TEST_PDF_PATH
pipeline_stages = []
def create_pipeline_pdf(stages, filename):
    os.makedirs("test_outputs", exist_ok=True)

    pages = []

    for name, img in stages:
        if not isinstance(img, Image.Image):
            img = Image.fromarray(img)

        img = img.convert("RGB")

        # opcional: agregar nombre de etapa arriba
        pages.append(img)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = f"test_outputs/{filename}{timestamp}.pdf"

    pages[0].save(
        output,
        save_all=True,
        append_images=pages[1:]
    )

    print(f"PDF del pipeline generado: {output}")

def test_complete_pipeline():
    """Test completo del pipeline OCR con preprocesamiento y postprocesamiento"""
    
    print("\n" + "="*60)
    print("TEST COMPLETO: OCR Pipeline con Pre/Postprocesamiento")
    print("="*60)
    
    # Verificar que el archivo de prueba existe
    if not os.path.exists(TEST_PDF_PATH):
        print(f"Error: Archivo de prueba no encontrado: {TEST_PDF_PATH}")
        return
    
    print(f"\n📄 Archivo de prueba: {TEST_PDF_PATH}")
    
    # 1. Test básico sin preprocesamiento
    print("\n" + "-"*60)
    print("1.  EJECUTANDO: OCR básico (SIN preprocesamiento)")
    print("-"*60)
    
    try:
        from pdf2image import convert_from_bytes
        import io

        pipeline = OCRPipeline()
        with open(TEST_PDF_PATH, "rb") as f:
            pdf_bytes = f.read()


        images = convert_from_bytes(pdf_bytes)


        cleaner = ImageCleaner()

        cleaned = cleaner.clean_image(
            images[0]
        )


        text = pipeline.ocr_engine.extract_text(
            cleaned
        )


        result = {
            "text": text
        }
        
        #print(f"OK: OCR completado en {elapsed:.2f}s")
        print(f"OK: Caracteres extraídos: {len(result['text'])}")
        print("\nMuestra de texto extraído (primeros 300 caracteres):")
        print(result['text'])
    except Exception as e:
        print(f"Error en OCR básico: {e}")
        return
    
    # 2. Test de preprocesamiento
    print("\n" + "-"*60)
    print("2 EJECUTANDO: Pruebas de preprocesamiento")
    print("-"*60)
    
    try:
        from pdf2image import convert_from_bytes
        with open(TEST_PDF_PATH, "rb") as f:
            images = convert_from_bytes(f.read())
        
        if images:
            img = images[0]
            print(f"OK: PDF convertido a {len(images)} imagen(es)")
            pipeline_stages.append(
                ("Original", img)
            )
            # Test Image Cleaner
            cleaner = ImageCleaner(resize_width=2000)
            import numpy as np
            img_array = np.array(img)
            cleaned_img = cleaner.clean_image(img)
            print(f"OK: Imagen limpiada: {cleaned_img.shape}")
            pipeline_stages.append(
                ("Limpieza", cleaned_img)
            )
            # Test Skew Detection
            skew_detector = SkewDetector()
            skew_angle = skew_detector.detect_skew(img_array)
            print(f"OK: Ángulo de inclinación detectado: {skew_angle:.2f}°")
            
            if abs(skew_angle) > 0.5:
                corrected_img, final_angle = skew_detector.auto_correct(img_array)
                print(f"OK: Imagen corregida: ángulo final {final_angle:.2f}°")
                pipeline_stages.append(
                    ("Correción inclinación", corrected_img)
                )
    except Exception as e:
        print(f"Aviso en preprocesamiento: {e}")
    
    # 3. Test de postprocesamiento
    print("\n" + "-"*60)
    print("3. EJECUTANDO: Pruebas de postprocesamiento")
    print("-"*60)
    
    try:
        raw_text = result['text']
        # Test Text Cleaner
        cleaner = TextCleaner()
        cleaned_text = cleaner.clean(raw_text)
        print(f"OK: Texto limpiado")
        print(f"  - Antes: {len(raw_text)} caracteres")
        print(f"  - Después: {len(cleaned_text)} caracteres")
        print(f"  - Reducción: {((len(raw_text)-len(cleaned_text))/len(raw_text)*100):.1f}%")
        print("Texto despues\n")
        print(cleaned_text)
        # Test Text Structurer
        structurer = TextStructurer()
        blocks = structurer.structure(cleaned_text)
        print(f"\nOK: Texto estructurado en {len(blocks)} bloques")
        
        # Contar tipos de bloques
        block_types = {}
        for block in blocks:
            block_types[block.type] = block_types.get(block.type, 0) + 1
        
        for btype, count in block_types.items():
            print(f"  - {btype}: {count}")
        
        # Test extracción de campos
        fields = structurer.extract_key_fields(cleaned_text)
        print(f"\nOK: Campos extraídos: {len(fields)}")
        for field, value in fields.items():
            if value:
                print(f"  - {field}: {value}")
    except Exception as e:
        print(f"Error en postprocesamiento: {e}")
        import traceback
        traceback.print_exc()
    #creación de pdf de etapas
    create_pipeline_pdf(
        pipeline_stages, "resultado_pipeline"
    )
    # 4. Resumen
    print("\n" + "="*60)
    print("TEST COMPLETO FINALIZADO")
    print("="*60)
    print("\nEstadísticas:")
    print(f"  - Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - Archivo procesado: {os.path.basename(TEST_PDF_PATH)}")
    #print(f"  - Tiempo total OCR: {elapsed:.2f}s")
    print(f"  - Tamaño de texto final: {len(cleaned_text)} caracteres")
    print("\n")

if __name__ == "__main__":
    test_complete_pipeline()