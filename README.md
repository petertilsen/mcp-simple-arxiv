# mcp-simple-arxiv

[![smithery badge](https://smithery.ai/badge/mcp-simple-arxiv)](https://smithery.ai/server/mcp-simple-arxiv)

An MCP server that provides access to arXiv papers through their API.

<a href="https://glama.ai/mcp/servers/p38q3nagwb"><img width="380" height="200" src="https://glama.ai/mcp/servers/p38q3nagwb/badge" alt="mcp-simple-arxiv MCP server" /></a>

## Features

This server allows LLM clients (like Claude Desktop and Amazon Q) to:
- Search for scientific papers on arXiv by title and abstract content
- Get paper metadata and abstracts
- Access links to available paper formats (PDF/HTML)
- **NEW**: Find the most cited papers on a topic using citation data from Semantic Scholar

The server implements proper rate limiting according to arXiv's API guidelines (max 1 request every 3 seconds) and Semantic Scholar API guidelines.

## Installation

### Installing via Smithery

To install Simple Arxiv for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-simple-arxiv):

```bash
npx -y @smithery/cli install mcp-simple-arxiv --client claude
```

### Manual Installation
```bash
pip install mcp-simple-arxiv
```

## Usage with Claude Desktop or Amazon Q

### Claude Desktop Configuration

Add this configuration to your `claude_desktop_config.json`:

(Mac OS)

```json
{
  "mcpServers": {
    "simple-arxiv": {
      "command": "python",
      "args": ["-m", "mcp_simple_arxiv"]
      }
  }
}
```

(Windows version):

```json
{
  "mcpServers": {
    "simple-arxiv": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
      "args": [
        "-m",
        "mcp_simple_arxiv"
      ]
    }
  }
}
```

### Amazon Q Configuration

Add this configuration to your `~/.aws/amazonq/mcp.json`:

```json
{
  "mcpServers": {
    "simple-arxiv": {
      "command": "python",
      "args": ["-m", "mcp_simple_arxiv"]
    }
  }
}
```

After restarting your LLM client, the following capabilities will be available:

### Searching Papers

You can search for papers using queries like:
```
Can you search arXiv for recent papers about large language models?
```

The search will return basic information about matching papers including:
- Paper title
- Authors
- arXiv ID
- Publication date

### Getting Paper Details

Once you have a paper ID, you can ask for more details:
```
Can you show me the details for paper 2103.08220?
```

This will return:
- Full paper title
- Authors
- Publication and update dates
- Journal reference (if available)
- Paper abstract
- Links to available formats (PDF/HTML)

### Finding Most Cited Papers (NEW)

You can now find the most influential papers on a topic based on citation count:
```
What are the most cited papers on quantum computing?
```

This will return:
- Paper titles sorted by citation count
- Number of citations for each paper
- Publication year
- Authors
- Brief abstract preview

## Development

To install fork for development:
```bash
git clone https://github.com/petertilsen/mcp-simple-arxiv
cd mcp-simple-arxiv
pip install -e ".[dev]"
```

### Running Tests

This project includes a comprehensive test suite with high coverage of core functionality.

#### Quick Start
```bash
# Install with test dependencies
pip install -e ".[test]"

# Run core functionality tests (recommended)
pytest tests/test_core_functionality.py tests/test_categories.py tests/test_update_taxonomy.py tests/test_arxiv_client.py -v

# Or use the test runner script
python run_tests.py core
```

#### Test Options
```bash
# Quick test run
python run_tests.py quick

# Full test suite with coverage
python run_tests.py coverage

# All tests (some may fail due to MCP framework changes)
python run_tests.py all
```

#### Test Coverage
The test suite provides:
- **100% coverage** for ArxivClient and Categories modules
- **92% coverage** for CitationService
- **Comprehensive mocking** of external APIs
- **Async testing** with proper event loop management
- **Error handling** for network failures and edge cases

See `tests/README.md` for detailed testing documentation.

### API Guidelines

This server follows API usage guidelines:
- arXiv API: Rate limiting to max 1 request per 3 seconds
- Semantic Scholar API: Rate limiting to max 1 request per second
- Single connection at a time
- Proper error handling and retry logic
- Caching to reduce API calls

## License

MIT
