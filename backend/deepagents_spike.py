"""
Deep Agents SDK — compatibility, security, and integration notes (no runtime dependency).

Stack today (see requirements.txt): langgraph==0.2.45, langchain-core==0.3.63.

The Deep Agents harness (planning, virtual filesystem, subagents, summarization) is documented at:
https://docs.langchain.com/oss/python/deepagents/overview
https://github.com/langchain-ai/deepagents

Spike (pip install deepagents --dry-run): resolving deepagents pulls langgraph>=1.1,
langchain-core>=1.2, langchain>=1.2, anthropic>=0.86, etc. That conflicts with this repo’s pins
(langgraph==0.2.45, langchain-core==0.3.63). Do not add deepagents to requirements.txt until you
plan a coordinated LangChain/LangGraph upgrade.

Security (from upstream Deep Agents / tool-using agents in general):
- Treat filesystem, shell, and network tools as the real security boundary — not model self-policing.
- Run agents with least-privilege OS users, read-only roots where possible, and explicit allowlists
  for paths and hosts if you expose execute/read_file.
- Log and redact secrets; never pass raw credentials into agent-accessible files.
- For clinical/regulated workloads, keep PHI out of agent-writable scratch paths and sandbox
  code execution (Modal/Daytona/etc.) if you adopt Deep Agents sandboxes.

Suggested pilot after upgrade: use create_deep_agent only for final synthesis with filesystem-backed
payload shards. Replacing DynamicReasoningEngine end-to-end is not advised without redesigning
clinical agent/tool boundaries.
"""
