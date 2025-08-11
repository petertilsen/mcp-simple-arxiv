"""
Unit tests for ArxivClient.
"""

import asyncio
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import feedparser
import httpx

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.arxiv_client import ArxivClient


class TestArxivClient:
    """Test cases for ArxivClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = ArxivClient()

    def test_init(self):
        """Test ArxivClient initialization."""
        assert self.client.base_url == "https://export.arxiv.org/api/query"
        assert self.client._last_request is None
        assert self.client._lock is not None

    @pytest.mark.asyncio
    async def test_wait_for_rate_limit_first_request(self):
        """Test rate limiting on first request."""
        start_time = datetime.now()
        await self.client._wait_for_rate_limit()
        end_time = datetime.now()
        
        # First request should not wait
        assert (end_time - start_time).total_seconds() < 0.1
        assert self.client._last_request is not None

    @pytest.mark.asyncio
    async def test_wait_for_rate_limit_subsequent_request(self):
        """Test rate limiting on subsequent requests."""
        # Make first request
        await self.client._wait_for_rate_limit()
        first_request_time = self.client._last_request
        
        # Make second request immediately
        start_time = datetime.now()
        await self.client._wait_for_rate_limit()
        end_time = datetime.now()
        
        # Should wait approximately 3 seconds
        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 2.9  # Allow some tolerance
        assert self.client._last_request > first_request_time

    @pytest.mark.asyncio
    async def test_wait_for_rate_limit_after_delay(self):
        """Test rate limiting when enough time has passed."""
        # Set last request to 4 seconds ago
        self.client._last_request = datetime.now() - timedelta(seconds=4)
        
        start_time = datetime.now()
        await self.client._wait_for_rate_limit()
        end_time = datetime.now()
        
        # Should not wait since enough time has passed
        assert (end_time - start_time).total_seconds() < 0.1

    def test_clean_text(self):
        """Test text cleaning functionality."""
        # Test with extra whitespace and newlines
        dirty_text = "  This  is\n\n  some   text\t\twith\nextra   whitespace  "
        clean_text = self.client._clean_text(dirty_text)
        assert clean_text == "This is some text with extra whitespace"
        
        # Test with empty string
        assert self.client._clean_text("") == ""
        
        # Test with already clean text
        clean_input = "This is clean text"
        assert self.client._clean_text(clean_input) == clean_input

    def test_get_html_url(self):
        """Test HTML URL construction."""
        # Test with version suffix
        arxiv_id = "2103.08220v1"
        html_url = self.client._get_html_url(arxiv_id)
        assert html_url == "https://arxiv.org/html/2103.08220v1"
        
        # Test without version suffix
        arxiv_id = "2103.08220"
        html_url = self.client._get_html_url(arxiv_id)
        assert html_url == "https://arxiv.org/html/2103.08220"

    def test_parse_entry_complete(self):
        """Test parsing a complete feed entry."""
        # Mock feed entry with all fields
        entry = {
            'id': 'http://arxiv.org/abs/2103.08220v1',
            'title': '  Test Paper Title  \n\n  ',
            'authors': [{'name': 'John Doe'}, {'name': 'Jane Smith'}],
            'arxiv_primary_category': {'term': 'cs.AI'},
            'tags': [{'term': 'cs.AI'}, {'term': 'cs.LG'}],
            'published': '2021-03-15T17:58:35Z',
            'updated': '2021-03-16T10:30:00Z',
            'summary': '  This is the abstract\nwith multiple lines  ',
            'arxiv_comment': '  10 pages, 5 figures  ',
            'arxiv_journal_ref': 'Nature 2021',
            'arxiv_doi': '10.1038/s41586-021-03819-2',
            'links': [
                {'type': 'application/pdf', 'href': 'http://arxiv.org/pdf/2103.08220v1.pdf'},
                {'type': 'text/html', 'href': 'http://arxiv.org/abs/2103.08220v1'}
            ]
        }
        
        result = self.client._parse_entry(entry)
        
        assert result['id'] == '2103.08220v1'
        assert result['title'] == 'Test Paper Title'
        assert result['authors'] == ['John Doe', 'Jane Smith']
        assert result['primary_category'] == 'cs.AI'
        assert result['categories'] == ['cs.LG']  # cs.AI removed as it's primary
        assert result['published'] == '2021-03-15T17:58:35Z'
        assert result['updated'] == '2021-03-16T10:30:00Z'
        assert result['summary'] == 'This is the abstract with multiple lines'
        assert result['comment'] == '10 pages, 5 figures'
        assert result['journal_ref'] == 'Nature 2021'
        assert result['doi'] == '10.1038/s41586-021-03819-2'
        assert result['pdf_url'] == 'http://arxiv.org/pdf/2103.08220v1.pdf'
        assert result['abstract_url'] == 'http://arxiv.org/abs/2103.08220v1'
        assert result['html_url'] == 'https://arxiv.org/html/2103.08220v1'

    def test_parse_entry_minimal(self):
        """Test parsing a minimal feed entry."""
        entry = {
            'id': 'http://arxiv.org/abs/1234.5678',
            'title': 'Minimal Paper',
            'authors': [],
            'tags': [],
            'published': '2021-01-01T00:00:00Z',
            'updated': '2021-01-01T00:00:00Z',
            'summary': 'Minimal abstract',
            'links': []
        }
        
        result = self.client._parse_entry(entry)
        
        assert result['id'] == '1234.5678'
        assert result['title'] == 'Minimal Paper'
        assert result['authors'] == []
        assert result['primary_category'] is None
        assert result['categories'] == []
        assert result['summary'] == 'Minimal abstract'
        assert result['comment'] == ''
        assert result['journal_ref'] == ''
        assert result['doi'] == ''
        assert result['pdf_url'] is None
        assert result['abstract_url'] is None
        assert result['html_url'] == 'https://arxiv.org/html/1234.5678'

    def test_parse_entry_with_object_attributes(self):
        """Test parsing entry with object-style attributes."""
        # Mock objects with attributes instead of dictionaries
        class MockAuthor:
            def __init__(self, name):
                self.name = name
        
        class MockCategory:
            def __init__(self, term):
                self.term = term
        
        class MockPrimaryCategory:
            def __init__(self, term):
                self.term = term
        
        entry = {
            'id': 'http://arxiv.org/abs/2103.08220',
            'title': 'Test Paper',
            'authors': [MockAuthor('John Doe'), MockAuthor('Jane Smith')],
            'arxiv_primary_category': MockPrimaryCategory('cs.AI'),
            'tags': [MockCategory('cs.AI'), MockCategory('cs.LG')],
            'published': '2021-03-15T17:58:35Z',
            'updated': '2021-03-16T10:30:00Z',
            'summary': 'Test abstract',
            'links': []
        }
        
        result = self.client._parse_entry(entry)
        
        assert result['authors'] == ['John Doe', 'Jane Smith']
        assert result['primary_category'] == 'cs.AI'
        assert result['categories'] == ['cs.LG']

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful search operation."""
        # Mock response data
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
            self.client._wait_for_rate_limit = AsyncMock()
            
            results = await self.client.search("machine learning", max_results=10)
            
            assert len(results) == 1
            assert results[0]['id'] == '2103.08220v1'
            assert results[0]['title'] == 'Test Paper'
            assert results[0]['summary'] == 'Test abstract'
            
            # Verify API call parameters
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            assert call_args[0][0] == self.client.base_url
            assert call_args[1]['params']['search_query'] == 'machine learning'
            assert call_args[1]['params']['max_results'] == 10

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no results."""
        mock_feed_data = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        </feed>"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.text = mock_feed_data
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            self.client._wait_for_rate_limit = AsyncMock()
            
            results = await self.client.search("nonexistent query")
            
            assert results == []

    @pytest.mark.asyncio
    async def test_search_max_results_limit(self):
        """Test search respects max_results limit."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.text = '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            self.client._wait_for_rate_limit = AsyncMock()
            
            # Test with max_results > 2000 (API limit)
            await self.client.search("test", max_results=3000)
            
            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            assert call_args[1]['params']['max_results'] == 2000

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """Test search with HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )
            self.client._wait_for_rate_limit = AsyncMock()
            
            with pytest.raises(ValueError, match="arXiv API HTTP error"):
                await self.client.search("test query")

    @pytest.mark.asyncio
    async def test_search_invalid_response(self):
        """Test search with invalid response."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.text = "Invalid XML data"
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            self.client._wait_for_rate_limit = AsyncMock()
            
            with patch('feedparser.parse') as mock_parse:
                mock_parse.return_value = "invalid"  # Not a dict
                
                with pytest.raises(ValueError, match="Invalid response from arXiv API"):
                    await self.client.search("test query")

    @pytest.mark.asyncio
    async def test_get_paper_success(self):
        """Test successful paper retrieval."""
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
            self.client._wait_for_rate_limit = AsyncMock()
            
            result = await self.client.get_paper("2103.08220")
            
            assert result['id'] == '2103.08220v1'
            assert result['title'] == 'Test Paper'
            assert result['summary'] == 'Test abstract'
            
            # Verify API call parameters
            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            assert call_args[1]['params']['id_list'] == '2103.08220'
            assert call_args[1]['params']['max_results'] == 1

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self):
        """Test paper retrieval when paper doesn't exist."""
        mock_feed_data = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        </feed>"""
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.text = mock_feed_data
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            self.client._wait_for_rate_limit = AsyncMock()
            
            with pytest.raises(ValueError, match="Paper not found: nonexistent"):
                await self.client.get_paper("nonexistent")

    @pytest.mark.asyncio
    async def test_get_paper_http_error(self):
        """Test paper retrieval with HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )
            self.client._wait_for_rate_limit = AsyncMock()
            
            with pytest.raises(ValueError, match="arXiv API HTTP error"):
                await self.client.get_paper("2103.08220")

    @pytest.mark.asyncio
    async def test_get_paper_invalid_response(self):
        """Test paper retrieval with invalid response."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.text = "Invalid XML data"
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            self.client._wait_for_rate_limit = AsyncMock()
            
            with patch('feedparser.parse') as mock_parse:
                mock_parse.return_value = {}  # Missing 'entries' key
                
                with pytest.raises(ValueError, match="Invalid response from arXiv API"):
                    await self.client.get_paper("2103.08220")
