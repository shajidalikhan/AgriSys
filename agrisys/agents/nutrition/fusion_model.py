"""Cross-Modal Fusion Network for Crop Nutrition Deficiency Diagnosis and Dose Prediction."""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# 12 Agronomic Deficiency Classes
DEFICIENCY_CLASSES: list[str] = [
    "Nitrogen (N) Deficiency",
    "Phosphorus (P) Deficiency",
    "Potassium (K) Deficiency",
    "Calcium (Ca) Deficiency",
    "Magnesium (Mg) Deficiency",
    "Sulfur (S) Deficiency",
    "Iron (Fe) Deficiency",
    "Zinc (Zn) Deficiency",
    "Manganese (Mn) Deficiency",
    "Boron (B) Deficiency",
    "Copper (Cu) Deficiency",
    "Healthy / Optimal",
]

# Associated diagnostic descriptions
DEFICIENCY_SYMPTOMS: dict[str, tuple[str, str]] = {
    "Nitrogen (N) Deficiency": ("N", "General chlorosis starting on older bottom leaves; stunted growth and pale yellow foliage."),
    "Phosphorus (P) Deficiency": ("P", "Dark green foliage with purple or reddish pigmentation along leaf veins and margins; delayed maturity."),
    "Potassium (K) Deficiency": ("K", "Marginal scorch and necrosis (tip burning) on older leaves; curling leaf edges and weak stems."),
    "Calcium (Ca) Deficiency": ("Ca", "Distorted growing tips, blossom end rot in fruits, and hooked/cupped young leaves."),
    "Magnesium (Mg) Deficiency": ("Mg", "Interveinal chlorosis on older leaves while leaf veins remain distinctly green."),
    "Sulfur (S) Deficiency": ("S", "Uniform light green/yellow chlorosis appearing first on younger top leaves."),
    "Iron (Fe) Deficiency": ("Fe", "Severe interveinal chlorosis on youngest leaves; veins remain sharply green."),
    "Zinc (Zn) Deficiency": ("Zn", "Little leaf syndrome, rosetting of leaves, and bleaching/mottled chlorotic bands."),
    "Manganese (Mn) Deficiency": ("Mn", "Interveinal yellowing on middle leaves with brown necrotic specks and lesions."),
    "Boron (B) Deficiency": ("B", "Brittle leaves, death of terminal apical buds, and internal hollow heart/cracking in fruits."),
    "Copper (Cu) Deficiency": ("Cu", "Dieback of young twigs, bleaching and wilting of leaf tips."),
    "Healthy / Optimal": ("None", "Foliage exhibits vigorous chlorophyll content, uniform color, and balanced vegetative growth."),
}


# ------------------------------------------------------------------
# Modular PyTorch ResNet-50 Backbone Implementation
# ------------------------------------------------------------------

class Bottleneck(nn.Module):
    expansion: int = 4

    def __init__(self, in_planes: int, planes: int, stride: int = 1, downsample: nn.Module | None = None):
        super().__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * self.expansion, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return self.relu(out)


class ResNet50FeatureExtractor(nn.Module):
    """Produces 2048-dimensional visual feature vectors from leaf images."""

    def __init__(self):
        super().__init__()
        self.in_planes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.layer1 = self._make_layer(64, 3, stride=1)
        self.layer2 = self._make_layer(128, 4, stride=2)
        self.layer3 = self._make_layer(256, 6, stride=2)
        self.layer4 = self._make_layer(512, 3, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

    def _make_layer(self, planes: int, blocks: int, stride: int = 1) -> nn.Sequential:
        downsample = None
        if stride != 1 or self.in_planes != planes * Bottleneck.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.in_planes, planes * Bottleneck.expansion, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * Bottleneck.expansion),
            )

        layers = [Bottleneck(self.in_planes, planes, stride, downsample)]
        self.in_planes = planes * Bottleneck.expansion
        for _ in range(1, blocks):
            layers.append(Bottleneck(self.in_planes, planes))

        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        return torch.flatten(x, 1)  # shape: (B, 2048)


# ------------------------------------------------------------------
# Soil Sensor Normalizer
# ------------------------------------------------------------------

