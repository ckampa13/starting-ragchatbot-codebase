"""Test data fixtures for RAG chatbot tests."""

from models import Course, Lesson, CourseChunk
from vector_store import SearchResults


def create_sample_course():
    """Create a sample course for testing."""
    return Course(
        title="Introduction to Python",
        link="https://example.com/python-course",
        instructor="Jane Doe",
        lessons=[
            Lesson(number=1, title="Getting Started", link="https://example.com/lesson1"),
            Lesson(number=2, title="Variables and Types", link="https://example.com/lesson2"),
            Lesson(number=3, title="Control Flow", link="https://example.com/lesson3"),
        ]
    )


def create_sample_chunks():
    """Create sample course chunks for testing."""
    return [
        CourseChunk(
            content="Python is a high-level programming language.",
            course_title="Introduction to Python",
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="Variables store data values in Python.",
            course_title="Introduction to Python",
            lesson_number=2,
            chunk_index=0
        ),
        CourseChunk(
            content="Control flow uses if statements and loops.",
            course_title="Introduction to Python",
            lesson_number=3,
            chunk_index=0
        ),
    ]


def create_sample_search_results():
    """Create sample SearchResults object with documents and metadata."""
    return SearchResults(
        documents=[
            "Python is a high-level programming language.",
            "Variables store data values in Python.",
            "Control flow uses if statements and loops."
        ],
        metadata=[
            {"course_title": "Introduction to Python", "lesson_number": 1},
            {"course_title": "Introduction to Python", "lesson_number": 2},
            {"course_title": "Introduction to Python", "lesson_number": 3},
        ],
        distances=[0.1, 0.2, 0.3],
        error=None
    )


def create_empty_search_results(error_msg=None):
    """Create empty SearchResults with optional error."""
    if error_msg:
        return SearchResults.empty(error_msg)
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error=None
    )
