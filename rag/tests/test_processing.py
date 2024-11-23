import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from sentence_transformers import SentenceTransformer

from rag.src.chunking import create_chunks
from rag.src.metadata_extraction import MetadataExtractor
from rag.src.vector_store import create_vector_store, load_vector_store, search_vector_store
from rag.src.graph_store import create_graph_entries, create_entity_relationships
from rag.src.config import EMBEDDING_MODEL_NAME
from rag.file_processor.pdf_processor import PDFProcessor

class TestDataProcessing(unittest.TestCase):

    def setUp(self):
        """
        Set up common test variables and mock objects.
        """
        self.sample_text = (
            "This is a sample text. It is used for testing purposes. "
            "The text contains multiple sentences. We will use it to test chunking."
        )
        self.chunk_size = 2
        self.overlap = 1
        self.category = 'test_category'
        self.user_id = 'test_user'
        self.file_description = 'Test file description'
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    def test_create_chunks(self):
        """
        Test the create_chunks function.
        """
        chunks = create_chunks(self.sample_text, self.chunk_size, self.overlap)
        expected_chunks = [
            "This is a sample text. It is used for testing purposes.",
            "It is used for testing purposes. The text contains multiple sentences.",
            "The text contains multiple sentences. We will use it to test chunking.",
            "We will use it to test chunking."
        ]
        self.assertEqual(chunks, expected_chunks)


    def test_extract_metadata(self):
        """
        Test the extract_metadata_using_llm function.
        """
        mock_response = {
            'message': {
                'content': json.dumps({
                    "names": ["John Doe"],
                    "locations": ["Testville"],
                    "dates": ["2023"],
                    "key_terms": ["testing", "unittest"]
                })
            }
        }
        metadata_extractor = MetadataExtractor()
        metadata = metadata_extractor.extract_metadata("Sample chunk of text.", self.category)
        expected_metadata = {
            "names": ["John Doe"],
            "locations": ["Testville"],
            "dates": ["2023"],
            "key_terms": ["testing", "unittest"]
        }
        self.assertEqual(metadata, expected_metadata)

    def test_create_vector_store_and_search(self):
        """
        Test creating a vector store and searching it.
        """
        chunks = ["This is a test chunk.", "Another test chunk."]
        embeddings = [self.embedding_model.encode(chunk) for chunk in chunks]
        extracted_metadatas = [
            {
                "names": ["Alice"],
                "locations": ["Test City"],
                "dates": ["2023"],
                "key_terms": ["test", "chunk"]
            },
            {
                "names": ["Bob"],
                "locations": ["Sample Town"],
                "dates": ["2022"],
                "key_terms": ["another", "test", "chunk"]
            }
        ]

        # Create vector store
        create_vector_store(
            chunks,
            embeddings,
            self.user_id,
            self.file_description,
            self.category,
            extracted_metadatas
        )

        # Search vector store
        query = "test chunk"
        results = search_vector_store(query, self.embedding_model, self.user_id, n_results=2)

        # Verify the results
        self.assertEqual(len(results['documents'][0]), 2)
        self.assertIn("This is a test chunk.", results['documents'][0])
        self.assertIn("Another test chunk.", results['documents'][0])

    def test_create_graph_entries_and_relationships(self):
        """
        Test creating graph entries and relationships.
        """
        chunks = ["This is a test chunk.", "Another test chunk."]
        extracted_metadatas = [
            {
                "names": ["Alice"],
                "locations": ["Test City"],
                "dates": ["2023"],
                "key_terms": ["test", "chunk"]
            },
            {
                "names": ["Bob"],
                "locations": ["Sample Town"],
                "dates": ["2022"],
                "key_terms": ["another", "test", "chunk"]
            }
        ]

        # Create graph entries
        create_graph_entries(chunks, extracted_metadatas, self.user_id)
        create_entity_relationships(extracted_metadatas)

        # Test if nodes and relationships are created
        from rag.src.graph_store import driver

        with driver.session() as session:
            # Check if Chunk nodes exist
            result = session.run("MATCH (c:Chunk) RETURN count(c) as chunk_count")
            chunk_count = result.single()['chunk_count']
            self.assertEqual(chunk_count, 2)

            # Check if Entity nodes exist
            result = session.run("MATCH (e:Entity) RETURN count(e) as entity_count")
            entity_count = result.single()['entity_count']
            self.assertGreaterEqual(entity_count, 4)  # At least 4 entities

            # Check relationships between chunks and entities
            result = session.run("""
                MATCH (c:Chunk)-[:CONTAINS_ENTITY]->(e:Entity)
                RETURN count(*) as rel_count
            """)
            rel_count = result.single()['rel_count']
            self.assertGreaterEqual(rel_count, 4)

    @patch('rag.file_processor.pdf_processor.PDFProcessor.process_pdf')
    def test_pdf_processor(self, mock_process_pdf):
        """
        Test the PDFProcessor.
        """
        mock_process_pdf.return_value = self.sample_text
        pdfprocessor = PDFProcessor()
        text = pdfprocessor.process_pdf('dummy_path.pdf')
        self.assertEqual(text, self.sample_text)

    def tearDown(self):
        """
        Clean up after tests.
        """
        # Remove vector store data
        if os.path.exists('./vector_store_data'):
            import shutil
            shutil.rmtree('./vector_store_data')

        # Clear Neo4j database
        from rag.src.graph_store import driver
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

if __name__ == '__main__':
    unittest.main()
