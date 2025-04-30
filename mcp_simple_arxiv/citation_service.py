import time
import requests
from typing import Dict, Any, List, Optional

class CitationService:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/v1/paper/arXiv:"
        self.cache = {}
        self.last_request_time = 0
        self.rate_limit = 1  # seconds between requests
        
    def get_citation_data(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Get citation data for an arXiv paper."""
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_request_time < self.rate_limit:
            time.sleep(self.rate_limit - (current_time - self.last_request_time))
        
        # Check cache first
        if arxiv_id in self.cache:
            return self.cache[arxiv_id]
            
        # Make API request
        try:
            response = requests.get(f"{self.base_url}{arxiv_id}")
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                citation_data = {
                    "citation_count": data.get("citationCount", 0),
                    "influential_citations": data.get("influentialCitationCount", 0),
                    "references": len(data.get("references", [])),
                    "year": data.get("year")
                }
                self.cache[arxiv_id] = citation_data
                return citation_data
        except Exception as e:
            print(f"Error fetching citation data: {e}")
        
        return None
        
    def enrich_papers_with_citations(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add citation data to a list of papers."""
        for paper in papers:
            arxiv_id = paper.get("id").split("/")[-1]
            citation_data = self.get_citation_data(arxiv_id)
            if citation_data:
                paper["citation_data"] = citation_data
        return papers
        
    def get_most_cited_papers(self, papers: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Sort papers by citation count and return top results."""
        papers_with_citations = self.enrich_papers_with_citations(papers)
        sorted_papers = sorted(
            papers_with_citations, 
            key=lambda x: x.get("citation_data", {}).get("citation_count", 0), 
            reverse=True
        )
        return sorted_papers[:limit]
