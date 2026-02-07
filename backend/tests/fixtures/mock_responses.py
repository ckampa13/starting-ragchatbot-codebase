"""Mock Anthropic API responses for testing."""

from unittest.mock import Mock


def create_tool_use_response(tool_name="search_course_content", tool_input=None):
    """Create a mock Anthropic API response with tool_use."""
    if tool_input is None:
        tool_input = {"query": "test query"}

    response = Mock()
    response.stop_reason = "tool_use"

    # Create tool_use content block
    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = "tool_abc123"
    tool_block.input = tool_input

    response.content = [tool_block]
    return response


def create_text_response(text="This is a test response"):
    """Create a mock Anthropic API response with text content."""
    response = Mock()
    response.stop_reason = "end_turn"

    # Create text content block
    text_block = Mock()
    text_block.type = "text"
    text_block.text = text

    response.content = [text_block]
    return response


def create_empty_response():
    """Create a mock response with empty content."""
    response = Mock()
    response.stop_reason = "end_turn"
    response.content = []
    return response


def create_malformed_response():
    """Create a mock response with malformed content (no text attribute)."""
    response = Mock()
    response.stop_reason = "end_turn"

    # Create content block without text attribute
    content_block = Mock(spec=[])  # Empty spec means no attributes
    del content_block.text  # Ensure text doesn't exist

    response.content = [content_block]
    return response


def create_multiple_tool_use_response():
    """Create a mock response with multiple tool_use blocks."""
    response = Mock()
    response.stop_reason = "tool_use"

    # Create two tool_use content blocks
    tool_block_1 = Mock()
    tool_block_1.type = "tool_use"
    tool_block_1.name = "search_course_content"
    tool_block_1.id = "tool_1"
    tool_block_1.input = {"query": "first query"}

    tool_block_2 = Mock()
    tool_block_2.type = "tool_use"
    tool_block_2.name = "search_course_content"
    tool_block_2.id = "tool_2"
    tool_block_2.input = {"query": "second query"}

    response.content = [tool_block_1, tool_block_2]
    return response
