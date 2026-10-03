# AgriSys Update: Web Search Agent Integration

## Overview
This update integrates an autonomous **Web Search Agent** into the AgriSys LangGraph multi-agent pipeline. It expands the system's reasoning capabilities to fetch, analyze, and cite up-to-date web information—including real-time agricultural advisories, breaking pest reports, weather events, and government subsidies/schemes (e.g., PM-KISAN, PMFBY).

## Key Files & Directories
- `docs/updates/web_search_agent_integration/implementation_plan.md`: Full architectural and technical implementation specification.
- `agrisys/agents/web_search/`:
  - `models.py`: Data models for query representation, raw search results, and agent reports.
  - `client.py`: Multi-provider search client (DuckDuckGo, Tavily, direct HTTP).
  - `agent.py`: Agent reasoning, query reformulation, and content extraction.
  - `node.py`: LangGraph state node executing the search flow and appending findings to `state`.
- `config/providers.yaml`: Central provider configuration for search engines.
- `config/agents.yaml`: Feature flags and thresholds for the search agent.
- `agrisys/config.py`: Pydantic validation schemas.
- `agrisys/orchestrator/intent_router.py`: Rule-based and LLM-assisted intent routing triggers for web search.
- `agrisys/orchestrator/graph.py`: StateGraph compilation incorporating `web_search_agent`.
- `tests/test_web_search_agent.py`: Test suite validating search querying, intent classification, and graph orchestration.

## How to Test
```bash
pytest tests/test_web_search_agent.py -v
```
