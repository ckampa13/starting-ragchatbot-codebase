"""Integration tests for FastAPI API endpoints.

Uses a self-contained test app that mirrors app.py's endpoint logic without
mounting static files, avoiding import-time side effects (ChromaDB init,
frontend directory checks).
"""

import pytest
import anthropic
from unittest.mock import Mock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Pydantic models — mirrors app.py definitions
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class SourceCitation(BaseModel):
    text: str
    link: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Test app factory — same endpoint logic as app.py, no static file mount
# ---------------------------------------------------------------------------

def create_test_app(rag_system) -> FastAPI:
    """Return a FastAPI app whose endpoints use *rag_system* (a mock or real)."""
    test_app = FastAPI(title="Test RAG API")

    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except anthropic.APIError as e:
            raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_rag_system):
    """Synchronous TestClient backed by the test app and a mock RAGSystem."""
    app = create_test_app(mock_rag_system)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests — POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    """Tests for POST /api/query."""

    def test_query_success(self, client, mock_rag_system):
        """Happy path: returns 200 with answer and session_id."""
        mock_rag_system.query.return_value = ("Python is a programming language.", [])

        response = client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "test-session"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Python is a programming language."
        assert data["session_id"] == "test-session"
        assert isinstance(data["sources"], list)

    def test_query_auto_creates_session_when_omitted(self, client, mock_rag_system):
        """Session is created automatically when session_id is not provided."""
        response = client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "auto-session-id"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_uses_provided_session_id(self, client, mock_rag_system):
        """Provided session_id is forwarded to rag_system.query; no new session created."""
        response = client.post(
            "/api/query",
            json={"query": "Follow-up question?", "session_id": "existing-session"},
        )

        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with("Follow-up question?", "existing-session")
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_missing_required_field_returns_422(self, client):
        """Missing required 'query' field returns 422 Unprocessable Entity."""
        response = client.post("/api/query", json={"session_id": "test-session"})

        assert response.status_code == 422

    def test_query_empty_body_returns_422(self, client):
        """Completely empty request body returns 422."""
        response = client.post("/api/query", json={})

        assert response.status_code == 422

    def test_query_returns_sources_in_response(self, client, mock_rag_system):
        """Sources returned by rag_system are serialized correctly."""
        sources = [
            SourceCitation(text="Introduction to Python - Lesson 1", link="https://example.com/l1"),
            SourceCitation(text="Introduction to Python - Lesson 2", link=None),
        ]
        mock_rag_system.query.return_value = ("Here is your answer.", sources)

        response = client.post(
            "/api/query",
            json={"query": "Tell me about Python lessons", "session_id": "s"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "Introduction to Python - Lesson 1"
        assert data["sources"][0]["link"] == "https://example.com/l1"
        assert data["sources"][1]["link"] is None

    def test_query_anthropic_api_error_returns_503(self, client, mock_rag_system):
        """anthropic.APIError propagates as 503 Service Unavailable."""
        mock_request = Mock()
        mock_rag_system.query.side_effect = anthropic.APIError(
            "Rate limit exceeded", request=mock_request, body=None
        )

        response = client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "s"},
        )

        assert response.status_code == 503
        assert "AI service error" in response.json()["detail"]

    def test_query_general_exception_returns_500(self, client, mock_rag_system):
        """Unexpected exception from rag_system returns 500 Internal Server Error."""
        mock_rag_system.query.side_effect = RuntimeError("Database unavailable")

        response = client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "s"},
        )

        assert response.status_code == 500
        assert "Query processing error" in response.json()["detail"]

    def test_query_response_has_required_fields(self, client):
        """Response JSON contains answer, sources, and session_id with correct types."""
        response = client.post(
            "/api/query",
            json={"query": "Test query", "session_id": "s"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)


# ---------------------------------------------------------------------------
# Tests — GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    """Tests for GET /api/courses."""

    def test_courses_success(self, client):
        """Happy path: returns 200 with course count and titles."""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert "Introduction to Python" in data["course_titles"]
        assert "Advanced ML" in data["course_titles"]

    def test_courses_response_has_required_fields(self, client):
        """Response JSON contains total_courses (int) and course_titles (list)."""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_courses_empty_catalog(self, client, mock_rag_system):
        """Returns zero courses and empty list when no courses are loaded."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_total_matches_titles_length(self, client, mock_rag_system):
        """total_courses matches the number of entries in course_titles."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Course A", "Course B", "Course C"],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == len(data["course_titles"])

    def test_courses_exception_returns_500(self, client, mock_rag_system):
        """Exception from rag_system returns 500 Internal Server Error."""
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")

        response = client.get("/api/courses")

        assert response.status_code == 500
