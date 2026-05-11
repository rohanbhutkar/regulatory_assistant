"""
Normalize citations to {text, url} for API/WebSocket consumers and the frontend.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_URL_IN_TEXT = re.compile(r"https?://[^\s\|\]\)\"'<>]+", re.IGNORECASE)


def _strip_trailing_punct(url: str) -> str:
    return url.rstrip(").,]'\"»")


def clinicaltrials_url(nct_id: object) -> str:
    raw = str(nct_id or "").strip().upper().replace(" ", "")
    if raw.startswith("NCT"):
        nid = raw
    elif raw.isdigit():
        nid = f"NCT{raw}"
    else:
        nid = raw or "UNKNOWN"
    return f"https://clinicaltrials.gov/study/{nid}"


def pubmed_url(pmid: object) -> str:
    p = str(pmid or "").strip()
    if not p.isdigit():
        return ""
    return f"https://pubmed.ncbi.nlm.nih.gov/{p}/"


def _first_http_url(d: Dict[str, Any]) -> str:
    for key in ("url", "document_url", "link", "href", "general_url", "dhpc_url", "psusa_url", "pip_url"):
        v = d.get(key)
        if isinstance(v, str) and v.strip().lower().startswith(("http://", "https://")):
            return _strip_trailing_punct(v.strip())
    su = d.get("source_urls")
    if isinstance(su, list):
        for u in su:
            if isinstance(u, str) and u.strip().lower().startswith(("http://", "https://")):
                return _strip_trailing_punct(u.strip())
    oid = d.get("id")
    if isinstance(oid, str) and oid.strip().lower().startswith(("http://", "https://")):
        return _strip_trailing_punct(oid.strip())
    return ""


def citation_link_from_content(content: dict, layer_type: str) -> Optional[Dict[str, str]]:
    """
    Build a single {text, url} citation from a context/search item dict.
    Returns None if there is nothing useful to show.
    """
    if not isinstance(content, dict):
        return None

    url = _first_http_url(content)
    title = (
        content.get("title")
        or content.get("name")
        or content.get("brief_title")
        or content.get("drug_name")
        or "Source"
    )
    title = str(title).strip() or "Source"

    if "nct_id" in content and content.get("nct_id"):
        nid = str(content["nct_id"]).strip()
        u = clinicaltrials_url(nid)
        parts = [f"{nid}: {title}"]
        for key, label in (
            ("condition", "Condition"),
            ("phase", "Phase"),
            ("status", "Status"),
        ):
            if content.get(key):
                parts.append(f"{label}: {content[key]}")
        return {"text": " | ".join(parts), "url": u}

    if "pmid" in content and content.get("pmid") is not None:
        pm = str(content["pmid"]).strip()
        u = pubmed_url(pm)
        parts = [f"PMID {pm}: {title}"]
        if content.get("journal"):
            parts.append(f"Journal: {content['journal']}")
        return {"text": " | ".join(parts), "url": u}

    if url:
        src = (
            content.get("source")
            or content.get("source_domain")
            or content.get("portal")
            or layer_type.replace("_", " ")
        )
        text = f"{src}: {title}"
        return {"text": text[:500], "url": url}

    if "id" in content and isinstance(content.get("id"), str) and content["id"].lower().startswith("http"):
        u = _strip_trailing_punct(content["id"].strip())
        return {"text": f"{layer_type}: {title}"[:500], "url": u}

    # Labels / openfda-style without URL: still show text (no link)
    if content.get("openfda") or content.get("application_number"):
        text = title
        if content.get("application_number"):
            text = f"{content.get('application_number')}: {title}"
        return {"text": text[:500], "url": ""}

    return None


def dedupe_citation_links(links: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set = set()
    out: List[Dict[str, str]] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        text = (link.get("text") or "").strip()
        url = (link.get("url") or "").strip()
        if not text and not url:
            continue
        key = (url.lower(), text[:120].lower()) if url else (text[:200].lower(),)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": text or url, "url": url})
    return out


def normalize_citation_entries(raw: Any) -> List[Dict[str, str]]:
    """
    Coerce legacy string citations or mixed payloads into {text, url} dicts.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raw = [raw]
    out: List[Dict[str, str]] = []
    for item in raw:
        if item is None:
            continue
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("label") or item.get("title") or "").strip()
            url = str(item.get("url") or item.get("href") or item.get("link") or "").strip()
            if not text and url:
                text = url
            if text or url:
                out.append({"text": text or url, "url": url})
            continue
        s = str(item).strip()
        if not s:
            continue
        m = _URL_IN_TEXT.search(s)
        url = _strip_trailing_punct(m.group(0)) if m else ""
        text = s
        if url:
            text = s.replace(url, "").replace("URL:", "").replace("|", " ").strip()
            text = re.sub(r"\s{2,}", " ", text).strip() or url
        out.append({"text": text[:600], "url": url})
    return dedupe_citation_links(out)
