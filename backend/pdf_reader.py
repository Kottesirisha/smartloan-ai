try:
    import pymupdf as fitz
except ImportError:
    import fitz


def extract_text_from_pdf(file_path: str) -> str:
    document = fitz.open(file_path)

    extracted_text = []

    for page in document:
        extracted_text.append(page.get_text())

    document.close()

    return "\n".join(extracted_text)
