from sentence_transformers import SentenceTransformer
from src.search_engine import search_and_rerank
from file_processor.pdf_processor import PDFProcessor
from src.chunking import create_chunks

def display_results(results):
    print("\nWyniki wyszukiwania i rerankingu:")
    for result in results:
        source = result.get('source', 'unknown')
        content = result.get('content', '')
        similarity_score = result.get('similarity_score', 0)
        normalized_score = result.get('normalized_score', 0)
        metadata = result.get('metadata', {})

        print(f"Źródło: {source}")
        print(f"Treść:\n{content}\n")

        if metadata:
            if 'entities' in metadata and metadata['entities']:
                print(f"Encje: {metadata['entities']}")
            if 'relations' in metadata and metadata['relations']:
                print(f"Relacje: {metadata['relations']}")
        print(f"Wynik podobieństwa: {similarity_score:.4f}")
        print(f"Wynik znormalizowany: {normalized_score:.4f}")
        print("-" * 40)


def main():
    # # Sample data setup (replace with actual data)
    pdfprocessor = PDFProcessor()
    text = pdfprocessor.process_pdf('./tests/test_files/test.pdf', start_page=7, end_page=90)
    #
    if text is None:
        print("Error: Failed to process PDF.")
        return

    user_id = 'user123'
    file_description = 'To jest książka o psychologii'
    category = 'psychologia'

    # # Chunking the text
    chunks = create_chunks(text)
    embeddings = []
    extracted_metadatas = []

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
    query = "Wytłumacz mi czym jest System 1 i System 2"
    results = search_and_rerank(query, embedding_model, user_id, n_results=5)

    # Print the results
    display_results(results)




if __name__ == '__main__':
    main()
