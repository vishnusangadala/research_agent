# Research Summarizer — Project 2: Fan-Out / Fan-In

A multi-source research pipeline. Input a topic, get a unified brief that
synthesizes web search, arXiv papers, and GitHub repos into one markdown
file with cross-source triangulation.

This is **Project 2** of an agentic-workflows course. The pattern is
**fan-out → fan-in**: independent work runs in parallel, then a final step
merges the outputs.

```
                    [topic]
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    Tavily        arXiv API       GitHub API         ← I/O parallel
        │              │              │
        ▼              ▼              ▼
    summarize     summarize       summarize          ← LLM parallel
        └──────────────┼──────────────┘
                       ▼
                  merge brief                        ← waits on all 3
                       │
                       ▼
                 [research.md]
```

---

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — paste OPENAI_API_KEY and TAVILY_API_KEY (GITHUB_TOKEN optional)
export $(cat .env | xargs)
```

API keys you need:
- **OpenAI** — same as Project 1
- **Tavily** — https://app.tavily.com/ — free tier is 1000 searches/month, no card
- **GitHub token** — optional, just raises rate limit. Create at https://github.com/settings/tokens with no scopes

---

## Usage

```bash
python main.py "multi-agent LLM systems"
```

You'll see a per-step trace and timings, then a markdown brief lands in
`outputs/`. The brief has cross-source triangulation: claims tagged with
which sources back them, contradictions surfaced, gaps named.

## Browser UI

Run the chatbot-style interface:

```bash
python app.py
```

Then open `http://127.0.0.1:8000`. Enter a research topic, and the page will
run the full pipeline and render the synthesized brief on screen. Use
**Refresh** to clear the chat and start over.

To **see** why parallel matters:

```bash
python benchmark.py "multi-agent LLM systems"
```

Runs the same workload twice — once with `asyncio.gather`, once sequentially.
You'll typically see a 2.5–3x speedup on the parallel version.

---

## File map

| File | Role |
|------|------|
| `models.py` | Pydantic schemas (SearchHit, BranchSummary, ResearchBrief) |
| `prompts.py` | Two prompts: per-branch summarize, final merge |
| `llm.py` | Async OpenAI wrapper with structured outputs |
| `sources/web.py` | Tavily search client |
| `sources/arxiv.py` | arXiv Atom XML client |
| `sources/github.py` | GitHub repo search client |
| `pipeline.py` | Fan-out / fan-in orchestration |
| `render.py` | Markdown brief renderer |
| `benchmark.py` | Sequential vs parallel timing demo |
| `main.py` | Entry point |

---

## What this teaches

1. **Async LLM calls** with `AsyncOpenAI` — `await` instead of blocking
2. **`asyncio.gather`** — running independent work concurrently
3. **Why parallel beats sequential** for I/O-bound workloads — the benchmark
   makes the speedup visible
4. **Reduce/merge step design** — the final LLM call doesn't just concatenate;
   it triangulates across sources
5. **Graceful degradation** — `return_exceptions=True` in gather means one
   branch failing doesn't kill the run; the brief notes which branch errored

---

## Cost

Four GPT-5.4 mini calls per run (3 branch summaries + 1 merge). Cost per run:
roughly **$0.02–0.05** depending on how much each source returns. Tavily and
GitHub are free at this scale; arXiv is always free.

---

## Architecture notes (worth internalizing)

- **Why per-branch summaries before the merge?** Two reasons. First, the
  merge model only sees ~3-7 distilled findings per source instead of 24
  raw hits — much cleaner reasoning. Second, the per-branch step lets each
  source be reasoned about with source-specific epistemics (arXiv ≠ GitHub
  ≠ web).
- **Why structured outputs at every step?** Same reason as Project 1, but
  more important here: the merge step's input is the previous step's output.
  Schema-conformant data flowing between steps means no string parsing
  fragility in the orchestration layer.
- **Why graceful failure?** In production agent pipelines, individual tool
  calls fail constantly (rate limits, network blips, API errors). A pipeline
  that hard-fails on one bad branch is brittle. `return_exceptions=True`
  + a fallback BranchSummary keeps the run useful.

---

## Next steps (Project 3 of the course)

Project 3 introduces **routing** — an LLM picks which downstream chain to
run based on input. The async + structured-output patterns from this project
carry forward; the new piece is conditional logic driven by classification.
