"""
arXiv search via the public Atom XML API.

No API key needed. arXiv asks for ~3 second spacing between bulk requests;
a single search per pipeline run is well within their TOS.

Docs: https://info.arxiv.org/help/api/user-manual.html
"""
from typing import List
from xml.etree import ElementTree as ET
import httpx
from models import SearchHit

ARXIV_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# arXiv asks for an identifying User-Agent; default httpx UA gets 403'd
# from some networks. See https://info.arxiv.org/help/api/tou.html
HEADERS = {"User-Agent": "research-summarizer/1.0 (educational; httpx)"}


async def search_arxiv(client: httpx.AsyncClient, query: str, n: int = 8) -> List[SearchHit]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": n,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    response = await client.get(ARXIV_URL, params=params, headers=HEADERS, timeout=20.0)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    hits: List[SearchHit] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip()
        url = entry.findtext("atom:id", default="", namespaces=ATOM_NS) or ""
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""

        authors = [
            (a.findtext("atom:name", default="", namespaces=ATOM_NS) or "")
            for a in entry.findall("atom:author", ATOM_NS)
        ]
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        date_str = published[:10]  # YYYY-MM-DD

        hits.append(SearchHit(
            source="arxiv",
            title=title.replace("\n", " "),
            url=url,
            snippet=summary[:600],
            extra=f"{author_str} ({date_str})" if author_str else date_str,
        ))
    return hits
