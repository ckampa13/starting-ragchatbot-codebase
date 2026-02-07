"""Unit tests for VectorStore - Baseline validation of error handling."""

import pytest
from unittest.mock import Mock, MagicMock, patch

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from vector_store import VectorStore, SearchResults
from models import Course, Lesson


class TestVectorStoreErrorHandling:
    """Test VectorStore error handling - should ALL PASS (good error handling)."""

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_search_with_chromadb_exception(self, mock_transformer, mock_chromadb):
        """Test that ChromaDB exceptions are caught and returned in SearchResults."""
        # Setup
        mock_client = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client

        # Mock collection that raises exception
        mock_collection = Mock()
        mock_collection.query.side_effect = Exception("ChromaDB connection error")
        mock_client.get_or_create_collection.return_value = mock_collection

        # Create store
        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        # Execute search - should NOT raise exception
        results = store.search(query="test query")

        # Verify error returned in SearchResults
        assert isinstance(results, SearchResults)
        assert results.error is not None
        assert "error" in results.error.lower()
        assert results.is_empty()

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_get_lesson_link_course_not_found(self, mock_transformer, mock_chromadb):
        """Test that get_lesson_link handles missing course gracefully."""
        # Setup
        mock_client = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Create store
        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        # Execute with course that doesn't exist
        result = store.get_lesson_link("Nonexistent Course", 1)

        # Verify returns None gracefully
        assert result is None


class TestSearchResults:
    """Test SearchResults helper class."""

    def test_search_results_is_empty_with_no_documents(self):
        """Test is_empty returns True when no documents."""
        results = SearchResults(documents=[], metadata=[], distances=[], error=None)
        assert results.is_empty()

    def test_search_results_is_empty_with_documents(self):
        """Test is_empty returns False when documents exist."""
        results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1],
            error=None
        )
        assert not results.is_empty()

    def test_search_results_empty_factory(self):
        """Test SearchResults.empty factory method."""
        results = SearchResults.empty("Test error message")
        assert results.is_empty()
        assert results.error == "Test error message"

    def test_search_results_with_documents(self):
        """Test SearchResults with actual documents."""
        results = SearchResults(
            documents=["First chunk", "Second chunk"],
            metadata=[
                {"course_title": "Course", "lesson_number": 1},
                {"course_title": "Course", "lesson_number": 1}
            ],
            distances=[0.1, 0.2],
            error=None
        )

        assert results.documents == ["First chunk", "Second chunk"]
        assert len(results.metadata) == 2

    def test_search_results_with_error(self):
        """Test SearchResults with error."""
        results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database error"
        )

        assert results.is_empty()
        assert results.error == "Database error"
