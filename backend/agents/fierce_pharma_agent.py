"""
Google Search Agent
Performs web searches using Google Custom Search Engine API with instructions from the dynamic reasoning engine
"""
import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from utils.logger import log_api_call, log_error, log_warning
from utils.cache import cache_manager
from utils.rate_limiter import rate_limiter
from utils.brave_web_search import clip_brave_query, fetch_brave_web_urls
from models.schemas import FiercePharmaResult
from agents.llm_agent import llm_agent
from datetime import datetime
import urllib.parse
from bs4 import BeautifulSoup
import random

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Publishers (Wiley, BMJ, Sage, Elsevier, etc.) often block scrapers. A current browser UA +
# Sec-Fetch-* / Referer (search traffic) improves success somewhat; many sites still 403
# datacenter IPs or require subscriptions — that is expected, not a bug in CSE.
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _clip_cse_query(q: str, limit: int = 380) -> str:
    """Google CSE often returns empty `items` for very long, highly boolean queries."""
    q = (q or "").strip()
    if len(q) <= limit:
        return q
    cut = q[:limit].rsplit(" ", 1)[0].strip()
    return cut if len(cut) > 48 else q[:limit]


def _google_cse_query_variants(query: str, search_instructions: Optional[str] = None) -> List[str]:
    """Shorter queries tend to yield `items` more reliably than a single max-length planner string."""
    raw = (query or "").strip()
    seen: set[str] = set()
    out: List[str] = []

    def add(s: str) -> None:
        s = (s or "").strip()
        if len(s) < 3 or s in seen:
            return
        seen.add(s)
        out.append(s)

    add(_clip_cse_query(raw, 380))
    words = raw.split()
    if len(words) > 16:
        add(" ".join(words[:16]))
    if len(words) > 10:
        add(" ".join(words[:10]))
    if len(words) > 6:
        add(" ".join(words[:6]))
    add(raw)
    if search_instructions:
        ins = search_instructions.strip()
        if ins and len(ins) < 160:
            for head in list(out[:3]):
                add(_clip_cse_query(f"{head} {ins}", 380))
    return out[:8]


async def _llm_expand_cse_queries(
    raw_query: str, search_instructions: Optional[str] = None
) -> List[str]:
    """Per-query LLM: entity/topic-aware CSE strings (not hardcoded rules)."""
    if not settings.GOOGLE_CSE_LLM_QUERY_PLANNING:
        return []
    rq = (raw_query or "").strip()
    ins_norm = (search_instructions or "").strip()[:500]
    cache_key = cache_manager._generate_key(
        "llm_cse_expand", {"q": rq[:900], "i": ins_norm}
    )
    cached = cache_manager.get(cache_key)
    if isinstance(cached, list):
        out_cached: List[str] = []
        seen_c: set[str] = set()
        for q in cached:
            s = _clip_cse_query(str(q).strip(), 380)
            if len(s) < 4:
                continue
            kl = s.lower()
            if kl in seen_c:
                continue
            seen_c.add(kl)
            out_cached.append(s)
        return out_cached[:14]

    prompt = f"""You propose Google web search query strings for clinical/regulatory research.

PLANNER SEARCH STRING (may be long):
{rq[:900]}

OPTIONAL INSTRUCTIONS:
{ins_norm}

1. List 2-8 salient topics or entities for THIS query only, ordered from the most specific anchor to broader context (e.g. company, drug, modality, disease, regulatory artifact).
2. Output 5-12 distinct search_queries, each under 88 characters.
   - Prefer queries that join the anchor entity with another topic (e.g. company + pipeline, company + modality).
   - Avoid queries that drop the main anchor and only combine two generic fragments (e.g. if the user cares about a specific company + pipeline + CART, do not emit only "pipeline CART" without that anchor).
   - If the planner string names a pharmaceutical company or sponsor, include that company name (or unmistakable short form used in the text) in most queries; avoid company-agnostic strings that match unrelated manufacturers or generic industry reports.
   - Include one or two tight paraphrases of the original intent.

Return ONLY valid JSON:
{{"topics":["..."],"search_queries":["...", "..."]}}
"""
    try:
        raw = await llm_agent.generate_structured_response(
            prompt,
            system_prompt="You output only valid JSON objects.",
            max_tokens=900,
        )
        if not raw or "Error generating" in raw:
            return []
        data = json.loads(raw) if raw.strip().startswith("{") else {}
        queries = data.get("search_queries") or []
        out: List[str] = []
        seen: set[str] = set()
        for q in queries:
            s = _clip_cse_query(str(q).strip(), 380)
            if len(s) < 4:
                continue
            k = s.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(s)
        out = out[:14]
        if int(settings.LLM_AUX_CACHE_TTL_SECONDS) > 0:
            cache_manager.set(
                cache_key, out, ttl=int(settings.LLM_AUX_CACHE_TTL_SECONDS)
            )
        return out
    except Exception as e:
        log_error(e, "LLM CSE query expansion")
        return []


