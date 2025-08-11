"""
Integration tests for the MCP simple arXiv implementation.
"""

import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
import json

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.server import app
from mcp_simple_arxiv.arxiv_client import ArxivClient
from mcp_simple_arxiv.citation_service import CitationService


class TestIntegration:
    """Integration tests that test multiple components working together."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self, mock_httpx_client, mock_arxiv_response):
        """Test complete search workflow from server to client."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = mock_arxiv_response
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test the full workflow
        result = await app.call_tool("search_papers", {
            "query": "machine learning",
            "max_results": 5
        })
        
        assert len(result) == 1
        text = result[0].text
        
        # Verify the formatted output contains expected information
        assert "Search Results:" in text
        assert "Test Paper Title" in text
        assert "John Doe, Jane Smith" in text
        assert "2103.08220v1" in text
        assert "Primary: cs.AI" in text
        assert "Additional: cs.LG" in text
        assert "This is a test abstract" in text

    @pytest.mark.asyncio
    async def test_full_paper_retrieval_workflow(self, mock_httpx_client, mock_arxiv_response):
        """Test complete paper retrieval workflow."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = mock_arxiv_response
        mock_response.raise_for_status = Mock()
        
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test the full workflow
        result = await app.call_tool("get_paper_data", {"paper_id": "2103.08220"})
        
        assert len(result) == 1
        text = result[0].text
        
        # Verify all sections are present and formatted correctly
        assert "Title: Test Paper Title" in text
        assert "Metadata:" in text
        assert "Authors: John Doe, Jane Smith" in text
        assert "Primary: cs.AI, Additional: cs.LG" in text
        assert "DOI: 10.1038/s41586-021-03819-2" in text
        assert "Abstract:" in text
        assert "Access Options:" in text
        assert "Additional Information:" in text
        assert "Comment: 10 pages, 5 figures" in text

    @pytest.mark.asyncio
    async def test_citation_workflow_integration(self, mock_httpx_client, mock_arxiv_response, mock_requests, mock_time):
        """Test integration of search with citation service."""
        # Mock arXiv API response
        mock_response = Mock()
        mock_response.text = mock_arxiv_response
        mock_response.raise_for_status = Mock()
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Mock Semantic Scholar API response
        mock_citation_response = Mock()
        mock_citation_response.status_code = 200
        mock_citation_response.json.return_value = {
            "citationCount": 42,
            "influentialCitationCount": 5,
            "references": [{"paperId": "1"}, {"paperId": "2"}],
            "year": 2021
        }
        mock_requests.return_value = mock_citation_response
        
        # Mock time for rate limiting
        mock_time['time'].side_effect = [0, 2, 4]
        
        # Test the full workflow
        result = await app.call_tool("get_most_cited_papers", {
            "query": "machine learning",
            "max_results": 10,
            "limit": 3
        })
        
        assert len(result) == 1
        text = result[0].text
        
        # Verify citation data is included
        assert "Most Cited Papers" in text
        assert "Test Paper Title" in text
        assert "Citations: 42" in text
        assert "Year: 2021" in text
        assert "Semantic Scholar API" in text

    @pytest.mark.asyncio
    async def test_taxonomy_workflow_integration(self, sample_taxonomy):
        """Test taxonomy loading and listing workflow."""
        with patch('mcp_simple_arxiv.server.load_taxonomy') as mock_load:
            mock_load.return_value = sample_taxonomy
            
            result = await app.call_tool("list_categories", {})
            
            text = result[0].text
            
            # Verify taxonomy is properly formatted
            assert "arXiv Categories:" in text
            assert "cs: Computer Science" in text
            assert "cs.AI: Artificial Intelligence" in text
            assert "math: Mathematics" in text
            assert "Usage in search:" in text

    @pytest.mark.asyncio
    async def test_taxonomy_update_workflow(self, sample_taxonomy):
        """Test taxonomy update workflow."""
        with patch('mcp_simple_arxiv.server.update_taxonomy_file') as mock_update:
            mock_update.return_value = sample_taxonomy
            
            result = await app.call_tool("update_categories", {})
            
            text = result[0].text
            
            # Verify update success message
            assert "Successfully updated category taxonomy" in text
            assert "Found 2 primary categories" in text
            assert "cs: Computer Science (3 subcategories)" in text
            assert "math: Mathematics (2 subcategories)" in text

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_httpx_client):
        """Test error handling across the full stack."""
        # Mock HTTP error
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Network error")
        )
        
        result = await app.call_tool("search_papers", {"query": "test"})
        
        assert len(result) == 1
        assert result[0].isError is True
        assert "Error:" in result[0].text

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_httpx_client, mock_arxiv_response):
        """Test that rate limiting works in the full workflow."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = mock_arxiv_response
        mock_response.raise_for_status = Mock()
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Create a real ArxivClient to test rate limiting
        client = ArxivClient()
        
        # Mock the rate limiting method to track calls
        original_wait = client._wait_for_rate_limit
        client._wait_for_rate_limit = AsyncMock(side_effect=original_wait)
        
        with patch('mcp_simple_arxiv.server.arxiv_client', client):
            # Make multiple calls
            await app.call_tool("search_papers", {"query": "test1"})
            await app.call_tool("search_papers", {"query": "test2"})
            
            # Verify rate limiting was called
            assert client._wait_for_rate_limit.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_results_integration(self, mock_httpx_client, mock_empty_arxiv_response):
        """Test handling of empty results across the full stack."""
        # Mock empty HTTP response
        mock_response = Mock()
        mock_response.text = mock_empty_arxiv_response
        mock_response.raise_for_status = Mock()
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Test search with no results
        result = await app.call_tool("search_papers", {"query": "nonexistent"})
        
        text = result[0].text
        assert "Search Results:" in text
        # Should handle empty results gracefully
        
        # Test citation workflow with no results
        result = await app.call_tool("get_most_cited_papers", {"query": "nonexistent"})
        
        text = result[0].text
        assert "No papers found matching query: nonexistent" in text

    @pytest.mark.asyncio
    async def test_parameter_validation_integration(self):
        """Test parameter validation across the full stack."""
        # Test with very large max_results
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.search = AsyncMock(return_value=[])
            
            await app.call_tool("search_papers", {
                "query": "test",
                "max_results": 5000  # Should be limited to 50
            })
            
            # Verify the limit was applied
            mock_client.search.assert_called_once_with("test", 50)

    @pytest.mark.asyncio
    async def test_text_formatting_integration(self, mock_httpx_client):
        """Test text formatting and cleaning across the full stack."""
        # Mock response with messy text
        messy_response = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/1234.5678</id>
                <title>  Messy   Title\n\n  With   Whitespace  </title>
                <summary>  This is a messy\n\nabstract with\textra   whitespace  </summary>
                <published>2021-01-01T00:00:00Z</published>
                <updated>2021-01-01T00:00:00Z</updated>
                <author><name>Test Author</name></author>
            </entry>
        </feed>"""
        
        mock_response = Mock()
        mock_response.text = messy_response
        mock_response.raise_for_status = Mock()
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        result = await app.call_tool("search_papers", {"query": "test"})
        
        text = result[0].text
        
        # Verify text was cleaned properly
        assert "Messy Title With Whitespace" in text
        assert "This is a messy abstract with extra whitespace" in text
        # Should not contain extra whitespace or newlines
        assert "\n\n" not in text.replace("Search Results:\n\n", "")

    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, mock_httpx_client, mock_arxiv_response):
        """Test handling of concurrent requests."""
        import asyncio
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = mock_arxiv_response
        mock_response.raise_for_status = Mock()
        mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        # Make concurrent requests
        tasks = [
            app.call_tool("search_papers", {"query": f"test{i}"})
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert len(results) == 3
        for result in results:
            assert len(result) == 1
            assert "Search Results:" in result[0].text

    def test_module_imports(self):
        """Test that all modules can be imported without errors."""
        # This test ensures all modules are properly structured
        from mcp_simple_arxiv import server
        from mcp_simple_arxiv import arxiv_client
        from mcp_simple_arxiv import citation_service
        from mcp_simple_arxiv import categories
        from mcp_simple_arxiv import update_taxonomy
        
        # Verify key classes and functions exist
        assert hasattr(server, 'app')
        assert hasattr(server, 'get_first_sentence')
        assert hasattr(arxiv_client, 'ArxivClient')
        assert hasattr(citation_service, 'CitationService')
        assert hasattr(categories, 'CATEGORIES')
        assert hasattr(update_taxonomy, 'load_taxonomy')
        assert hasattr(update_taxonomy, 'update_taxonomy_file')

    def test_categories_consistency(self):
        """Test consistency between categories module and taxonomy functions."""
        from mcp_simple_arxiv.categories import CATEGORIES
        from mcp_simple_arxiv.update_taxonomy import update_taxonomy_file
        
        # Update taxonomy should return the same data as CATEGORIES
        updated_taxonomy = update_taxonomy_file()
        assert updated_taxonomy == CATEGORIES
