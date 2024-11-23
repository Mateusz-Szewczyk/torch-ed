# pdf_processor.py
import fitz
import pix2text
import PyPDF2
import logging

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, language='pol', device='cpu'):
        """
        Initializes the PDFProcessor with specified configurations.

        Args:
            language (str, optional): Language code for OCR. Defaults to 'pol' (Polish).
            device (str, optional): Device to run OCR on (e.g., 'cuda' for GPU, 'cpu').
                Defaults to 'cpu'.
        """

        self.language = language

        # Initialize Pix2Text with CPU device
        self.p2t = pix2text.Pix2Text.from_config(device=device)

    def process_pdf(self, pdf_file, start_page=0, end_page=None):
        """
           Processes a PDF file and extracts its content into a single text file.

           The method determines the type of PDF (text-based, image-based, or mixed) and
           applies the appropriate extraction strategy. The extracted text is returned as a string.

           Args:
               pdf_file (str): Path to the PDF file to be processed.
               start_page (int, optional): Starting page number (0-based index) for extraction.
                   Defaults to 0.
               end_page (int, optional): Ending page number (exclusive) for extraction.
                   Defaults to None, which processes up to the last page.

           Returns:
               str or None: Extracted text upon successful extraction,
                   or None if extraction fails.
        """
        # Ensure start_page is an integer
        if start_page is None:
            start_page = 0
        if end_page is not None and not isinstance(end_page, int):
            end_page = None

        pdf_type = self._determine_pdf_type(pdf_file)

        try:
            if pdf_type == "text_based":
                text = self._pdf_to_text(pdf_file, start_page, end_page)
            elif pdf_type == "image_based":
                print("PDF is image-based. Skipping processing as per user request.")
                return None
            elif pdf_type == "mixed_content":
                # Process only the text content, skip images
                text = self._extract_text_directly_from_range(pdf_file, start_page, end_page)
            else:
                print("Cannot process PDF content. Unsupported or empty PDF.")
                return None

            if text:
                return text
            else:
                print("No text extracted from the PDF.")
                return None
        except Exception as e:
            print(f"Error processing PDF file {pdf_file}: {e}")
            return None

    def _pdf_to_text(self, pdf_path, start_page=0, end_page=None):
        """
        Extract text directly from a text-based PDF.

        :param pdf_path: Path to the PDF file
        :param start_page: Starting page number (0-based index)
        :param end_page: Ending page number (exclusive)
        :return: Extracted text as a string
        """
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)

                # Set default values for start_page and end_page if not provided
                start_page = max(0, min(start_page, total_pages - 1))
                end_page = min(end_page if end_page is not None else total_pages, total_pages)

                print(f"Extracting text from pages {start_page + 1} to {end_page} out of {total_pages}")

                text = ''
                for page_num in range(start_page, end_page):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += f"Page {page_num + 1}:\n{page_text}\n\n"
                    else:
                        print(f"No text found on page {page_num + 1}")
                return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None

    def _extract_text_directly_from_range(self, pdf_file, start_page=0, end_page=None):
        """
        Extract text directly from a range of pages in a PDF, skipping images.

        :param pdf_file: Path to the PDF file
        :param start_page: Starting page number (0-based index)
        :param end_page: Ending page number (exclusive)
        :return: Extracted text as a string
        """
        all_text = []
        try:
            with fitz.open(pdf_file) as doc:
                num_pages = doc.page_count
                start = max(0, start_page)
                end = min(end_page if end_page is not None else num_pages, num_pages)

                print(f"Extracting text from pages {start + 1} to {end} out of {num_pages}")

                for i in range(start, end):
                    try:
                        page = doc.load_page(i)
                        text = page.get_text()
                        if text and text.strip():
                            all_text.append(f"Page {i + 1}:\n{text}\n\n")
                        else:
                            print(f"No text found on page {i + 1}")
                    except Exception as e:
                        logger.error(f"Error extracting text from page {i + 1}: {e}", exc_info=True)

            return ''.join(all_text)
        except Exception as e:
            logger.error(f"Error opening PDF file {pdf_file}: {e}", exc_info=True)
            return None

    def _analyze_pdf_content(self, pdf_path, sample_size=5):
        """
        Analyzes a PDF to determine if it contains extractable text or if it's primarily image-based.

        :param pdf_path: Path to the PDF file
        :param sample_size: Number of pages to sample (default is 5)
        :return: A tuple (has_text, has_images, total_pages)
        """
        has_text = False
        has_images = False

        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                # Determine how many pages to check
                pages_to_check = min(sample_size, total_pages)

                for i in range(pages_to_check):
                    page = pdf_reader.pages[i]

                    # Check for text
                    if not has_text:
                        text = page.extract_text()
                        if text and text.strip():
                            has_text = True

                    # Check for images
                    if not has_images and '/XObject' in page['/Resources']:
                        x_object = page['/Resources']['/XObject'].get_object()
                        if x_object:
                            for obj in x_object:
                                if x_object[obj]['/Subtype'] == '/Image':
                                    has_images = True
                                    break

                    # If we've found both text and images, we can stop checking
                    if has_text and has_images:
                        break
        except Exception as e:
            print(f"Error analyzing PDF content: {e}")
            return False, False, 0

        return has_text, has_images, total_pages

    def _determine_pdf_type(self, pdf_path):
        """
        Determines the type of PDF based on its content.

        :param pdf_path: Path to the PDF file
        :return: A string describing the PDF type
        """
        print(pdf_path)
        has_text, has_images, total_pages = self._analyze_pdf_content(pdf_path)

        if has_text and not has_images:
            return "text_based"
        elif has_images and not has_text:
            return "image_based"
        elif has_text and has_images:
            return "mixed_content"
        else:
            return False

# Example usage
if __name__ == "__main__":
    pdf_path = '../matematyks.pdf'
    processor = PDFProcessor()

    desired_start_page = 74  # 0-based index (i.e., page 75)
    desired_end_page = 79    # Exclusive (i.e., up to page 79)

    result = processor.process_pdf(pdf_path, start_page=desired_start_page, end_page=desired_end_page)

    if result:
        print("PDF preprocessing and text extraction completed successfully.")
        print(result)  # Print the extracted text
    else:
        print("An error occurred during PDF preprocessing.")
