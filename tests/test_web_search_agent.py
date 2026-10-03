"""Unit and Integration Tests for Web Search Agent in AgriSys."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agrisys.agents.web_search.models import SearchResultItem, WebSearchQuery, WebSearchReport
from agrisys.agents.web_search.client import WebSearchClient
from agrisys.agents.web_search.agent import WebSearchAgent
from agrisys.agents.web_search.node import web_search_agent_node
from agrisys.orchestrator.intent_router import IntentRouter
from agrisys.orchestrator.graph import create_agrisys_graph, route_next_agents
from agrisys.orchestrator.response_merger import ResponseMerger


def test_web_search_models():
    """Verify Pydantic models instantiate and validate fields correctly."""
    item = SearchResultItem(
        title="PM-Kisan Scheme Guidelines",
        url="https://pmkisan.gov.in/guidelines",
        snippet="Guidelines on farmer eligibility and disbursement schedules.",
        source="duckduckgo",
    )
    assert item.title == "PM-Kisan Scheme Guidelines"
    assert "pmkisan.gov.in" in item.url

    report = WebSearchReport(
        query="PM-Kisan 16th installment",
        results=[item],
        summary="PM-Kisan funds released to registered farmers.",
        citations=[f"Web Source: [{item.title}]({item.url})"],
    )
    assert len(report.results) == 1
    assert len(report.citations) == 1
    assert "guidelines" in report.citations[0]


def test_agent_query_formulation():
    """Verify agricultural and geographic context anchoring."""
    agent = WebSearchAgent()
    formulated = agent.formulate_query("when is next installment", crop="Wheat", location="Punjab")
    assert "India agriculture" in formulated
    assert "Wheat" in formulated
    assert "Punjab" in formulated


@pytest.mark.asyncio
async def test_agent_search_and_synthesize():
    """Verify search execution and synthesis with mocked client."""
    mock_client = MagicMock(spec=WebSearchClient)
    mock_items = [
        SearchResultItem(
            title="PM Fasal Bima Yojana Portal",
            url="https://pmfby.gov.in",
            snippet="Official portal for crop insurance enrollment and claim tracking.",
            source="duckduckgo",
        ),
        SearchResultItem(
            title="ICAR Crop Advisory 2026",
            url="https://icar.org.in/advisory",
            snippet="Advisory regarding kharif season crop selection.",
            source="duckduckgo",
        ),
    ]
    mock_client.search = AsyncMock(return_value=mock_items)
    mock_client.provider = "duckduckgo"

    agent = WebSearchAgent(client=mock_client)
    report = await agent.search_and_synthesize(query="pmfby crop insurance status")

    assert len(report.results) == 2
    assert any("pmfby.gov.in" in c for c in report.citations)
    assert "PM Fasal Bima Yojana Portal" in report.summary or "PM Fasal Bima" in report.summary


@pytest.mark.asyncio
async def test_web_search_agent_node():
    """Verify LangGraph state node returns agent_results, citations, and rag_chunks."""
    mock_client = MagicMock(spec=WebSearchClient)
    mock_client.search = AsyncMock(
        return_value=[
            SearchResultItem(
                title="Fertilizer Subsidy Updates",
                url="https://agricoop.nic.in/subsidies",
                snippet="Subsidies on DAP and Urea for smallholder farmers.",
                source="duckduckgo",
            )
        ]
    )
    mock_client.provider = "duckduckgo"

    with patch("agrisys.agents.web_search.node.WebSearchAgent") as mock_agent_cls:
        agent_instance = WebSearchAgent(client=mock_client)
        mock_agent_cls.return_value = agent_instance

        dummy_state = {
            "query": "What are current fertilizer subsidies in Haryana?",
            "active_crop": "Wheat",
            "language": "en",
            "location": {"district": "Karnal", "state": "Haryana"},
        }
        res = await web_search_agent_node(dummy_state)

        assert "web_search_data" in res
        assert "citations" in res
        assert "rag_chunks" in res
        assert "agent_results" in res
        assert len(res["rag_chunks"]) == 1
        assert res["agent_results"][0]["agent"] == "web_search_agent"


@pytest.mark.asyncio
async def test_intent_router_classifies_web_search():
    """Verify keyword routing detects web_search intents."""
    router = IntentRouter()
    intents = await router.route("What are the latest government subsidies under PM-Kisan yojana?")
    assert "web_search" in intents


def test_route_next_agents_routing():
    """Verify route_next_agents sends web_search to web_search_agent."""
    state = {"intents": ["web_search", "weather"]}
    targets = route_next_agents(state)
    assert "web_search_agent" in targets
    assert "weather_agent" in targets


def test_response_merger_formats_web_search():
    """Verify ResponseMerger handles web_search_agent results."""
    merger = ResponseMerger()
    agent_results = [
        {
            "agent": "web_search_agent",
            "summary": "Latest subsidy released on 15th March across all registered farmer accounts.",
            "source_count": 1,
            "top_sources": ["https://pmkisan.gov.in"],
        }
    ]
    citations = ["Web Source: [PM-Kisan](https://pmkisan.gov.in)"]
    merged = merger.merge(query="pm kisan status", agent_results=agent_results, citations=citations)

    assert "🌐 Live Web Search & Government Updates" in merged["merged_response"]
    assert "Latest subsidy released" in merged["merged_response"]
    assert "pmkisan.gov.in" in merged["merged_response"]
    assert merged["confidence_score"] > 0.80


def test_graph_compilation_with_web_search():
    """Verify LangGraph StateGraph builds with web_search_agent node."""
    graph = create_agrisys_graph()
    assert "web_search_agent" in graph.nodes
    assert "intent_router" in graph.nodes
    assert "response_merger" in graph.nodes
