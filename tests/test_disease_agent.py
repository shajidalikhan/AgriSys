"""Integration tests for Disease Diagnostic Agent (§4, §12.1).

Tests the full sequential pipeline:
CropDetector -> CropModelRouter -> EnsembleVoter -> GradCAM -> RAG -> disease_agent_node.
"""

from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from agrisys.agents.disease.crop_detector import CropDetector
from agrisys.agents.disease.model_router import CropModelRouter
from agrisys.agents.disease.ensemble import WeightedEnsembleVoter
from agrisys.agents.disease.chain import AgriChainDiagnosticEngine
from agrisys.agents.disease.node import DiseaseAgent, disease_agent_node
from agrisys.agents.disease.models import DiseasePrediction
from agrisys.xai.gradcam import DiseaseGradCAM
from agrisys.rag.retrieval.pipeline import RetrievalPipeline
from agrisys.rag.ingestion.upserter import QdrantUpserter
from agrisys.rag.ingestion.models import Chunk, ChunkMetadata
from agrisys.providers.local_embedding import LocalEmbeddingProvider


def create_mock_leaf_bytes(color=(34, 139, 34)) -> bytes:
    """Generate valid test leaf image bytes with lesions and texture."""
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :] = color
    # Add dark brown lesion patch
    arr[60:180, 60:180] = [139, 69, 19]
    for i in range(0, 256, 12):
        arr[i : i + 2, :] = [20, 100, 20]
    img = Image.fromarray(arr)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_crop_detector_consensus():
    """Verify CropDetector extracts farmer text hint and corroborates with vision model."""
    detector = CropDetector()
    leaf_bytes = create_mock_leaf_bytes()

    # Consensus scenario: farmer says tomato and vision detects tomato
    res_consensus = await detector.detect_crop(leaf_bytes, user_query="My tomato leaves have black rings")
    assert res_consensus.crop == "tomato"
    assert res_consensus.source in ["consensus", "vision"]

    # Hint extraction without text
    res_raw = await detector.detect_crop(leaf_bytes, user_query=None)
    assert res_raw.crop != ""
    assert res_raw.confidence > 0.0


@pytest.mark.asyncio
async def test_crop_model_router():
    """Verify router selects crop-specific models or falls back to general detector."""
    router = CropModelRouter()
    tomato_tools = router.get_candidate_tools("tomato")
    assert len(tomato_tools) >= 1
    assert any("tomato" in t.name or "specialist" in t.name for t in tomato_tools)

    # Unknown crop falls back to general disease detector
    exotic_tools = router.get_candidate_tools("dragonfruit")
    assert len(exotic_tools) >= 1
    assert any(t.role == "general_disease" for t in exotic_tools)


def test_weighted_ensemble_voter():
    """Verify voter computes correct weighted scores and assigns severity."""
    p1 = DiseasePrediction(crop="tomato", disease="early_blight", confidence=0.90, severity=3, model_name="m1")
    p2 = DiseasePrediction(crop="tomato", disease="late_blight", confidence=0.60, severity=2, model_name="m2")

    winner = WeightedEnsembleVoter.vote([p1, p2], weights=[0.7, 0.3])
    assert winner.disease == "early_blight"
    assert winner.confidence >= 0.70
    assert winner.severity == 3
    assert winner.severity_label == "Moderate"


def test_disease_gradcam_overlay(tmp_path):
    """Verify GradCAM/adaptive lesion generator creates visual heatmap image."""
    gradcam = DiseaseGradCAM(artifacts_dir=str(tmp_path))
    arr = np.zeros((224, 224, 3), dtype=np.uint8)
    arr[:, :] = [34, 139, 34]
    arr[50:150, 50:150] = [139, 69, 19]  # brown lesion

    overlay, saved_path = gradcam.generate_heatmap_overlay(arr)
    assert overlay.shape == (224, 224, 3)
    assert saved_path is not None
    assert (tmp_path / saved_path).exists() or Path(saved_path).exists()


@pytest.mark.asyncio
async def test_disease_agent_end_to_end_diagnosis():
    """Verify complete diagnosis flow with RAG treatment protocol lookup."""
    # Set up in-memory RAG pipeline with ICAR treatment
    embed = LocalEmbeddingProvider(dimension=256)
    upserter = QdrantUpserter(embedding_provider=embed, collection_name="test_disease_rag", in_memory=True)
    await upserter.upsert_chunks([
        Chunk(
            id="treat_1",
            text="ICAR Treatment for Tomato Early Blight: Spray Mancozeb 75 WP at 2.0g per liter water.",
            metadata=ChunkMetadata(source="icar", crop="tomato", domain="disease"),
        )
    ])
    rag = RetrievalPipeline(
        embedding_provider=embed,
        qdrant_client=upserter.client,
        collection_name="test_disease_rag",
        hyde_enabled=False,
    )

    agent = DiseaseAgent(retrieval_pipeline=rag)
    leaf_bytes = create_mock_leaf_bytes()

    result = await agent.diagnose(leaf_bytes, user_query="What is wrong with my tomato crop?")
    assert result["status"] == "success"
    assert result["crop"] == "tomato"
    assert "blight" in result["disease"].lower()
    assert result["confidence"] > 0.5
    assert result["severity_score"] >= 1
    assert "Mancozeb" in result["treatment_protocol"]
    assert result["heatmap_path"] is not None


@pytest.mark.asyncio
async def test_langgraph_disease_agent_node():
    """Verify LangGraph node execution interface disease_agent_node(state)."""
    leaf_bytes = create_mock_leaf_bytes()
    state = {
        "image_bytes": leaf_bytes,
        "query": "Look at my tomato leaf",
        "language": "en",
    }

    updated_state = await disease_agent_node(state)
    assert "disease_result" in updated_state
    assert updated_state["disease_result"]["status"] == "success"
    assert updated_state["active_agent"] == "disease"
    assert "Tomato" in updated_state["final_advisory"]
