from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from src.metadata_extraction import extract_metadata_using_llm
from src.vector_store import create_vector_store
from src.graph_store import create_graph_entries, create_entity_relationships
from src.search_engine import search_and_rerank
from src.file_processor.pdf_processor import PDFProcessor
from src.chunking import create_chunks

def main():
    # Sample data setup (replace with actual data)
    # pdfprocessor = PDFProcessor()
    # text = pdfprocessor.process_pdf('./data/pulapki-myslenia.pdf', start_page=89, end_page=90)

    # if text is None:
    #     print("Error: Failed to process PDF.")
    #     return

    user_id = 'user123'
    # file_description = 'To jest książka o psychologii'
    # category = 'psychologia'
    #
    # # Chunking the text
    # chunks = create_chunks(text)
    # embeddings = []
    # extracted_metadatas = []

    # Initialize the embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    #
    # # Use tqdm to track progress through the chunks
    # for chunk in tqdm(chunks, desc="Processing chunks", unit="chunk"):
    #     # Generate embeddings
    #     embedding = embedding_model.encode(chunk)
    #     embeddings.append(embedding)
    #
    #     # Extract metadata using LLM
    #     metadata = extract_metadata_using_llm(chunk, category)
    #     extracted_metadatas.append(metadata)
    #
    # # Create vector store (after metadata extraction)
    # create_vector_store(chunks, embeddings, user_id, file_description, category, extracted_metadatas)
    #
    # # Create graph entries (nodes and relationships)
    # create_graph_entries(chunks, extracted_metadatas, user_id)
    # create_entity_relationships(extracted_metadatas, user_id)
    #
    # # Optional: print or log final metadata for debugging purposes
    # for chunk, metadata in zip(chunks, extracted_metadatas):
    #     print("Chunk: ", chunk)
    #     print("Metadata: ", metadata)

    # Now, use the search engine to query the data
    query = "Czym jest efekt halo?"
    results = search_and_rerank(query, embedding_model, user_id, n_results=5)

    # Print the results
    print("\nWyniki wyszukiwania i rerankingu:")
    for result in results:
        source = result.get('source', 'unknown')
        content = result.get('content', '')
        similarity_score = result.get('similarity_score', 0)
        normalized_score = result.get('normalized_score', 0)
        metadata = result.get('metadata', {})

        if source == 'vector':
            print("Z bazy wektorowej:")
            print(f"Treść dokumentu:\n{content}\n")
            print("Metadane:")
            print(f" - Kategoria: {metadata.get('category', 'N/A')}")
            print(f" - Opis: {metadata.get('description', 'N/A')}")
        elif source == 'graph_entity':
            print("Z grafu (Encja):")
            print(f"Encja: {metadata.get('type', 'N/A')}")
            print(f"Treść: {content}")
        elif source == 'graph_relation':
            print("Z grafu (Relacja):")
            print(f"Relacja: {metadata.get('relation', 'N/A')}")
            print(f"Treść: {content}")
        else:
            print("Nieznane źródło:")
            print(f"Treść: {content}")

        print(f"Wynik podobieństwa: {similarity_score:.4f}")
        print(f"Wynik znormalizowany: {normalized_score:.4f}")
        print("-" * 40)


if __name__ == '__main__':
    main()
