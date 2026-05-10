"""Source-specific search clients. Each returns a list of normalized SearchHit objects."""
from .web import search_web
from .arxiv import search_arxiv
from .github import search_github

__all__ = ["search_web", "search_arxiv", "search_github"]
