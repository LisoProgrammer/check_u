import os
from ..core.orchestrator import OCRPipeline

PDF_PATH = os.path.join(os.path.dirname(__file__), "../../test_data/cc_escaneada.pdf")

def main():
    pipeline = OCRPipeline()

    with open(PDF_PATH, "rb") as f:
        result = pipeline.process(f.read())

    print("\n===== TEXTO EXTRAÍDO =====\n")
    print(result["text"])

if __name__ == "__main__":
    main()