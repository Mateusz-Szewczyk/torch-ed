import requests
from bs4 import BeautifulSoup
import time
import random


def scrape_for_urls(url: str = "https://docs.python.org/3/tutorial/index.html"):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all internal links
    links = ["https://docs.python.org/3/tutorial/" + link.get("href")
             for link in soup.find_all('a') if link.get("href") and not link.get("href").startswith('http')]

    # Removing fragments (anything after #) to avoid duplicates
    links = set([link.split('#')[0] for link in links])
    return links


def scrape_page_content(url_list):
    final_text = ''
    for url in url_list:
        try:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the specific div with class 'body' and role 'main'
            main_body = soup.find('div', class_='body', role='main')

            if main_body:
                # Remove script and style elements within the main body
                for script in main_body(["script", "style"]):
                    script.decompose()

                # Get the text content
                text = main_body.get_text(strip=True)

                # Append text to final output
                final_text += text + "\n\n"
            else:
                print(f"No main body found on page {url}")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")

        # Sleep to avoid overloading the server
        time.sleep(random.uniform(2, 5))

    return final_text


def save_to_file(entries, filename="python_docs_index.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"{entries}\n")


def main():
    print("Scraping Python documentation...")
    urls = scrape_for_urls()
    print(f"Found {len(urls)} URLs.")

    # Scrape content from the pages
    text = scrape_page_content(urls)

    # Save the content to a file
    save_to_file(text)
    print("Data saved to python_docs_index.txt")


if __name__ == "__main__":
    main()
