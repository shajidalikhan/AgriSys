"""Data models for Disease Diagnostic Agent (§4).

Defines structured schemas for:
- Plant foliage gatekeeper verification
- Crop detection results with text/vision consensus
- Targeted disease predictions with 0-5 severity indexing
- Comprehensive agronomic diagnostic reports
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GatekeeperResult(BaseModel):
    """Result of leaf presence & image clarity gatekeeping."""
    is_plant: bool = Field(..., description="True if image contains plant foliage")
    foliage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    blur_score: float = Field(default=100.0, description="Laplacian variance score")
    is_blurred: bool = Field(default=False)
    message: str = Field(default="Image accepted for diagnosis")


class CropDetectionResult(BaseModel):
    """Result of Stage 1 crop identification."""
    crop: str = Field(..., description="Normalized crop name (e.g. tomato, wheat, rice)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(default="vision", description="'vision', 'text_hint', or 'consensus'")
    top_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    discrepancy_note: Optional[str] = Field(default=None)


class DiseasePrediction(BaseModel):
    """Result of targeted or universal disease model inference."""
    crop: str
    disease: str = Field(..., description="Standard disease label or 'healthy'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: int = Field(default=1, ge=0, le=5, description="Severity grade 0-5")
    severity_label: str = Field(default="Mild", description="Healthy, Trace, Mild, Moderate, Severe, Critical")
    top_k: List[Dict[str, Any]] = Field(default_factory=list)
    model_name: str = Field(default="unknown")
    execution_mode: str = Field(default="endpoint")


class DiseaseDiagnosticReport(BaseModel):
    """Final unified agronomic diagnostic report."""
    crop: str
    disease: str
    confidence: float
    severity_score: int
    severity_label: str
    advisory: str
    treatment_protocol: str
    verified_sources: List[Dict[str, Any]] = Field(default_factory=list)
    heatmap_artifact_path: Optional[str] = None
    gatekeeper: GatekeeperResult
    crop_detection: CropDetectionResult
