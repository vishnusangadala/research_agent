"""
GitHub repo search via the public REST API.

Works without auth (60 req/hour rate limit) but a personal access token
bumps it to 5000/hour. Token needs zero scopes — public-only is enough.

Create a token: https://github.com/settings/tokens
Set GITHUB_TOKEN in .env (optional but recommended).

Docs: https://docs.github.com/en/rest/search/search#search-repositories
"""
import os
from typing import List
import httpx
from models import SearchHit

GITHUB_URL = "https://api.github.com/search/repositories"


async def search_github(client: httpx.AsyncClient, query: str, n: int = 8) -> List[SearchHit]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": n,
    }
    response = await client.get(GITHUB_URL, params=params, headers=headers, timeout=20.0)
    response.raise_for_status()
    data = response.json()

    return [
        SearchHit(
            source="github",
            title=item.get("full_name", "(unknown)"),
            url=item.get("html_url", ""),
            snippet=(item.get("description") or "(no description)")[:400],
            extra=f"⭐ {item.get('stargazers_count', 0)} | {item.get('language') or 'mixed'} | "
                  f"updated {(item.get('pushed_at') or '')[:10]}",
        )
        for item in data.get("items", [])
    ]
