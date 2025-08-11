"""
Unit tests for CitationService.
"""

import time
import pytest
import sys
from unittest.mock import Mock, patch
import requests

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.citation_service import CitationService


class TestCitationService:
    """Test cases for CitationService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = CitationService()

    def test_init(self):
        """Test CitationService initialization."""
        assert self.service.base_url == "https://api.semanticscholar.org/v1/paper/arXiv:"
        assert self.service.cache == {}
        assert self.service.rate_limit == 1
        assert self.service.last_request_time == 0

    @patch('requests.get')
    @patch('time.time')
    def test_get_citation_data_success(self, mock_time, mock_get):
        """Test successful citation data retrieval."""
        # Mock time to avoid rate limiting
        mock_time.side_effect = [0, 2]  # First call returns 0, second returns 2
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "citationCount": 42,
            "influentialCitationCount": 5,
            "references": [{"paperId": "1"}, {"paperId": "2"}],
            "year": 2021
        }
        mock_get.return_value = mock_response
        
        result = self.service.get_citation_data("2103.08220")
        
        expected = {
            "citation_count": 42,
            "influential_citations": 5,
            "references": 2,
            "year": 2021
        }
        assert result == expected
        
        # Verify API call
        mock_get.assert_called_once_with("https://api.semanticscholar.org/v1/paper/arXiv:2103.08220")
        
        # Verify caching
        assert self.service.cache["2103.08220"] == expected

    @patch('requests.get')
    @patch('time.time')
    def test_get_citation_data_cached(self, mock_time, mock_get):
        """Test citation data retrieval from cache."""
        # Pre-populate cache
        cached_data = {
            "citation_count": 10,
            "influential_citations": 2,
            "references": 5,
            "year": 2020
        }
        self.service.cache["2103.08220"] = cached_data
        
        result = self.service.get_citation_data("2103.08220")
        
        assert result == cached_data
        # Should not make API call
        mock_get.assert_not_called()

    @patch('requests.get')
    @patch('time.time')
    @patch('time.sleep')
    def test_get_citation_data_rate_limiting(self, mock_sleep, mock_time, mock_get):
        """Test rate limiting functionality."""
        # Mock time to simulate rapid requests
        mock_time.side_effect = [0, 0.5, 1.5]  # Last request was 0.5 seconds ago
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"citationCount": 10}
        mock_get.return_value = mock_response
        
        # Set last request time to simulate recent request
        self.service.last_request_time = 0
        
        self.service.get_citation_data("2103.08220")
        
        # Should sleep for remaining time (1 - 0.5 = 0.5 seconds)
        mock_sleep.assert_called_once_with(0.5)

    @patch('requests.get')
    @patch('time.time')
    def test_get_citation_data_api_error(self, mock_time, mock_get):
        """Test citation data retrieval with API error."""
        mock_time.side_effect = [0, 2]
        
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.service.get_citation_data("nonexistent")
        
        assert result is None
        # Should not cache failed requests
        assert "nonexistent" not in self.service.cache

    @patch('requests.get')
    @patch('time.time')
    def test_get_citation_data_request_exception(self, mock_time, mock_get):
        """Test citation data retrieval with request exception."""
        mock_time.side_effect = [0, 2]
        
        # Mock request exception
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = self.service.get_citation_data("2103.08220")
        
        assert result is None

    @patch('requests.get')
    @patch('time.time')
    def test_get_citation_data_json_error(self, mock_time, mock_get):
        """Test citation data retrieval with JSON parsing error."""
        mock_time.side_effect = [0, 2]
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        result = self.service.get_citation_data("2103.08220")
        
        assert result is None

    @patch('requests.get')
    @patch('time.time')
    def test_get_citation_data_missing_fields(self, mock_time, mock_get):
        """Test citation data retrieval with missing fields in response."""
        mock_time.side_effect = [0, 2]
        
        # Mock response with missing fields
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "citationCount": 10
            # Missing other fields
        }
        mock_get.return_value = mock_response
        
        result = self.service.get_citation_data("2103.08220")
        
        expected = {
            "citation_count": 10,
            "influential_citations": 0,  # Default value
            "references": 0,  # Default value for empty list
            "year": None  # Default value for missing field
        }
        assert result == expected

    def test_enrich_papers_with_citations(self):
        """Test enriching papers with citation data."""
        papers = [
            {"id": "2103.08220", "title": "Paper 1"},
            {"id": "1234.5678", "title": "Paper 2"}
        ]
        
        # Mock citation data
        citation_data_1 = {"citation_count": 42, "year": 2021}
        citation_data_2 = {"citation_count": 10, "year": 2020}
        
        with patch.object(self.service, 'get_citation_data') as mock_get_citation:
            mock_get_citation.side_effect = [citation_data_1, citation_data_2]
            
            result = self.service.enrich_papers_with_citations(papers)
            
            assert len(result) == 2
            assert result[0]["citation_data"] == citation_data_1
            assert result[1]["citation_data"] == citation_data_2
            
            # Verify correct paper IDs were used
            mock_get_citation.assert_any_call("2103.08220")
            mock_get_citation.assert_any_call("1234.5678")

    def test_enrich_papers_with_citations_no_data(self):
        """Test enriching papers when no citation data is available."""
        papers = [
            {"id": "2103.08220", "title": "Paper 1"},
            {"id": "1234.5678", "title": "Paper 2"}
        ]
        
        with patch.object(self.service, 'get_citation_data') as mock_get_citation:
            mock_get_citation.return_value = None
            
            result = self.service.enrich_papers_with_citations(papers)
            
            assert len(result) == 2
            assert "citation_data" not in result[0]
            assert "citation_data" not in result[1]

    def test_enrich_papers_with_citations_mixed_data(self):
        """Test enriching papers with mixed citation data availability."""
        papers = [
            {"id": "2103.08220", "title": "Paper 1"},
            {"id": "1234.5678", "title": "Paper 2"}
        ]
        
        citation_data_1 = {"citation_count": 42, "year": 2021}
        
        with patch.object(self.service, 'get_citation_data') as mock_get_citation:
            mock_get_citation.side_effect = [citation_data_1, None]
            
            result = self.service.enrich_papers_with_citations(papers)
            
            assert len(result) == 2
            assert result[0]["citation_data"] == citation_data_1
            assert "citation_data" not in result[1]

    def test_enrich_papers_with_citations_complex_id(self):
        """Test enriching papers with complex arXiv IDs."""
        papers = [
            {"id": "arxiv:2103.08220v1", "title": "Paper 1"},
            {"id": "http://arxiv.org/abs/1234.5678", "title": "Paper 2"}
        ]
        
        with patch.object(self.service, 'get_citation_data') as mock_get_citation:
            mock_get_citation.return_value = {"citation_count": 10}
            
            self.service.enrich_papers_with_citations(papers)
            
            # Should extract just the ID part
            mock_get_citation.assert_any_call("2103.08220v1")
            mock_get_citation.assert_any_call("1234.5678")

    def test_get_most_cited_papers(self):
        """Test getting most cited papers."""
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
        
        with patch.object(self.service, 'enrich_papers_with_citations') as mock_enrich:
            mock_enrich.return_value = enriched_papers
            
            result = self.service.get_most_cited_papers(papers, limit=2)
            
            assert len(result) == 2
            # Should be sorted by citation count (descending)
            assert result[0]["id"] == "2"  # 50 citations
            assert result[1]["id"] == "3"  # 25 citations

    def test_get_most_cited_papers_no_citation_data(self):
        """Test getting most cited papers when no citation data is available."""
        papers = [
            {"id": "1", "title": "Paper 1"},
            {"id": "2", "title": "Paper 2"}
        ]
        
        # Mock enriched papers without citation data
        enriched_papers = [
            {"id": "1", "title": "Paper 1"},
            {"id": "2", "title": "Paper 2"}
        ]
        
        with patch.object(self.service, 'enrich_papers_with_citations') as mock_enrich:
            mock_enrich.return_value = enriched_papers
            
            result = self.service.get_most_cited_papers(papers, limit=2)
            
            assert len(result) == 2
            # Should return papers in original order when no citation data
            assert result[0]["id"] == "1"
            assert result[1]["id"] == "2"

    def test_get_most_cited_papers_mixed_citation_data(self):
        """Test getting most cited papers with mixed citation data."""
        papers = [
            {"id": "1", "title": "Paper 1"},
            {"id": "2", "title": "Paper 2"},
            {"id": "3", "title": "Paper 3"}
        ]
        
        # Mock enriched papers with mixed citation data
        enriched_papers = [
            {"id": "1", "title": "Paper 1"},  # No citation data
            {"id": "2", "title": "Paper 2", "citation_data": {"citation_count": 30}},
            {"id": "3", "title": "Paper 3", "citation_data": {"citation_count": 10}}
        ]
        
        with patch.object(self.service, 'enrich_papers_with_citations') as mock_enrich:
            mock_enrich.return_value = enriched_papers
            
            result = self.service.get_most_cited_papers(papers, limit=3)
            
            assert len(result) == 3
            # Papers with citation data should come first, sorted by count
            assert result[0]["id"] == "2"  # 30 citations
            assert result[1]["id"] == "3"  # 10 citations
            assert result[2]["id"] == "1"  # 0 citations (default)

    def test_get_most_cited_papers_limit_respected(self):
        """Test that the limit parameter is respected."""
        papers = [
            {"id": str(i), "title": f"Paper {i}"} for i in range(10)
        ]
        
        # Mock enriched papers with citation data
        enriched_papers = [
            {"id": str(i), "title": f"Paper {i}", "citation_data": {"citation_count": i}}
            for i in range(10)
        ]
        
        with patch.object(self.service, 'enrich_papers_with_citations') as mock_enrich:
            mock_enrich.return_value = enriched_papers
            
            result = self.service.get_most_cited_papers(papers, limit=3)
            
            assert len(result) == 3
            # Should return top 3 most cited papers
            assert result[0]["id"] == "9"  # 9 citations
            assert result[1]["id"] == "8"  # 8 citations
            assert result[2]["id"] == "7"  # 7 citations
