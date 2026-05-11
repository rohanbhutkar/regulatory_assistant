"""
Deep research orchestration: brief + outline, verifier, replan helpers.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from config import settings
from agents.llm_agent import llm_agent
from models.schemas import GraphPlan
from utils.cache import cache_manager


def research_spec_from_llm_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize LLM output for research_spec stored in ContextManager."""
    return {
        "brief": str(data.get("brief") or "").strip(),
        "assumptions": list(data.get("assumptions") or []),
        "must_have_facts": list(data.get("must_have_facts") or []),
        "outline": list(data.get("outline") or []),
    }


async def build_research_brief_and_outline(query: str) -> Dict[str, Any]:
    """STORM-style brief + hierarchical outline (JSON)."""
    qn = (query or "").strip() or " "
    cache_key = cache_manager._generate_key("llm_research_brief", qn[:12000])
    cached = cache_manager.get(cache_key)
    if isinstance(cached, dict) and cached.get("brief") is not None:
        return cached

    prompt = f"""You are planning a rigorous multi-source research task for a clinical / regulatory intelligence product.

USER QUERY:
{query}

Return ONLY valid JSON (no markdown):
{{
  "brief": "2-5 sentences: scope, intent, and what a complete answer must cover",
  "assumptions": ["short assumption strings"],
  "must_have_facts": ["specific factual checkpoints, e.g. primary registry IDs, label sections, geographies"],
  "outline": [
    {{
      "section_id": "snake_case_id",
      "title": "Section title",
      "sub_questions": ["concrete sub-question 1", "sub-question 2"]
    }}
  ]
}}

Rules:
- Use 4-10 outline sections for broad questions; 2-4 for narrow questions.
- Sub-questions should be specific enough to map to search nodes later.
- section_id must be unique snake_case.
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="You output only valid JSON for research planning.",
        max_tokens=min(4096, settings.GRAPH_PLAN_MAX_TOKENS),
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError("brief/outline: invalid JSON")
        data = json.loads(m.group())
    spec = research_spec_from_llm_dict(data)
    cache_manager.set(cache_key, spec, ttl=int(settings.LLM_AUX_CACHE_TTL_SECONDS))
    return spec


def format_research_spec_for_planner(spec: Dict[str, Any]) -> str:
    lines = [
        "\n\nINTERNAL RESEARCH BRIEF (follow this coverage; map nodes to section_id):",
        spec.get("brief", ""),
        "\nASSUMPTIONS:",
        *[f"- {a}" for a in spec.get("assumptions", [])],
        "\nMUST-HAVE FACTS / CHECKPOINTS:",
        *[f"- {m}" for m in spec.get("must_have_facts", [])],
        "\nOUTLINE (each section should be addressable by one or more nodes; put section_id in node description):",
    ]
    for sec in spec.get("outline", []):
        sid = sec.get("section_id", "")
        title = sec.get("title", "")
        subs = sec.get("sub_questions") or []
        lines.append(f"- [{sid}] {title}")
        for sq in subs:
            lines.append(f"    • {sq}")
    return "\n".join(lines)


def summarize_execution_for_verifier(
    execution_results: Dict[str, Any],
    max_chars: int = 14000,
) -> str:
    """Compact text for verifier LLM (not full raw dumps)."""
    parts: List[str] = []
    used = 0
    for node_id, payload in execution_results.items():
        chunk_head = f"\n--- NODE {node_id} ---\n"
        if isinstance(payload, list):
            n = len(payload)
            sample = payload[:3]
            body = json.dumps(sample, default=str)[:4000]
            block = f"{chunk_head}type=list count={n} sample={body}"
        elif isinstance(payload, dict):
            body = json.dumps(payload, default=str)[:6000]
            block = f"{chunk_head}{body}"
        else:
            block = f"{chunk_head}{str(payload)[:2000]}"
        if used + len(block) > max_chars:
            parts.append("\n[... additional nodes omitted for verifier budget ...]")
            break
        parts.append(block)
        used += len(block)
    return "".join(parts) if parts else "(no execution results)"


async def verify_research_coverage(
    query: str,
    research_spec: Dict[str, Any],
    execution_summary: str,
) -> Dict[str, Any]:
    """LLM verifier: gaps vs outline + user intent."""
    outline = research_spec.get("outline", [])
    outline_ids = [str(s.get("section_id", "")) for s in outline]
    prompt = f"""You verify whether executed research adequately covers the planned outline and user query.

