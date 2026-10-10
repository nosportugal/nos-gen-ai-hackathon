import fitz
     

#You can modify the filename below with any PDF path you upload
pdf_path = "raw_data/document_to_anonymize.pdf"
     

# Define a function to extract all text from a PDF file. It reads every page and returns the combined text.

def extract_text_from_pdf(path: str) -> str:
    """
      Extracts text content from all pages of a PDF file.

      Parameters:
          path (str): The file path to the PDF document.

      Returns:
          str: The extracted text from the entire PDF.
    """
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text
     
raw_text = extract_text_from_pdf(pdf_path)

print(raw_text)
     
