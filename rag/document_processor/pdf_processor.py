# pdf_processor.py

import os
import fitz  # PyMuPDF
import pix2text
from pix2text.layout_parser import ElementType


class PDFProcessor:
    def __init__(self, output_dir='../output_pdf2txt', log_dir='log', language='pol', device='cuda'):
        self.output_dir = output_dir
        self.log_dir = log_dir
        self.language = language

        # Initialize Pix2Text
        self.p2t = pix2text.Pix2Text.from_config(device=device)

        # Create necessary directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

    def process_pdf(self, pdf_file, start_page=0, end_page=None):
        """
        Process the PDF file and extract content.

        :param pdf_file: Path to the PDF file
        :param start_page: Starting page number (0-based index)
        :param end_page: Ending page number (exclusive)
        :return: List of extracted documents
        """
        all_titles = self._get_pdf_content(pdf_file, start_page, end_page)
        if all_titles is None:
            print("Failed to process PDF content.")
            return None

        print(f"Extracted Titles: {all_titles}")

        # Convert all Markdown files to text and store them
        documents = self._collect_markdown_documents()
        print(f"Total documents created: {len(documents)}")

        return documents

    def _get_pdf_content(self, pdf_file, start_page=0, end_page=None):
        all_titles = []

        try:
            doc = fitz.open(pdf_file)
            num_pages = doc.page_count
            print(f"Total pages in PDF: {num_pages}")

            start = start_page
            end = min(end_page if end_page is not None else num_pages, num_pages)

            print(f"Processing pages from {start + 1} to {end}")

            for i in range(start, end):
                try:
                    page = doc.load_page(i)
                    pix = page.get_pixmap(dpi=300)
                    img_path = os.path.join(self.output_dir, f'page_{i}.png')
                    pix.save(img_path)

                    md_path, titles = self._get_page_content(img_path, i)
                    if titles:
                        all_titles.extend(titles)

                    os.remove(img_path)

                except Exception as e:
                    print(f"Error handling page {i + 1} of {pdf_file}: {e}")

            return all_titles

        except Exception as e:
            print(f"Error opening PDF file {pdf_file}: {e}")
            return None

    def _get_page_content(self, page_img, page_num):
        titles = []
        page_output_path = os.path.join(self.output_dir, f'page_{page_num}', 'output-md')
        os.makedirs(page_output_path, exist_ok=True)

        try:
            doc = self.p2t.recognize_page(
                page_img,
                table_as_image=True,
                text_contain_formula=False,
                save_debug_res=self.log_dir,
                page_numbers=[page_num]
            )

            md_file_path = os.path.join(page_output_path, f'page_{page_num}.md')
            doc.to_markdown(md_file_path)

            for element in doc.elements:
                if element.type == ElementType.TITLE:
                    print(f"Page {page_num + 1} - Title: {element.text}")
                    titles.append(element.text)

        except Exception as e:
            print(f"Error processing page {page_num + 1}: {e}")

        return md_file_path, titles

    def _collect_markdown_documents(self):
        documents = []
        for root, dirs, files in os.walk(self.output_dir):
            for file in files:
                if file.endswith('.md'):
                    md_path = os.path.join(root, file)
                    text = self._read_text_file(md_path)
                    documents.append(text)
        return documents

    @staticmethod
    def _read_text_file(filename):
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()


# Example usage
if __name__ == "__main__":
    pdf_path = 'matematyks.pdf'
    processor = PDFProcessor()

    desired_start_page = 74
    desired_end_page = 115

    documents = processor.process_pdf(pdf_path, start_page=desired_start_page, end_page=desired_end_page)

    if documents:
        print("PDF preprocessing and Markdown file creation completed successfully.")
    else:
        print("An error occurred during PDF preprocessing.")