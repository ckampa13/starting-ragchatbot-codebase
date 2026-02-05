# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) Chatbot** - a full-stack web application that enables semantic search and AI-powered Q&A over educational course materials. The system uses ChromaDB for vector storage, Anthropic's Claude API for generation, and serves a vanilla JavaScript frontend.

## Running the Application

### Prerequisites
- Python 3.13+
- `uv` package manager
- Anthropic API key in `.env` file

### Start the server
```bash
./run.sh
```

Or manually:
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

Access at: `http://localhost:8000`

### Environment Setup
Create `.env` in the root directory:
```
ANTHROPIC_API_KEY=your-api-key-here
```

### Installing Dependencies
```bash
uv sync
```

## Architecture

### RAG Pipeline Flow
The system implements a **tool-based RAG architecture** with two-turn AI conversations:

```
User Query
  → FastAPI endpoint (/api/query)
  → RAGSystem.query()
  → AIGenerator.generate_response() with tools
  → [First Claude API call] → stop_reason: "tool_use"
  → CourseSearchTool.execute()
  → VectorStore.search() → ChromaDB semantic search
  → [Second Claude API call] with tool results → final answer
  → Response + sources returned to frontend
```

### Core Components

**RAGSystem** (`rag_system.py`) - Central orchestrator
- Initializes and coordinates all components
- Manages tool registration (CourseSearchTool)
- Handles query processing with conversation history

**DocumentProcessor** (`document_processor.py`) - Text parsing and chunking
- Parses course documents with expected format:
  ```
  Course Title: [title]
  Course Link: [url]
  Course Instructor: [instructor]
  Lesson N: [title]
  [content]
  ```
- Chunks text using sentence-based splitting (800 chars, 100 char overlap)
- Adds context prefixes to chunks: `"Course X Lesson N content: {chunk}"`

**VectorStore** (`vector_store.py`) - ChromaDB wrapper with dual collections
- **Two-collection design**:
  - `course_catalog`: Course metadata for semantic course name matching
  - `course_content`: Actual lesson chunks with metadata
- Embeds using `all-MiniLM-L6-v2` model
- Supports filtering by course_name and lesson_number

**AIGenerator** (`ai_generator.py`) - Claude API wrapper
- Implements tool-based conversation pattern
- Static system prompt optimized for educational Q&A
- `_handle_tool_execution()` manages two-turn flow:
  1. Initial query with tools → tool_use response
  2. Execute tools → final response with tool results

**SearchTools** (`search_tools.py`) - Tool definitions and execution
- Abstract `Tool` base class for extensibility
- `CourseSearchTool`: Semantic search with parameters:
  - `query` (required)
  - `course_name` (optional, partial matches work)
  - `lesson_number` (optional)
- `ToolManager`: Routes tool calls, tracks sources for UI

**SessionManager** (`session_manager.py`) - Conversation state
- In-memory session storage (not persistent)
- Maintains limited history (default: 2 exchanges = 4 messages)
- Sessions auto-created on first query

### Data Models

**Course** - Container for course metadata + lessons list
**Lesson** - Individual lesson with number, title, optional link
**CourseChunk** - Text chunk with course_title, lesson_number, chunk_index metadata

### Frontend Architecture

- **Vanilla JavaScript** (no frameworks)
- `sendMessage()` function handles:
  - API calls to `/api/query`
  - Session ID persistence (reused across queries)
  - Loading states and markdown rendering (marked.js)
  - Sources display in collapsible details element

## Key Implementation Patterns

### Startup Document Loading
On server startup (`app.py:startup_event`):
1. Scans `../docs` folder for `.txt`, `.pdf`, `.docx` files
2. Processes each through DocumentProcessor
3. Stores in ChromaDB (checks existing titles to avoid duplicates)

### Tool-Based Search
Claude decides when to call `search_course_content` based on query context. The tool:
1. Optionally resolves course_name via semantic search in `course_catalog`
2. Searches `course_content` with filters
3. Formats results with `[Course - Lesson N]` headers
4. Tracks sources for frontend display

### Chunk Context Enhancement
- First chunk of each lesson: `"Lesson {num} content: {chunk}"`
- Last lesson chunks: `"Course {title} Lesson {num} content: {chunk}"`
- Helps AI understand document structure during retrieval

### Session Continuity
- Frontend stores `session_id` in `currentSessionId` variable
- Reuses same session for follow-up questions
- Backend maintains conversation history with max limit
- History injected into system prompt as context

## Configuration

Settings in `config.py` (loaded from environment):
- `CHUNK_SIZE`: 800 characters (text chunk size)
- `CHUNK_OVERLAP`: 100 characters (overlap between chunks)
- `MAX_RESULTS`: 5 (number of search results)
- `MAX_HISTORY`: 2 (conversation exchanges to remember)
- `CHROMA_PATH`: `./chroma_db` (persistent vector store)
- `ANTHROPIC_MODEL`: `claude-sonnet-4-20250514`
- `EMBEDDING_MODEL`: `all-MiniLM-L6-v2`

## Important Notes

### Python Execution with uv
**ALWAYS use `uv` to run Python files in this project. DO NOT use `pip` or `python` directly.**

- To run Python scripts: `uv run python script.py` or `uv run script.py`
- To run commands: `uv run uvicorn app:app --reload`
- To install dependencies: `uv sync` (NOT `pip install`)
- To add packages: `uv add package-name` (NOT `pip install package-name`)

This ensures the Python environment is properly managed by `uv` with the correct dependencies from the project's configuration.

### Document Format Requirements
Course documents must follow this structure for proper parsing:
- First 3 lines: Course Title, Course Link, Course Instructor
- Lesson markers: `Lesson N: Title`
- Optional lesson links: `Lesson Link: URL`

### ChromaDB Persistence
- Vector database stored in `./chroma_db/` directory
- Persists across restarts
- Duplicate prevention via `get_existing_course_titles()` check

### Two-Turn AI Pattern
The system ALWAYS makes two Claude API calls per query when tool use is needed:
1. First call: Claude decides to use search tool
2. Execute tool, collect results
3. Second call: Claude synthesizes answer from tool results

This is by design - do not try to "optimize" to single call.

### Session Storage Limitation
Sessions are in-memory only. Server restart clears all session history.

## File Structure Reference

```
backend/
  ├── app.py              # FastAPI server, endpoints, startup logic
  ├── rag_system.py       # Main orchestrator
  ├── vector_store.py     # ChromaDB wrapper
  ├── document_processor.py # Text parsing & chunking
  ├── ai_generator.py     # Claude API client
  ├── search_tools.py     # Tool definitions & manager
  ├── session_manager.py  # Conversation history
  ├── models.py          # Pydantic data models
  └── config.py          # Configuration & env vars

frontend/
  ├── index.html         # Web UI layout
  ├── script.js          # Client-side logic
  └── style.css          # Styling

docs/                    # Course documents to index
```

## API Endpoints

- `POST /api/query` - Process user query
  - Request: `{query: str, session_id?: str}`
  - Response: `{answer: str, sources: List[str], session_id: str}`

- `GET /api/courses` - Get course statistics
  - Response: `{total_courses: int, course_titles: List[str]}`

- `/` - Serves static frontend files
- `/docs` - FastAPI auto-generated API documentation
