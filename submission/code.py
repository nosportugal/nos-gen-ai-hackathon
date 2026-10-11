import pymupdf

def extrair_texto():
    caminho_pdf = "../raw_data/document_to_anonymize.pdf"

    documento = pymupdf.open(caminho_pdf)
    texto_completo = ""

    for pagina in documento:
        texto_completo += pagina.get_text()

    documento.close()
    return texto_completo