USER QUERY:
{query}

RESEARCH BRIEF:
{research_spec.get("brief", "")}

OUTLINE SECTION IDS: {outline_ids}

EXECUTION SUMMARY (truncated tool/node outputs):
{execution_summary}

Return ONLY JSON:
{{
  "passed": true or false,
  "section_status": [{{"section_id": "...", "adequate": true/false, "note": "one line"}}],
  "gaps": [{{"section_id": "...", "reason": "what is missing"}}],
  "contradictions": ["optional short notes"],
  "confidence": "high|medium|low"
}}

passed=true only if all outline sections are adequately supported OR the outline was over-scoped and remaining gaps are minor.
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="You output only valid JSON. Be strict about missing primary evidence for regulatory/clinical claims.",
        max_tokens=2048,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {
                "passed": True,
                "section_status": [],
                "gaps": [],
                "contradictions": [],
                "confidence": "low",
            }
        return json.loads(m.group())


_REPLAN_ALLOWED_SOURCES = frozenset(
    {
        "aact",
        "clinical_trials",
        "trialtrove",
        "pubmed",
        "biomcp",
        "openfda",
        "ema_eu",
        "china_regulatory",
        "fda_labels",
        "google_search",
        "claims_data",
        "payer_data",
        "site_trove",
        "goodrx",
        "nih_reporter",
        "npi_registry",
        "openalex",
        "crossref",
        "ror",
        "open_payments",
        "eu_ctis",
        "isrctn",
        "cms_open_data",
        "fda_datadashboard",
        "healthcare_analytics",
    }
)


