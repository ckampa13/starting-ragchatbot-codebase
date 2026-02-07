import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to comprehensive search and outline tools.

Tool Selection Guidelines:
- **get_course_outline**: Use when users ask about:
  - Course structure, outline, or table of contents
  - "What topics are covered" or "What lessons are in this course"
  - Lesson lists, course overview, or curriculum
  - Return ALL outline details (course link, instructor, complete lesson list with links)

- **search_course_content**: Use when users ask about:
  - Specific topics, concepts, or content within lessons
  - Questions requiring detailed educational material
  - "How does X work" or "Explain Y from the course"
  - Can be used after get_course_outline to search specific lessons

Multi-Step Reasoning:
- You may use up to TWO rounds of tool calls to answer complex queries
- Example workflow: get_course_outline → analyze results → search_course_content with lesson filter
- Example workflow: Search broad topic → refine search based on initial results
- Each tool call builds on previous results - use information from earlier tool outputs
- If you can answer with one tool call, do so - don't unnecessarily chain tools

- **No tool needed**: Use existing knowledge for:
  - General knowledge questions unrelated to specific courses
  - Greetings, clarifications, or conversational queries

Response Protocol:
- **Outline queries**: When returning course outlines, include:
  - Full course title and instructor
  - Course link (if available)
  - Complete numbered lesson list with titles
  - Lesson links (if available) - format as markdown links

- **Content queries**: Synthesize search results into accurate, fact-based responses

- **No meta-commentary**:
  - Provide direct answers only — no reasoning process, tool explanations, or query-type analysis
  - Do not mention "based on the search results" or "according to the outline"
  - Never explain which tool you used or why
  - Do not mention tool call rounds or "first I searched" explanations

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
5. **Complete** - For outlines, show ALL lessons; don't truncate or summarize

Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        try:
            # Build system content efficiently - avoid string ops when possible
            system_content = (
                f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
                if conversation_history
                else self.SYSTEM_PROMPT
            )

            # Prepare API call parameters efficiently
            api_params = {
                **self.base_params,
                "messages": [{"role": "user", "content": query}],
                "system": system_content
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude
            response = self.client.messages.create(**api_params)

            # Handle tool execution if needed
            if response.stop_reason == "tool_use" and tool_manager:
                return self._execute_tool_rounds(response, api_params, tool_manager)

            # Validate response before accessing content
            if not response.content or len(response.content) == 0:
                return "Unable to generate response (empty content)"
            if not hasattr(response.content[0], 'text'):
                return "Unable to generate response (invalid content type)"

            # Return direct response
            return response.content[0].text

        except anthropic.APIError as e:
            return f"API error: {str(e)}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _execute_all_tools(self, response, tool_manager) -> list:
        """
        Execute all tools from one API response.

        Args:
            response: API response with tool_use content blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool_result dictionaries for Claude API
        """
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )
                except Exception as tool_error:
                    # Pass error to AI for graceful handling
                    result = f"Tool execution error: {str(tool_error)}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": result
                })

        return tool_results

    def _execute_tool_rounds(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls with support for up to 2 sequential rounds.

        Uses message builder pattern: maintains growing message array across rounds.
        Claude can see previous tool results and decide whether to call more tools.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters (messages, system, tools)
            tool_manager: Manager to execute tools

        Returns:
            Final response text after all rounds complete
        """
        try:
            # Initialize message array - will grow with each round
            messages = base_params["messages"].copy()
            current_response = initial_response
            round_count = 0
            MAX_ROUNDS = 2

            # Loop while Claude wants tools and we haven't hit limit
            while round_count < MAX_ROUNDS and current_response.stop_reason == "tool_use":
                round_count += 1

                # Add assistant's tool_use response
                messages.append({"role": "assistant", "content": current_response.content})

                # Execute all tools and get results
                tool_results = self._execute_all_tools(current_response, tool_manager)

                # Add tool results as user message
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

                # Make next API call WITH tools still available
                api_params = {
                    **self.base_params,
                    "messages": messages.copy(),  # Copy to avoid reference issues
                    "system": base_params["system"],
                    "tools": base_params.get("tools"),  # Preserve tools!
                    "tool_choice": {"type": "auto"}
                }

                try:
                    current_response = self.client.messages.create(**api_params)
                except anthropic.APIError as e:
                    return f"API error in round {round_count}: {str(e)}"
                except Exception as e:
                    return f"Error in round {round_count}: {str(e)}"

            # SAFETY MECHANISM: If exited due to max rounds with tool_use still active,
            # execute those final tools but force a text response
            if current_response.stop_reason == "tool_use":
                # Add final tool_use to messages
                messages.append({"role": "assistant", "content": current_response.content})

                # Execute final round of tools
                tool_results = self._execute_all_tools(current_response, tool_manager)

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

                # Final call WITHOUT tools to force text conclusion
                final_params = {
                    **self.base_params,
                    "messages": messages.copy(),  # Copy to avoid reference issues
                    "system": base_params["system"]
                    # No tools - forces text response
                }

                try:
                    current_response = self.client.messages.create(**final_params)
                except anthropic.APIError as e:
                    return f"API error in final response: {str(e)}"
                except Exception as e:
                    return f"Error in final response: {str(e)}"

            # Validate and return final text response
            if not current_response.content or len(current_response.content) == 0:
                return "Unable to generate response (empty content)"
            if not hasattr(current_response.content[0], 'text'):
                return "Unable to generate response (invalid content type)"

            return current_response.content[0].text

        except Exception as e:
            return f"Unexpected error in tool execution: {str(e)}"