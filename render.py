"""
Render the ResearchBrief + branch summaries as a single markdown file.

Markdown is the right choice here (not docx). The output is a research
artifact you'll read in an editor, paste into Notion/Obsidian, or share
in Slack — not a formal document.
"""
from datetime import datetime
from pathlib import Path
from pipeline import PipelineResult


def render_brief(result: PipelineResult, output_dir: str = "outputs") -> str:
    b = result.brief
    lines = []
    lines.append(f"# Research Brief: {b.topic}\n")
    lines.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_  ")
    lines.append(f"_Pipeline runtime: {result.timings['total']:.1f}s "
                 f"(fan-out {result.timings['fanout']:.1f}s, merge {result.timings['merge']:.1f}s)_\n")

    lines.append("---\n")
    lines.append("## Executive Summary\n")
    lines.append(b.executive_summary + "\n")

    lines.append("## Key Claims\n")
    for c in b.key_claims:
        sources = ", ".join(c.sources)
        confidence = "🟢 multi-source" if len(c.sources) > 1 else "🟡 single source"
        lines.append(f"- **{confidence}** ({sources}): {c.claim}")
    lines.append("")

    lines.append("## State of Research (arXiv)\n")
    lines.append(b.state_of_research + "\n")

    lines.append("## State of Practice (GitHub)\n")
    lines.append(b.state_of_practice + "\n")

    lines.append("## State of Discourse (Web)\n")
    lines.append(b.state_of_discourse + "\n")

    lines.append("## Contradictions & Gaps\n")
    lines.append(b.contradictions_or_gaps + "\n")

    lines.append("## Recommended Next Steps\n")
    for step in b.recommended_next_steps:
        lines.append(f"- {step}")
    lines.append("")

    lines.append("## Top Resources\n")
    for r in b.top_resources:
        lines.append(f"- {r}")
    lines.append("")

    # Appendix: per-branch details for verification
    lines.append("---\n")
    lines.append("## Appendix: Per-Branch Summaries\n")
    for src in ["web", "arxiv", "github"]:
        s = result.branch_summaries[src]
        lines.append(f"### {src.upper()}\n")
        lines.append(f"**Headline:** {s.headline}\n")
        lines.append(f"**Consensus/conflict:** {s.consensus_or_conflict}\n")
        if s.key_findings:
            lines.append("**Key findings:**")
            hits = result.raw_hits.get(src, [])
            for f in s.key_findings:
                # Resolve citation back to its hit (1-based)
                idx = f.citation_index - 1
                hit_url = hits[idx].url if 0 <= idx < len(hits) else ""
                tag = f" [{src}#{f.citation_index}]"
                src_link = f" — {hit_url}" if hit_url else ""
                lines.append(f"- {f.claim}{tag}{src_link}")
            lines.append("")
        if s.notable_resources:
            lines.append("**Notable:**")
            for r in s.notable_resources:
                lines.append(f"- {r}")
            lines.append("")

    # Save
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_slug = "".join(c if c.isalnum() else "_" for c in b.topic.lower())[:50]
    out_path = Path(output_dir) / f"brief_{topic_slug}_{timestamp}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
