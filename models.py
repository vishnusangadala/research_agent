"""
Data contracts for the research pipeline.

Three branch summaries flow in; one unified brief flows out.
"""
from pydantic import BaseModel, Field
from typing import List, Literal


# ---------- Raw search results (from each source API) ----------

class SearchHit(BaseModel):
    """A single result from any source. Normalized shape across web/arxiv/github."""
    source: Literal["web", "arxiv", "github"]
    title: str
    url: str
    snippet: str = Field(description="Description, abstract, or repo description")
    extra: str = Field(
        default="",
        description="Source-specific metadata: authors+date for arxiv, stars+lang for github, domain for web",
    )


# ---------- Per-branch LLM summary ----------

class KeyFinding(BaseModel):
    claim: str = Field(description="A specific factual claim or insight from this source")
    citation_index: int = Field(description="1-based index into the hits list this claim came from")


class BranchSummary(BaseModel):
    """The output of summarizing one source's hits."""
    source: Literal["web", "arxiv", "github"]
    headline: str = Field(description="One sentence: what does this source collectively tell us?")
    key_findings: List[KeyFinding] = Field(
        description="3-7 specific findings. Each must cite a hit by index."
    )
    consensus_or_conflict: str = Field(
        description="Do the hits agree? Disagree? Note any contradictions or open questions."
    )
    notable_resources: List[str] = Field(
        description="Up to 3 standout titles+urls worth flagging in the final brief"
    )


# ---------- Final merged brief ----------

class CitedClaim(BaseModel):
    claim: str
    sources: List[Literal["web", "arxiv", "github"]] = Field(
        description="Which branches support this claim. >1 source = stronger signal."
    )


class ResearchBrief(BaseModel):
    """The unified output across all three sources."""
    topic: str
    executive_summary: str = Field(
        description="3-5 sentences. The TL;DR. What does someone need to know if they only read this?"
    )
    key_claims: List[CitedClaim] = Field(
        description="The most important claims, each tagged with which sources back it."
    )
    state_of_research: str = Field(
        description="What does academic literature (arXiv) say about maturity/open problems?"
    )
    state_of_practice: str = Field(
        description="What does the open-source ecosystem (GitHub) show about real adoption?"
    )
    state_of_discourse: str = Field(
        description="What is the broader web saying — news, blogs, industry?"
    )
    contradictions_or_gaps: str = Field(
        description="Where do sources disagree? What's missing? Open questions?"
    )
    recommended_next_steps: List[str] = Field(
        description="3-5 specific things the reader should investigate next, given this picture."
    )
    top_resources: List[str] = Field(
        description="Up to 8 must-read titles+urls drawn from across all branches."
    )
