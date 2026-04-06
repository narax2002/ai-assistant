"""DuckDuckGo web search wrapper."""

import logging
from dataclasses import dataclass

from duckduckgo_search import DDGS

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


def search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search DuckDuckGo and return up to *max_results* results.

    Returns an empty list on any failure.
    """
    try:
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results)
    except Exception:
        LOGGER.exception("Web search failed for query: %s", query)
        return []

    results: list[SearchResult] = []
    for item in raw:
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
            )
        )
    return results


def format_results(results: list[SearchResult]) -> str:
    """Format search results as numbered text for LLM context."""
    if not results:
        return ""
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.title}\n    {r.snippet}\n    출처: {r.url}")
    return "\n\n".join(lines)
