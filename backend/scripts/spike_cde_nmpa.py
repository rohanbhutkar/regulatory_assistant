#!/usr/bin/env python3
"""
Phase 0 spike: CDE / NMPA / zwfw discovery via Google CSE + direct HTTP probes.

Run from repository root or backend:
  cd backend && python scripts/spike_cde_nmpa.py

Requires GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID in backend/.env (or env).

DECISION LOG (also printed at end of run):
- Prefer Google CSE with site: restriction in the query when using the default
  search engine; optionally create a second Programmable Search Engine restricted
  to cde.org.cn, nmpa.gov.cn, zwfw.nmpa.gov.cn and set GOOGLE_CSE_CHINA_ENGINE_ID
  to drop redundant site: tokens from q.
- If many result pages are JS shells (tiny text after soup), defer structured
  scraping to a later Playwright phase; server-rendered HTML is enough for v1.
- Respect robots.txt and rate limits; do not crawl aggressively.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")
load_dotenv(BACKEND_ROOT.parent / ".env")

SITE_CLAUSE = "(site:cde.org.cn OR site:nmpa.gov.cn OR site:zwfw.nmpa.gov.cn)"

# ~10 queries: English, Chinese guidance-style, one product-ish topic
QUERY_MATRIX = [
    "drug approval China NMPA",
    "clinical trial regulation China",
    "指导原则 抗肿瘤",
    "药审中心 通告",
    "临床试验 质量管理规范",
    "国家药监局 药品注册",
    "突破性治疗 公示",
    "化学药品 目录集",
    "生物制品 技术指导原则",
    "zwfw 药物临床试验",
]

CSE_URL = "https://www.googleapis.com/customsearch/v1"
USER_AGENT_PAGE = (
    "Mozilla/5.0 (compatible; Clinical-Knowledge-Agent-Spike/1.0; +https://example.local)"
)


def _env(name: str) -> str:
    import os

    return (os.environ.get(name) or "").strip()


async def run_cse_matrix(api_key: str, cx: str) -> list[dict]:
    out = []
    timeout = httpx.Timeout(20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for q in QUERY_MATRIX:
            full_q = f"{SITE_CLAUSE} {q}".strip()
            params = {"key": api_key, "cx": cx, "q": full_q, "num": 5, "safe": "off"}
            try:
                r = await client.get(CSE_URL, params=params)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                out.append({"query": q, "error": str(e), "items": 0, "links": []})
                continue
            items = data.get("items") or []
            links = []
            for it in items:
                link = it.get("link") or ""
                host = urlparse(link).netloc
                links.append(
                    {
                        "link": link,
                        "host": host,
                        "pdf": link.lower().endswith(".pdf"),
                    }
                )
            out.append({"query": q, "error": None, "items": len(items), "links": links})
            await asyncio.sleep(0.4)
    return out


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for el in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
        el.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln and len(ln) > 2)


async def probe_url(client: httpx.AsyncClient, url: str) -> dict:
    try:
        r = await client.get(
            url,
            headers={
                "User-Agent": USER_AGENT_PAGE,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
            },
            follow_redirects=True,
        )
        r.raise_for_status()
        ct = (r.headers.get("content-type") or "").lower()
        raw_len = len(r.content or b"")
        if "pdf" in ct or url.lower().endswith(".pdf"):
            return {"url": url, "status": "pdf", "raw_len": raw_len, "text_len": 0, "note": "PDF body skipped"}
        text = _visible_text(r.text)
        text_len = len(text)
        if text_len < 200:
            return {"url": url, "status": "thin_shell", "raw_len": raw_len, "text_len": text_len}
        return {"url": url, "status": "ok", "raw_len": raw_len, "text_len": text_len}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


async def fetch_robots(client: httpx.AsyncClient, base: str) -> dict:
    try:
        r = await client.get(base.rstrip("/") + "/robots.txt", headers={"User-Agent": USER_AGENT_PAGE})
        return {"url": base + "/robots.txt", "status": r.status_code, "snippet": (r.text or "")[:800]}
    except Exception as e:
        return {"url": base + "/robots.txt", "error": str(e)}


async def main() -> None:
    api_key = _env("GOOGLE_API_KEY")
    cx = _env("GOOGLE_CSE_CHINA_ENGINE_ID") or _env("GOOGLE_SEARCH_ENGINE_ID")

    print("=== CDE / NMPA spike ===\n")
    print(f"SITE_CLAUSE: {SITE_CLAUSE}\n")

    if not api_key or not cx:
        print("SKIP: Set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID (or GOOGLE_CSE_CHINA_ENGINE_ID) to run CSE matrix.")
        rows = []
    else:
        print("--- CSE matrix ---")
        rows = await run_cse_matrix(api_key, cx)
        for row in rows:
            if row.get("error"):
                print(f"  Q: {row['query'][:50]}... | ERROR: {row['error']}")
            else:
                print(f"  Q: {row['query'][:50]}... | items={row['items']}")
                for L in row.get("links", [])[:3]:
                    print(f"      {L['host']} pdf={L['pdf']} {L['link'][:80]}")

    # Collect up to 5 distinct URLs from first successful rows for fetch probe
    sample_urls: list[str] = []
    seen = set()
    for row in rows:
        for L in row.get("links") or []:
            u = L.get("link") or ""
            if u and u not in seen and not L.get("pdf"):
                seen.add(u)
                sample_urls.append(u)
            if len(sample_urls) >= 5:
                break
        if len(sample_urls) >= 5:
            break

    timeout = httpx.Timeout(25.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        print("\n--- robots.txt ---")
        for base in (
            "https://www.cde.org.cn",
            "https://www.nmpa.gov.cn",
            "https://zwfw.nmpa.gov.cn",
        ):
            info = await fetch_robots(client, base)
            print(info)

        if sample_urls:
            print("\n--- URL fetch probe ---")
            for u in sample_urls:
                info = await probe_url(client, u)
                print(info)
                await asyncio.sleep(0.5)
        else:
            print("\n--- URL fetch probe: no sample URLs (CSE skipped or empty) ---")

    print("\n=== DECISION LOG ===")
    print(
        "1. CSE with site: clause on default cx is viable for discovery; optional "
        "GOOGLE_CSE_CHINA_ENGINE_ID (engine restricted to official hosts) reduces query noise."
    )
    print(
        "2. If probe status is often thin_shell, plan Playwright for those patterns only; "
        "otherwise httpx + BeautifulSoup is sufficient for v1."
    )
    print(
        "3. PDF links: agent should not parse binary; surface URL + title only or skip fetch."
    )
    print(
        "4. Translation: keep optional LLM snippet translate off by default; rely on synthesize step for English."
    )


if __name__ == "__main__":
    asyncio.run(main())
