import pymupdf  # PyMuPDF

# Caminho relativo a partir da pasta submission/
caminho_pdf = "../raw_data/document_to_anonymize.pdf"

# Abrir e extrair o texto
documento = pymupdf.open(caminho_pdf)
texto_completo = ""

for pagina in documento:
    texto_completo += pagina.get_text()

# Imprimir os primeiros caracteres apenas para confirmar no terminal que a extração funcionou
print(texto_completo[:500])