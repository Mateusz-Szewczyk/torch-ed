# manual_test.py
from rag.src.file_processor import PDFProcessor

def manual_test():
    pdf_path = 'uploads/test.pdf'
    processor = PDFProcessor()

    start_page = 0
    end_page = 3  # Adjust based on your PDF's actual number of pages

    result = processor.process_pdf(pdf_path, start_page=start_page, end_page=end_page)

    if result:
        print("PDF preprocessing and text extraction completed successfully.")
        print("Extracted Text:")
        print(result)
    else:
        print("An error occurred during PDF preprocessing.")

if __name__ == "__main__":
    manual_test()
