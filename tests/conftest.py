"""
Pytest configuration and fixtures for mcp_simple_arxiv tests.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_arxiv_response():
    """Mock arXiv API response data."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2103.08220v1</id>
            <title>Test Paper Title</title>
            <summary>This is a test abstract with multiple sentences. This contains important information.</summary>
            <published>2021-03-15T17:58:35Z</published>
            <updated>2021-03-16T10:30:00Z</updated>
            <author><name>John Doe</name></author>
            <author><name>Jane Smith</name></author>
            <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI"/>
            <category term="cs.AI"/>
            <category term="cs.LG"/>
            <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">10 pages, 5 figures</arxiv:comment>
            <arxiv:journal_ref xmlns:arxiv="http://arxiv.org/schemas/atom">Nature 2021</arxiv:journal_ref>
            <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.1038/s41586-021-03819-2</arxiv:doi>
            <link type="application/pdf" href="http://arxiv.org/pdf/2103.08220v1.pdf"/>
            <link type="text/html" href="http://arxiv.org/abs/2103.08220v1"/>
        </entry>
    </feed>"""


@pytest.fixture
def mock_empty_arxiv_response():
    """Mock empty arXiv API response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
    </feed>"""


@pytest.fixture
def sample_paper():
    """Sample paper data for testing."""
    return {
        "id": "2103.08220v1",
        "title": "Test Paper Title",
        "authors": ["John Doe", "Jane Smith"],
        "primary_category": "cs.AI",
        "categories": ["cs.LG"],
        "published": "2021-03-15T17:58:35Z",
        "updated": "2021-03-16T10:30:00Z",
        "summary": "This is a test abstract with multiple sentences. This contains important information.",
        "comment": "10 pages, 5 figures",
        "journal_ref": "Nature 2021",
        "doi": "10.1038/s41586-021-03819-2",
        "pdf_url": "http://arxiv.org/pdf/2103.08220v1.pdf",
        "abstract_url": "http://arxiv.org/abs/2103.08220v1",
        "html_url": "https://arxiv.org/html/2103.08220v1"
    }


@pytest.fixture
def sample_papers():
    """Sample list of papers for testing."""
    return [
        {
            "id": "2103.08220",
            "title": "First Paper",
            "authors": ["John Doe"],
            "primary_category": "cs.AI",
            "categories": ["cs.LG"],
            "published": "2021-03-15T17:58:35Z",
            "summary": "First paper abstract."
        },
        {
            "id": "1234.5678",
            "title": "Second Paper", 
            "authors": ["Jane Smith"],
            "primary_category": "cs.CV",
            "categories": [],
            "published": "2020-12-01T10:00:00Z",
            "summary": "Second paper abstract."
        }
    ]


@pytest.fixture
def sample_taxonomy():
    """Sample taxonomy data for testing."""
    return {
        "cs": {
            "name": "Computer Science",
            "subcategories": {
                "AI": "Artificial Intelligence",
                "LG": "Machine Learning",
                "CV": "Computer Vision and Pattern Recognition"
            }
        },
        "math": {
            "name": "Mathematics",
            "subcategories": {
                "NT": "Number Theory",
                "PR": "Probability"
            }
        }
    }


@pytest.fixture
def mock_citation_data():
    """Mock citation data from Semantic Scholar."""
    return {
        "citation_count": 42,
        "influential_citations": 5,
        "references": 15,
        "year": 2021
    }


@pytest.fixture
def mock_semantic_scholar_response():
    """Mock Semantic Scholar API response."""
    return {
        "citationCount": 42,
        "influentialCitationCount": 5,
        "references": [{"paperId": "1"}, {"paperId": "2"}],
        "year": 2021
    }


@pytest.fixture(autouse=True)
def reset_citation_service_cache():
    """Reset citation service cache before each test."""
    from mcp_simple_arxiv.citation_service import CitationService
    # Clear any existing cache
    if hasattr(CitationService, '_instance_cache'):
        CitationService._instance_cache = {}
    yield
    # Clean up after test
    if hasattr(CitationService, '_instance_cache'):
        CitationService._instance_cache = {}


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing."""
    with patch('httpx.AsyncClient') as mock_client:
        yield mock_client


@pytest.fixture
def mock_requests():
    """Mock requests module for testing."""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_time():
    """Mock time module for testing."""
    with patch('time.time') as mock_time_func, \
         patch('time.sleep') as mock_sleep:
        yield {
            'time': mock_time_func,
            'sleep': mock_sleep
        }
