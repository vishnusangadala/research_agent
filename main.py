"""
Entry point. Run:  python main.py "your research topic here"
"""
import asyncio
import sys
from pipeline import run_pipeline
from render import render_brief


async def amain():
    if len(sys.argv) < 2:
        print('Usage: python main.py "your research topic"')
        print('Example: python main.py "multi-agent LLM systems"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    print(f"Researching: {topic}\n")

    result = await run_pipeline(topic, hits_per_source=8)

    out_path = render_brief(result)
    print(f"\n✓ Brief saved to: {out_path}")
    print(f"  Total wall time: {result.timings['total']:.1f}s")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
