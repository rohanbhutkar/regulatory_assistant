#!/usr/bin/env python3
"""
Manual test for china_regulatory_agent: granular query + instructions, prints ranked hits.

Usage (from backend/, with GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID in .env):
  python3 scripts/run_china_regulatory_demo.py \\
    --query "慢性鼻窦炎 鼻息肉 临床试验" \\
    --instructions "CDE 技术指导原则 正式稿 非征求意见稿" \\
    --max-results 5

Omit --live to only print query variations and exit (no CSE).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")
load_dotenv(BACKEND.parent / ".env")


def main() -> None:
    p = argparse.ArgumentParser(description="Run China regulatory CSE + fetch demo")
    p.add_argument("--query", "-q", required=True, help="Main search string (Chinese recommended)")
    p.add_argument(
        "--instructions",
        "-i",
        default="",
        help="Granular hints: document type, CDE vs NMPA, year, 正式稿/征求意见, etc.",
    )
    p.add_argument("--max-results", "-n", type=int, default=5)
    p.add_argument(
        "--live",
        action="store_true",
        help="Call Google CSE + fetch pages (requires API keys). Without this, only print variations.",
    )
    args = p.parse_args()

    from agents.china_regulatory_agent import _expand_query_variations, _stem_instructions
    from config import settings

    mv = max(1, min(8, settings.CHINA_REGULATORY_QUERY_VARIATIONS_MAX))
    stems = _expand_query_variations(args.query, args.instructions or None, mv)
    print("=== Query variations (CSE stems) ===")
    for i, s in enumerate(stems):
        ins = _stem_instructions(s, i, args.instructions or None)
        print(f"  [{i}] stem={s!r}")
        print(f"      +instructions fragment: {ins!r}")

    if not args.live:
        print("\n(No --live: set GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID and pass --live to run CSE.)")
        return

    async def run() -> None:
        from agents.china_regulatory_agent import china_regulatory_agent

        results = await china_regulatory_agent.search_regulatory(
            args.query,
            args.instructions or None,
            max_results=args.max_results,
        )
        print(f"\n=== {len(results)} result(s) ===")
        for j, r in enumerate(results, 1):
            print(f"\n--- {j}. {r.title[:120]}")
            print(f"    url: {r.url}")
            print(f"    domain: {r.source_domain} portal={r.metadata.get('portal')} score={r.relevance_score}")
            if r.metadata.get("html_title"):
                print(f"    html_title: {r.metadata['html_title'][:100]}")
            body = (r.content or "")[:400].replace("\n", " ")
            print(f"    excerpt: {body}...")

    asyncio.run(run())


if __name__ == "__main__":
    main()
