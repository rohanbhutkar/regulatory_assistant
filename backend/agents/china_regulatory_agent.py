"""
CDE / NMPA / zwfw regulatory web discovery via Google CSE + HTML text extraction.

Runs multiple query variations in parallel (EMA-style multi-angle coverage), merges and
ranks URLs, then fetches excerpts concurrently. Optional LLM English snippet in
metadata["content_en"] (off by default).
"""
from __future__ import annotations

import asyncio
import random
import re
from datetime import datetime
from typing import List, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from agents.llm_agent import llm_agent
from config import settings
from models.schemas import ChinaRegulatoryResult
from utils.cache import cache_manager
from utils.logger import log_api_call, log_error, log_warning
from utils.rate_limiter import rate_limiter
from utils.brave_web_search import clip_brave_query, fetch_brave_web_urls

SITE_CLAUSE = "(site:cde.org.cn OR site:nmpa.gov.cn OR site:zwfw.nmpa.gov.cn)"

# Graph execution runs many china_regulatory nodes concurrently; Google CSE is strict per-second.
# Serialize all Custom Search HTTP calls process-wide (lock is cheap vs 429 storm).
_CHINA_CSE_HTTP_LOCK = asyncio.Lock()


def _china_regulatory_official_host(host: str) -> bool:
    h = (host or "").lower()
    if h.startswith("www."):
        h = h[4:]
    if not h:
        return False
    return h == "cde.org.cn" or h.endswith(".cde.org.cn") or h == "nmpa.gov.cn" or h.endswith(".nmpa.gov.cn")


def _china_host_tier_scores(u: str) -> tuple[int, int]:
    """(official_regulatory, cn_tld) for URL ordering — same rules for Google CSE and Brave."""
    try:
        hn = (urlparse(u).netloc or "").lower()
    except Exception:
        return (0, 0)
    official = 1 if _china_regulatory_official_host(hn) else 0
    cn = 1 if ".cn" in hn else 0
    return (official, cn)


