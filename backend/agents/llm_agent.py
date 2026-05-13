"""
LLM Agent — Anthropic Claude, OpenAI, or Azure OpenAI (config: LLM_PROVIDER).
All Python backend LLM usage should go through this module (see module docstring in repo docs / audit).
"""
import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic
from config import settings
from utils.logger import log_error


def _openai_parse_chat_assistant_text(response: Any) -> tuple[str, Optional[str], str]:
    """
    Returns (content, finish_reason, refusal_text).
    Some models return empty content with a populated refusal, or length-stopped empty output.
    """
    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return "", None, ""
        ch = choices[0]
        msg = getattr(ch, "message", None)
        fr = getattr(ch, "finish_reason", None)
        if msg is None:
            return "", fr, ""
        raw = getattr(msg, "content", None)
        content = (raw or "").strip() if isinstance(raw, str) else ""
        ref_obj = getattr(msg, "refusal", None)
        refusal = str(ref_obj).strip() if ref_obj else ""
        return content, fr, refusal
    except Exception:
        return "", None, ""


class LLMAgent:
    def __init__(self) -> None:
        self.provider = (settings.LLM_PROVIDER or "anthropic").lower().strip()
        self.max_tokens = settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE

        if self.provider == "azure_openai":
            from openai import AsyncAzureOpenAI

            deployment = settings.azure_openai_deployment
            if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT or not deployment:
                raise ValueError(
                    "Azure OpenAI selected but AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and "
                    "AZURE_OPENAI_DEPLOYMENT_NAME (or AZURE_OPENAI_API_INSTANCE_NAME) must be set."
                )
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                max_retries=2,
            )
            self.model = deployment
            self._openai_request_sem = None
        elif self.provider == "openai":
            from openai import AsyncOpenAI

            if not (settings.OPENAI_API_KEY or "").strip():
                raise ValueError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be set.")
            client_kw: Dict[str, Any] = {
                "api_key": settings.OPENAI_API_KEY.strip(),
                "max_retries": 2,
            }
            base = (settings.OPENAI_BASE_URL or "").strip()
            if base:
                client_kw["base_url"] = base
            self.client = AsyncOpenAI(**client_kw)
            self.model = (settings.OPENAI_MODEL or "gpt-5-mini").strip()
            self._openai_request_sem = None
        else:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model = settings.ANTHROPIC_MODEL
            self._openai_request_sem = None

    def _uses_openai_chat_completions(self) -> bool:
        return self.provider in ("azure_openai", "openai")

    def _openai_completion_token_kw(self, mt: int) -> Dict[str, int]:
        """Newer OpenAI models expect max_completion_tokens instead of max_tokens."""
        m = (self.model or "").lower()
        if len(m) >= 2 and m.startswith("o") and m[1].isdigit():
            return {"max_completion_tokens": mt}
        if "gpt-5" in m:
            return {"max_completion_tokens": mt}
        return {"max_tokens": mt}

    def _openai_temperature_allowed(self) -> bool:
        m = (self.model or "").lower()
        if len(m) >= 2 and m.startswith("o") and m[1].isdigit():
            return False
        if "gpt-5" in m:
            return False
        return True

    def _get_current_date_info(self) -> str:
        from datetime import datetime

        now = datetime.now()
        return f"Current Date: {now.strftime('%Y-%m-%d')} ({now.strftime('%B %d, %Y')})"

    async def _anthropic_messages(
        self,
        *,
        user_content: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        mt = max_tokens if max_tokens is not None else self.max_tokens
        temp = temperature if temperature is not None else self.temperature
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": mt,
            "temperature": temp,
            "messages": [{"role": "user", "content": user_content}],
        }
        if system:
            kwargs["system"] = system
        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def _openai_sdk_chat(
        self,
        *,
        user_content: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """OpenAI Chat Completions — SDK handles retries; no app-level TPM/RPM pacing."""
        mt = max_tokens if max_tokens is not None else self.max_tokens
        temp = temperature if temperature is not None else self.temperature
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_content})
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        kwargs.update(self._openai_completion_token_kw(mt))
        if self._openai_temperature_allowed():
            kwargs["temperature"] = temp

        response = await self.client.chat.completions.create(**kwargs)
        text, finish_reason, refusal = _openai_parse_chat_assistant_text(response)

        if text:
            return text
        if refusal:
            log_error(
                refusal[:4000],
                "OpenAI chat: refusal (empty assistant content)",
            )
            return refusal
        if finish_reason == "length":
            cap_key = "max_completion_tokens" if "max_completion_tokens" in kwargs else "max_tokens"
            old_cap = int(kwargs[cap_key])
            bumped = min(old_cap * 2, 8192)
            if bumped > old_cap:
                log_error(
                    f"finish_reason=length with empty content; retrying {cap_key} {old_cap}→{bumped}",
                    "OpenAI chat completion",
                )
                kwargs2 = {**kwargs, cap_key: bumped}
                response2 = await self.client.chat.completions.create(**kwargs2)
                text2, _, refusal2 = _openai_parse_chat_assistant_text(response2)
                if text2:
                    return text2
                if refusal2:
                    log_error(refusal2[:4000], "OpenAI chat: refusal after length retry")
                    return refusal2
        log_error(
            f"empty assistant content (finish_reason={finish_reason})",
            "OpenAI chat completion",
        )
        return ""

    async def _complete(
        self,
        user_content: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        if self._uses_openai_chat_completions():
            return await self._openai_sdk_chat(
                user_content=user_content,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        return await self._anthropic_messages(
            user_content=user_content,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        try:
            return await self._complete(
                prompt,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            log_error(e, "LLM response generation")
            return f"Error generating response: {str(e)}"

    async def generate_synthesis_response(
        self,
        *,
        user_content: str,
        system_prompt: Optional[str] = None,
        use_prompt_cache: bool = False,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Clinical synthesis: long static instructions in system (Anthropic prompt caching when enabled).
        """
        try:
            sp = (system_prompt or "").strip()
            mt = (
                max_tokens
                if max_tokens is not None
                else getattr(settings, "SYNTHESIS_MAX_TOKENS", self.max_tokens)
            )
            temp = temperature if temperature is not None else self.temperature

            if self._uses_openai_chat_completions():
                return await self._complete(
                    user_content, system=sp or None, max_tokens=mt, temperature=temp
                )

            if not sp:
                return await self._complete(user_content, system=None, max_tokens=mt, temperature=temp)

            from utils.token_counting import estimate_tokens

            if (
                use_prompt_cache
                and settings.ENABLE_ANTHROPIC_PROMPT_CACHE
                and estimate_tokens(sp) >= settings.ANTHROPIC_CACHE_MIN_SYSTEM_TOKENS
            ):
                system_blocks = [
                    {"type": "text", "text": sp, "cache_control": {"type": "ephemeral"}},
                ]
                user_blocks = [{"type": "text", "text": user_content}]
                response = await self.client.beta.prompt_caching.messages.create(
                    model=self.model,
                    max_tokens=mt,
                    temperature=temp,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_blocks}],
                )
                return response.content[0].text

            return await self._complete(user_content, system=sp, max_tokens=mt, temperature=temp)
        except Exception as e:
            log_error(e, "LLM synthesis response generation")
            return f"Error generating response: {str(e)}"

    async def analyze_query(self, query: str) -> Dict[str, Any]:
        current_date = self._get_current_date_info()
        analysis_prompt = f"""
        Analyze the following clinical research query and extract key information for dynamic graph construction:
        
        {current_date}
        Query: {query}
        
        GENERAL APPROACH:
        1. Identify the main information needs
        2. Choose appropriate data sources
        3. Plan efficient search strategies
        4. Consider analysis and synthesis needs
        
        DATE CONTEXT:
        - When the query mentions "recent", "latest", "new", or similar terms, consider the current date above
        - "Recent" typically means within the last 1-2 years from the current date
        - "Latest" typically means within the last 6-12 months from the current date
        - "New" typically means within the last 1-3 months from the current date
        
        Please provide a JSON response with the following structure:
        {{
            "key_terms": ["term1", "term2", "term3"],
            "required_sources": ["aact", "pubmed", "biomcp_data"],
            "search_strategy": "search_strategy_name",
            "query_type": "clinical_trial_search",
            "complexity": "simple|moderate|complex",
            "notes": "Brief explanation of approach",
            "suggested_nodes": [
                {{
                    "type": "search",
                    "description": "Search task description",
                    "parameters": {{
                        "source": "aact",
                        "query": "search terms",
                        "limit": 50
                    }}
                }},
                {{
                    "type": "analyze",
                    "description": "Analysis task description",
                    "parameters": {{
                        "analysis_focus": {{
                            "type": "analysis_type",
                            "aspects": ["aspect1", "aspect2"]
                        }}
                    }}
                }},
                {{
                    "type": "synthesize",
                    "description": "Synthesis task description",
                    "parameters": {{
                        "synthesis_type": "answer_type",
                        "focus": ["focus1"]
                    }}
                }}
            ]
        }}
        
        CONSIDERATIONS:
        1. Medical conditions and diseases
        2. Interventions and treatments
        3. Study types and phases
        4. Appropriate data sources
        5. Analysis and synthesis needs
        6. Query complexity and scope
        7. Temporal context (use current date for "recent" interpretations)
        
        Make the node descriptions and parameters appropriate for the query.
        """

        try:
            response = await self.generate_response(analysis_prompt)
            return json.loads(response)
        except Exception as e:
            log_error(e, "Query analysis")
            return {
                "key_terms": [query],
                "required_sources": ["clinical_trials", "pubmed", "biomcp_data"],
                "search_strategy": "parallel_search",
                "query_type": "general_search",
                "complexity": "simple",
                "suggested_nodes": [],
            }

    async def synthesize_results(self, query: str, results: Dict[str, List]) -> Dict[str, Any]:
        for source, data in results.items():
            if isinstance(data, list) and data:
                _ = data[0] if isinstance(data[0], dict) else str(data[0])

        context_parts: List[str] = []
        total_results = 0

        context_parts.append("COMPREHENSIVE DATA SUMMARY:")
        context_parts.append(f"Total data sources: {len(results)}")

        for source, data in results.items():
            if isinstance(data, list) and data:
                if data is not None:
                    total_results += len(data)
                context_parts.append(f"\n{source.upper()} RESULTS ({len(data)} items):")

                if source.startswith("raw_"):
                    context_parts.append(
                        f"  SOURCE TYPE: Raw search data from {source.replace('raw_', '').replace('_', ' ').title()}"
                    )
                elif "analysis" in source.lower():
                    context_parts.append("  SOURCE TYPE: Analysis results")
                elif "reasoning" in source.lower():
                    context_parts.append("  SOURCE TYPE: Reasoning insights")
                else:
                    context_parts.append("  SOURCE TYPE: Structured data")

                for i, item in enumerate(data[:15]):
                    if isinstance(item, dict):
                        if "nct_id" in item:
                            context_parts.append(
                                f"  {i+1}. {item.get('title', 'No title')} (NCT: {item.get('nct_id', 'Unknown')})"
                            )
                            context_parts.append(f"     Condition: {item.get('condition', 'Not specified')}")
                            context_parts.append(
                                f"     Intervention: {item.get('intervention', 'Not specified')}"
                            )
                            context_parts.append(f"     Status: {item.get('status', 'Not specified')}")
                            context_parts.append(f"     Phase: {item.get('phase', 'Not specified')}")
                            if item.get("sponsor"):
                                context_parts.append(f"     Sponsor: {item.get('sponsor')}")
                            if item.get("enrollment"):
                                context_parts.append(f"     Enrollment: {item.get('enrollment')}")
                            if item.get("start_date"):
                                context_parts.append(f"     Start Date: {item.get('start_date')}")
                            if item.get("completion_date"):
                                context_parts.append(f"     Completion Date: {item.get('completion_date')}")
                            if item.get("description"):
                                context_parts.append(
                                    f"     Description: {item.get('description', '')[:300]}..."
                                )
                            if item.get("relevance_score"):
                                context_parts.append(f"     Relevance Score: {item.get('relevance_score')}")
                            metadata = item.get("metadata", {})
                            if metadata:
                                facility_info = []
                                if metadata.get("facility_name"):
                                    facility_info.append(f"Facility: {metadata.get('facility_name')}")
                                if metadata.get("city"):
                                    facility_info.append(f"City: {metadata.get('city')}")
                                if metadata.get("state"):
                                    facility_info.append(f"State: {metadata.get('state')}")
                                if metadata.get("country"):
                                    facility_info.append(f"Country: {metadata.get('country')}")
                                if facility_info:
                                    context_parts.append(f"     Location: {' | '.join(facility_info)}")
                                design_info = []
                                if metadata.get("study_type"):
                                    design_info.append(f"Study Type: {metadata.get('study_type')}")
                                if metadata.get("allocation"):
                                    design_info.append(f"Allocation: {metadata.get('allocation')}")
                                if metadata.get("intervention_model"):
                                    design_info.append(
                                        f"Intervention Model: {metadata.get('intervention_model')}"
                                    )
                                if metadata.get("primary_purpose"):
                                    design_info.append(f"Primary Purpose: {metadata.get('primary_purpose')}")
                                if design_info:
                                    context_parts.append(f"     Design: {' | '.join(design_info)}")
                                if metadata.get("primary_outcomes"):
                                    context_parts.append(
                                        f"     Primary Outcomes: {str(metadata.get('primary_outcomes'))[:200]}..."
                                    )
                                if metadata.get("secondary_outcomes"):
                                    context_parts.append(
                                        f"     Secondary Outcomes: {str(metadata.get('secondary_outcomes'))[:200]}..."
                                    )
                                if metadata.get("eligibility_criteria"):
                                    context_parts.append(
                                        f"     Eligibility: {str(metadata.get('eligibility_criteria'))[:300]}..."
                                    )
                                other_metadata = []
                                for key, value in metadata.items():
                                    if (
                                        key
                                        not in [
                                            "facility_name",
                                            "city",
                                            "state",
                                            "country",
                                            "zip",
                                            "study_type",
                                            "allocation",
                                            "intervention_model",
                                            "primary_purpose",
                                            "primary_outcomes",
                                            "secondary_outcomes",
                                            "eligibility_criteria",
                                        ]
                                        and value
                                    ):
                                        other_metadata.append(f"{key}: {value}")
                                if other_metadata:
                                    context_parts.append(f"     Additional: {' | '.join(other_metadata[:8])}")
                        elif "pmid" in item:
                            context_parts.append(
                                f"  {i+1}. {item.get('title', 'No title')} (PMID: {item.get('pmid', 'Unknown')})"
                            )
                            context_parts.append(
                                f"     Authors: {', '.join(item.get('authors', [])[:5])}"
                            )
                            context_parts.append(f"     Journal: {item.get('journal', 'Not specified')}")
                            context_parts.append(
                                f"     Date: {item.get('publication_date', 'Not specified')}"
                            )
                            if item.get("doi"):
                                context_parts.append(f"     DOI: {item.get('doi')}")
                            if item.get("abstract"):
                                context_parts.append(
                                    f"     Abstract: {item.get('abstract', '')[:400]}..."
                                )
                            if item.get("keywords"):
                                context_parts.append(
                                    f"     Keywords: {', '.join(item.get('keywords', [])[:8])}"
                                )
                            if item.get("relevance_score"):
                                context_parts.append(f"     Relevance Score: {item.get('relevance_score')}")
                            if item.get("full_text"):
                                context_parts.append(
                                    f"     Full Text Available: Yes ({len(item.get('full_text', ''))} characters)"
                                )
                        elif "application_number" in item or "brand_name" in item:
                            context_parts.append(f"  {i+1}. FDA Drug Information")
                            if item.get("brand_name"):
                                context_parts.append(
                                    f"     Brand Name: {', '.join(item.get('brand_name', []))}"
                                )
                            if item.get("generic_name"):
                                context_parts.append(
                                    f"     Generic Name: {', '.join(item.get('generic_name', []))}"
                                )
                            if item.get("manufacturer_name"):
                                context_parts.append(
                                    f"     Manufacturer: {', '.join(item.get('manufacturer_name', []))}"
                                )
                            if item.get("application_number"):
                                context_parts.append(
                                    f"     Application Number: {item.get('application_number')}"
                                )
                            if item.get("dosage_form"):
                                context_parts.append(f"     Dosage Form: {item.get('dosage_form')}")
                            if item.get("route"):
                                context_parts.append(f"     Route: {item.get('route')}")
                            if item.get("marketing_status"):
                                context_parts.append(
                                    f"     Marketing Status: {item.get('marketing_status')}"
                                )
                            if item.get("active_ingredients"):
                                context_parts.append(
                                    f"     Active Ingredients: {str(item.get('active_ingredients', []))[:200]}..."
                                )
                            if item.get("pharm_class_epc"):
                                context_parts.append(
                                    f"     Pharmacologic Class: {', '.join(item.get('pharm_class_epc', [])[:3])}"
                                )
                            if item.get("sponsor_name"):
                                context_parts.append(f"     Sponsor: {item.get('sponsor_name')}")
                            metadata = item.get("metadata", {})
                            if metadata:
                                submissions = metadata.get("submissions", [])
                                if submissions and isinstance(submissions, list) and len(submissions) > 0:
                                    latest_submission = (
                                        submissions[0] if isinstance(submissions[0], dict) else {}
                                    )
                                    if latest_submission.get("submission_status_date"):
                                        context_parts.append(
                                            f"     Latest Submission Date: {latest_submission.get('submission_status_date')}"
                                        )
                                    if latest_submission.get("submission_type"):
                                        context_parts.append(
                                            f"     Submission Type: {latest_submission.get('submission_type')}"
                                        )
                                    if latest_submission.get("submission_status"):
                                        context_parts.append(
                                            f"     Submission Status: {latest_submission.get('submission_status')}"
                                        )
                                products = metadata.get("products", [])
                                if products and isinstance(products, list) and len(products) > 0:
                                    for j, product in enumerate(products[:2]):
                                        if isinstance(product, dict):
                                            if product.get("marketing_start_date"):
                                                context_parts.append(
                                                    f"     Product {j+1} Marketing Start: {product.get('marketing_start_date')}"
                                                )
                                            if product.get("marketing_end_date"):
                                                context_parts.append(
                                                    f"     Product {j+1} Marketing End: {product.get('marketing_end_date')}"
                                                )
                                openfda = metadata.get("openfda", {})
                                if openfda and isinstance(openfda, dict):
                                    if openfda.get("approval_date"):
                                        context_parts.append(
                                            f"     FDA Approval Date: {openfda.get('approval_date')}"
                                        )
                                    if openfda.get("expiration_date"):
                                        context_parts.append(
                                            f"     Expiration Date: {openfda.get('expiration_date')}"
                                        )
                                    if openfda.get("last_updated"):
                                        context_parts.append(
                                            f"     Last Updated: {openfda.get('last_updated')}"
                                        )
                            if item.get("relevance_score"):
                                context_parts.append(f"     Relevance Score: {item.get('relevance_score')}")
                        elif "id" in item and "http" in item.get("id", ""):
                            context_parts.append(f"  {i+1}. {item.get('title', 'No title')}")
                            context_parts.append(f"     ID: {item.get('id', 'Not specified')}")
                            context_parts.append(f"     Type: {item.get('type', 'Not specified')}")
                            context_parts.append(
                                f"     Description: {item.get('description', 'Not specified')[:300]}..."
                            )
                            if item.get("url"):
                                context_parts.append(f"     URL: {item.get('url')}")
                            if item.get("relevance_score"):
                                context_parts.append(f"     Relevance Score: {item.get('relevance_score')}")
                        elif "url" in item and "title" in item and "content" in item:
                            context_parts.append(f"  {i+1}. {item.get('title', 'No title')}")
                            context_parts.append(f"     URL: {item.get('url', 'No URL')}")
                            context_parts.append(
                                f"     Content: {item.get('content', 'No content')[:800]}..."
                            )
                            if item.get("publication_date"):
                                context_parts.append(
                                    f"     Publication Date: {item.get('publication_date')}"
                                )
                            if item.get("companies"):
                                context_parts.append(
                                    f"     Companies Mentioned: {', '.join(item.get('companies', []))}"
                                )
                            if item.get("drugs"):
                                context_parts.append(
                                    f"     Drugs Mentioned: {', '.join(item.get('drugs', []))}"
                                )
                            if item.get("topics"):
                                context_parts.append(
                                    f"     Topics: {', '.join(item.get('topics', []))}"
                                )
                            if item.get("relevance_score"):
                                context_parts.append(f"     Relevance Score: {item.get('relevance_score')}")
                            if item.get("source_domain"):
                                context_parts.append(f"     Source Domain: {item.get('source_domain')}")
                            metadata = item.get("metadata", {})
                            if metadata:
                                if metadata.get("search_query"):
                                    context_parts.append(
                                        f"     Search Query: {metadata.get('search_query')}"
                                    )
                                if metadata.get("search_instructions"):
                                    context_parts.append(
                                        f"     Search Instructions: {metadata.get('search_instructions')}"
                                    )
                                if metadata.get("content_length"):
                                    context_parts.append(
                                        f"     Content Length: {metadata.get('content_length')} characters"
                                    )
                        elif "analysis" in item:
                            context_parts.append(f"  {i+1}. Analysis Results")
                            context_parts.append(f"     Analysis: {item.get('analysis', '')[:600]}...")
                            if item.get("node_id"):
                                context_parts.append(f"     Node ID: {item.get('node_id')}")
                        elif "reasoning" in item:
                            context_parts.append(f"  {i+1}. Reasoning Results")
                            context_parts.append(f"     Reasoning: {item.get('reasoning', '')[:600]}...")
                            if item.get("node_id"):
                                context_parts.append(f"     Node ID: {item.get('node_id')}")
                        else:
                            context_parts.append(f"  {i+1}. {str(item)[:400]}...")
                    else:
                        context_parts.append(f"  {i+1}. {str(item)[:400]}...")

                if len(data) > 15:
                    context_parts.append(f"  ... and {len(data) - 15} more items")
                if data:
                    sample_item = data[0]
                    if isinstance(sample_item, dict):
                        context_parts.append(f"  DATA QUALITY: {len(sample_item.keys())} fields per item")
                        if "relevance_score" in sample_item:
                            relevance_scores = [
                                item.get("relevance_score", 0)
                                for item in data
                                if isinstance(item, dict) and item.get("relevance_score") is not None
                            ]
                            if relevance_scores:
                                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                                context_parts.append(f"  AVERAGE RELEVANCE: {avg_relevance:.2f}")
                            else:
                                context_parts.append("  AVERAGE RELEVANCE: No valid scores available")
            elif isinstance(data, dict):
                context_parts.append(f"\n{source.upper()} ANALYSIS:")
                for key, value in data.items():
                    context_parts.append(f"  {key}: {str(value)[:400]}...")

        context_parts.append("\nOVERALL SUMMARY:")
        context_parts.append(f"Total items across all sources: {total_results}")
        context_parts.append(f"Data sources analyzed: {', '.join(results.keys())}")

        context = "\n".join(context_parts) if context_parts else "No specific data found."

        current_date = self._get_current_date_info()
        synthesis_prompt = f"""
You are an expert clinical research analyst. Answer the user's question using the provided data.

{current_date}

INSTRUCTIONS:
1. **Prioritize depth** — specific facts, numbers, phases, endpoints, populations, and protocol detail wherever the data supports them. Do not shorten for brevity.
2. **Citations and links** — every substantive claim should reference identifiers from the data. In the JSON **citations** array, use objects **{{"text": "short label", "url": "https://..."}}** whenever a URL exists in the data; use **https://clinicaltrials.gov/study/NCTxxxxxxxx** for trials and **https://pubmed.ncbi.nlm.nih.gov/PMID/** for publications. Plain strings are allowed only when no URL is available. Also embed those URLs in the main **answer** string as Markdown links `[label](url)` wherever a URL exists or can be formed from an NCT/PMID in the data—do not rely on the citations array alone for discoverability.
3. **Quotes** — include short verbatim quotes with attribution when the source text is high-value (endpoints, eligibility, regulatory wording).
4. Provide a **direct** answer first, then supporting detail, tables, and comparisons as needed. In the main body, avoid long generic caveat paragraphs; only note a limitation inline when it changes how to read a specific claim.
5. End the **answer** string with a final subsection titled exactly `## Data quality and limitations` — at most **2–4 short sentences** OR **up to 4 bullet points** (not both). State coverage gaps, truncation/windowing if evident from the data, and overall confidence tersely. Do not repeat the same caveats from the body unless one clause is needed for clarity.
6. Write the "answer" and all user-facing text in **English**; translate non-English sources faithfully (keep official foreign titles in parentheses when helpful).
7. Return ONLY the JSON object, no other text or formatting.

DATE CONTEXT:
- Use the current date above for "recent", "latest", and similar terms.

Return ONLY valid JSON

JSON Response:
{{
    "answer": "Long, evidence-dense answer: cite NCT/PMID inline; use Markdown links [label](url) in the prose for every URL you use; use quotes where appropriate; tables for comparisons. Must end with ## Data quality and limitations (2–4 sentences or ≤4 bullets only).",
    "citations": [
        {{"text": "NCT01234567: trial title", "url": "https://clinicaltrials.gov/study/NCT01234567"}},
        {{"text": "Source title", "url": "https://example.gov/guidance"}}
    ],
    "confidence": "high|medium|low",
    "data_quality": "One concise sentence (≤30 words): mirror the final Data quality section; no duplication of the full answer."
}}

ORIGINAL QUESTION: {query}

DATA FOUND:
{context}
"""

        try:
            if not results or not isinstance(results, dict):
                return {
                    "answer": f"Analysis completed for '{query}'. No valid data was found to synthesize.",
                    "citations": [],
                    "confidence": "low",
                    "data_quality": "No data available",
                }

            response = await self.generate_structured_response(
                synthesis_prompt,
                system_prompt="You are an expert clinical research analyst. Provide detailed, citation-heavy, quote-backed answers in English. Prefer evidence over summary; do not artificially shorten. Include Markdown links in the answer body wherever URLs exist in the data. Put routine coverage and completeness notes only in the final ## Data quality and limitations section of the answer (short, per user instructions).",
                max_tokens=getattr(settings, "SYNTHESIS_MAX_TOKENS", self.max_tokens),
            )

            try:
                return json.loads(response)
            except json.JSONDecodeError as json_error:
                print(f"❌ JSON parsing error: {json_error}")
                print(f"❌ Raw response: {response}")
                cleaned_response = re.sub(r"```json\s*", "", response)
                cleaned_response = re.sub(r"```\s*$", "", cleaned_response)
                cleaned_response = re.sub(r"```\s*", "", cleaned_response)
                try:
                    return json.loads(cleaned_response)
                except Exception:
                    pass
                json_matches = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
                if json_matches:
                    json_matches.sort(key=len, reverse=True)
                    for match in json_matches:
                        try:
                            return json.loads(match)
                        except Exception:
                            continue
                try:
                    start = response.find("{")
                    end = response.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        json_content = response[start : end + 1]
                        return json.loads(json_content)
                except Exception:
                    pass
                return {
                    "answer": f"Analysis completed for '{query}'. Found data from {len(results)} sources with {total_results} total items. The data quality and completeness varies across sources. Please review the individual results for detailed information.",
                    "citations": [],
                    "confidence": "medium",
                    "data_quality": "Data was successfully retrieved but synthesis encountered an error",
                }
        except Exception as e:
            log_error(e, "Results synthesis")
            return {
                "answer": f"Analysis completed for '{query}'. Found data from {len(results)} sources with {total_results} total items. The data quality and completeness varies across sources. Please review the individual results for detailed information.",
                "citations": [],
                "confidence": "medium",
                "data_quality": "Data was successfully retrieved but synthesis encountered an error",
            }

    async def calculate_relevance_score(self, query: str, content: str) -> float:
        current_date = self._get_current_date_info()
        prompt = f"""
        Rate the relevance of the following content to the query on a scale of 0.0 to 1.0.
        
        {current_date}
        Query: {query}
        Content: {content[:500]}...
        
        DATE CONSIDERATIONS:
        - If the query mentions "recent", "latest", "new", or similar temporal terms, consider the current date above
        - Recent content (within the last 1-2 years) should be scored higher for "recent" queries
        - Very old content (5+ years) should be scored lower for "recent" queries
        
        Return only a number between 0.0 and 1.0.
        """
        try:
            response_text = await self._complete(prompt, max_tokens=10, temperature=0.0)
            score_text = response_text.strip()
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))
            except ValueError:
                return 0.5
        except Exception as e:
            log_error(e, "Relevance scoring")
            return 0.5

    async def extract_medical_entities(self, text: str) -> List[str]:
        current_date = self._get_current_date_info()
        prompt = f"""
        Extract medical entities (diseases, drugs, procedures, etc.) from the following text.
        Return only a JSON array of strings.
        
        {current_date}
        Text: {text[:1000]}
        
        CONTEXT:
        - Consider the current date when extracting entities that might have temporal relevance
        - Include both current and historical medical entities as appropriate
        
        Response format: ["entity1", "entity2", "entity3"]
        """
        try:
            response_text = await self._complete(prompt, max_tokens=200, temperature=0.0)
            entities = json.loads(response_text)
            return entities if isinstance(entities, list) else []
        except Exception as e:
            log_error(e, "Entity extraction")
            return []

    async def generate_structured_response_with_cached_document(
        self,
        *,
        variable_user_message: str,
        cached_document: str,
        system_preamble: str = (
            "You are an expert clinical research analyst. A DOCUMENT defines available sources, "
            "planning rules, and the exact JSON shape for the graph plan. Follow the DOCUMENT precisely. "
            "The user message contains only the live QUERY context and task framing. Return valid JSON only."
        ),
        max_tokens: Optional[int] = None,
        use_document_cache: bool = True,
    ) -> str:
        """
        Graph planner: huge stable DOCUMENT can use Anthropic prompt caching; variable query stays in user message.
        Falls back to concatenated prompt on Azure or when cache disabled.
        """
        mt = max_tokens if max_tokens is not None else self.max_tokens
        try:
            if self._uses_openai_chat_completions():
                combined = (
                    f"{system_preamble}\n\n---DOCUMENT---\n{cached_document}\n\n---USER---\n{variable_user_message}"
                )
                return await self.generate_structured_response(
                    combined, system_prompt=None, max_tokens=mt
                )

            if (
                not use_document_cache
                or not settings.ENABLE_GRAPH_PLANNER_PROMPT_CACHE
                or not settings.ENABLE_ANTHROPIC_PROMPT_CACHE
            ):
                combined = (
                    f"{system_preamble}\n\n---DOCUMENT---\n{cached_document}\n\n---USER---\n{variable_user_message}"
                )
                return await self._complete(combined, system=None, max_tokens=mt, temperature=0.0)

            from utils.token_counting import estimate_tokens

            if estimate_tokens(cached_document) < settings.ANTHROPIC_CACHE_MIN_SYSTEM_TOKENS:
                combined = (
                    f"{system_preamble}\n\n---DOCUMENT---\n{cached_document}\n\n---USER---\n{variable_user_message}"
                )
                return await self._complete(combined, system=None, max_tokens=mt, temperature=0.0)

            system_blocks = [
                {"type": "text", "text": system_preamble},
                {
                    "type": "text",
                    "text": cached_document,
                    "cache_control": {"type": "ephemeral"},
                },
            ]
            user_blocks = [{"type": "text", "text": variable_user_message}]
            response = await self.client.beta.prompt_caching.messages.create(
                model=self.model,
                max_tokens=mt,
                temperature=0.0,
                system=system_blocks,
                messages=[{"role": "user", "content": user_blocks}],
            )
            text = response.content[0].text
            if text and text.strip().startswith("```"):
                text = re.sub(r"```json\s*", "", text)
                text = re.sub(r"```\s*$", "", text)
                text = re.sub(r"```\s*", "", text)
            return (text or "").strip()
        except Exception as e:
            log_error(e, "Structured response with cached document")
            combined = (
                f"{system_preamble}\n\n---DOCUMENT---\n{cached_document}\n\n---USER---\n{variable_user_message}"
            )
            return await self.generate_structured_response(combined, system_prompt=None, max_tokens=mt)

    async def calculate_relevance_scores_batch(self, query: str, contents: List[str]) -> List[float]:
        """Score many snippets in one call (same query). Returns 0.5 on failure."""
        if not contents:
            return []
        lines = []
        for i, c in enumerate(contents):
            excerpt = (c or "")[:650].replace("\n", " ")
            lines.append(f"[{i}] {excerpt}")
        prompt = f"""Rate relevance of each numbered snippet to the query. Query: {query}

Snippets:
{chr(10).join(lines)}

Return ONLY a JSON array of {len(contents)} floats in order, each 0.0–1.0, no other text."""
        try:
            raw = await self._complete(prompt, system=None, max_tokens=120, temperature=0.0)
            raw = raw.strip()
            m = re.search(r"\[[\s0-9.,]+\]", raw)
            if m:
                raw = m.group()
            arr = json.loads(raw)
            if not isinstance(arr, list) or len(arr) != len(contents):
                return [0.5] * len(contents)
            out: List[float] = []
            for x in arr:
                try:
                    v = float(x)
                    out.append(max(0.0, min(1.0, v)))
                except (TypeError, ValueError):
                    out.append(0.5)
            return out
        except Exception as e:
            log_error(e, "Batch relevance scoring")
            return [0.5] * len(contents)

    async def generate_structured_response(
        self, prompt: str, system_prompt: str = None, max_tokens: Optional[int] = None
    ) -> str:
        try:
            mt = max_tokens if max_tokens is not None else self.max_tokens
            response_text = await self._complete(
                prompt,
                system=system_prompt,
                max_tokens=mt,
                temperature=0.0,
            )
            if not response_text:
                log_error("Empty response text", "Structured response generation")
                return "Error generating structured response: Empty response text from LLM"
            if response_text.strip().startswith("```"):
                response_text = re.sub(r"```json\s*", "", response_text)
                response_text = re.sub(r"```\s*$", "", response_text)
                response_text = re.sub(r"```\s*", "", response_text)
            return response_text.strip()
        except Exception as e:
            log_error(e, "Structured response generation")
            return f"Error generating structured response: {str(e)}"

    async def generate_structured_analysis(
        self,
        query: str,
        node_description: str,
        analysis_type: str,
        analysis_aspects: List[str],
        data: List[Dict],
    ) -> str:
        current_date = self._get_current_date_info()
        analysis_prompt = f"""
You are an expert clinical research analyst. Generate a structured analysis based on the specific requirements.

{current_date}

ORIGINAL QUERY: {query}

ANALYSIS TASK: {node_description}

ANALYSIS TYPE: {analysis_type}

ANALYSIS ASPECTS: {', '.join(analysis_aspects) if analysis_aspects else 'Based on the analysis task description'}

DATA TO ANALYZE: {json.dumps(data[:15], indent=2)}

INSTRUCTIONS:
1. Focus specifically on the analysis task described above
2. Consider the original query context
3. Look for patterns and insights relevant to the analysis type
4. Provide structured findings based on the specific aspects requested
5. Be specific and actionable in your analysis
6. Consider temporal context when analyzing recent developments

ANALYSIS REQUIREMENTS:
- If analyzing sites/facilities: Focus on geographic patterns, facility types, sponsor preferences
- If analyzing drug patterns: Focus on drug classes, mechanisms, development stages
- If analyzing trial characteristics: Focus on phases, enrollment, completion rates
- If analyzing sponsor behavior: Focus on sponsor types, funding patterns, collaboration networks
- If analyzing condition overlap: Focus on cross-condition applications, repurposing opportunities
- If analyzing temporal patterns: Focus on trends over time, recent developments (use current date as reference)
- If analyzing outcomes: Focus on success rates, endpoint types, statistical significance

DATE CONTEXT:
- Use the current date above to interpret temporal references
- When analyzing "recent" patterns, consider the current date as the reference point
- Provide temporal context for findings and trends

Provide a structured analysis that directly addresses the specific analysis task described above.

ANALYSIS:
"""
        try:
            return await self.generate_response(analysis_prompt)
        except Exception as e:
            log_error(e, "Structured analysis generation")
            return f"Error generating structured analysis: {str(e)}"

    def _detect_source_type(self, source: str, data: List) -> str:
        if not data:
            return "Empty data"
        sample = data[0] if isinstance(data[0], dict) else {}
        if source.startswith("raw_"):
            return f"Raw search data from {source.replace('raw_', '').replace('_', ' ').title()}"
        if "analysis" in source.lower():
            return "Analysis results"
        if "reasoning" in source.lower():
            return "Reasoning insights"
        if "nct_id" in sample:
            return "Clinical trial data"
        if "pmid" in sample:
            return "Publication data"
        if "application_number" in sample or "brand_name" in sample:
            return "FDA drug information"
        if "url" in sample and "title" in sample:
            return "Web search results"
        if "id" in sample and "http" in str(sample.get("id", "")):
            return "BioOntology data"
        return "Structured data"

    def _format_context_item(self, item: Any, index: int) -> List[str]:
        formatted: List[str] = []
        if isinstance(item, dict):
            if "nct_id" in item:
                formatted.append(
                    f"  {index}. {item.get('title', 'No title')} (NCT: {item.get('nct_id', 'Unknown')})"
                )
                formatted.append(f"     Condition: {item.get('condition', 'Not specified')}")
                formatted.append(f"     Intervention: {item.get('intervention', 'Not specified')}")
                formatted.append(f"     Status: {item.get('status', 'Not specified')}")
                formatted.append(f"     Phase: {item.get('phase', 'Not specified')}")
                if item.get("sponsor"):
                    formatted.append(f"     Sponsor: {item.get('sponsor')}")
                if item.get("enrollment"):
                    formatted.append(f"     Enrollment: {item.get('enrollment')}")
                if item.get("start_date"):
                    formatted.append(f"     Start Date: {item.get('start_date')}")
                if item.get("completion_date"):
                    formatted.append(f"     Completion Date: {item.get('completion_date')}")
                if item.get("description"):
                    formatted.append(f"     Description: {item.get('description', '')[:300]}...")
                if item.get("relevance_score"):
                    formatted.append(f"     Relevance Score: {item.get('relevance_score')}")
                metadata = item.get("metadata", {})
                if metadata:
                    facility_info = []
                    if metadata.get("facility_name"):
                        facility_info.append(f"Facility: {metadata.get('facility_name')}")
                    if metadata.get("city"):
                        facility_info.append(f"City: {metadata.get('city')}")
                    if metadata.get("state"):
                        facility_info.append(f"State: {metadata.get('state')}")
                    if metadata.get("country"):
                        facility_info.append(f"Country: {metadata.get('country')}")
                    if facility_info:
                        formatted.append(f"     Location: {' | '.join(facility_info)}")
                    design_info = []
                    if metadata.get("study_type"):
                        design_info.append(f"Study Type: {metadata.get('study_type')}")
                    if metadata.get("allocation"):
                        design_info.append(f"Allocation: {metadata.get('allocation')}")
                    if metadata.get("intervention_model"):
                        design_info.append(f"Intervention Model: {metadata.get('intervention_model')}")
                    if metadata.get("primary_purpose"):
                        design_info.append(f"Primary Purpose: {metadata.get('primary_purpose')}")
                    if design_info:
                        formatted.append(f"     Design: {' | '.join(design_info)}")
                    if metadata.get("primary_outcomes"):
                        formatted.append(
                            f"     Primary Outcomes: {str(metadata.get('primary_outcomes'))[:200]}..."
                        )
                    if metadata.get("secondary_outcomes"):
                        formatted.append(
                            f"     Secondary Outcomes: {str(metadata.get('secondary_outcomes'))[:200]}..."
                        )
                    if metadata.get("eligibility_criteria"):
                        formatted.append(
                            f"     Eligibility: {str(metadata.get('eligibility_criteria'))[:300]}..."
                        )
            elif "pmid" in item:
                formatted.append(
                    f"  {index}. {item.get('title', 'No title')} (PMID: {item.get('pmid', 'Unknown')})"
                )
                formatted.append(f"     Authors: {', '.join(item.get('authors', [])[:5])}")
                formatted.append(f"     Journal: {item.get('journal', 'Not specified')}")
                formatted.append(f"     Date: {item.get('publication_date', 'Not specified')}")
                if item.get("doi"):
                    formatted.append(f"     DOI: {item.get('doi')}")
                if item.get("abstract"):
                    formatted.append(f"     Abstract: {item.get('abstract', '')[:400]}...")
                if item.get("keywords"):
                    formatted.append(f"     Keywords: {', '.join(item.get('keywords', [])[:8])}")
                if item.get("relevance_score"):
                    formatted.append(f"     Relevance Score: {item.get('relevance_score')}")
                if item.get("full_text"):
                    formatted.append(
                        f"     Full Text Available: Yes ({len(item.get('full_text', ''))} characters)"
                    )
            elif "application_number" in item or "brand_name" in item:
                formatted.append(f"  {index}. FDA Drug Information")
                if item.get("brand_name"):
                    formatted.append(f"     Brand Name: {', '.join(item.get('brand_name', []))}")
                if item.get("generic_name"):
                    formatted.append(f"     Generic Name: {', '.join(item.get('generic_name', []))}")
                if item.get("manufacturer_name"):
                    formatted.append(
                        f"     Manufacturer: {', '.join(item.get('manufacturer_name', []))}"
                    )
                if item.get("application_number"):
                    formatted.append(f"     Application Number: {item.get('application_number')}")
                if item.get("dosage_form"):
                    formatted.append(f"     Dosage Form: {item.get('dosage_form')}")
                if item.get("route"):
                    formatted.append(f"     Route: {item.get('route')}")
                if item.get("marketing_status"):
                    formatted.append(f"     Marketing Status: {item.get('marketing_status')}")
                if item.get("active_ingredients"):
                    formatted.append(
                        f"     Active Ingredients: {str(item.get('active_ingredients', []))[:200]}..."
                    )
                if item.get("pharm_class_epc"):
                    formatted.append(
                        f"     Pharmacologic Class: {', '.join(item.get('pharm_class_epc', [])[:3])}"
                    )
                if item.get("sponsor_name"):
                    formatted.append(f"     Sponsor: {item.get('sponsor_name')}")
                if item.get("relevance_score"):
                    formatted.append(f"     Relevance Score: {item.get('relevance_score')}")
            elif "url" in item and "title" in item:
                formatted.append(f"  {index}. {item.get('title', 'No title')}")
                formatted.append(f"     URL: {item.get('url', 'Not specified')}")
                formatted.append(f"     Source: {item.get('source_domain', 'Not specified')}")
                if item.get("publication_date"):
                    formatted.append(f"     Date: {item.get('publication_date')}")
                if item.get("content"):
                    formatted.append(f"     Content: {item.get('content', '')[:400]}...")
                if item.get("companies"):
                    formatted.append(f"     Companies: {', '.join(item.get('companies', [])[:5])}")
                if item.get("drugs"):
                    formatted.append(f"     Drugs: {', '.join(item.get('drugs', [])[:5])}")
                if item.get("topics"):
                    formatted.append(f"     Topics: {', '.join(item.get('topics', [])[:5])}")
                if item.get("relevance_score"):
                    formatted.append(f"     Relevance Score: {item.get('relevance_score')}")
            elif "id" in item and "http" in str(item.get("id", "")):
                formatted.append(f"  {index}. {item.get('title', 'No title')}")
                formatted.append(f"     ID: {item.get('id', 'Not specified')}")
                formatted.append(f"     Type: {item.get('type', 'Not specified')}")
                formatted.append(
                    f"     Description: {item.get('description', 'Not specified')[:300]}..."
                )
                if item.get("url"):
                    formatted.append(f"     URL: {item.get('url')}")
                if item.get("relevance_score"):
                    formatted.append(f"     Relevance Score: {item.get('relevance_score')}")
            elif "analysis" in item:
                formatted.append(f"  {index}. Analysis Results")
                formatted.append(f"     Analysis: {item.get('analysis', '')[:600]}...")
                if item.get("node_id"):
                    formatted.append(f"     Node ID: {item.get('node_id')}")
            elif "reasoning" in item:
                formatted.append(f"  {index}. Reasoning Results")
                formatted.append(f"     Reasoning: {item.get('reasoning', '')[:600]}...")
                if item.get("node_id"):
                    formatted.append(f"     Node ID: {item.get('node_id')}")
            else:
                formatted.append(f"  {index}. {str(item)[:400]}...")
        else:
            formatted.append(f"  {index}. {str(item)[:400]}...")
        return formatted

    def _calculate_data_quality(self, data: List) -> List[str]:
        quality_info: List[str] = []
        if not data:
            return quality_info
        sample_item = data[0]
        if isinstance(sample_item, dict):
            quality_info.append(f"  DATA QUALITY: {len(sample_item.keys())} fields per item")
            if "relevance_score" in sample_item:
                relevance_scores = [
                    item.get("relevance_score", 0)
                    for item in data
                    if isinstance(item, dict) and item.get("relevance_score") is not None
                ]
                if relevance_scores:
                    avg_relevance = sum(relevance_scores) / len(relevance_scores)
                    quality_info.append(f"  AVERAGE RELEVANCE: {avg_relevance:.2f}")
                else:
                    quality_info.append("  AVERAGE RELEVANCE: No valid scores available")
        return quality_info


llm_agent = LLMAgent()
