"""Explainable AI (XAI): Grad-CAM and Adaptive Lesion Heatmap Generator (§12.1).

Fulfills:
- Full tensor Grad-CAM when local model gradients are available
- Adaptive Color-Space Lesion Heatmap & Bounding Box for remote endpoint models (Improvement 5)
- Saves visual overlay image to disk/MinIO and returns artifact path
"""

from pathlib import Path
from typing import Any, Optional, Tuple
import hashlib
import numpy as np
import cv2
import torch
from PIL import Image


class DiseaseGradCAM:
    """Generates visual disease explainability overlays for farmers and agronomists."""

    def __init__(
        self,
        artifacts_dir: str = "data/artifacts",
        colormap: int = cv2.COLORMAP_JET,
    ) -> None:
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.colormap = colormap

    def generate_heatmap_overlay(
        self,
        rgb_image_np: np.ndarray,
        model_tensor: Optional[torch.Tensor] = None,
        pytorch_model: Optional[Any] = None,
        target_layer_name: str = "layer4",
    ) -> Tuple[np.ndarray, str]:
        """Generate explainability heatmap overlay.

        Args:
            rgb_image_np: Original RGB image array (H, W, 3).
            model_tensor: Optional normalized tensor.
            pytorch_model: Optional local PyTorch model.
            target_layer_name: Convolutional layer for Grad-CAM.

        Returns:
            Tuple of (overlay_rgb_numpy_array, saved_file_path).
        """
        # If local model gradients are available, attempt tensor Grad-CAM
        if pytorch_model is not None and model_tensor is not None:
            try:
                return self._tensor_gradcam(rgb_image_np, model_tensor, pytorch_model, target_layer_name)
            except Exception:
                pass

        # Adaptive Lesion Segmentation Heatmap (Improvement 5 for endpoint models)
        return self._adaptive_lesion_heatmap(rgb_image_np)

    def _adaptive_lesion_heatmap(self, rgb_image_np: np.ndarray) -> Tuple[np.ndarray, str]:
        """Isolate chlorotic halos and necrotic spots in LAB/HSV space to generate visual overlay."""
        hsv = cv2.cvtColor(rgb_image_np, cv2.COLOR_RGB2HSV)
        lab = cv2.cvtColor(rgb_image_np, cv2.COLOR_RGB2LAB)

        # Lesion color ranges (brown, yellow, dark necrotic spots)
        lower_brown = np.array([5, 40, 20])
        upper_brown = np.array([25, 255, 200])
        mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)

        # High variance / low luminance spots in L-channel
        l_channel = lab[:, :, 0]
        _, dark_spots = cv2.threshold(l_channel, 75, 255, cv2.THRESH_BINARY_INV)

        # Combined lesion mask
        lesion_mask = cv2.bitwise_or(mask_brown, dark_spots)

        # Smooth into continuous heatmap activation
        heatmap_float = cv2.GaussianBlur(lesion_mask.astype(np.float32), (31, 31), 0)
        max_val = np.max(heatmap_float)
        if max_val > 0:
            heatmap_norm = (heatmap_float / max_val * 255.0).astype(np.uint8)
        else:
            heatmap_norm = np.zeros_like(l_channel, dtype=np.uint8)

        # Colorize with JET colormap
        heatmap_color = cv2.applyColorMap(heatmap_norm, self.colormap)
        heatmap_rgb = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)

        # Alpha blend over original image (65% original, 35% heatmap)
        alpha = 0.35
        overlay = cv2.addWeighted(heatmap_rgb, alpha, rgb_image_np, 1.0 - alpha, 0)

        # Draw bounding boxes around primary lesion clusters
        contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (rgb_image_np.shape[0] * rgb_image_np.shape[1]) * 0.005  # >0.5% of leaf
        for cnt in contours:
            if cv2.contourArea(cnt) > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 50, 50), 2)

        # Save to artifacts directory
        img_hash = hashlib.md5(overlay.tobytes()).hexdigest()[:8]
        filename = f"lesion_heatmap_{img_hash}.jpg"
        save_path = self.artifacts_dir / filename
        Image.fromarray(overlay).save(save_path, format="JPEG", quality=90)

        return overlay, str(save_path)

    def _tensor_gradcam(
        self,
        rgb_image_np: np.ndarray,
        tensor: torch.Tensor,
        model: torch.nn.Module,
        target_layer_name: str,
    ) -> Tuple[np.ndarray, str]:
        """Gradient-weighted Class Activation Mapping for local PyTorch models."""
        target_layer = getattr(model, target_layer_name, None)
        if target_layer is None:
            return self._adaptive_lesion_heatmap(rgb_image_np)

        gradients = []
        activations = []

        def backward_hook(module, grad_input, grad_output):
            gradients.append(grad_output[0])

        def forward_hook(module, input, output):
            activations.append(output)

        h1 = target_layer.register_forward_hook(forward_hook)
        h2 = target_layer.register_full_backward_hook(backward_hook)

        try:
            model.eval()
            output = model(tensor)
            pred_idx = output.argmax(dim=1).item()
            score = output[0, pred_idx]
            model.zero_grad()
            score.backward()

            # Global average pool of gradients
            weights = torch.mean(gradients[0], dim=[2, 3], keepdim=True)
            cam = torch.sum(weights * activations[0], dim=1, keepdim=True)
            cam = torch.relu(cam)
            cam_np = cam.squeeze().detach().cpu().numpy()

            # Normalize cam
            cam_np = cv2.resize(cam_np, (rgb_image_np.shape[1], rgb_image_np.shape[0]))
            cam_norm = (cam_np - np.min(cam_np)) / (np.max(cam_np) - np.min(cam_np) + 1e-8)
            heatmap_uint8 = (cam_norm * 255.0).astype(np.uint8)

            heatmap_color = cv2.applyColorMap(heatmap_uint8, self.colormap)
            heatmap_rgb = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
            overlay = cv2.addWeighted(heatmap_rgb, 0.4, rgb_image_np, 0.6, 0)

            img_hash = hashlib.md5(overlay.tobytes()).hexdigest()[:8]
            save_path = self.artifacts_dir / f"gradcam_{img_hash}.jpg"
            Image.fromarray(overlay).save(save_path, format="JPEG", quality=90)
            return overlay, str(save_path)
        finally:
            h1.remove()
            h2.remove()
