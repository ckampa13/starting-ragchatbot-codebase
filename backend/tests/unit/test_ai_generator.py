"""Unit tests for AIGenerator - Testing tool execution flow and error handling."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import anthropic

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from ai_generator import AIGenerator
from tests.fixtures.mock_responses import (
    create_tool_use_response,
    create_text_response,
    create_empty_response,
    create_malformed_response,
    create_multiple_tool_use_response
)


class TestAIGeneratorBasic:
    """Test basic AIGenerator functionality without tools."""

    def test_generate_response_without_tools(self, mock_anthropic_client, mock_config):
        """Test simple API call without tool usage."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Mock simple text response
        mock_anthropic_client.messages.create.return_value = create_text_response("Simple answer")

        # Execute
        result = generator.generate_response("What is Python?")

        # Verify
        assert result == "Simple answer"
        assert mock_anthropic_client.messages.create.call_count == 1

        # Verify API parameters
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs["messages"][0]["content"] == "What is Python?"
        assert "tools" not in call_args.kwargs

    def test_generate_response_with_conversation_history(self, mock_anthropic_client, mock_config):
        """Test that conversation history is included in system prompt."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value = create_text_response("Answer")

        # Execute with history
        history = "User: Previous question\nAssistant: Previous answer"
        result = generator.generate_response("Follow-up question", conversation_history=history)

        # Verify history included in system prompt
        call_args = mock_anthropic_client.messages.create.call_args
        assert "Previous conversation:" in call_args.kwargs["system"]
        assert history in call_args.kwargs["system"]


class TestAIGeneratorToolExecution:
    """Test tool execution flow (happy path)."""

    def test_generate_response_with_tool_use(self, mock_anthropic_client, mock_tool_manager, mock_config):
        """Test full two-turn flow with tool usage."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Mock two-turn flow
        tool_use_resp = create_tool_use_response()
        final_resp = create_text_response("Answer based on search results")
        mock_anthropic_client.messages.create.side_effect = [tool_use_resp, final_resp]

        # Mock tool execution
        mock_tool_manager.execute_tool.return_value = "Search results content"

        # Execute
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        result = generator.generate_response(
            "What is in lesson 3?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Verify
        assert result == "Answer based on search results"
        assert mock_anthropic_client.messages.create.call_count == 2
        assert mock_tool_manager.execute_tool.call_count == 1

        # Verify tool was executed with correct parameters
        tool_call_args = mock_tool_manager.execute_tool.call_args
        assert tool_call_args.args[0] == "search_course_content"

        # Verify tools were available in follow-up call
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        assert "tools" in second_call_args.kwargs
        assert second_call_args.kwargs["tools"] is not None

    def test_execute_tool_rounds_success(self, mock_anthropic_client, mock_tool_manager):
        """Test _execute_tool_rounds with successful flow."""
        # Setup
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Create mock tool use response
        tool_use_resp = create_tool_use_response(
            tool_name="search_course_content",
            tool_input={"query": "test query", "course_name": "Python"}
        )

        # Mock tool execution
        mock_tool_manager.execute_tool.return_value = "Found content"

        # Mock final response
        final_resp = create_text_response("Final answer")
        mock_anthropic_client.messages.create.return_value = final_resp

        # Prepare base params
        base_params = {
            "messages": [{"role": "user", "content": "What is X?"}],
            "system": "System prompt"
        }

        # Execute
        result = generator._execute_tool_rounds(tool_use_resp, base_params, mock_tool_manager)

        # Verify
        assert result == "Final answer"
        assert mock_tool_manager.execute_tool.called

        # Verify messages array structure
        final_call_args = mock_anthropic_client.messages.create.call_args
        messages = final_call_args.kwargs["messages"]
        assert len(messages) == 3  # Original user message + assistant tool use + user tool results
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_tool_execution_loop_multiple_tools(self, mock_anthropic_client, mock_tool_manager):
        """Test handling multiple tool_use blocks in one response."""
        # Setup
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Create response with multiple tool uses
        multi_tool_resp = create_multiple_tool_use_response()

        # Mock tool execution
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        # Mock final response
        final_resp = create_text_response("Combined answer")
        mock_anthropic_client.messages.create.return_value = final_resp

        # Execute
        base_params = {
            "messages": [{"role": "user", "content": "Question"}],
            "system": "System"
        }
        result = generator._execute_tool_rounds(multi_tool_resp, base_params, mock_tool_manager)

        # Verify both tools executed
        assert mock_tool_manager.execute_tool.call_count == 2
        assert result == "Combined answer"


class TestAIGeneratorErrorHandling:
    """Test error handling in tool execution flow - CRITICAL TESTS."""

    def test_execute_tool_rounds_tool_raises_exception(self, mock_anthropic_client, mock_tool_manager):
        """
        🔴 CRITICAL TEST - Expected to FAIL
        Test that tool execution exceptions are caught and handled gracefully.
        Currently crashes because no try-catch around tool_manager.execute_tool()
        """
        # Setup
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Create tool use response
        tool_use_resp = create_tool_use_response()

        # Mock tool execution to raise exception
        mock_tool_manager.execute_tool.side_effect = Exception("Database connection failed")

        # Mock final response (should still be called with error message)
        final_resp = create_text_response("I encountered an error")
        mock_anthropic_client.messages.create.return_value = final_resp

        # Execute - should NOT crash
        base_params = {
            "messages": [{"role": "user", "content": "Question"}],
            "system": "System"
        }

        # This should not raise an exception - should handle gracefully
        result = generator._execute_tool_rounds(tool_use_resp, base_params, mock_tool_manager)

        # Verify it returns something (error message or AI response)
        assert result is not None
        assert isinstance(result, str)
        # Should either return error string or AI's response about the error

    def test_execute_tool_rounds_second_api_call_fails(self, mock_anthropic_client, mock_tool_manager):
        """
        🔴 CRITICAL TEST - Expected to FAIL
        Test that API errors in second call are caught and handled.
        Currently crashes because no try-catch around second client.messages.create()
        """
        # Setup
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Create tool use response
        tool_use_resp = create_tool_use_response()

        # Mock successful tool execution
        mock_tool_manager.execute_tool.return_value = "Search results"

        # Mock second API call to raise Anthropic API error
        # Create a proper APIError with required request parameter
        mock_request = Mock()
        api_error = anthropic.APIError("Rate limit exceeded", request=mock_request, body=None)
        mock_anthropic_client.messages.create.side_effect = api_error

        # Execute - should NOT crash
        base_params = {
            "messages": [{"role": "user", "content": "Question"}],
            "system": "System"
        }

        # This should not raise an exception - should handle gracefully
        result = generator._execute_tool_rounds(tool_use_resp, base_params, mock_tool_manager)

        # Verify it returns an error message instead of crashing
        assert result is not None
        assert isinstance(result, str)
        # Should contain some indication of error
        assert "error" in result.lower() or "unable" in result.lower()

    def test_execute_tool_rounds_malformed_response(self, mock_anthropic_client, mock_tool_manager):
        """
        🔴 CRITICAL TEST - Expected to FAIL
        Test that malformed API responses are validated before accessing content[0].text
        Currently crashes with AttributeError because no validation
        """
        # Setup
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Create tool use response
        tool_use_resp = create_tool_use_response()

        # Mock successful tool execution
        mock_tool_manager.execute_tool.return_value = "Search results"

        # Mock second API call returning malformed response (no text attribute)
        malformed_resp = create_malformed_response()
        mock_anthropic_client.messages.create.return_value = malformed_resp

        # Execute - should NOT crash
        base_params = {
            "messages": [{"role": "user", "content": "Question"}],
            "system": "System"
        }

        # This should not raise AttributeError - should handle gracefully
        result = generator._execute_tool_rounds(tool_use_resp, base_params, mock_tool_manager)

        # Verify it returns an error message
        assert result is not None
        assert isinstance(result, str)

    def test_generate_response_empty_content(self, mock_anthropic_client, mock_config):
        """Test handling of API response with empty content array."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Mock response with empty content
        empty_resp = create_empty_response()
        mock_anthropic_client.messages.create.return_value = empty_resp

        # Execute - should handle gracefully
        # Currently this will crash with IndexError on line 106: response.content[0].text
        result = generator.generate_response("Question")

        # Should return error message instead of crashing
        assert result is not None
        assert isinstance(result, str)

    def test_generate_response_api_error(self, mock_anthropic_client, mock_config):
        """Test handling of API errors in initial call."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Mock API error
        mock_request = Mock()
        api_error = anthropic.APIError("Connection timeout", request=mock_request, body=None)
        mock_anthropic_client.messages.create.side_effect = api_error

        # Execute - should handle gracefully
        result = generator.generate_response("Question")

        # Should return error message instead of raising exception
        assert result is not None
        assert isinstance(result, str)
        assert "error" in result.lower()


class TestAIGeneratorEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_tool_execution_with_no_tool_results(self, mock_anthropic_client, mock_tool_manager):
        """Test handling when tool returns None or empty result."""
        # Setup
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Create tool use response
        tool_use_resp = create_tool_use_response()

        # Mock tool returning empty string
        mock_tool_manager.execute_tool.return_value = ""

        # Mock final response
        final_resp = create_text_response("No results found")
        mock_anthropic_client.messages.create.return_value = final_resp

        # Execute
        base_params = {
            "messages": [{"role": "user", "content": "Question"}],
            "system": "System"
        }
        result = generator._execute_tool_rounds(tool_use_resp, base_params, mock_tool_manager)

        # Should still work with empty tool result
        assert result == "No results found"


class TestAIGeneratorSequentialTools:
    """Test sequential tool calling (up to 2 rounds)."""

    def test_sequential_tool_execution_two_rounds(self, mock_anthropic_client, mock_tool_manager, mock_config):
        """Test full 2-round sequential flow with different tools in each round."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Mock 3 API responses:
        # 1. Initial: tool_use (get_course_outline)
        # 2. Round 1: tool_use (search_course_content)
        # 3. Round 2: text (final answer)
        outline_tool_resp = create_tool_use_response(
            tool_name="get_course_outline",
            tool_input={"course_title": "Python Basics"}
        )
        search_tool_resp = create_tool_use_response(
            tool_name="search_course_content",
            tool_input={"query": "variables", "lesson_number": 4}
        )
        final_text_resp = create_text_response("Variables are discussed in lesson 4...")

        mock_anthropic_client.messages.create.side_effect = [
            outline_tool_resp,
            search_tool_resp,
            final_text_resp
        ]

        # Mock tool executions
        mock_tool_manager.execute_tool.side_effect = [
            "Course: Python Basics\nLesson 4: Variables",
            "Search results about variables"
        ]

        # Execute
        tools = [
            {"name": "get_course_outline", "description": "Get outline", "input_schema": {}},
            {"name": "search_course_content", "description": "Search", "input_schema": {}}
        ]
        result = generator.generate_response(
            "What does lesson 4 of Python Basics cover?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Verify
        assert result == "Variables are discussed in lesson 4..."
        assert mock_anthropic_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify tools were preserved in round 1 call (within _execute_tool_rounds loop)
        round1_call = mock_anthropic_client.messages.create.call_args_list[1]
        assert "tools" in round1_call.kwargs
        assert round1_call.kwargs["tools"] is not None

        # Verify message history growth
        # calls[1] is the first call inside _execute_tool_rounds after executing outline tool
        assert len(round1_call.kwargs["messages"]) == 3  # user + asst(outline_tool) + user(outline_result)

    def test_sequential_tool_execution_stops_at_max_rounds(self, mock_anthropic_client, mock_tool_manager, mock_config):
        """Test that execution stops after 2 rounds and forces text response."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Mock 4 responses - first 3 are all tool_use
        tool_resp_1 = create_tool_use_response(tool_name="search_course_content")
        tool_resp_2 = create_tool_use_response(tool_name="search_course_content")
        tool_resp_3 = create_tool_use_response(tool_name="search_course_content")  # Triggers limit
        final_forced_resp = create_text_response("Based on available information...")

        mock_anthropic_client.messages.create.side_effect = [
            tool_resp_1,
            tool_resp_2,
            tool_resp_3,  # Loop exits here
            final_forced_resp  # Final call WITHOUT tools
        ]

        mock_tool_manager.execute_tool.return_value = "Search results"

        # Execute
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        result = generator.generate_response("Complex query", tools=tools, tool_manager=mock_tool_manager)

        # Verify
        assert result == "Based on available information..."
        assert mock_anthropic_client.messages.create.call_count == 4
        assert mock_tool_manager.execute_tool.call_count == 3

        # Verify final call had NO tools (safety mechanism)
        final_call = mock_anthropic_client.messages.create.call_args_list[3]
        assert "tools" not in final_call.kwargs or final_call.kwargs.get("tools") is None

    def test_sequential_tool_execution_stops_naturally(self, mock_anthropic_client, mock_tool_manager, mock_config):
        """Test that execution stops when Claude returns text before hitting max rounds."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Only 2 API calls - Claude decides after 1 round
        tool_resp = create_tool_use_response()
        text_resp = create_text_response("Here's the answer")

        mock_anthropic_client.messages.create.side_effect = [tool_resp, text_resp]
        mock_tool_manager.execute_tool.return_value = "Tool results"

        # Execute
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        result = generator.generate_response("Simple query", tools=tools, tool_manager=mock_tool_manager)

        # Verify only 2 calls (natural termination)
        assert mock_anthropic_client.messages.create.call_count == 2
        assert result == "Here's the answer"

    def test_sequential_tool_execution_handles_tool_error_in_round_2(self, mock_anthropic_client, mock_tool_manager, mock_config):
        """Test that tool failures in round 2 are handled gracefully."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # Round 1 succeeds, round 2 tool fails
        tool_resp_1 = create_tool_use_response(tool_name="get_course_outline")
        tool_resp_2 = create_tool_use_response(tool_name="search_course_content")
        final_resp = create_text_response("I encountered an issue searching...")

        mock_anthropic_client.messages.create.side_effect = [tool_resp_1, tool_resp_2, final_resp]

        # First tool succeeds, second raises exception
        mock_tool_manager.execute_tool.side_effect = [
            "Outline results",
            Exception("Database timeout")
        ]

        # Execute
        tools = [
            {"name": "get_course_outline", "description": "Outline", "input_schema": {}},
            {"name": "search_course_content", "description": "Search", "input_schema": {}}
        ]
        result = generator.generate_response("Query", tools=tools, tool_manager=mock_tool_manager)

        # Should not crash - error passed to Claude as tool_result
        assert result == "I encountered an issue searching..."
        assert mock_anthropic_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_conversation_context_preserved_across_rounds(self, mock_anthropic_client, mock_tool_manager, mock_config):
        """Test that message history accumulates correctly across rounds."""
        # Setup
        generator = AIGenerator(
            api_key=mock_config.ANTHROPIC_API_KEY,
            model=mock_config.ANTHROPIC_MODEL
        )
        generator.client = mock_anthropic_client

        # 2 rounds of tools
        tool_resp_1 = create_tool_use_response(tool_name="get_course_outline")
        tool_resp_2 = create_tool_use_response(tool_name="search_course_content")
        final_resp = create_text_response("Final answer")

        mock_anthropic_client.messages.create.side_effect = [tool_resp_1, tool_resp_2, final_resp]
        mock_tool_manager.execute_tool.side_effect = ["Outline", "Search results"]

        # Execute
        tools = [
            {"name": "get_course_outline", "description": "Outline", "input_schema": {}},
            {"name": "search_course_content", "description": "Search", "input_schema": {}}
        ]
        result = generator.generate_response("Original query", tools=tools, tool_manager=mock_tool_manager)

        # Verify message history growth
        calls = mock_anthropic_client.messages.create.call_args_list

        # Call 0 (initial in generate_response): Just user query
        assert len(calls[0].kwargs["messages"]) == 1
        assert calls[0].kwargs["messages"][0]["role"] == "user"

        # Call 1 (round 1 in _execute_tool_rounds): User query + round 1 exchange (asst + user)
        assert len(calls[1].kwargs["messages"]) == 3
        assert calls[1].kwargs["messages"][0]["role"] == "user"
        assert calls[1].kwargs["messages"][1]["role"] == "assistant"
        assert calls[1].kwargs["messages"][2]["role"] == "user"

        # Call 2 (round 2 in _execute_tool_rounds): Full history (user + round 1 + round 2)
        assert len(calls[2].kwargs["messages"]) == 5
        assert calls[2].kwargs["messages"][0]["role"] == "user"
        assert calls[2].kwargs["messages"][1]["role"] == "assistant"
        assert calls[2].kwargs["messages"][2]["role"] == "user"
        assert calls[2].kwargs["messages"][3]["role"] == "assistant"
        assert calls[2].kwargs["messages"][4]["role"] == "user"