async def replan_targeted_nodes_and_edges(
    query: str,
    research_spec: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    existing_node_ids: List[str],
    replan_round: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    One small LLM call: map each verifier gap to a single targeted SEARCH (one agent/source),
    instead of re-planning a full graph. Falls back to empty if parse fails (caller may use legacy replan).
    """
    mx = max(1, int(settings.DEEP_RESEARCH_MAX_NEW_NODES_PER_ROUND))
    gap_txt = json.dumps(gaps, indent=2)[:12000]
    existing = ", ".join(existing_node_ids[:80])
    prompt = f"""The research verifier reported coverage gaps. Propose up to {mx} new SEARCH nodes only — one primary search per gap, each using a single data source/agent.

USER QUERY:
{query}

BRIEF:
{str(research_spec.get("brief") or "")[:2000]}

GAPS (JSON):
{gap_txt}

EXISTING NODE IDS (never reuse): {existing}
REPLAN ROUND NUMBER: {replan_round}

Return ONLY valid JSON:
{{
  "fills": [
    {{
      "section_id": "outline section_id from gap or empty string",
      "source": "ema_eu",
      "search_focus": "concise string passed to that agent",
      "search_instructions": "optional short hints",
      "max_results": 28,
      "facet": "regulatory|clinical|commercial|sites|publications|meta",
      "description": "one line for the graph node",
      "rationale": "one line why this fixes the gap"
    }}
  ]
}}

Rules:
- At most {mx} objects in "fills". Pick the highest-impact gaps first.
- Each "source" must be exactly one of: aact, clinical_trials, trialtrove, pubmed, biomcp, openfda, ema_eu, china_regulatory, fda_labels, google_search, claims_data, payer_data, site_trove, goodrx, nih_reporter, npi_registry, openalex, crossref, ror, open_payments, eu_ctis, isrctn, cms_open_data, fda_datadashboard, healthcare_analytics
- Only type "search" — no analyze or synthesize nodes.
- dependencies must be [] for every new node (they run in a batch before final synthesize).
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="Return only valid JSON.",
        max_tokens=min(2500, settings.GRAPH_PLAN_MAX_TOKENS),
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return [], []
        data = json.loads(m.group())
    fills = list(data.get("fills") or [])
    nodes: List[Dict[str, Any]] = []
    for i, f in enumerate(fills[:mx]):
        if not isinstance(f, dict):
            continue
        src = str(f.get("source") or "google_search").strip().lower()
        if src not in _REPLAN_ALLOWED_SOURCES:
            src = "google_search"
        nid = f"replan_r{replan_round}_{src}_{i}"
        nodes.append(
            {
                "id": nid,
                "type": "search",
                "description": str(f.get("description") or f.get("rationale") or f"Gap fill: {src}")[:600],
                "parameters": {
                    "source": src,
                    "max_results": int(f.get("max_results") or 28),
                    "search_focus": str(f.get("search_focus") or query)[:900],
                    "outline_section_id": str(f.get("section_id") or ""),
                    "facet": str(f.get("facet") or "regulatory"),
                    "search_instructions": str(f.get("search_instructions") or "")[:1200],
                },
                "dependencies": [],
            }
        )
    return nodes, []


async def replan_new_nodes_json(
    query: str,
    research_spec: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    existing_node_ids: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Ask LLM for a small set of new graph nodes (JSON dicts) to fill gaps."""
    gap_txt = json.dumps(gaps, indent=2)
    existing = ", ".join(existing_node_ids[:80])
    prompt = f"""The research run has coverage gaps. Propose AT MOST {settings.DEEP_RESEARCH_MAX_NEW_NODES_PER_ROUND} new SEARCH or ANALYZE nodes (no synthesize).

USER QUERY: {query}
BRIEF: {research_spec.get("brief", "")}
GAPS: {gap_txt}
EXISTING NODE IDS (do not reuse ids): {existing}

Return JSON:
{{ "nodes": [ {{ same shape as graph plan nodes: id, type, description, parameters, dependencies }} ], "edges": [{{"from":"...","to":"..."}}] }}

Rules:
- Use only sources from the main planner list: trialtrove, aact, pubmed, google_search, openfda, fda_labels, ema_eu, china_regulatory, clinical_trials, etc.
- type must be "search" or "analyze"
- ids must be new, descriptive, prefix replan_ round e.g. replan_r1_pubmed_x
- dependencies should reference existing nodes or other new nodes you add
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="Return only valid JSON.",
        max_tokens=4096,
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return [], []
        data = json.loads(m.group())
    nodes = list(data.get("nodes") or [])
    edges = list(data.get("edges") or [])
    clean_edges: List[Dict[str, str]] = []
    for e in edges:
        if isinstance(e, dict) and e.get("from") and e.get("to"):
            clean_edges.append({"from": str(e["from"]), "to": str(e["to"])})
    return nodes, clean_edges


def merge_replan_into_plan(
    plan: GraphPlan,
    new_nodes: List[GraphNode],
    new_edges: List[Dict[str, str]],
) -> GraphPlan:
    """Insert new nodes before the last synthesize node in execution order; merge edges."""
    nodes_by_id = {n.id: n for n in plan.nodes}
    for n in new_nodes:
        nodes_by_id[n.id] = n
    all_nodes = list(nodes_by_id.values())

    synth_exec_idx = None
    for i, nid in enumerate(plan.execution_order):
        node = nodes_by_id.get(nid)
        if node and node.type == "synthesize":
            synth_exec_idx = i
            break

    existing_order_set = set(plan.execution_order)
    new_ids = [n.id for n in new_nodes if n.id not in existing_order_set]

    if synth_exec_idx is not None and new_ids:
        order = (
            plan.execution_order[:synth_exec_idx]
            + new_ids
            + plan.execution_order[synth_exec_idx:]
        )
    else:
        order = list(plan.execution_order) + new_ids

    # Dedupe order preserving first occurrence
    seen = set()
    deduped_order: List[str] = []
    for nid in order:
        if nid not in seen:
            seen.add(nid)
            deduped_order.append(nid)

    edges = list(plan.edges) + list(new_edges)
    return GraphPlan(
        nodes=all_nodes,
        edges=edges,
        execution_order=deduped_order,
        reasoning=(plan.reasoning or "")
        + f" [Deep research replan: +{len(new_ids)} nodes]",
    )


def broad_query_explanation(
    query: str, research_spec: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Same gate as parallel sub-runs, with human-readable rationale lines."""
    lines: List[str] = []
    outline = research_spec.get("outline") or []
    n = len(outline)
    th = settings.DEEP_RESEARCH_MIN_OUTLINE_SECTIONS_FOR_PARALLEL
    if n >= th:
        br = max(2, min(int(getattr(settings, "DEEP_RESEARCH_PARALLEL_BRANCH_COUNT", 4) or 4), 8))
        lines.append(
            f"Outline has {n} sections (threshold is {th}), so this request is treated as broad: "
            f"I'll run up to {br} parallel sub-plans (split by outline) and merge their evidence before synthesis."
        )
        return True, lines
    ql = (query or "").lower()
    breadth_kw = (
        "compare",
        "versus",
        " vs ",
        "landscape",
        "overview",
        "multiple",
        "across jurisdictions",
        "global",
        "comprehensive survey",
    )
    matched = [k.strip() for k in breadth_kw if k in ql]
    if matched:
        br = max(2, min(int(getattr(settings, "DEEP_RESEARCH_PARALLEL_BRANCH_COUNT", 4) or 4), 8))
        lines.append(
            "Query text signals a wide scope (matched: "
            + ", ".join(repr(m) for m in matched[:6])
            + f"); up to {br} parallel branches may run when the outline is large enough."
        )
        return True, lines
    lines.append(
        f"Outline has only {n} section(s) and no breadth keywords matched, "
        "so I'm using a single execution path (no parallel split)."
    )
    return False, lines


def is_broad_query(query: str, research_spec: Dict[str, Any]) -> bool:
    """Heuristic for parallel sub-runs."""
    ok, _ = broad_query_explanation(query, research_spec)
    return ok


def ui_brief_payload(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Narration for research_brief_ready WebSocket."""
    assumptions = [str(a).strip() for a in (spec.get("assumptions") or []) if str(a).strip()]
    must_have = [str(m).strip() for m in (spec.get("must_have_facts") or []) if str(m).strip()]
    thinking_lines: List[str] = [
        "I'm locking scope before touching tools: the brief is the contract for what “done” means.",
    ]
    if assumptions:
        thinking_lines.append(
            f"Stated assumptions ({len(assumptions)}): "
            + "; ".join(assumptions[:5])
            + (" …" if len(assumptions) > 5 else "")
        )
    else:
        thinking_lines.append("No explicit assumptions listed — planner will infer scope from the question only.")
    if must_have:
        thinking_lines.append(
            f"Must-have checkpoints ({len(must_have)}): later I'll check coverage against these concrete facts."
        )
    return {"thinking_lines": thinking_lines}


def ui_outline_payload(outline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Structured preview for research_outline_ready."""
    sections: List[Dict[str, Any]] = []
    for sec in outline:
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("section_id") or "")
        title = str(sec.get("title") or "")
        subs = sec.get("sub_questions") or []
        if not isinstance(subs, list):
            subs = []
        sections.append(
            {
                "section_id": sid,
                "title": title,
                "sub_question_count": len(subs),
                "sub_questions_preview": [str(s) for s in subs[:4]],
            }
        )
    thinking_lines: List[str] = [
        f"I'm decomposing the brief into {len(sections)} outline sections — each should map to one or more search/analyze nodes.",
    ]
    if sections:
        labels = [f"[{s['section_id']}] {s['title']}" for s in sections[:10]]
        thinking_lines.append("Coverage map: " + " · ".join(labels) + (" · …" if len(sections) > 10 else ""))
    return {"thinking_lines": thinking_lines, "sections_preview": sections}


def ui_verifier_payload(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Readable verifier outcome for the UI (not just pass/fail counts)."""
    passed = bool(verdict.get("passed"))
    conf = str(verdict.get("confidence") or "unknown")
    thinking_lines: List[str] = [
        f"Running the coverage verifier (confidence reported: {conf}).",
    ]
    if passed:
        thinking_lines.append(
            "Verdict: pass — every outline section is adequately supported, or remaining gaps are minor enough to accept."
        )
    else:
        gaps = verdict.get("gaps") or []
        thinking_lines.append(
            f"Verdict: needs more work — {len(gaps)} gap(s) where evidence or analysis is thin vs the outline."
        )
    detail_bullets: List[str] = []
    for s in verdict.get("section_status") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("section_id") or "?")
        ok = s.get("adequate")
        note = str(s.get("note") or "").strip()
        mark = "adequate" if ok else "thin"
        detail_bullets.append(f"Section [{sid}] — {mark}: {note}" if note else f"Section [{sid}] — {mark}")
    for g in verdict.get("gaps") or []:
        if not isinstance(g, dict):
            continue
        sid = str(g.get("section_id") or "").strip()
        reason = str(g.get("reason") or "").strip()
        if reason:
            detail_bullets.append(f"Gap{f' [{sid}]' if sid else ''}: {reason}")
    for c in verdict.get("contradictions") or []:
        if c:
            detail_bullets.append(f"Possible tension: {c}")
    return {"thinking_lines": thinking_lines, "detail_bullets": detail_bullets}


def ui_replan_started_payload(
    gaps: List[Dict[str, Any]],
    new_nodes: List[Any],
) -> Dict[str, Any]:
    """Why we're replanning and what nodes we're injecting."""
    gap_bullets: List[str] = []
    for g in gaps:
        if isinstance(g, dict):
            sid = str(g.get("section_id") or "").strip()
            reason = str(g.get("reason") or "").strip()
            if reason:
                gap_bullets.append(f"[{sid}] {reason}" if sid else reason)
    thinking_lines: List[str] = [
        "Coverage is still thin vs the outline — I'm extending the graph with targeted nodes instead of stretching the final synthesis.",
        "Each addition below is meant to close a specific gap; execution stays ordered before synthesize.",
    ]
    planned_additions: List[Dict[str, str]] = []
    for n in new_nodes:
        planned_additions.append(
            {
                "id": str(getattr(n, "id", "") or ""),
                "type": str(getattr(n, "type", "") or ""),
                "description": (getattr(n, "description", None) or "")[:500],
            }
        )
    return {
        "thinking_lines": thinking_lines,
        "gap_bullets": gap_bullets,
        "planned_additions": planned_additions,
    }


def node_result_ok_for_skip(payload: Any) -> bool:
    """Whether replan can skip re-executing this node."""
    if payload is None:
        return False
    if isinstance(payload, dict) and payload.get("error"):
        return False
    if isinstance(payload, str) and payload.lower().startswith("error"):
        return False
    if isinstance(payload, list) and len(payload) == 0:
        return False
    return True


def build_compact_node_artifact(node: GraphNode, payload: Any) -> Dict[str, Any]:
    """Small handoff blob for context_manager."""
    art: Dict[str, Any] = {
        "node_id": node.id,
        "node_type": node.type,
        "description": (node.description or "")[:400],
    }
    if node.type == "search":
        art["source"] = (node.parameters or {}).get("source")
        if isinstance(payload, list):
            art["result_count"] = len(payload)
            keys = []
            for item in payload[:5]:
                if isinstance(item, dict):
                    if item.get("nct_id"):
                        keys.append({"nct_id": item.get("nct_id"), "title": (item.get("title") or "")[:120]})
                    elif item.get("url"):
                        keys.append({"url": item.get("url"), "title": (item.get("title") or "")[:120]})
            art["sample_keys"] = keys
        elif isinstance(payload, dict):
            art["summary_keys"] = list(payload.keys())[:20]
    elif isinstance(payload, dict):
        art["keys"] = list(payload.keys())[:30]
    return art


def dedupe_citation_dicts(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for c in citations:
        if not isinstance(c, dict):
            continue
        url = str(c.get("url") or "")
        text = str(c.get("text") or "")
        key = url or text
        if key and key not in seen:
            seen.add(key)
            out.append(c)
    return out
