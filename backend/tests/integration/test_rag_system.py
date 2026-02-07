"""Integration tests for RAGSystem - Testing full query flow."""

import pytest
from unittest.mock import Mock, MagicMock
import anthropic

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from rag_system import RAGSystem
from tests.fixtures.mock_responses import (
    create_tool_use_response,
    create_text_response
)
from tests.fixtures.test_data import (
    create_sample_search_results,
    create_empty_search_results
)


class TestRAGSystemQuerySuccess:
    """Test successful query flows."""

    def test_query_content_question_success(self, mock_config):
        """Test full happy path with tool-based search."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock vector store
        rag.vector_store.search = Mock(return_value=create_sample_search_results())
        rag.vector_store.get_lesson_link = Mock(return_value="https://example.com/lesson1")

        # Mock Anthropic API with two-turn flow
        tool_use_resp = create_tool_use_response(
            tool_name="search_course_content",
            tool_input={"query": "What is Python?"}
        )
        final_resp = create_text_response("Python is a high-level programming language.")
        rag.ai_generator.client.messages.create = Mock(side_effect=[tool_use_resp, final_resp])

        # Execute
        answer, sources = rag.query("What is Python?")

        # Verify
        assert answer == "Python is a high-level programming language."
        assert len(sources) > 0  # Should have sources from search
        assert rag.ai_generator.client.messages.create.call_count == 2  # Two-turn flow

        # Verify search was called
        assert rag.vector_store.search.called

    def test_query_without_tool_use(self, mock_config):
        """Test query where AI answers without using search tool."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock direct response (no tool use)
        direct_resp = create_text_response("General programming concept answer.")
        rag.ai_generator.client.messages.create = Mock(return_value=direct_resp)

        # Execute
        answer, sources = rag.query("What is a variable?")

        # Verify
        assert answer == "General programming concept answer."
        assert len(sources) == 0  # No sources without tool use
        assert rag.ai_generator.client.messages.create.call_count == 1  # Single call

    def test_query_with_conversation_history(self, mock_config):
        """Test query with session continuity."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock responses for two queries
        resp1 = create_text_response("First answer")
        resp2 = create_text_response("Follow-up answer")
        rag.ai_generator.client.messages.create = Mock(side_effect=[resp1, resp2])

        # First query - creates session
        answer1, sources1 = rag.query("First question", session_id="test-session")
        assert answer1 == "First answer"

        # Second query - uses same session
        answer2, sources2 = rag.query("Follow-up question", session_id="test-session")
        assert answer2 == "Follow-up answer"

        # Verify history exists
        history = rag.session_manager.get_conversation_history("test-session")
        assert history is not None
        assert "First question" in history
        assert "First answer" in history


class TestRAGSystemQueryErrors:
    """Test error handling in query flow."""

    def test_query_with_search_error(self, mock_config):
        """Test handling when VectorStore returns error."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock vector store returning error
        error_results = create_empty_search_results(error_msg="Database connection failed")
        rag.vector_store.search = Mock(return_value=error_results)

        # Mock AI flow - tool use then response
        tool_use_resp = create_tool_use_response()
        final_resp = create_text_response("I encountered an error searching the database.")
        rag.ai_generator.client.messages.create = Mock(side_effect=[tool_use_resp, final_resp])

        # Execute - should handle gracefully
        answer, sources = rag.query("What is in lesson 3?")

        # Verify system handles error gracefully
        assert answer is not None
        assert isinstance(answer, str)
        # Tool should have received the error from VectorStore
        # AI should still respond (possibly about the error)

    def test_query_with_anthropic_api_error(self, mock_config):
        """
        🔴 CRITICAL TEST - Expected to FAIL
        Test that Anthropic API errors don't crash the entire query.
        """
        # Setup
        rag = RAGSystem(mock_config)

        # Mock API to raise error
        mock_request = Mock()
        api_error = anthropic.APIError("Rate limit exceeded", request=mock_request, body=None)
        rag.ai_generator.client.messages.create = Mock(side_effect=api_error)

        # Execute - should NOT crash the entire system
        answer, sources = rag.query("What is Python?")

        # Verify error is handled gracefully
        assert answer is not None
        assert isinstance(answer, str)
        # Should return error message instead of crashing
        assert "error" in answer.lower() or "unable" in answer.lower()

    def test_query_with_empty_search_results(self, mock_config):
        """Test handling when search returns no results."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock empty search results
        empty_results = create_empty_search_results(error_msg=None)
        rag.vector_store.search = Mock(return_value=empty_results)

        # Mock AI flow
        tool_use_resp = create_tool_use_response()
        final_resp = create_text_response("I couldn't find information about that topic.")
        rag.ai_generator.client.messages.create = Mock(side_effect=[tool_use_resp, final_resp])

        # Execute
        answer, sources = rag.query("Nonexistent topic")

        # Verify
        assert answer is not None
        assert len(sources) == 0  # No sources for empty results


class TestRAGSystemSessionManagement:
    """Test session and conversation history management."""

    def test_query_creates_new_session(self, mock_config):
        """Test that querying without session_id works."""
        # Setup
        rag = RAGSystem(mock_config)
        rag.ai_generator.client.messages.create = Mock(
            return_value=create_text_response("Answer")
        )

        # Execute without session_id
        answer, sources = rag.query("Question")

        # Verify - should still work
        assert answer == "Answer"

    def test_query_maintains_session_context(self, mock_config):
        """Test that session history is passed to AI generator."""
        # Setup
        rag = RAGSystem(mock_config)

        # Add some history to session
        session_id = "test-session"
        rag.session_manager.add_exchange(session_id, "Previous question", "Previous answer")

        # Mock AI response
        rag.ai_generator.client.messages.create = Mock(
            return_value=create_text_response("Context-aware answer")
        )

        # Execute query with session
        answer, sources = rag.query("Follow-up question", session_id=session_id)

        # Verify history was passed to AI generator
        call_args = rag.ai_generator.client.messages.create.call_args
        system_prompt = call_args.kwargs.get("system", "")
        assert "Previous conversation:" in system_prompt or "Previous question" in system_prompt

    def test_query_resets_sources_after_retrieval(self, mock_config):
        """Test that sources are reset after being retrieved."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock search with sources
        rag.vector_store.search = Mock(return_value=create_sample_search_results())
        rag.vector_store.get_lesson_link = Mock(return_value=None)

        # Mock AI flow
        tool_use_resp = create_tool_use_response()
        final_resp = create_text_response("Answer")
        rag.ai_generator.client.messages.create = Mock(side_effect=[tool_use_resp, final_resp])

        # First query
        answer1, sources1 = rag.query("First question")
        assert len(sources1) > 0

        # Second query - sources should be reset
        rag.ai_generator.client.messages.create = Mock(
            return_value=create_text_response("Second answer")
        )
        answer2, sources2 = rag.query("Second question")

        # If second query doesn't use tools, sources should be empty
        assert len(sources2) == 0


