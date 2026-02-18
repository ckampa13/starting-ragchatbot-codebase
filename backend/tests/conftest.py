"""Shared pytest fixtures for RAG chatbot tests."""

import pytest
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from tests.fixtures.mock_responses import (
    create_tool_use_response,
    create_text_response,
    create_empty_response,
    create_malformed_response,
    create_multiple_tool_use_response
)
from tests.fixtures.test_data import (
    create_sample_course,
    create_sample_chunks,
    create_sample_search_results,
    create_empty_search_results
)


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.MAX_TOKENS = 4096
    config.TEMPERATURE = 0.7
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.CHROMA_PATH = "./test_chroma_db"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    return config


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client."""
    client = Mock()
    client.messages = Mock()
    client.messages.create = Mock()
    return client


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore with configurable responses."""
    store = Mock()
    store.search = Mock(return_value=create_sample_search_results())
    store.get_lesson_link = Mock(return_value=None)
    store.resolve_course_name = Mock(return_value=None)
    store.get_existing_course_titles = Mock(return_value=[])
    return store


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager."""
    manager = Mock()
    manager.execute_tool = Mock(return_value="Tool execution successful")
    manager.get_tool_definitions = Mock(return_value=[])
    manager.last_sources = []
    return manager


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager."""
    manager = Mock()
    manager.get_or_create_session = Mock(return_value=("test-session-id", []))
    manager.add_exchange = Mock()
    return manager


@pytest.fixture
def sample_course():
    """Sample course object."""
    return create_sample_course()


@pytest.fixture
def sample_chunks():
    """Sample course chunks."""
    return create_sample_chunks()


@pytest.fixture
def sample_search_results():
    """Sample SearchResults object."""
    return create_sample_search_results()


@pytest.fixture
def empty_search_results():
    """Empty SearchResults object."""
    return create_empty_search_results()


@pytest.fixture
def mock_tool_use_response():
    """Mock API response with tool_use."""
    return create_tool_use_response()


@pytest.fixture
def mock_text_response():
    """Mock API response with text content."""
    return create_text_response()


@pytest.fixture
def mock_empty_response():
    """Mock API response with empty content."""
    return create_empty_response()


@pytest.fixture
def mock_malformed_response():
    """Mock API response with malformed content."""
    return create_malformed_response()


@pytest.fixture
def mock_multiple_tool_use_response():
    """Mock API response with multiple tool_use blocks."""
    return create_multiple_tool_use_response()


@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API endpoint testing."""
    rag = Mock()
    rag.query = Mock(return_value=("Test answer", []))
    rag.get_course_analytics = Mock(return_value={
        "total_courses": 2,
        "course_titles": ["Introduction to Python", "Advanced ML"],
    })
    rag.session_manager = Mock()
    rag.session_manager.create_session = Mock(return_value="auto-session-id")
    return rag
