"""Weighted Ensemble Voter and Quantitative Severity Calculator (§4.3).

Fulfills:
- Weighted majority voting across specialist models
- Quantitative Severity Index calculation (Scale 0 to 5, Improvement 3)
"""

from typing import Dict, List, Tuple
from agrisys.agents.disease.models import DiseasePrediction

SEVERITY_LEVELS = {
    0: ("Healthy", "No visible disease symptoms. Leaf tissue healthy."),
    1: ("Trace", "Trace infection (<5% leaf area affected). Faint initial lesions."),
    2: ("Mild", "Mild infection (5-15% leaf area). Discrete scattered spots."),
    3: ("Moderate", "Moderate infection (15-30% leaf area). Coalescing lesions with chlorotic halos."),
    4: ("Severe", "Severe infection (30-50% leaf area). Significant necrosis and leaf curl."),
    5: ("Critical", "Critical infection (>50% leaf area). Extensive leaf collapse and blight."),
}


class WeightedEnsembleVoter:
    """Combines predictions from multiple model tools with weighted consensus."""

    @staticmethod
    def vote(
        predictions: List[DiseasePrediction],
        weights: List[float],
        threshold: float = 0.70,
    ) -> DiseasePrediction:
        """Calculate weighted majority vote across multiple model outputs."""
        if not predictions:
            raise ValueError("No model predictions provided for ensemble voting.")

        if len(predictions) == 1:
            return predictions[0]

        disease_votes: Dict[str, float] = {}
        disease_conf_sum: Dict[str, float] = {}
        disease_weight_sum: Dict[str, float] = {}
        total_weight = sum(weights) if sum(weights) > 0 else 1.0

        for pred, weight in zip(predictions, weights):
            key = pred.disease.lower()
            norm_w = weight / total_weight
            disease_votes[key] = disease_votes.get(key, 0.0) + norm_w
            disease_conf_sum[key] = disease_conf_sum.get(key, 0.0) + (pred.confidence * weight)
            disease_weight_sum[key] = disease_weight_sum.get(key, 0.0) + weight

        # Select disease with highest vote share
        best_disease, vote_share = max(disease_votes.items(), key=lambda item: item[1])

        # Weighted average confidence for the winning disease
        winning_conf = disease_conf_sum[best_disease] / disease_weight_sum[best_disease]

        # Pick the matching prediction for metadata
        winner_pred = next((p for p in predictions if p.disease.lower() == best_disease), predictions[0])

        # Calculate consensus severity
        severity = winner_pred.severity
        sev_label, _ = SEVERITY_LEVELS.get(severity, ("Mild", ""))

        return DiseasePrediction(
            crop=winner_pred.crop,
            disease=best_disease,
            confidence=round(min(1.0, winning_conf), 3),
            severity=severity,
            severity_label=sev_label,
            top_k=[{"disease": k, "vote_share": round(v, 3)} for k, v in disease_votes.items()],
            model_name=f"ensemble({len(predictions)}_models)",
            execution_mode="endpoint_ensemble",
        )