class TestRAGSystemToolIntegration:
    """Test integration between RAG system and tools."""

    def test_search_tool_filters_passed_correctly(self, mock_config):
        """Test that tool parameters are passed through correctly."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock vector store
        rag.vector_store.search = Mock(return_value=create_sample_search_results())

        # Mock AI requesting search with filters
        tool_use_resp = create_tool_use_response(
            tool_input={
                "query": "Variables",
                "course_name": "Python",
                "lesson_number": 2
            }
        )
        final_resp = create_text_response("Answer about variables")
        rag.ai_generator.client.messages.create = Mock(side_effect=[tool_use_resp, final_resp])

        # Execute
        answer, sources = rag.query("What about variables in lesson 2?")

        # Verify filters passed to vector store
        rag.vector_store.search.assert_called_once()
        call_args = rag.vector_store.search.call_args
        assert call_args.kwargs["query"] == "Variables"
        assert call_args.kwargs["course_name"] == "Python"
        assert call_args.kwargs["lesson_number"] == 2

    def test_outline_tool_execution(self, mock_config):
        """Test that outline tool can be used."""
        # Setup
        rag = RAGSystem(mock_config)

        # Mock vector store outline response
        mock_outline = {
            "course_title": "Introduction to Python",
            "course_link": "https://example.com/course",
            "instructor": "Jane Doe",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Getting Started", "lesson_link": None}
            ]
        }
        rag.vector_store.get_course_outline = Mock(return_value=mock_outline)

        # Mock AI requesting outline
        tool_use_resp = create_tool_use_response(
            tool_name="get_course_outline",
            tool_input={"course_title": "Python"}
        )
        final_resp = create_text_response("Here's the course outline...")
        rag.ai_generator.client.messages.create = Mock(side_effect=[tool_use_resp, final_resp])

        # Execute
        answer, sources = rag.query("What lessons are in the Python course?")

        # Verify outline tool was called
        rag.vector_store.get_course_outline.assert_called_once_with("Python")
        assert answer == "Here's the course outline..."