def _browser_like_headers() -> dict[str, str]:
    return {
        "User-Agent": _BROWSER_UA,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "Referer": "https://www.google.com/",
    }


class GoogleSearchAgent:
    def __init__(self):
        # Google Custom Search Engine API configuration
        self.api_key = settings.GOOGLE_API_KEY
        self.search_engine_id = settings.GOOGLE_SEARCH_ENGINE_ID
        self.base_url = settings.GOOGLE_CSE_BASE_URL
        self.timeout = httpx.Timeout(15.0)
    
    @staticmethod
    def _urls_from_cse_payload(data: Dict[str, Any]) -> List[str]:
        urls: List[str] = []
        for item in data.get("items") or []:
            if isinstance(item, dict) and item.get("link"):
                urls.append(item["link"])
        return urls

    async def _brave_search_urls(self, brave_variants: List[str], num_results: int) -> List[str]:
        """Brave Web Search when Google CSE returns 429."""
        urls = await fetch_brave_web_urls(
            brave_variants,
            num_results=num_results,
            timeout=self.timeout,
            operators=False,
        )
        if urls:
            print(f"✅ Found {len(urls)} URLs via Brave Web Search (Google CSE rate-limited)")
        return urls

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def _make_google_search(self, query: str, num_results: int = 10, search_instructions: str = None) -> List[str]:
        """Make Google Custom Search Engine API request with retry logic"""
        await rate_limiter.acquire("google_search")

        headers = {
            "User-Agent": "Clinical-Knowledge-Agent/1.0",
            "Accept": "application/json",
        }
        variants = _google_cse_query_variants(query, search_instructions)
        llm_vars = await _llm_expand_cse_queries(query, search_instructions)
        seen_v = {v.lower() for v in variants}
        for q in llm_vars:
            kl = q.lower()
            if kl not in seen_v:
                seen_v.add(kl)
                variants.insert(0, q)
        variants = variants[:14]

        seen_br: set[str] = set()
        brave_variants: List[str] = []
        for v in variants:
            bq = clip_brave_query(v)
            if len(bq) < 2:
                continue
            kl = bq.lower()
            if kl in seen_br:
                continue
            seen_br.add(kl)
            brave_variants.append(bq)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            start_time = asyncio.get_event_loop().time()
            last_data: Dict[str, Any] = {}
            last_status = 200

            try:
                for q_try in variants:
                    params = {
                        "key": self.api_key,
                        "cx": self.search_engine_id,
                        "q": q_try,
                        "num": min(num_results, 10),
                        "safe": "off",
                    }
                    response = await client.get(self.base_url, params=params, headers=headers)
                    if response.status_code == 429 and (settings.BRAVE_API_KEY or "").strip():
                        print("⚠️ Google CSE returned 429; trying Brave Web Search")
                        urls = await self._brave_search_urls(brave_variants, num_results)
                        if urls:
                            return urls[:num_results]
                        print("⚠️ Brave Search returned no URLs after Google 429")
                        return []
                    response.raise_for_status()
                    last_status = response.status_code
                    data = response.json()
                    last_data = data
                    urls = self._urls_from_cse_payload(data)
                    if urls:
                        end_time = asyncio.get_event_loop().time()
                        log_api_call(
                            "google_search",
                            "google_cse_search",
                            response.status_code,
                            end_time - start_time,
                        )
                        print(f"✅ Found {len(urls)} URLs using Google CSE API ({len(q_try)} char query)")
                        return urls
                    si = data.get("searchInformation") or {}
                    tr = si.get("totalResults")
                    print(
                        f"⚠️ CSE returned no items (query len={len(q_try)}, totalResults={tr!r}); trying shorter variant…"
                    )

                end_time = asyncio.get_event_loop().time()
                log_api_call("google_search", "google_cse_search", last_status, end_time - start_time)
                print(f"⚠️ No results found in Google CSE API response after {len(variants)} query variant(s)")
                if last_data:
                    err = last_data.get("error")
                    if err:
                        print(f"   CSE error object: {err}")
                return await self._fallback_search(query, num_results, search_instructions)

            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 429 and (settings.BRAVE_API_KEY or "").strip():
                    print("⚠️ Google CSE HTTP 429; trying Brave Web Search")
                    urls = await self._brave_search_urls(brave_variants, num_results)
                    if urls:
                        return urls[:num_results]
                    print("⚠️ Brave Search returned no URLs after Google CSE HTTP 429")
                    return []
                est = e.response.status_code if e.response is not None else 0
                error_detail = f"Google CSE API error: {est}"
                try:
                    if e.response is not None:
                        error_detail += f" - {e.response.text[:200]}"
                except Exception:
                    pass
                log_error(e, error_detail)

                if e.response is not None and e.response.status_code == 403 and "suspended" in e.response.text.lower():
                    print("⚠️ Google API key suspended, using mock data")
                    return await self._get_mock_urls(query, num_results)

                print("⚠️ Google CSE API error, trying fallback search")
                return await self._fallback_search(query, num_results, search_instructions)
            except Exception as e:
                log_error(e, "Google CSE API search")
                print("⚠️ Google CSE API error, trying fallback")
                return await self._fallback_search(query, num_results, search_instructions)
    
    async def _get_mock_urls(self, query: str, num_results: int) -> List[str]:
        """Provide mock URLs when API is unavailable"""
        print(f"🔄 Providing mock URLs for: {query}")
        
        # Generate mock URLs based on the query
        mock_urls = [
            "https://www.example.com/mock-article-1",
            "https://www.example.com/article/mock-article-2", 
            "https://www.example.com/news/mock-article-3",
            "https://www.example.com/research/mock-article-4",
            "https://www.example.com/study/mock-article-5"
        ]
        
        # Return a subset based on num_results
        return mock_urls[:num_results]
    
    async def _fallback_search(self, query: str, num_results: int, search_instructions: str = None) -> List[str]:
        """Fallback search without site restrictions"""
        try:
            print(f"🔄 Trying fallback search for: {query}")

            headers = {
                "User-Agent": "Clinical-Knowledge-Agent/1.0",
                "Accept": "application/json",
            }
            variants = _google_cse_query_variants(query, search_instructions)

            seen_br: set[str] = set()
            brave_variants: List[str] = []
            for v in variants:
                bq = clip_brave_query(v)
                if len(bq) < 2:
                    continue
                kl = bq.lower()
                if kl in seen_br:
                    continue
                seen_br.add(kl)
                brave_variants.append(bq)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    for q_try in variants:
                        params = {
                            "key": self.api_key,
                            "cx": self.search_engine_id,
                            "q": q_try,
                            "num": min(num_results, 10),
                            "safe": "off",
                        }
                        response = await client.get(self.base_url, params=params, headers=headers)
                        if response.status_code == 429 and (settings.BRAVE_API_KEY or "").strip():
                            urls = await self._brave_search_urls(brave_variants, num_results)
                            if urls:
                                print(f"✅ Found {len(urls)} URLs via Brave (Google CSE 429 in fallback)")
                                return urls[:num_results]
                            return []
                        response.raise_for_status()
                        data = response.json()
                        urls = self._urls_from_cse_payload(data)
                        if urls:
                            print(f"✅ Found {len(urls)} URLs using fallback search")
                            return urls[:num_results]

                    short = _clip_cse_query(query, 220)
                    tail = (short.split() or [""])[-1] if short else ""
                    for extra in ("news", "FDA", "clinical trial", tail):
                        if not extra or len(extra) < 2:
                            continue
                        q_news = _clip_cse_query(f"{short} {extra}", 380)
                        print("🔄 Trying even broader search")
                        params = {
                            "key": self.api_key,
                            "cx": self.search_engine_id,
                            "q": q_news,
                            "num": min(num_results, 10),
                            "safe": "off",
                        }
                        response = await client.get(self.base_url, params=params, headers=headers)
                        if response.status_code == 429 and (settings.BRAVE_API_KEY or "").strip():
                            urls = await self._brave_search_urls(brave_variants, num_results)
                            if urls:
                                print(f"✅ Found {len(urls)} URLs via Brave (Google CSE 429 in fallback)")
                                return urls[:num_results]
                            return []
                        response.raise_for_status()
                        data = response.json()
                        urls = self._urls_from_cse_payload(data)
                        if urls:
                            return urls[:num_results]

                    return []

                except httpx.HTTPStatusError as e:
                    if e.response is not None and e.response.status_code == 429 and (settings.BRAVE_API_KEY or "").strip():
                        urls = await self._brave_search_urls(brave_variants, num_results)
                        if urls:
                            print(f"✅ Found {len(urls)} URLs via Brave (Google CSE HTTP 429 in fallback)")
                            return urls[:num_results]
                        return []
                    if e.response is not None and e.response.status_code == 403 and "suspended" in e.response.text.lower():
                        print("⚠️ Google API key suspended in fallback, using mock data")
                        return await self._get_mock_urls(query, num_results)
                    raise e

        except Exception as e:
            print(f"⚠️ Fallback search also failed: {e}")
            return []
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def _extract_text_from_url(self, url: str) -> str:
        """Extract text content from a URL with retry logic"""
        await rate_limiter.acquire("google_search_content")

        headers = _browser_like_headers()

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                raw = response.content
                ct = (response.headers.get("content-type") or "").lower()
                url_path = (url or "").lower().split("?")[0]

                def _is_pdf_body() -> bool:
                    if "pdf" in ct or url_path.endswith(".pdf"):
                        return True
                    return len(raw) >= 5 and raw[:5] == b"%PDF-"

                if _is_pdf_body():
                    if fitz is None:
                        return f"PDF at {url} detected but text extraction (PyMuPDF) is unavailable."
                    try:
                        doc = fitz.open(stream=raw, filetype="pdf")
                        parts: List[str] = []
                        n_pages = min(int(doc.page_count or 0), 45)
                        for i in range(n_pages):
                            parts.append(doc.load_page(i).get_text())
                        doc.close()
                        text = "\n".join(
                            line.strip() for line in "\n".join(parts).splitlines() if line.strip()
                        )
                        cap = max(8000, int(settings.GOOGLE_SEARCH_CONTENT_MAX_CHARS) * 2)
                        if text.strip():
                            return text[:cap]
                        return f"PDF at {url} opened but contained little extractable text."
                    except Exception as ex:
                        return f"Failed to extract PDF text from {url}: {ex}"

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove scripts, styles, and other non-content elements
                for element in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
                    element.decompose()
                
                # Get text and clean up
                text = soup.get_text(separator="\n")
                lines = [line.strip() for line in text.splitlines()]
                text = "\n".join(line for line in lines if line and len(line) > 10)
                
                return text
                
            except Exception as e:
                return f"Failed to extract content from {url}: {str(e)}"
    
    async def search_web(self, query: str, search_instructions: str = None, max_results: int = 20) -> List[FiercePharmaResult]:
        """Search the web based on query and search instructions from the dynamic reasoning engine"""
        try:
            print(f"🔍 Performing web search for: '{query}'")
            if search_instructions:
                print(f"📋 Search instructions: {search_instructions}")
            
            # Check cache first
            cache_key = f"google_search:{query}:{search_instructions}:{max_results}"
            cached_result = cache_manager.get(cache_key)
            
            if cached_result:
                print(f"    ✅ Returning cached results")
                return [FiercePharmaResult(**item) for item in cached_result]
            
            # Get URLs from Google search
            urls = await self._make_google_search(query, max_results, search_instructions)
            
            if not urls:
                print(f"    ❌ No results found from Google search")
                return []
            
            # Extract content from URLs
            results = []
            for url in urls:
                try:
                    content = await self._extract_text_from_url(url)
                    if content and not content.startswith("Failed to extract"):
                        result = self._create_result(url, content, query, search_instructions)
                        if result:
                            results.append(result)
                except Exception as e:
                    print(f"    ⚠️ Error processing URL {url}: {e}")
                    continue
            
            if results:
                # Cache results for this query
                cache_manager.set(cache_key, [result.dict() for result in results])
                print(f"    ✅ Found {len(results)} results")
            
            return results[:max_results]
            
        except Exception as e:
            print(f"❌ Google search error: {e}")
            log_error(e, "Google search")
            return []
    
    async def search_news(self, query: str, max_results: int = 20) -> List[FiercePharmaResult]:
        """Search for pharmaceutical news articles"""
        try:
            # Add pharmaceutical news context to the query
            news_query = f"{query} pharmaceutical news"
            search_instructions = "Focus on recent pharmaceutical industry news, drug approvals, clinical trial results, and company announcements"
            
            return await self.search_web(news_query, search_instructions, max_results)
            
        except Exception as e:
            print(f"❌ News search error: {e}")
            log_error(e, "News search")
            return []
    
    def _create_result(self, url: str, content: str, query: str, search_instructions: str = None) -> Optional[FiercePharmaResult]:
        """Create a search result"""
        try:
            # Extract a simple title from URL or content
            title = self._extract_simple_title(url, content)
            
            # Calculate a simple relevance score
            relevance_score = self._calculate_simple_relevance(content, query)
            
            # Extract domain from URL
            domain = self._extract_domain(url)
            
            # Build result
            cap = max(4000, settings.GOOGLE_SEARCH_CONTENT_MAX_CHARS)
            result = FiercePharmaResult(
                url=url,
                title=title,
                content=content[:cap],
                publication_date=None,  # Not extracting dates
                companies=[],  # Not extracting companies
                drugs=[],  # Not extracting drugs
                topics=[],  # Not extracting topics
                relevance_score=relevance_score,
                source_domain=domain,
                metadata={
                    'search_query': query,
                    'search_instructions': search_instructions,
                    'content_length': len(content),
                    'extraction_timestamp': datetime.now().isoformat()
                }
            )
            
            return result
            
        except Exception as e:
            print(f"⚠️ Error creating result: {e}")
            return None
    
    def _extract_simple_title(self, url: str, content: str) -> str:
        """Extract a simple title from URL or content"""
        # Try to extract from URL first
        url_parts = url.split('/')
        if len(url_parts) > 3:
            title_from_url = url_parts[-1].replace('-', ' ').replace('_', ' ').title()
            if len(title_from_url) > 10:
                return title_from_url
        
        # Try to extract from content
        lines = content.split('\n')
        for line in lines[:25]:  # Increased from 10 to 25 lines for better title extraction
            line = line.strip()
            if len(line) > 20 and len(line) < 200 and not line.startswith('http'):
                return line
        
        return "Web Search Result"
    
    def _calculate_simple_relevance(self, content: str, search_query: str) -> float:
        """Calculate a simple relevance score"""
        content_lower = content.lower()
        search_query_lower = search_query.lower()
        
        # Count occurrences of search terms
        term_count = 0
        for term in search_query_lower.split():
            term_count += content_lower.count(term)
        
        # Normalize by content length
        if len(content) > 0:
            score = min(term_count / (len(content) / 1000), 1.0)
        else:
            score = 0.0
        
        return round(score, 2)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return "unknown"

# Create a singleton instance
google_search_agent = GoogleSearchAgent() 