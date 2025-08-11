"""
Unit tests for the MCP server.
"""

import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
import mcp.types as types

# Add a mock reconfigure method to stdin/stdout if it doesn't exist
if not hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure = lambda **kwargs: None
if not hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure = lambda **kwargs: None

from mcp_simple_arxiv.server import app, get_first_sentence


class TestServerHelpers:
    """Test cases for server helper functions."""

    def test_get_first_sentence_with_period(self):
        """Test extracting first sentence ending with period."""
        text = "This is the first sentence. This is the second sentence."
        result = get_first_sentence(text)
        assert result == "This is the first sentence."

    def test_get_first_sentence_with_exclamation(self):
        """Test extracting first sentence ending with exclamation."""
        text = "This is exciting! This is the second sentence."
        result = get_first_sentence(text)
        assert result == "This is exciting!"

    def test_get_first_sentence_with_question(self):
        """Test extracting first sentence ending with question mark."""
        text = "Is this a question? This is the answer."
        result = get_first_sentence(text)
        assert result == "Is this a question?"

    def test_get_first_sentence_no_ending(self):
        """Test extracting first sentence when no sentence ending found."""
        text = "This is a very long text without proper sentence endings that goes on and on"
        result = get_first_sentence(text, max_len=50)
        assert result == "This is a very long text without proper sentence"
        assert result.endswith("...")

    def test_get_first_sentence_short_text(self):
        """Test extracting first sentence from short text."""
        text = "Short text"
        result = get_first_sentence(text)
        assert result == "Short text"

    def test_get_first_sentence_empty_text(self):
        """Test extracting first sentence from empty text."""
        text = ""
        result = get_first_sentence(text)
        assert result == ""

    def test_get_first_sentence_sentence_too_long(self):
        """Test extracting first sentence when sentence is longer than max_len."""
        text = "This is a very long sentence that exceeds the maximum length limit and should be truncated properly. This is the second sentence."
        result = get_first_sentence(text, max_len=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_get_first_sentence_sentence_at_max_len(self):
        """Test extracting first sentence when sentence is exactly at max_len."""
        text = "This sentence is exactly fifty characters long. Second sentence."
        result = get_first_sentence(text, max_len=50)
        assert result == "This sentence is exactly fifty characters long."


class TestServerTools:
    """Test cases for MCP server tool definitions."""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test that list_tools returns all expected tools."""
        tools = await app.list_tools()
        
        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "search_papers",
            "get_paper_data", 
            "list_categories",
            "update_categories",
            "get_most_cited_papers"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_structure(self):
        """Test that tools have the correct structure."""
        tools = await app.list_tools()
        
        for tool in tools:
            assert isinstance(tool, types.Tool)
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.inputSchema, dict)

    @pytest.mark.asyncio
    async def test_search_papers_tool_schema(self):
        """Test search_papers tool schema."""
        tools = await app.list_tools()
        search_tool = next(tool for tool in tools if tool.name == "search_papers")
        
        schema = search_tool.inputSchema
        assert schema["type"] == "object"
        assert "query" in schema["required"]
        assert "query" in schema["properties"]
        assert "max_results" in schema["properties"]
        
        # Check query property
        query_prop = schema["properties"]["query"]
        assert query_prop["type"] == "string"
        
        # Check max_results property
        max_results_prop = schema["properties"]["max_results"]
        assert max_results_prop["type"] == "number"
        assert max_results_prop["minimum"] == 1
        assert max_results_prop["maximum"] == 50

    @pytest.mark.asyncio
    async def test_get_paper_data_tool_schema(self):
        """Test get_paper_data tool schema."""
        tools = await app.list_tools()
        paper_tool = next(tool for tool in tools if tool.name == "get_paper_data")
        
        schema = paper_tool.inputSchema
        assert schema["type"] == "object"
        assert "paper_id" in schema["required"]
        assert "paper_id" in schema["properties"]
        
        paper_id_prop = schema["properties"]["paper_id"]
        assert paper_id_prop["type"] == "string"


class TestServerToolCalls:
    """Test cases for MCP server tool call handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_arxiv_client = Mock()
        self.mock_citation_service = Mock()

    @pytest.mark.asyncio
    async def test_search_papers_success(self):
        """Test successful search_papers tool call."""
        # Mock search results
        mock_papers = [
            {
                "id": "2103.08220",
                "title": "Test Paper",
                "authors": ["John Doe", "Jane Smith"],
                "primary_category": "cs.AI",
                "categories": ["cs.LG"],
                "published": "2021-03-15T17:58:35Z",
                "summary": "This is a test abstract with multiple sentences. This is the second sentence."
            }
        ]
        
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.search = AsyncMock(return_value=mock_papers)
            
            result = await app.call_tool("search_papers", {"query": "machine learning", "max_results": 10})
            
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            assert "Test Paper" in result[0].text
            assert "John Doe, Jane Smith" in result[0].text
            assert "2103.08220" in result[0].text
            assert "Primary: cs.AI" in result[0].text
            assert "Additional: cs.LG" in result[0].text
            
            # Verify client was called correctly
            mock_client.search.assert_called_once_with("machine learning", 10)

    @pytest.mark.asyncio
    async def test_search_papers_default_max_results(self):
        """Test search_papers with default max_results."""
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.search = AsyncMock(return_value=[])
            
            await app.call_tool("search_papers", {"query": "test"})
            
            # Should use default max_results of 10
            mock_client.search.assert_called_once_with("test", 10)

    @pytest.mark.asyncio
    async def test_search_papers_max_results_limit(self):
        """Test search_papers respects max_results limit."""
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.search = AsyncMock(return_value=[])
            
            await app.call_tool("search_papers", {"query": "test", "max_results": 100})
            
            # Should limit to 50
            mock_client.search.assert_called_once_with("test", 50)

    @pytest.mark.asyncio
    async def test_get_paper_data_success(self):
        """Test successful get_paper_data tool call."""
        mock_paper = {
            "id": "2103.08220",
            "title": "Test Paper",
            "authors": ["John Doe"],
            "primary_category": "cs.AI",
            "categories": ["cs.LG"],
            "published": "2021-03-15T17:58:35Z",
            "updated": "2021-03-16T10:30:00Z",
            "summary": "This is a test abstract.",
            "comment": "10 pages, 5 figures",
            "journal_ref": "Nature 2021",
            "doi": "10.1038/example",
            "abstract_url": "http://arxiv.org/abs/2103.08220",
            "html_url": "https://arxiv.org/html/2103.08220",
            "pdf_url": "http://arxiv.org/pdf/2103.08220.pdf"
        }
        
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.get_paper = AsyncMock(return_value=mock_paper)
            
            result = await app.call_tool("get_paper_data", {"paper_id": "2103.08220"})
            
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            text = result[0].text
            
            # Check all sections are present
            assert "Title: Test Paper" in text
            assert "Metadata:" in text
            assert "Authors: John Doe" in text
            assert "Primary: cs.AI" in text
            assert "DOI: 10.1038/example" in text
            assert "Journal Reference: Nature 2021" in text
            assert "Abstract:" in text
            assert "This is a test abstract." in text
            assert "Access Options:" in text
            assert "Abstract page: http://arxiv.org/abs/2103.08220" in text
            assert "Full text HTML version: https://arxiv.org/html/2103.08220" in text
            assert "PDF version: http://arxiv.org/pdf/2103.08220.pdf" in text
            assert "Additional Information:" in text
            assert "Comment: 10 pages, 5 figures" in text
            
            mock_client.get_paper.assert_called_once_with("2103.08220")

    @pytest.mark.asyncio
    async def test_get_paper_data_minimal(self):
        """Test get_paper_data with minimal paper data."""
        mock_paper = {
            "id": "1234.5678",
            "title": "Minimal Paper",
            "authors": [],
            "primary_category": None,
            "categories": [],
            "published": "2021-01-01T00:00:00Z",
            "updated": "2021-01-01T00:00:00Z",
            "summary": "Minimal abstract",
            "comment": "",
            "journal_ref": "",
            "doi": "",
            "abstract_url": "http://arxiv.org/abs/1234.5678",
            "html_url": None,
            "pdf_url": "http://arxiv.org/pdf/1234.5678.pdf"
        }
        
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.get_paper = AsyncMock(return_value=mock_paper)
            
            result = await app.call_tool("get_paper_data", {"paper_id": "1234.5678"})
            
            text = result[0].text
            assert "Title: Minimal Paper" in text
            assert "Authors: " in text  # Empty authors
            assert "Categories: " in text  # Empty categories
            assert "DOI:" not in text  # No DOI section
            assert "Journal Reference:" not in text  # No journal ref section
            assert "Full text HTML version:" not in text  # No HTML version

    @pytest.mark.asyncio
    async def test_list_categories_success(self):
        """Test successful list_categories tool call."""
        mock_taxonomy = {
            "cs": {
                "name": "Computer Science",
                "subcategories": {
                    "AI": "Artificial Intelligence",
                    "LG": "Machine Learning"
                }
            },
            "math": {
                "name": "Mathematics", 
                "subcategories": {
                    "NT": "Number Theory"
                }
            }
        }
        
        with patch('mcp_simple_arxiv.server.load_taxonomy') as mock_load:
            mock_load.return_value = mock_taxonomy
            
            result = await app.call_tool("list_categories", {})
            
            assert len(result) == 1
            text = result[0].text
            
            assert "arXiv Categories:" in text
            assert "cs: Computer Science" in text
            assert "cs.AI: Artificial Intelligence" in text
            assert "cs.LG: Machine Learning" in text
            assert "math: Mathematics" in text
            assert "math.NT: Number Theory" in text
            assert "Usage in search:" in text
            assert "cat:cs.AI" in text

    @pytest.mark.asyncio
    async def test_list_categories_with_filter(self):
        """Test list_categories with primary_category filter."""
        mock_taxonomy = {
            "cs": {
                "name": "Computer Science",
                "subcategories": {"AI": "Artificial Intelligence"}
            },
            "math": {
                "name": "Mathematics",
                "subcategories": {"NT": "Number Theory"}
            }
        }
        
        with patch('mcp_simple_arxiv.server.load_taxonomy') as mock_load:
            mock_load.return_value = mock_taxonomy
            
            result = await app.call_tool("list_categories", {"primary_category": "cs"})
            
            text = result[0].text
            assert "cs: Computer Science" in text
            assert "cs.AI: Artificial Intelligence" in text
            assert "math: Mathematics" not in text

    @pytest.mark.asyncio
    async def test_list_categories_load_error(self):
        """Test list_categories when taxonomy loading fails."""
        with patch('mcp_simple_arxiv.server.load_taxonomy') as mock_load:
            mock_load.side_effect = Exception("Load error")
            
            result = await app.call_tool("list_categories", {})
            
            text = result[0].text
            assert "Error loading category taxonomy" in text
            assert "update_categories" in text

    @pytest.mark.asyncio
    async def test_update_categories_success(self):
        """Test successful update_categories tool call."""
        mock_taxonomy = {
            "cs": {
                "name": "Computer Science",
                "subcategories": {"AI": "Artificial Intelligence"}
            }
        }
        
        with patch('mcp_simple_arxiv.server.update_taxonomy_file') as mock_update:
            mock_update.return_value = mock_taxonomy
            
            result = await app.call_tool("update_categories", {})
            
            text = result[0].text
            assert "Successfully updated category taxonomy" in text
            assert "Found 1 primary categories" in text
            assert "cs: Computer Science (1 subcategories)" in text

    @pytest.mark.asyncio
    async def test_update_categories_error(self):
        """Test update_categories when update fails."""
        with patch('mcp_simple_arxiv.server.update_taxonomy_file') as mock_update:
            mock_update.side_effect = Exception("Update error")
            
            result = await app.call_tool("update_categories", {})
            
            assert result[0].isError is True
            assert "Error updating taxonomy: Update error" in result[0].text

    @pytest.mark.asyncio
    async def test_get_most_cited_papers_success(self):
        """Test successful get_most_cited_papers tool call."""
        mock_papers = [
            {
                "id": "2103.08220",
                "title": "Test Paper 1",
                "authors": ["John Doe"],
                "published": "2021-03-15T17:58:35Z",
                "summary": "First test abstract."
            }
        ]
        
        mock_cited_papers = [
            {
                "id": "2103.08220",
                "title": "Test Paper 1",
                "authors": ["John Doe"],
                "published": "2021-03-15T17:58:35Z",
                "summary": "First test abstract.",
                "citation_data": {"citation_count": 42, "year": 2021}
            }
        ]
        
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client, \
             patch('mcp_simple_arxiv.server.citation_service') as mock_service:
            
            mock_client.search = AsyncMock(return_value=mock_papers)
            mock_service.get_most_cited_papers.return_value = mock_cited_papers
            
            result = await app.call_tool("get_most_cited_papers", {
                "query": "machine learning",
                "max_results": 20,
                "limit": 5
            })
            
            text = result[0].text
            assert "Most Cited Papers for 'machine learning'" in text
            assert "Test Paper 1" in text
            assert "Citations: 42" in text
            assert "Year: 2021" in text
            assert "Semantic Scholar API" in text
            
            mock_client.search.assert_called_once_with("machine learning", 20)
            mock_service.get_most_cited_papers.assert_called_once_with(mock_papers, 5)

    @pytest.mark.asyncio
    async def test_get_most_cited_papers_no_results(self):
        """Test get_most_cited_papers when no papers found."""
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.search = AsyncMock(return_value=[])
            
            result = await app.call_tool("get_most_cited_papers", {"query": "nonexistent"})
            
            text = result[0].text
            assert "No papers found matching query: nonexistent" in text

    @pytest.mark.asyncio
    async def test_get_most_cited_papers_no_citation_data(self):
        """Test get_most_cited_papers when no citation data available."""
        mock_papers = [{"id": "1234.5678", "title": "Test Paper"}]
        
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client, \
             patch('mcp_simple_arxiv.server.citation_service') as mock_service:
            
            mock_client.search = AsyncMock(return_value=mock_papers)
            mock_service.get_most_cited_papers.return_value = []
            
            result = await app.call_tool("get_most_cited_papers", {"query": "test"})
            
            text = result[0].text
            assert "No citation data available" in text

    @pytest.mark.asyncio
    async def test_get_most_cited_papers_defaults(self):
        """Test get_most_cited_papers with default parameters."""
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client, \
             patch('mcp_simple_arxiv.server.citation_service') as mock_service:
            
            mock_client.search = AsyncMock(return_value=[])
            mock_service.get_most_cited_papers.return_value = []
            
            await app.call_tool("get_most_cited_papers", {"query": "test"})
            
            # Should use defaults: max_results=20, limit=5
            mock_client.search.assert_called_once_with("test", 20)

    @pytest.mark.asyncio
    async def test_get_most_cited_papers_limits(self):
        """Test get_most_cited_papers respects limits."""
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client, \
             patch('mcp_simple_arxiv.server.citation_service') as mock_service:
            
            mock_client.search = AsyncMock(return_value=[])
            mock_service.get_most_cited_papers.return_value = []
            
            await app.call_tool("get_most_cited_papers", {
                "query": "test",
                "max_results": 100,  # Should be limited to 50
                "limit": 30  # Should be limited to 20
            })
            
            mock_client.search.assert_called_once_with("test", 50)
            mock_service.get_most_cited_papers.assert_called_once_with([], 20)

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling unknown tool."""
        result = await app.call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert result[0].isError is True
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_tool_call_exception(self):
        """Test tool call with exception."""
        with patch('mcp_simple_arxiv.server.arxiv_client') as mock_client:
            mock_client.search = AsyncMock(side_effect=Exception("Test error"))
            
            result = await app.call_tool("search_papers", {"query": "test"})
            
            assert len(result) == 1
            assert result[0].isError is True
            assert "Error: Test error" in result[0].text