class SensorNormalizer:
    """Normalizes continuous soil sensor parameters to [0, 1] range."""

    RANGES = {
        "N": (0.0, 600.0),
        "P": (0.0, 100.0),
        "K": (0.0, 600.0),
        "pH": (3.5, 10.5),
        "EC": (0.0, 5.0),
        "Moisture": (0.0, 100.0),
    }

    @classmethod
    def normalize(cls, raw_vals: list[float]) -> torch.Tensor:
        """Takes [N, P, K, pH, EC, moisture] and normalizes each to [0, 1]."""
        keys = ["N", "P", "K", "pH", "EC", "Moisture"]
        normed = []
        for val, key in zip(raw_vals, keys):
            min_v, max_v = cls.RANGES[key]
            clamped = max(min_v, min(float(val), max_v))
            normed.append((clamped - min_v) / (max_v - min_v))
        return torch.tensor(normed, dtype=torch.float32).unsqueeze(0)  # (1, 6)


# ------------------------------------------------------------------
# Cross-Modal Fusion Network (§5.1)
# ------------------------------------------------------------------

class CrossModalNutritionFusionNet(nn.Module):
    """
    Cross-modal fusion model combining 2048-dim leaf image features with
    6-dim normalized soil sensor metrics.
    """

    def __init__(self, num_classes: int = 12):
        super().__init__()
        # 1. Visual Encoder
        self.visual_encoder = ResNet50FeatureExtractor()

        # 2. Sensor Projection (optional mapping to enhance 6-dim representation)
        self.sensor_dim = 6
        self.visual_dim = 2048
        self.joint_dim = self.visual_dim + self.sensor_dim  # 2054

        # 3. Cross-Modal Fusion MLP (§5.1)
        self.fusion_mlp = nn.Sequential(
            nn.Linear(self.joint_dim, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
        )

        # 4. Multi-Task Heads
        # Head A: Deficiency classification
        self.deficiency_head = nn.Linear(64, num_classes)

        # Head B: Dose recommendation (N, P, K kg/ha continuous values)
        self.dose_head = nn.Sequential(
            nn.Linear(64, 3),
            nn.ReLU(),  # Doses are non-negative
        )

    def forward(
        self,
        image_tensor: torch.Tensor | None = None,
        sensor_tensor: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass with graceful multimodal fallbacks:
        - If image is missing, zero-pads the visual vector.
        - If sensor is missing, default-pads the sensor vector to 0.5 (medium).
        Returns:
            (deficiency_logits [B, 12], dose_preds [B, 3])
        """
        device = next(self.parameters()).device
        batch_size = 1

        # 1. Process Visual Stream
        if image_tensor is not None:
            image_tensor = image_tensor.to(device)
            batch_size = image_tensor.size(0)
            vis_features = self.visual_encoder(image_tensor)
        else:
            vis_features = torch.zeros((batch_size, self.visual_dim), device=device)

        # 2. Process Sensor Stream
        if sensor_tensor is not None:
            sensor_tensor = sensor_tensor.to(device)
            if sensor_tensor.size(0) != batch_size:
                sensor_tensor = sensor_tensor.repeat(batch_size, 1)
        else:
            # Default medium values [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
            sensor_tensor = torch.full((batch_size, self.sensor_dim), 0.5, device=device)

        # 3. Concatenate to Joint Representation
        joint_vector = torch.cat([vis_features, sensor_tensor], dim=1)  # (B, 2054)

        # 4. Shared Cross-Modal MLP
        shared_features = self.fusion_mlp(joint_vector)

        # 5. Dual Prediction Heads
        deficiency_logits = self.deficiency_head(shared_features)
        dose_preds = self.dose_head(shared_features)

        return deficiency_logits, dose_preds

    def predict(
        self,
        image_tensor: torch.Tensor | None = None,
        sensor_tensor: torch.Tensor | None = None,
    ) -> tuple[str, float, tuple[float, float, float]]:
        """
        Convenience inference method returning (predicted_label, confidence, (N, P, K doses)).
        """
        self.eval()
        with torch.no_grad():
            logits, doses = self.forward(image_tensor=image_tensor, sensor_tensor=sensor_tensor)
            probs = F.softmax(logits, dim=1)
            conf, pred_idx = torch.max(probs, dim=1)
            label = DEFICIENCY_CLASSES[pred_idx.item()]
            dose_tuple = (
                float(doses[0, 0].item()),
                float(doses[0, 1].item()),
                float(doses[0, 2].item()),
            )
            return label, float(conf.item()), dose_tuple