def _dedupe_url_list(urls: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for u in urls:
        u = (u or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _china_brave_query_variants(cse_query: str) -> List[str]:
    """Query stems for Brave when mirroring Google CSE strings (use ``operators=true`` at call site)."""
    raw = (cse_query or "").strip()
    seen: set[str] = set()
    out: List[str] = []

    def add(s: str) -> None:
        b = clip_brave_query(s)
        if len(b) < 2:
            return
        k = b.lower()
        if k in seen:
            return
        seen.add(k)
        out.append(b)

    add(raw)
    if SITE_CLAUSE in raw:
        core = re.sub(r"\s+", " ", raw.replace(SITE_CLAUSE, "").strip())
        if len(core) >= 2:
            add(f"{core} (site:cde.org.cn OR site:nmpa.gov.cn OR site:zwfw.nmpa.gov.cn)")
            add(f"{core} site:cde.org.cn")
    return out[:8]


def _classify_portal(url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
    except Exception:
        return "unknown"
    if "cde.org.cn" in host:
        return "cde"
    if "zwfw.nmpa.gov.cn" in host:
        return "zwfw"
    if "nmpa.gov.cn" in host:
        return "nmpa_root"
    return "unknown"


def _build_cse_query(query: str, search_instructions: Optional[str]) -> str:
    q = (query or "").strip()
    ins = (search_instructions or "").strip()
    if ins and len(q) + len(ins) + 1 < 200:
        q = f"{q} {ins}".strip()
    use_restricted_cx = bool(settings.GOOGLE_CSE_CHINA_ENGINE_ID)
    if use_restricted_cx:
        full = q
    else:
        full = f"{SITE_CLAUSE} {q}".strip()
    if len(full) > 2000:
        full = full[:1995] + "…"
    return full


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in (text or ""))


def _expand_query_variations(
    query: str,
    instructions: Optional[str],
    max_variations: int,
) -> List[str]:
    """
    Build up to max_variations distinct CSE stems (angles) for broader recall.
    Planner `search_instructions` are merged per stem in `_stem_instructions` (full on first stem,
    short tail on others) when they fit the CSE length budget.
    """
    q = (query or "").strip()
    if not q:
        return []
    mv = max(1, min(8, max_variations))
    ins = (instructions or "").strip()
    candidates: List[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", s.strip())
        if not s or len(s) > 500:
            return
        if s in seen:
            return
        seen.add(s)
        candidates.append(s)

    add(q)
    if ins and ins not in q and len(q) + len(ins) < 170:
        add(f"{q} {ins}".strip())

    low = q.lower()
    if "药审中心" not in q and "cde" not in low:
        add(f"{q} 药审中心")
    if "国家药监局" not in q and "nmpa" not in low:
        add(f"{q} 国家药监局")
    if "指导原则" not in q and "guidance" not in low and "guideline" not in low:
        add(f"{q} 技术指导原则")
    if "信息公开" not in q and "公示" not in q:
        add(f"{q} 信息公开 公示")
    if not _has_cjk(q):
        add(f"{q} 中国 药品审评")
    if "临床试验" not in q and "clinical" in low:
        add(f"{q} 临床试验")
    if "zwfw" not in low and "政务服务" not in q:
        add(f"{q} 政务服务门户")
    # Preclinical / early development / agency engagement (English or mixed queries)
    if any(t in low for t in ("preclinical", "nonclinical", "non-clinical", "ind ", "toxicology", "pharmacology")):
        if "临床前" not in q:
            add(f"{q} 临床前 非临床研究")
        if "沟通交流" not in q and "沟通" not in q:
            add(f"{q} 沟通交流 程序")
    if "pre-IND" in low or "preind" in low.replace("-", ""):
        add(f"{q} 沟通交流 临床前")

    return candidates[:mv]


def _merge_url_batches(batches: List[object]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for batch in batches:
        if isinstance(batch, BaseException):
            continue
        if not isinstance(batch, list):
            continue
        for u in batch:
            if u and isinstance(u, str) and u not in seen:
                seen.add(u)
                out.append(u)
    return out


def _url_path_quality(url: str) -> float:
    """Soft ranking: prefer guidance, disclosure, and news detail paths over bare homepages."""
    try:
        p = urlparse(url)
        path = (p.path or "").lower()
        full = url.lower()
    except Exception:
        return 0.0
    score = 0.0
    if "zdyz" in path or "zdyz" in full:
        score += 0.35
    if "viewinfocommon" in path or "/main/news/" in path:
        score += 0.28
    if "xxgk" in path or "ggtg" in path or "ypggtg" in path:
        score += 0.22
    if "hymlj" in path or "listpage" in path:
        score += 0.15
    if path.rstrip("/").endswith((".pdf", ".doc", ".docx")):
        score -= 0.15
    if path in ("", "/") or path.rstrip("/") in ("/main", "/web", "/web/index"):
        score -= 0.25
    for y in ("2026", "2025", "2024"):
        if y in full:
            score += 0.06
            break
    return max(-0.5, min(score, 1.0))


def _rank_urls_by_quality(urls: List[str]) -> List[str]:
    """Dedupe; order Google CSE and Brave URLs alike: official hosts, other ``.cn``, then path quality."""
    urls = _dedupe_url_list(urls)
    if not urls:
        return []
    rows: List[tuple[int, int, int, float, str]] = []
    for i, u in enumerate(urls):
        off, cn = _china_host_tier_scores(u)
        pq = _url_path_quality(u)
        rows.append((i, off, cn, pq, u))
    rows.sort(key=lambda r: (-r[1], -r[2], -r[3], r[0]))
    return [r[4] for r in rows]


def _terms_for_relevance(blob: str) -> List[str]:
    """
    Mix space-separated tokens (English) with Chinese phrases so scoring is not
    blind to CJK (Chinese is rarely space-delimited).
    """
    if not blob:
        return []
    terms: List[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        t = t.strip()
        if len(t) < 2 or t in seen:
            return
        seen.add(t)
        terms.append(t)

    for t in re.split(r"\s+", blob.lower()):
        if len(t) > 1:
            add(t)
    for m in re.finditer(r"[\u4e00-\u9fff]{2,}", blob):
        s = m.group()
        if len(s) <= 14:
            add(s)
        else:
            step = 5
            for i in range(0, min(len(s), 24), step):
                chunk = s[i : i + 8]
                if len(chunk) >= 2:
                    add(chunk)
    return terms


def _relevance_score(content: str, relevance_blob: str) -> float:
    if not content or not relevance_blob:
        return 0.0
    terms = _terms_for_relevance(relevance_blob)
    if not terms:
        return 0.0
    cl = content
    cl_low = content.lower()
    term_count = 0.0
    for t in terms:
        if re.search(r"[\u4e00-\u9fff]", t):
            term_count += cl.count(t) * 1.4
        else:
            term_count += cl_low.count(t)
    return round(min(term_count / max(len(content) / 700, 1), 1.0), 2)


def _stem_instructions(stem: str, stem_index: int, instructions: Optional[str]) -> Optional[str]:
    """Attach planner instructions to CSE q; primary stem gets more room, others a short tail for specificity."""
    ins = (instructions or "").strip()
    if not ins:
        return None
    budget = 175 if stem_index == 0 else 165
    room = budget - len(stem)
    if room < 24:
        return None
    if stem_index == 0:
        frag = ins[:room] if len(ins) > room else ins
        if len(frag) >= room - 1 and " " in frag:
            frag = frag.rsplit(" ", 1)[0]
        return frag or None
    tail = ins[: min(len(ins), room, 96)]
    return tail if len(tail) >= 6 else None


def _extract_simple_title(
    url: str, content: str, page_title: Optional[str] = None, h1: Optional[str] = None
) -> str:
    for candidate in (h1, page_title):
        if candidate:
            c = re.sub(r"\s+", " ", candidate.strip())
            if 12 < len(c) < 320 and not c.lower().startswith("http"):
                return c[:200]
    url_parts = url.split("/")
    if len(url_parts) > 3:
        title_from_url = url_parts[-1].replace("-", " ").replace("_", " ").replace(".html", "").title()
        if len(title_from_url) > 10:
            return title_from_url[:200]
    for line in content.split("\n")[:25]:
        line = line.strip()
        if 20 < len(line) < 200 and not line.startswith("http"):
            return line[:200]
    return "China regulatory page"


class ChinaRegulatoryAgent:
    def __init__(self) -> None:
        self.api_key = settings.GOOGLE_API_KEY
        self.base_url = settings.GOOGLE_CSE_BASE_URL
        self.timeout = httpx.Timeout(20.0)

    def _cx(self) -> str:
        return (settings.GOOGLE_CSE_CHINA_ENGINE_ID or settings.GOOGLE_SEARCH_ENGINE_ID or "").strip()

    async def _try_brave_cse_fallback(self, cse_query: str, num_results: int) -> List[str]:
        """Brave Web Search with ``site:`` operators; keep only CDE/NMPA/zwfw hosts."""
        if not (settings.BRAVE_API_KEY or "").strip():
            return []
        variants = _china_brave_query_variants(cse_query)
        if not variants:
            return []
        raw = await fetch_brave_web_urls(
            variants,
            num_results=min(max(1, num_results), 20),
            timeout=self.timeout,
            operators=True,
            country="CN",
        )
        return _rank_urls_by_quality(raw)[:num_results]

    async def _cse_urls(self, cse_query: str, num_results: int) -> List[str]:
        cx = self._cx()
        if not self.api_key or not cx:
            return []

        params = {
            "key": self.api_key,
            "cx": cx,
            "q": cse_query,
            "num": min(max(1, num_results), 10),
            "safe": "off",
        }
        headers = {
            "User-Agent": "Clinical-Knowledge-Agent/1.0",
            "Accept": "application/json",
        }
        max_attempts = max(1, settings.CHINA_REGULATORY_CSE_MAX_RETRIES)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_attempts):
                await rate_limiter.acquire("china_regulatory")
                backoff_s: Optional[float] = None
                async with _CHINA_CSE_HTTP_LOCK:
                    start = asyncio.get_event_loop().time()
                    try:
                        response = await client.get(self.base_url, params=params, headers=headers)
                        elapsed = asyncio.get_event_loop().time() - start
                        sc = response.status_code

                        if sc == 429:
                            log_warning(
                                "China regulatory Google CSE returned 429; trying Brave Web Search."
                            )
                            brave = await self._try_brave_cse_fallback(cse_query, int(params["num"]))
                            if brave:
                                log_warning(
                                    "China regulatory: using Brave Web Search results after Google CSE 429"
                                )
                                return brave
                            if attempt + 1 < max_attempts:
                                backoff_s = min(90.0, (2**attempt) + random.uniform(0.0, 0.75))
                                log_warning(
                                    f"China regulatory Google CSE 429 and Brave returned no URLs; "
                                    f"backing off {backoff_s:.1f}s (attempt {attempt + 1}/{max_attempts})"
                                )
                            else:
                                log_warning(
                                    "China regulatory Google CSE 429 and Brave returned no URLs; "
                                    "no further Google retries."
                                )
                                backoff_s = None
                        elif sc in (502, 503):
                            backoff_s = min(45.0, 1.5 * (2**attempt) + random.uniform(0.0, 0.5))
                            log_warning(
                                f"China regulatory Google CSE returned {sc}; "
                                f"retrying in {backoff_s:.1f}s (attempt {attempt + 1}/{max_attempts})"
                            )
                        else:
                            response.raise_for_status()
                            log_api_call("china_regulatory", "google_cse_search", sc, elapsed)
                            data = response.json()
                            urls: List[str] = []
                            for item in data.get("items") or []:
                                link = item.get("link")
                                if link:
                                    urls.append(link)
                            return _rank_urls_by_quality(urls)

                    except httpx.RequestError as e:
                        backoff_s = min(30.0, 1.5 * (2**attempt))
                        log_error(e, f"China regulatory CSE network error (attempt {attempt + 1}/{max_attempts})")
                    except httpx.HTTPStatusError as e:
                        est = e.response.status_code
                        if est == 429:
                            log_warning(
                                "China regulatory Google CSE HTTPStatusError 429; trying Brave Web Search."
                            )
                            brave = await self._try_brave_cse_fallback(cse_query, int(params["num"]))
                            if brave:
                                log_warning(
                                    "China regulatory: using Brave Web Search results after Google CSE 429"
                                )
                                return brave
                            if attempt + 1 < max_attempts:
                                backoff_s = min(90.0, (2**attempt) + random.uniform(0.0, 0.75))
                                log_warning(
                                    f"China regulatory Google CSE 429 and Brave returned no URLs; "
                                    f"backing off {backoff_s:.1f}s (attempt {attempt + 1}/{max_attempts})"
                                )
                            else:
                                log_warning(
                                    "China regulatory Google CSE 429 and Brave returned no URLs; "
                                    "no further Google retries."
                                )
                                backoff_s = None
                        elif est in (502, 503):
                            backoff_s = min(45.0, 1.5 * (2**attempt) + random.uniform(0.0, 0.5))
                            log_warning(
                                f"China regulatory Google CSE HTTP {est}; "
                                f"retry in {backoff_s:.1f}s (attempt {attempt + 1}/{max_attempts})"
                            )
                        else:
                            log_error(e, f"China regulatory CSE HTTP {est}")
                            return []
                    except Exception as e:
                        log_error(e, "China regulatory CSE")
                        return []

                if backoff_s is not None:
                    await asyncio.sleep(backoff_s)
                    continue

        log_warning(
            f"China regulatory Google CSE still failing after {max_attempts} attempt(s) "
            "(502/503/network); trying Brave Web Search once before giving up."
        )
        brave_last = await self._try_brave_cse_fallback(cse_query, int(params["num"]))
        if brave_last:
            log_warning("China regulatory: Brave Web Search supplied URLs after Google CSE retries exhausted")
            return brave_last
        log_warning("China regulatory: no URLs from Google CSE or Brave for this query stem.")
        return []

    async def _cse_parallel(
        self,
        stems: Sequence[str],
        instructions: Optional[str],
        num_per_stem: int,
    ) -> List[List[str]]:
        conc = max(1, min(4, settings.CHINA_REGULATORY_CSE_CONCURRENCY))
        sem = asyncio.Semaphore(conc)

        async def one(idx: int, stem: str) -> List[str]:
            async with sem:
                ins = _stem_instructions(stem, idx, instructions)
                cq = _build_cse_query(stem, ins)
                return await self._cse_urls(cq, num_per_stem)

        tasks = [one(i, s) for i, s in enumerate(stems)]
        return list(await asyncio.gather(*tasks, return_exceptions=True))

    async def _fetch_visible_text(self, url: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Returns (visible_text, html_title, first_h1_text)."""
        await rate_limiter.acquire("china_regulatory_content")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Clinical-Knowledge-Agent/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                ct = (response.headers.get("content-type") or "").lower()
                if "pdf" in ct or url.lower().endswith(".pdf"):
                    return (
                        "[PDF] Full text not extracted; use the official URL for the document.",
                        None,
                        None,
                    )
                soup = BeautifulSoup(response.text, "html.parser")
                page_title = None
                if soup.title and soup.title.string:
                    page_title = soup.title.string.strip() or None
                h1_el = soup.find("h1")
                h1_text = None
                if h1_el and h1_el.get_text(strip=True):
                    h1_text = h1_el.get_text(strip=True)
                for element in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
                    element.decompose()
                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.splitlines()]
                text = "\n".join(line for line in lines if line and len(line) > 10)
                return text, page_title, h1_text
            except Exception as e:
                return f"Failed to extract content from {url}: {e}", None, None

    async def _fetch_parallel(
        self,
        urls: List[str],
    ) -> List[Union[Tuple[str, str], BaseException]]:
        fc = max(1, min(8, settings.CHINA_REGULATORY_FETCH_CONCURRENCY))
        sem = asyncio.Semaphore(fc)

        async def one(u: str) -> Tuple[str, str, Optional[str], Optional[str]]:
            async with sem:
                body, ptitle, h1t = await self._fetch_visible_text(u)
                return (u, body, ptitle, h1t)

        return await asyncio.gather(*[one(u) for u in urls], return_exceptions=True)

    async def _optional_translate(self, text: str) -> Optional[str]:
        if not settings.CHINA_REGULATORY_TRANSLATE_SNIPPETS:
            return None
        cap = max(500, settings.CHINA_REGULATORY_TRANSLATE_MAX_CHARS)
        if len(text) > cap:
            return None
        system = (
            "You translate and summarize Chinese regulatory web excerpts into clear English for "
            "researchers. Preserve drug names, agency names, and document titles; note uncertainty. "
            "Do not add facts not in the source."
        )
        prompt = f"Source excerpt (may be Chinese):\n\n{text[:cap]}\n\nEnglish summary:"
        try:
            return (await llm_agent.generate_response(prompt, system_prompt=system)).strip()
        except Exception as e:
            log_error(e, "China regulatory snippet translate")
            return None

    async def search_regulatory(
        self,
        query: str,
        search_instructions: Optional[str] = None,
        max_results: int = 20,
    ) -> List[ChinaRegulatoryResult]:
        if not query or not str(query).strip():
            return []

        mv = max(1, min(8, settings.CHINA_REGULATORY_QUERY_VARIATIONS_MAX))
        stems = _expand_query_variations(query, search_instructions, mv)
        if not stems:
            return []

        num_per = max(2, min(10, settings.CHINA_REGULATORY_CSE_NUM_PER_VARIATION))
        relevance_blob = " ".join(stems + ([search_instructions] if search_instructions else []))

        cache_key = (
            f"china_regulatory:v4:{max_results}:{mv}:{num_per}:"
            f"{query}:{search_instructions or ''}"
        )
        cached = cache_manager.get(cache_key)
        if cached:
            return [ChinaRegulatoryResult.model_validate(item) for item in cached]

        batches = await self._cse_parallel(stems, search_instructions, num_per)
        merged = _merge_url_batches(batches)
        ranked = _rank_urls_by_quality(merged)

        fetch_budget = min(len(ranked), max(max_results * 3, max_results + 12))
        to_fetch = ranked[:fetch_budget]

        print(
            f"🔍 China regulatory: {len(stems)} query variation(s), "
            f"{len(merged)} unique URL(s), fetching top {len(to_fetch)}"
        )

        raw_pairs = await self._fetch_parallel(to_fetch)

        results: List[ChinaRegulatoryResult] = []
        for item in raw_pairs:
            if isinstance(item, BaseException):
                continue
            url, raw_text, page_title, h1_text = item
            if raw_text.startswith("Failed to extract"):
                continue

            title = _extract_simple_title(url, raw_text, page_title=page_title, h1=h1_text)
            domain = _classify_portal(url)
            try:
                host = urlparse(url).netloc
                if host.startswith("www."):
                    host = host[4:]
            except Exception:
                host = "unknown"

            metadata: dict = {
                "portal": domain,
                "original_language": "zh",
                "search_query": query,
                "search_instructions": search_instructions,
                "query_variations": stems,
                "query_variations_used": len(stems),
                "html_title": page_title,
                "h1": h1_text,
                "content_length": len(raw_text),
                "extraction_timestamp": datetime.now().isoformat(),
            }
            cap = max(4000, settings.CHINA_REGULATORY_PAGE_MAX_CHARS)
            content_slice = raw_text[:cap]
            content_en = await self._optional_translate(content_slice)
            if content_en:
                metadata["content_en"] = content_en[:8000]

            results.append(
                ChinaRegulatoryResult(
                    url=url,
                    title=title,
                    content=content_slice,
                    source_domain=host,
                    relevance_score=_relevance_score(raw_text, relevance_blob),
                    metadata=metadata,
                )
            )
            if len(results) >= max_results:
                break

        results.sort(key=lambda r: (-(r.relevance_score or 0), -_url_path_quality(r.url)))

        if results:
            cache_manager.set(cache_key, [r.model_dump() for r in results])

        return results[:max_results]


china_regulatory_agent = ChinaRegulatoryAgent()
