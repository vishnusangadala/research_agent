"""
The fan-out / fan-in pipeline.

This is the core lesson of Project 2: independent work runs concurrently
via asyncio.gather, and synchronization happens at the merge.

Topology:
                    [topic]
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    fetch_web()   fetch_arxiv()   fetch_github()      ← I/O parallel
        │              │              │
        ▼              ▼              ▼
    summarize_w   summarize_a    summarize_g          ← LLM parallel
        └──────────────┼──────────────┘
                       ▼
                  merge_brief()                       ← waits on all 3
                       │
                       ▼
                 [ResearchBrief]
"""
import asyncio
import time
from dataclasses import dataclass
from typing import List, Tuple
import httpx

from models import SearchHit, BranchSummary, ResearchBrief
from llm import call_llm
from prompts import (
    SUMMARIZE_BRANCH_SYSTEM, SUMMARIZE_BRANCH_USER,
    MERGE_BRIEF_SYSTEM, MERGE_BRIEF_USER,
)
from sources import search_web, search_arxiv, search_github


SOURCE_DESCRIPTIONS = {
    "web": "general web pages — news, blogs, vendor sites, tutorials",
    "arxiv": "academic preprints — peer-not-yet-reviewed research papers",
    "github": "open-source code repositories",
}


@dataclass
class PipelineResult:
    topic: str
    raw_hits: dict          # source_name -> List[SearchHit]
    branch_summaries: dict  # source_name -> BranchSummary
    brief: ResearchBrief
    timings: dict           # phase -> seconds


def _format_hits_for_prompt(hits: List[SearchHit]) -> str:
    """Format hits as a numbered list for the LLM."""
    if not hits:
        return "(no results returned)"
    lines = []
    for i, h in enumerate(hits, start=1):
        lines.append(f"[{i}] {h.title}")
        if h.extra:
            lines.append(f"    meta: {h.extra}")
        lines.append(f"    url: {h.url}")
        lines.append(f"    snippet: {h.snippet}")
        lines.append("")
    return "\n".join(lines)


async def _summarize_branch(source: str, topic: str, hits: List[SearchHit]) -> BranchSummary:
    """Summarize one source's hits. Called once per branch, in parallel."""
    if not hits:
        # Return a minimal summary rather than error out
        return BranchSummary(
            source=source,
            headline=f"No {source} results returned for this topic.",
            key_findings=[],
            consensus_or_conflict="N/A — no data.",
            notable_resources=[],
        )

    return await call_llm(
        prompt=SUMMARIZE_BRANCH_USER.format(
            topic=topic,
            source=source,
            source_description=SOURCE_DESCRIPTIONS[source],
            hits_formatted=_format_hits_for_prompt(hits),
        ),
        schema=BranchSummary,
        system=SUMMARIZE_BRANCH_SYSTEM,
        temperature=0.2,
    )


async def _fetch_and_summarize(
    source: str,
    fetch_coro,
    topic: str,
) -> Tuple[List[SearchHit], BranchSummary]:
    """
    Fetch hits from one source, then summarize them.

    Each branch chains fetch → summarize internally, but ALL THREE BRANCHES
    run in parallel via gather() above. The fetch and summarize within one
    branch are sequential (summarize needs fetch's output), but across
    branches they're concurrent.
    """
    hits = await fetch_coro
    summary = await _summarize_branch(source, topic, hits)
    return hits, summary


async def run_pipeline(topic: str, hits_per_source: int = 8, verbose: bool = True) -> PipelineResult:
    timings = {}

    async with httpx.AsyncClient() as http:
        # ---- FAN-OUT: three independent branches ----
        if verbose:
            print(f"→ Fanning out 3 parallel searches for: {topic!r}")
        t0 = time.perf_counter()

        web_branch = _fetch_and_summarize(
            "web", search_web(http, topic, n=hits_per_source), topic,
        )
        arxiv_branch = _fetch_and_summarize(
            "arxiv", search_arxiv(http, topic, n=hits_per_source), topic,
        )
        github_branch = _fetch_and_summarize(
            "github", search_github(http, topic, n=hits_per_source), topic,
        )

        # gather() runs all three concurrently. Total time ≈ slowest branch,
        # not sum of all branches.
        results = await asyncio.gather(
            web_branch, arxiv_branch, github_branch,
            return_exceptions=True,
        )
        timings["fanout"] = time.perf_counter() - t0

        # Unpack with graceful failure: if one source errors, the other
        # two still produce useful output.
        sources = ["web", "arxiv", "github"]
        raw_hits = {}
        branch_summaries = {}
        for src, result in zip(sources, results):
            if isinstance(result, Exception):
                if verbose:
                    print(f"  ⚠ {src} failed: {result}")
                raw_hits[src] = []
                branch_summaries[src] = BranchSummary(
                    source=src,
                    headline=f"{src} branch failed: {type(result).__name__}",
                    key_findings=[],
                    consensus_or_conflict="N/A — branch errored.",
                    notable_resources=[],
                )
            else:
                hits, summary = result
                raw_hits[src] = hits
                branch_summaries[src] = summary
                if verbose:
                    print(f"  ✓ {src}: {len(hits)} hits → {len(summary.key_findings)} findings")

        if verbose:
            print(f"  Fan-out complete in {timings['fanout']:.1f}s")

    # ---- FAN-IN: synchronize on all three, merge into single brief ----
    if verbose:
        print("\n→ Merging branches into unified brief...")
    t1 = time.perf_counter()

    brief = await call_llm(
        prompt=MERGE_BRIEF_USER.format(
            topic=topic,
            web_summary=branch_summaries["web"].model_dump_json(indent=2),
            arxiv_summary=branch_summaries["arxiv"].model_dump_json(indent=2),
            github_summary=branch_summaries["github"].model_dump_json(indent=2),
        ),
        schema=ResearchBrief,
        system=MERGE_BRIEF_SYSTEM,
        temperature=0.3,  # slight bump — synthesis benefits from a touch of variation
    )
    timings["merge"] = time.perf_counter() - t1
    timings["total"] = timings["fanout"] + timings["merge"]

    if verbose:
        print(f"  ✓ Brief assembled in {timings['merge']:.1f}s")
        print(f"  Total pipeline: {timings['total']:.1f}s")

    return PipelineResult(
        topic=topic,
        raw_hits=raw_hits,
        branch_summaries=branch_summaries,
        brief=brief,
        timings=timings,
    )
