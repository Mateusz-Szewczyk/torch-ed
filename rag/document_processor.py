# document_processor.py

import os
import sys
import fitz  # PyMuPDF
import pix2text
from pix2text.layout_parser import ElementType

# Initialize Pix2Text
p2t = pix2text.Pix2Text.from_config(device="cuda")
language = 'pol'  # Polish language code

# Define output directories
OUTPUT_DIR = 'ocr_output_pix2text'  # Directory to store OCR outputs
LOG_DIR = 'log'  # Directory to store debug logs

# Create necessary directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Function to extract content from a single page image
def get_page_content(page_img, page_num):
    titles = []
    page_output_path = os.path.join(OUTPUT_DIR, f'page_{page_num}', 'output-md')
    os.makedirs(page_output_path, exist_ok=True)  # Ensure the directory exists

    try:
        # Perform OCR using Pix2Text
        doc = p2t.recognize_page(
            page_img,
            table_as_image=True,
            text_contain_formula=False,
            save_debug_res=LOG_DIR,
            page_numbers=[page_num]  # Process current page only
        )

        # Export OCR result to Markdown
        md_file_path = os.path.join(page_output_path, f'page_{page_num}.md')
        doc.to_markdown(md_file_path)

        # Extract titles from the OCR result
        for element in doc.elements:
            if element.type == ElementType.TITLE:
                print(f"Page {page_num} - Title: {element.text}")
                titles.append(element.text)

    except Exception as e:
        print(f"Error processing page {page_num}: {e}")

    return md_file_path, titles

# Function to process the entire PDF and extract the content
def get_pdf_content(pdf_file):
    all_titles = []

    try:
        # Open the PDF file
        doc = fitz.open(pdf_file)
        num_pages = doc.page_count
        print(f"Total pages to process: {num_pages}")

        for i in range(num_pages):  # Iterate through all pages
            try:
                page = doc.load_page(i)  # Load page by index
                pix = page.get_pixmap(dpi=300)  # Render page to an image with 300 DPI
                img_path = os.path.join(OUTPUT_DIR, f'page_{i}.png')
                pix.save(img_path)  # Save image as PNG

                # Extract content from the page image
                md_path, titles = get_page_content(img_path, i)

                if titles:
                    all_titles.extend(titles)

                # Remove the image to save space
                os.remove(img_path)

            except Exception as e:
                print(f"Error handling page {i} of {pdf_file}: {e}")
                # Continue processing other pages even if one fails

        return all_titles

    except Exception as e:
        print(f"Error opening PDF file {pdf_file}: {e}")
        return None

# Function to read text from a Markdown file
def read_text_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()

# Main function to preprocess the PDF into Markdown files
def process_pdf(pdf_file):
    # Step 1: Perform OCR and extract titles
    titles = get_pdf_content(pdf_file)
    if titles is None:
        print("Failed to process PDF content.")
        return None
    print(f"Extracted Titles: {titles}")

    # Step 2: Convert all Markdown files to text and store them for future processing
    documents = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for file in files:
            if file.endswith('.md'):
                md_path = os.path.join(root, file)
                text = read_text_file(md_path)
                documents.append(text)

    print(f"Total documents created: {len(documents)}")

    return documents

# Example usage
if __name__ == "__main__":
    # Define the path to your PDF file
    pdf_path = 'matematyks.pdf'  # Replace with your actual PDF path

    # Ensure the PDF file exists
    if not os.path.isfile(pdf_path):
        print(f"PDF file not found at {pdf_path}")
        sys.exit(1)

    # Process the PDF and generate the Markdown files
    documents = process_pdf(pdf_path)

    if documents:
        print("PDF preprocessing and Markdown file creation completed successfully.")
    else:
        print("An error occurred during PDF preprocessing.")
