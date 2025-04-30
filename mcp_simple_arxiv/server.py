"""
MCP server for accessing arXiv papers.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

import asyncio
import json
import logging
from typing import Any, Sequence

from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

from .arxiv_client import ArxivClient
from .citation_service import CitationService
from .update_taxonomy import load_taxonomy, update_taxonomy_file

logger = logging.getLogger(__name__)

def get_first_sentence(text: str, max_len: int = 200) -> str:
    """Extract first sentence from text, limiting length."""
    # Look for common sentence endings
    for end in ['. ', '! ', '? ']:
        pos = text.find(end)
        if pos != -1 and pos < max_len:
            return text[:pos + 1]
    # If no sentence ending found, just take first max_len chars
    if len(text) > max_len:
        return text[:max_len].rstrip() + '...'
    return text

app = Server("arxiv-server")
arxiv_client = ArxivClient()
citation_service = CitationService()

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools for interacting with arXiv."""
    return [
        types.Tool(
            name="search_papers",
            description="""Search for papers on arXiv by title and abstract content.
            
You can use advanced search syntax:
- Search in title: ti:"search terms"
- Search in abstract: abs:"search terms"
- Search by author: au:"author name"
- Combine terms with: AND, OR, ANDNOT
- Filter by category: cat:cs.AI (use list_categories tool to see available categories)

Examples:
- "machine learning"  (searches all fields)
- ti:"neural networks" AND cat:cs.AI  (title with category)
- au:bengio AND ti:"deep learning"  (author and title)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against paper titles and abstracts"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of results to return (default: 10)",
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_paper_data",
            description="Get detailed information about a specific paper including abstract and available formats",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "arXiv paper ID (e.g., '2103.08220')"
                    }
                },
                "required": ["paper_id"]
            }
        ),
        types.Tool(
            name="list_categories",
            description="List all available arXiv categories and how to use them in search",
            inputSchema={
                "type": "object",
                "properties": {
                    "primary_category": {
                        "type": "string",
                        "description": "Optional: filter by primary category (e.g., 'cs' for Computer Science)"
                    }
                }
            }
        ),
        types.Tool(
            name="update_categories",
            description="Update the stored category taxonomy by fetching the latest version from arxiv.org",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="get_most_cited_papers",
            description="Find the most cited papers on arXiv for a given topic using citation data from Semantic Scholar",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against paper titles and abstracts"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "Maximum number of papers to search through (default: 20)",
                        "minimum": 5,
                        "maximum": 50
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of cited papers to return (default: 5)",
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls for arXiv operations."""
    
    try:
        if name == "search_papers":
            query = arguments["query"]
            max_results = min(int(arguments.get("max_results", 10)), 50)
            
            papers = await arxiv_client.search(query, max_results)
            
            # Format results in a readable way
            result = "Search Results:\n\n"
            for i, paper in enumerate(papers, 1):
                result += f"{i}. {paper['title']}\n"
                result += f"   Authors: {', '.join(paper['authors'])}\n"
                result += f"   ID: {paper['id']}\n"
                result += f"   Categories: "
                if paper['primary_category']:
                    result += f"Primary: {paper['primary_category']}"
                if paper['categories']:
                    result += f", Additional: {', '.join(paper['categories'])}"
                result += f"\n   Published: {paper['published']}\n"
                
                # Add first sentence of abstract
                abstract_preview = get_first_sentence(paper['summary'])
                result += f"   Preview: {abstract_preview}\n"
                result += "\n"
            
            return [types.TextContent(type="text", text=result)]
            
        elif name == "get_paper_data":
            paper_id = arguments["paper_id"]
            paper = await arxiv_client.get_paper(paper_id)
            
            # Format paper details in a readable way with clear sections
            result = f"Title: {paper['title']}\n\n"
            
            # Metadata section
            result += "Metadata:\n"
            result += f"- Authors: {', '.join(paper['authors'])}\n"
            result += f"- Published: {paper['published']}\n"
            result += f"- Last Updated: {paper['updated']}\n"
            result += "- Categories: "
            if paper['primary_category']:
                result += f"Primary: {paper['primary_category']}"
            if paper['categories']:
                result += f", Additional: {', '.join(paper['categories'])}"
            result += "\n"
            
            if paper['doi']:
                result += f"- DOI: {paper['doi']}\n"
            if paper["journal_ref"]:
                result += f"- Journal Reference: {paper['journal_ref']}\n"
            
            # Abstract section
            result += "\nAbstract:\n"
            result += paper["summary"]
            result += "\n"
            
            # Access options section
            result += "\nAccess Options:\n"
            result += "- Abstract page: " + paper["abstract_url"] + "\n"
            if paper["html_url"]:  # Add HTML version if available
                result += "- Full text HTML version: " + paper["html_url"] + "\n"
            result += "- PDF version: " + paper["pdf_url"] + "\n"
            
            # Additional information section
            if paper["comment"] or "code" in paper["comment"].lower():
                result += "\nAdditional Information:\n"
                if paper["comment"]:
                    result += "- Comment: " + paper["comment"] + "\n"
            
            return [types.TextContent(type="text", text=result)]

        elif name == "list_categories":
            try:
                taxonomy = load_taxonomy()
            except Exception as e:
                logger.error(f"Error loading taxonomy: {e}")
                return [types.TextContent(type="text", text=f"Error loading category taxonomy. Try using update_categories tool to refresh it.")]

            primary_filter = arguments.get("primary_category")
            result = "arXiv Categories:\n\n"
            
            for primary, data in taxonomy.items():
                if primary_filter and primary != primary_filter:
                    continue
                    
                result += f"{primary}: {data['name']}\n"
                for code, desc in data['subcategories'].items():
                    result += f"  {primary}.{code}: {desc}\n"
                result += "\n"
                
            result += "\nUsage in search:\n"
            result += '- Search in specific category: cat:cs.AI\n'
            result += '- Combine with other terms: "neural networks" AND cat:cs.AI\n'
            result += '- Multiple categories: (cat:cs.AI OR cat:cs.LG)\n'
            result += '\nNote: If categories seem outdated, use the update_categories tool to refresh them.\n'
            
            return [types.TextContent(type="text", text=result)]

        elif name == "update_categories":
            try:
                taxonomy = update_taxonomy_file()
                result = "Successfully updated category taxonomy.\n\n"
                result += f"Found {len(taxonomy)} primary categories:\n"
                for primary, data in taxonomy.items():
                    result += f"- {primary}: {data['name']} ({len(data['subcategories'])} subcategories)\n"
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                logger.error(f"Error updating taxonomy: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error updating taxonomy: {str(e)}",
                    isError=True
                )]
                
        elif name == "get_most_cited_papers":
            query = arguments["query"]
            max_results = min(int(arguments.get("max_results", 20)), 50)
            limit = min(int(arguments.get("limit", 5)), 20)
            
            # First search for papers
            papers = await arxiv_client.search(query, max_results)
            
            if not papers:
                return [types.TextContent(type="text", text=f"No papers found matching query: {query}")]
            
            # Then enrich with citation data and sort
            cited_papers = citation_service.get_most_cited_papers(papers, limit)
            
            # Format results in a readable way
            result = f"Most Cited Papers for '{query}':\n\n"
            
            if not cited_papers:
                result += "No citation data available for the papers found."
                return [types.TextContent(type="text", text=result)]
            
            for i, paper in enumerate(cited_papers, 1):
                result += f"{i}. {paper['title']}\n"
                result += f"   Authors: {', '.join(paper['authors'])}\n"
                result += f"   ID: {paper['id']}\n"
                
                # Add citation data if available
                if "citation_data" in paper:
                    result += f"   Citations: {paper['citation_data'].get('citation_count', 'Unknown')}\n"
                    if paper['citation_data'].get('year'):
                        result += f"   Year: {paper['citation_data'].get('year')}\n"
                
                result += f"   Published: {paper['published']}\n"
                
                # Add first sentence of abstract
                abstract_preview = get_first_sentence(paper['summary'])
                result += f"   Preview: {abstract_preview}\n"
                result += "\n"
            
            result += "\nNote: Citation data is provided by Semantic Scholar API and may not be complete for all papers."
            
            return [types.TextContent(type="text", text=result)]
            
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}",
                isError=True
            )]
            
    except Exception as e:
        logger.exception("Error handling tool call")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}",
            isError=True
        )]

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())