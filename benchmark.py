"""
Demonstration: parallel fan-out vs. sequential.

Runs the exact same three-source pipeline twice — once with asyncio.gather
(parallel) and once with await-in-sequence (serial) — and prints both wall
times. The point: parallel total ≈ slowest branch; serial total = sum of all.

Run: python benchmark.py "your topic here"
"""
import asyncio
import sys
import time
import httpx

from llm import call_llm
from models import BranchSummary
from pipeline import _summarize_branch, _format_hits_for_prompt
from prompts import SUMMARIZE_BRANCH_SYSTEM, SUMMARIZE_BRANCH_USER
from sources import search_web, search_arxiv, search_github


async def run_parallel(topic: str):
    async with httpx.AsyncClient() as http:
        t0 = time.perf_counter()

        async def branch(name, fetch_coro):
            hits = await fetch_coro
            return name, await _summarize_branch(name, topic, hits)

        results = await asyncio.gather(
            branch("web", search_web(http, topic, n=8)),
            branch("arxiv", search_arxiv(http, topic, n=8)),
            branch("github", search_github(http, topic, n=8)),
        )
        elapsed = time.perf_counter() - t0
    return elapsed, results


async def run_sequential(topic: str):
    async with httpx.AsyncClient() as http:
        t0 = time.perf_counter()

        web_hits = await search_web(http, topic, n=8)
        web_sum = await _summarize_branch("web", topic, web_hits)

        arxiv_hits = await search_arxiv(http, topic, n=8)
        arxiv_sum = await _summarize_branch("arxiv", topic, arxiv_hits)

        gh_hits = await search_github(http, topic, n=8)
        gh_sum = await _summarize_branch("github", topic, gh_hits)

        elapsed = time.perf_counter() - t0
    return elapsed, [("web", web_sum), ("arxiv", arxiv_sum), ("github", gh_sum)]


async def main():
    topic = " ".join(sys.argv[1:]) or "retrieval-augmented generation"
    print(f"Topic: {topic}\n")

    print("Running PARALLEL (asyncio.gather)...")
    par_time, _ = await run_parallel(topic)
    print(f"  Done in {par_time:.2f}s\n")

    print("Running SEQUENTIAL (one branch at a time)...")
    seq_time, _ = await run_sequential(topic)
    print(f"  Done in {seq_time:.2f}s\n")

    speedup = seq_time / par_time
    saved = seq_time - par_time
    print(f"Speedup: {speedup:.2f}x")
    print(f"Time saved: {saved:.2f}s")
    print()
    print(f"This is why fan-out matters. Three independent calls running")
    print(f"in parallel take ~max(t1, t2, t3) instead of t1 + t2 + t3.")


if __name__ == "__main__":
    asyncio.run(main())
