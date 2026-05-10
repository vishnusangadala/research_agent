"""
Web search via the Tavily API.

Why Tavily over Google/Bing/SerpAPI:
  - Built for LLM consumption: results come pre-cleaned, chunked, and ranked.
  - Free tier: 1000 searches/month, no credit card.
  - Single endpoint, simple JSON. No web scraping headaches.

Get a key: https://app.tavily.com/  (set TAVILY_API_KEY in .env)
"""
import os
from urllib.parse import urlparse
from typing import List
import httpx
from models import SearchHit

TAVILY_URL = "https://api.tavily.com/search"


async def search_web(client: httpx.AsyncClient, query: str, n: int = 8) -> List[SearchHit]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set. Get one at https://app.tavily.com/")

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": n,
        "search_depth": "basic",  # 'advanced' is slower + costs more credits
        "include_answer": False,  # we'll have the LLM synthesize, not Tavily
    }
    response = await client.post(TAVILY_URL, json=payload, timeout=20.0)
    response.raise_for_status()
    data = response.json()

    return [
        SearchHit(
            source="web",
            title=hit.get("title", "(untitled)"),
            url=hit.get("url", ""),
            snippet=hit.get("content", "")[:600],
            extra=urlparse(hit.get("url", "")).netloc,
        )
        for hit in data.get("results", [])
    ]
