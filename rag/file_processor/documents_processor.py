# document_processor.py

"""
Document Processor Module
=========================

This module provides the `DocumentProcessor` class, which facilitates the extraction of text content
from various document file formats, including `.doc`, `.docx`, `.odt`, and `.rtf`. The extracted
content is consolidated into a single `.txt` file.

Dependencies:
- pypandoc
- odfpy
- striprtf

Installation:
--------------
1. Install Python packages:
    pip install pypandoc odfpy striprtf

    PyPandoc will handle the installation of Pandoc automatically if it's not already installed.

Example Usage:
--------------
if __name__ == "__main__":
    doc_path = 'sample_document.docx'
    output_text = 'extracted_document.txt'
    processor = DocumentProcessor()

    result = processor.process_document(doc_path, output_text)

    if result:
        print(f"Text successfully extracted to {result}")
    else:
        print("Failed to extract text from the document.")
"""

import os
from typing import Optional

import pypandoc
from striprtf.striprtf import rtf_to_text
from odf.opendocument import load
from odf.text import P
from odf import teletype

# TODO Jak z doc zrobic txt???

class DocumentProcessor:
    '''
    A class to process various document file formats and extract their textual content.

    The `DocumentProcessor` supports the following formats:
        - Microsoft Word Documents (.doc, .docx)
        - OpenDocument Text (.odt)
        - Rich Text Format (.rtf)

    The extracted text from these documents can be consolidated into a single `.txt` file.
    '''

    def __init__(self, output_dir: str = '../output_doc2txt'):
        '''
        Initializes the DocumentProcessor with specified configurations.

        Args:
            output_dir (str, optional): Directory to store temporary and output files.
                Defaults to '../output_doc2txt'.
        '''
        self.output_dir = output_dir

        # Create necessary directories
        os.makedirs(self.output_dir, exist_ok=True)

        # Ensure Pandoc is installed
        self._ensure_pandoc_installed()

    def _ensure_pandoc_installed(self):
        '''
        Ensures that Pandoc is installed. If not, downloads and installs it.
        '''
        try:
            version = pypandoc.get_pandoc_version()
            print(f"Pandoc is already installed. Version: {version}")
        except (OSError, RuntimeError):
            print("Pandoc not found. Downloading Pandoc...")
            pypandoc.download_pandoc()
            print("Pandoc downloaded and installed successfully.")

    def process_document(self, doc_file: str, output_text_file: str) -> Optional[str]:
        '''
        Processes a document file and extracts its content into a single text file.

        Supports `.doc`, `.docx`, `.odt`, and `.rtf` formats.

        Args:
            doc_file (str): Path to the document file to be processed.
            output_text_file (str): Path where the extracted text will be saved.

        Returns:
            str or None: Path to the output text file upon successful extraction,
                or None if extraction fails.
        '''
        if not os.path.isfile(doc_file):
            print(f"File not found: {doc_file}")
            return None

        file_extension = os.path.splitext(doc_file)[1].lower()
        print(f"Processing file: {doc_file} with extension {file_extension}")

        try:
            if file_extension in ['.docx', '.doc']:
                text_content = self._extract_doc_pandoc(doc_file, file_extension)
            elif file_extension == '.odt':
                text_content = self._extract_odt(doc_file)
            elif file_extension == '.rtf':
                text_content = self._extract_rtf(doc_file)
            else:
                print(f"Unsupported file format: {file_extension}")
                return None

            if text_content:
                with open(output_text_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                print(f"Extracted text written to {output_text_file}")
                return output_text_file
            else:
                print("No text extracted from the document.")
                return None

        except Exception as e:
            print(f"Error processing document {doc_file}: {e}")
            return None

    def _extract_doc_pandoc(self, doc_path: str, file_extension: str) -> Optional[str]:
        '''
        Extracts text from a `.doc` or `.docx` file using PyPandoc.

        Args:
            doc_path (str): Path to the `.doc` or `.docx` file.
            file_extension (str): File extension to specify the input format.

        Returns:
            str or None: Extracted text as a single string, or None if extraction fails.
        '''
        try:
            # Determine input format based on file extension
            if file_extension == '.docx':
                input_format = 'docx'
            elif file_extension == '.doc':
                input_format = 'doc'
            else:
                print(f"Unsupported file extension for PyPandoc: {file_extension}")
                return None

            # Convert to plain text using PyPandoc
            output = pypandoc.convert_file(doc_path, 'plain', format=input_format)
            print(f"Successfully extracted text from {doc_path} using PyPandoc.")
            return output
        except Exception as e:
            print(f"Error extracting {file_extension} file {doc_path} with PyPandoc: {e}")
            return None

    def _extract_odt(self, odt_path: str) -> Optional[str]:
        '''
        Extracts text from an `.odt` file.

        Args:
            odt_path (str): Path to the `.odt` file.

        Returns:
            str or None: Extracted text as a single string, or None if extraction fails.
        '''
        try:
            doc = load(odt_path)
            all_paragraphs = doc.getElementsByType(P)
            full_text = []
            for para in all_paragraphs:
                text_content = teletype.extractText(para)
                full_text.append(text_content)
            print(f"Successfully extracted text from {odt_path} using odfpy.")
            return '\n'.join(full_text)
        except Exception as e:
            print(f"Error extracting .odt file {odt_path}: {e}")
            return None

    def _extract_rtf(self, rtf_path: str) -> Optional[str]:
        '''
        Extracts text from an `.rtf` file.

        Args:
            rtf_path (str): Path to the `.rtf` file.

        Returns:
            str or None: Extracted text as a single string, or None if extraction fails.
        '''
        try:
            with open(rtf_path, 'r', encoding='utf-8') as file:
                rtf_content = file.read()
            text_content = rtf_to_text(rtf_content)
            print(f"Successfully extracted text from {rtf_path} using striprtf.")
            return text_content
        except Exception as e:
            print(f"Error extracting .rtf file {rtf_path}: {e}")
            return None


# Example usage
if __name__ == "__main__":
    '''
    Example usage of the DocumentProcessor class.

    This script processes a specified document file, extracts its content, and writes the
    extracted text to an output `.txt` file. It demonstrates how to initialize the processor
    and invoke the `process_document` method.
    '''
    # Specify the path to the input document
    doc_path = 'lorem_ipsum.doc'  # Replace with your document file
    # Specify the path for the output text file
    output_text = 'extracted_document_li.txt'

    # Initialize the processor
    processor = DocumentProcessor()

    # Process the document and extract text
    result = processor.process_document(doc_path, output_text)

    if result:
        print(f"Text successfully extracted to {result}")
    else:
        print("Failed to extract text from the document.")