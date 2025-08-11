"""
Core functionality tests for mcp_simple_arxiv.
These tests focus on the core business logic without MCP server complexities.
"""

import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.arxiv_client import ArxivClient
from mcp_simple_arxiv.citation_service import CitationService
from mcp_simple_arxiv.server import get_first_sentence
from mcp_simple_arxiv.categories import CATEGORIES
from mcp_simple_arxiv.update_taxonomy import load_taxonomy, update_taxonomy_file


class TestCoreFunctionality:
    """Test core functionality of the arXiv MCP implementation."""

    def test_arxiv_client_initialization(self):
        """Test ArxivClient initializes correctly."""
        client = ArxivClient()
        assert client.base_url == "https://export.arxiv.org/api/query"
        assert client._last_request is None

    def test_citation_service_initialization(self):
        """Test CitationService initializes correctly."""
        service = CitationService()
        assert service.base_url == "https://api.semanticscholar.org/v1/paper/arXiv:"
        assert service.cache == {}
        assert service.rate_limit == 1

    def test_get_first_sentence_helper(self):
        """Test the get_first_sentence helper function."""
        # Test with period
        text = "This is the first sentence. This is the second."
        result = get_first_sentence(text)
        assert result == "This is the first sentence."
        
        # Test with exclamation
        text = "This is exciting! This is the second sentence."
        result = get_first_sentence(text)
        assert result == "This is exciting!"
        
        # Test with question
        text = "Is this a question? This is the answer."
        result = get_first_sentence(text)
        assert result == "Is this a question?"
        
        # Test with no ending - should truncate and add ellipsis
        text = "This is a very long text without proper sentence endings that goes on and on"
        result = get_first_sentence(text, max_len=50)
        assert result.endswith("...")
        assert len(result) <= 53  # 50 + "..."

    def test_categories_structure(self):
        """Test that categories have the expected structure."""
        assert isinstance(CATEGORIES, dict)
        assert len(CATEGORIES) > 0
        
        # Test Computer Science category
        assert "cs" in CATEGORIES
        cs_category = CATEGORIES["cs"]
        assert cs_category["name"] == "Computer Science"
        assert "AI" in cs_category["subcategories"]
        assert cs_category["subcategories"]["AI"] == "Artificial Intelligence"

    @pytest.mark.asyncio
    async def test_arxiv_client_rate_limiting(self):
        """Test ArxivClient rate limiting."""
        client = ArxivClient()
        
        # First request should not wait
        start_time = datetime.now()
        await client._wait_for_rate_limit()
        end_time = datetime.now()
        assert (end_time - start_time).total_seconds() < 0.1
        
        # Set last request to recent time to test waiting
        client._last_request = datetime.now() - timedelta(seconds=1)
        start_time = datetime.now()
        await client._wait_for_rate_limit()
        end_time = datetime.now()
        # Should wait approximately 2 seconds (3 - 1)
        assert (end_time - start_time).total_seconds() >= 1.9

    def test_arxiv_client_text_cleaning(self):
        """Test ArxivClient text cleaning."""
        client = ArxivClient()
        
        # Test cleaning messy text
        dirty_text = "  This  is\n\n  some   text\t\twith\nextra   whitespace  "
        clean_text = client._clean_text(dirty_text)
        assert clean_text == "This is some text with extra whitespace"
        
        # Test empty string
        assert client._clean_text("") == ""

    def test_arxiv_client_html_url_generation(self):
        """Test ArxivClient HTML URL generation."""
        client = ArxivClient()
        
        # Test with version
        url = client._get_html_url("2103.08220v1")
        assert url == "https://arxiv.org/html/2103.08220v1"
        
        # Test without version
        url = client._get_html_url("2103.08220")
        assert url == "https://arxiv.org/html/2103.08220"

    @patch('requests.get')
    @patch('time.time')
    def test_citation_service_get_data_success(self, mock_time, mock_get):
        """Test CitationService successful data retrieval."""
        service = CitationService()
        
        # Mock time to avoid rate limiting
        mock_time.side_effect = [0, 2]
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "citationCount": 42,
            "influentialCitationCount": 5,
            "references": [{"paperId": "1"}, {"paperId": "2"}],
            "year": 2021
        }
        mock_get.return_value = mock_response
        
        result = service.get_citation_data("2103.08220")
        
        expected = {
            "citation_count": 42,
            "influential_citations": 5,
            "references": 2,
            "year": 2021
        }
        assert result == expected
        
        # Verify caching
        assert service.cache["2103.08220"] == expected

    @patch('requests.get')
    @patch('time.time')
    def test_citation_service_api_error(self, mock_time, mock_get):
        """Test CitationService handling API errors."""
        service = CitationService()
        
        mock_time.side_effect = [0, 2]
        
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = service.get_citation_data("nonexistent")
        assert result is None

    def test_citation_service_enrich_papers(self):
        """Test CitationService paper enrichment."""
        service = CitationService()
        
        papers = [
            {"id": "2103.08220", "title": "Paper 1"},
            {"id": "1234.5678", "title": "Paper 2"}
        ]
        
        citation_data_1 = {"citation_count": 42, "year": 2021}
        citation_data_2 = {"citation_count": 10, "year": 2020}
        
        with patch.object(service, 'get_citation_data') as mock_get_citation:
            mock_get_citation.side_effect = [citation_data_1, citation_data_2]
            
            result = service.enrich_papers_with_citations(papers)
            
            assert len(result) == 2
            assert result[0]["citation_data"] == citation_data_1
            assert result[1]["citation_data"] == citation_data_2

    def test_citation_service_most_cited_sorting(self):
        """Test CitationService sorting by citation count."""
        service = CitationService()
        
        papers = [
            {"id": "1", "title": "Paper 1"},
            {"id": "2", "title": "Paper 2"},
            {"id": "3", "title": "Paper 3"}
        ]
        
        # Mock enriched papers with different citation counts
        enriched_papers = [
            {"id": "1", "title": "Paper 1", "citation_data": {"citation_count": 10}},
            {"id": "2", "title": "Paper 2", "citation_data": {"citation_count": 50}},
            {"id": "3", "title": "Paper 3", "citation_data": {"citation_count": 25}}
        ]
        
        with patch.object(service, 'enrich_papers_with_citations') as mock_enrich:
            mock_enrich.return_value = enriched_papers
            
            result = service.get_most_cited_papers(papers, limit=2)
            
            assert len(result) == 2
            # Should be sorted by citation count (descending)
            assert result[0]["id"] == "2"  # 50 citations
            assert result[1]["id"] == "3"  # 25 citations

    @patch('builtins.open')
    @patch('builtins.print')
    def test_update_taxonomy_file_creation(self, mock_print, mock_open):
        """Test taxonomy file creation."""
        result = update_taxonomy_file()
        
        # Should return the CATEGORIES dictionary
        assert result == CATEGORIES
        
        # Should attempt to write file
        mock_open.assert_called_once()

    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    @patch('builtins.print')
    def test_load_taxonomy_existing_file(self, mock_print, mock_open, mock_exists):
        """Test loading taxonomy from existing file."""
        mock_exists.return_value = True
        
        # Mock file content
        test_taxonomy = {"test": {"name": "Test", "subcategories": {}}}
        mock_open.return_value.__enter__.return_value.read.return_value = '{"test": {"name": "Test", "subcategories": {}}}'
        
        with patch('json.load') as mock_json_load:
            mock_json_load.return_value = test_taxonomy
            result = load_taxonomy()
            assert result == test_taxonomy

    @pytest.mark.asyncio
    async def test_arxiv_client_parse_entry(self):
        """Test ArxivClient entry parsing."""
        client = ArxivClient()
        
        # Mock complete entry
        entry = {
            'id': 'http://arxiv.org/abs/2103.08220v1',
            'title': '  Test Paper Title  ',
            'authors': [{'name': 'John Doe'}, {'name': 'Jane Smith'}],
            'arxiv_primary_category': {'term': 'cs.AI'},
            'tags': [{'term': 'cs.AI'}, {'term': 'cs.LG'}],
            'published': '2021-03-15T17:58:35Z',
            'updated': '2021-03-16T10:30:00Z',
            'summary': '  This is the abstract  ',
            'arxiv_comment': '  10 pages  ',
            'arxiv_journal_ref': 'Nature 2021',
            'arxiv_doi': '10.1038/example',
            'links': [
                {'type': 'application/pdf', 'href': 'http://arxiv.org/pdf/2103.08220v1.pdf'},
                {'type': 'text/html', 'href': 'http://arxiv.org/abs/2103.08220v1'}
            ]
        }
        
        result = client._parse_entry(entry)
        
        assert result['id'] == '2103.08220v1'
        assert result['title'] == 'Test Paper Title'
        assert result['authors'] == ['John Doe', 'Jane Smith']
        assert result['primary_category'] == 'cs.AI'
        assert result['categories'] == ['cs.LG']  # cs.AI removed as it's primary
        assert result['summary'] == 'This is the abstract'
        assert result['comment'] == '10 pages'
        assert result['journal_ref'] == 'Nature 2021'
        assert result['doi'] == '10.1038/example'
        assert result['pdf_url'] == 'http://arxiv.org/pdf/2103.08220v1.pdf'
        assert result['abstract_url'] == 'http://arxiv.org/abs/2103.08220v1'
        assert result['html_url'] == 'https://arxiv.org/html/2103.08220v1'

    def test_categories_completeness(self):
        """Test that all major categories are present."""
        expected_categories = [
            "cs",      # Computer Science
            "econ",    # Economics
            "eess",    # Electrical Engineering and Systems Science
            "math",    # Mathematics
            "physics", # Physics
            "q-bio",   # Quantitative Biology
            "q-fin",   # Quantitative Finance
            "stat",    # Statistics
        ]
        
        for category in expected_categories:
            assert category in CATEGORIES, f"Missing category: {category}"
            assert isinstance(CATEGORIES[category]["name"], str)
            assert len(CATEGORIES[category]["name"]) > 0
            assert isinstance(CATEGORIES[category]["subcategories"], dict)
            assert len(CATEGORIES[category]["subcategories"]) > 0

    def test_cs_subcategories(self):
        """Test Computer Science subcategories."""
        cs_subcategories = CATEGORIES["cs"]["subcategories"]
        
        # Test some important CS subcategories
        expected_subcategories = [
            "AI",  # Artificial Intelligence
            "LG",  # Machine Learning
            "CV",  # Computer Vision and Pattern Recognition
            "CL",  # Computation and Language
            "RO",  # Robotics
            "CR",  # Cryptography and Security
        ]
        
        for subcategory in expected_subcategories:
            assert subcategory in cs_subcategories, f"Missing CS subcategory: {subcategory}"
            assert isinstance(cs_subcategories[subcategory], str)
            assert len(cs_subcategories[subcategory]) > 0

    @pytest.mark.asyncio
    async def test_arxiv_client_search_mock(self):
        """Test ArxivClient search with mocked HTTP response."""
        client = ArxivClient()
        
        mock_feed_data = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/2103.08220v1</id>
                <title>Test Paper</title>
                <summary>Test abstract</summary>
                <published>2021-03-15T17:58:35Z</published>
                <updated>2021-03-16T10:30:00Z</updated>
                <author><name>John Doe</name></author>
                <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI"/>
                <category term="cs.AI"/>
                <link type="application/pdf" href="http://arxiv.org/pdf/2103.08220v1.pdf"/>
                <link type="text/html" href="http://arxiv.org/abs/2103.08220v1"/>
            </entry>
        </feed>"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.text = mock_feed_data
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Mock rate limiting
            client._wait_for_rate_limit = AsyncMock()
            
            results = await client.search("machine learning", max_results=10)
            
            assert len(results) == 1
            assert results[0]['id'] == '2103.08220v1'
            assert results[0]['title'] == 'Test Paper'
            assert results[0]['summary'] == 'Test abstract'

    def test_integration_categories_consistency(self):
        """Test consistency between categories module and taxonomy functions."""
        # Update taxonomy should return the same data as CATEGORIES
        with patch('builtins.open'), patch('builtins.print'):
            updated_taxonomy = update_taxonomy_file()
            assert updated_taxonomy == CATEGORIES

    def test_module_structure(self):
        """Test that all modules have expected structure."""
        # Test that key classes and functions exist
        assert hasattr(ArxivClient, 'search')
        assert hasattr(ArxivClient, 'get_paper')
        assert hasattr(CitationService, 'get_citation_data')
        assert hasattr(CitationService, 'get_most_cited_papers')
        assert callable(get_first_sentence)
        assert isinstance(CATEGORIES, dict)
        assert callable(load_taxonomy)
        assert callable(update_taxonomy_file)
