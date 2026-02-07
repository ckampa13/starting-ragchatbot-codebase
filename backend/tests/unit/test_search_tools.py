"""Unit tests for CourseSearchTool - Baseline validation of error handling."""

import pytest
from unittest.mock import Mock

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults
from tests.fixtures.test_data import create_sample_search_results, create_empty_search_results


class TestCourseSearchToolSuccess:
    """Test successful search operations."""

    def test_execute_successful_search(self, mock_vector_store, sample_search_results):
        """Test happy path with valid search results."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        result = tool.execute(query="What is Python?")

        # Verify
        assert result is not None
        assert isinstance(result, str)
        assert "[Introduction to Python" in result  # Should have course header
        assert "Lesson" in result  # Should have lesson markers
        assert len(tool.last_sources) > 0  # Should track sources

        # Verify search was called with correct params
        mock_vector_store.search.assert_called_once_with(
            query="What is Python?",
            course_name=None,
            lesson_number=None
        )

    def test_execute_with_filters(self, mock_vector_store, sample_search_results):
        """Test that course_name and lesson_number filters are passed correctly."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        # Execute with filters
        result = tool.execute(
            query="Variables",
            course_name="Python",
            lesson_number=2
        )

        # Verify filters passed to search
        mock_vector_store.search.assert_called_once_with(
            query="Variables",
            course_name="Python",
            lesson_number=2
        )

    def test_format_results_with_lesson_links(self, mock_vector_store, sample_search_results):
        """Test that lesson links are tracked in sources."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Execute
        result = tool.execute(query="test")

        # Verify sources contain links
        assert len(tool.last_sources) > 0
        for source in tool.last_sources:
            assert "text" in source
            assert "link" in source
            # At least one source should have a link
            if source["link"]:
                assert source["link"] == "https://example.com/lesson1"


class TestCourseSearchToolEmptyResults:
    """Test handling of empty search results."""

    def test_execute_empty_results(self, mock_vector_store):
        """Test handling when no content matches the query."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        empty_results = create_empty_search_results(error_msg=None)
        mock_vector_store.search.return_value = empty_results

        # Execute
        result = tool.execute(query="nonexistent topic")

        # Verify
        assert "No relevant content found" in result
        assert len(tool.last_sources) == 0  # No sources for empty results

    def test_execute_empty_results_with_course_filter(self, mock_vector_store):
        """Test empty results message includes filter information."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        empty_results = create_empty_search_results(error_msg=None)
        mock_vector_store.search.return_value = empty_results

        # Execute with course filter
        result = tool.execute(query="test", course_name="Python Course")

        # Verify filter info in message
        assert "No relevant content found" in result
        assert "Python Course" in result

    def test_execute_empty_results_with_lesson_filter(self, mock_vector_store):
        """Test empty results message includes lesson number."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        empty_results = create_empty_search_results(error_msg=None)
        mock_vector_store.search.return_value = empty_results

        # Execute with lesson filter
        result = tool.execute(query="test", lesson_number=5)

        # Verify lesson info in message
        assert "No relevant content found" in result
        assert "lesson 5" in result


class TestCourseSearchToolErrorHandling:
    """Test error handling - should ALL PASS (good error handling via SearchResults pattern)."""

    def test_execute_with_error(self, mock_vector_store):
        """Test that VectorStore errors are returned as strings, not raised."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        error_results = SearchResults.empty("Database connection failed")
        mock_vector_store.search.return_value = error_results

        # Execute - should NOT raise exception
        result = tool.execute(query="test")

        # Verify error message returned
        assert result == "Database connection failed"
        assert len(tool.last_sources) == 0  # No sources on error

    def test_execute_with_vector_store_exception(self, mock_vector_store):
        """Test handling when VectorStore.search raises exception."""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        # Mock search to raise exception
        mock_vector_store.search.side_effect = Exception("Unexpected error")

        # Execute - this will raise because CourseSearchTool doesn't catch exceptions
        # (relies on VectorStore to catch and return SearchResults with error)
        with pytest.raises(Exception) as exc_info:
            tool.execute(query="test")

        assert "Unexpected error" in str(exc_info.value)


class TestCourseOutlineTool:
    """Test CourseOutlineTool functionality."""

    def test_execute_successful_outline(self, mock_vector_store):
        """Test retrieving a course outline."""
        # Setup
        tool = CourseOutlineTool(mock_vector_store)
        mock_outline = {
            "course_title": "Introduction to Python",
            "course_link": "https://example.com/course",
            "instructor": "Jane Doe",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Getting Started",
                    "lesson_link": "https://example.com/lesson1"
                },
                {
                    "lesson_number": 2,
                    "lesson_title": "Variables",
                    "lesson_link": None
                }
            ]
        }
        mock_vector_store.get_course_outline.return_value = mock_outline

        # Execute
        result = tool.execute(course_title="Python")

        # Verify
        assert "Introduction to Python" in result
        assert "Jane Doe" in result
        assert "Lesson 1: Getting Started" in result
        assert "Lesson 2: Variables" in result
        assert len(tool.last_sources) > 0  # Should track sources

    def test_execute_course_not_found(self, mock_vector_store):
        """Test handling when course doesn't exist."""
        # Setup
        tool = CourseOutlineTool(mock_vector_store)
        mock_vector_store.get_course_outline.return_value = None

        # Execute
        result = tool.execute(course_title="Nonexistent Course")

        # Verify error message
        assert "No course found" in result
        assert "Nonexistent Course" in result


class TestToolManager:
    """Test ToolManager functionality."""

    def test_register_tool(self, mock_vector_store):
        """Test tool registration."""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        manager.register_tool(tool)

        # Verify
        assert "search_course_content" in manager.tools
        assert manager.tools["search_course_content"] == tool

    def test_get_tool_definitions(self, mock_vector_store):
        """Test retrieving tool definitions."""
        # Setup
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)
        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        # Execute
        definitions = manager.get_tool_definitions()

        # Verify
        assert len(definitions) == 2
        tool_names = [d["name"] for d in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_execute_tool(self, mock_vector_store, sample_search_results):
        """Test executing a registered tool."""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        mock_vector_store.search.return_value = sample_search_results

        # Execute
        result = manager.execute_tool("search_course_content", query="test")

        # Verify
        assert result is not None
        assert isinstance(result, str)

    def test_execute_tool_not_found(self):
        """Test executing a tool that doesn't exist."""
        # Setup
        manager = ToolManager()

        # Execute
        result = manager.execute_tool("nonexistent_tool", query="test")

        # Verify error message
        assert "not found" in result

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving sources from last search."""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        mock_vector_store.search.return_value = sample_search_results

        # Execute search to populate sources
        manager.execute_tool("search_course_content", query="test")

        # Get sources
        sources = manager.get_last_sources()

        # Verify
        assert len(sources) > 0
        assert all("text" in s and "link" in s for s in sources)

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test resetting sources."""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        mock_vector_store.search.return_value = sample_search_results

        # Execute search and verify sources exist
        manager.execute_tool("search_course_content", query="test")
        assert len(manager.get_last_sources()) > 0

        # Reset
        manager.reset_sources()

        # Verify sources cleared
        assert len(manager.get_last_sources()) == 0
