"""Unit tests for Image Preprocessing and Leaf Gatekeeper Pipeline (§4.2).

Tests image validation, blur rejection, foliage gatekeeper, and CLAHE enhancement.
"""

from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from agrisys.agents.disease.preprocessor import ImagePreprocessor


def create_mock_leaf_image(color=(34, 139, 34), size=(256, 256), with_lesions=True) -> bytes:
    """Create synthetic RGB leaf image with green foliage and optional brown lesions."""
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    # Fill with foliage green
    arr[:, :] = color

    if with_lesions:
        # Add brown/yellow lesion spots in center
        h, w = size
        arr[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = [139, 69, 19]

    # Add sharp texture lines to ensure non-blurry Laplacian variance
    for i in range(0, size[0], 10):
        arr[i : i + 2, :] = [20, 100, 20]

    img = Image.fromarray(arr)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_non_plant_image(size=(256, 256)) -> bytes:
    """Create a synthetic non-plant image (grey/black metallic texture like tractor or road)."""
    arr = np.full((size[1], size[0], 3), 128, dtype=np.uint8)
    for i in range(0, size[0], 8):
        arr[:, i : i + 2] = 40
    img = Image.fromarray(arr)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_valid_leaf_image_accepted():
    """Verify clean leaf photo passes gatekeeper and produces enhanced bytes + tensor."""
    preprocessor = ImagePreprocessor()
    leaf_bytes = create_mock_leaf_image()

    gatekeeper, pil_img = preprocessor.validate_and_gatekeep(leaf_bytes)
    assert gatekeeper.is_plant is True
    assert gatekeeper.is_blurred is False
    assert pil_img is not None

    enhanced_bytes, tensor, rgb_np = preprocessor.enhance(pil_img)
    assert len(enhanced_bytes) > 0
    assert tensor.shape == (1, 3, 224, 224)
    assert rgb_np.shape == (224, 224, 3)


def test_non_plant_image_rejected_by_gatekeeper():
    """Verify non-plant image (tractor/metal/pavement) is rejected by Leaf Gatekeeper (Improvement 1)."""
    preprocessor = ImagePreprocessor()
    non_plant_bytes = create_non_plant_image()

    gatekeeper, pil_img = preprocessor.validate_and_gatekeep(non_plant_bytes)
    assert gatekeeper.is_plant is False
    assert "does not appear to show plant foliage" in gatekeeper.message
    assert pil_img is None


def test_low_resolution_image_rejected():
    """Verify image smaller than minimum 224x224 is rejected."""
    preprocessor = ImagePreprocessor(min_resolution=224)
    tiny_img = create_mock_leaf_image(size=(100, 100))

    gatekeeper, pil_img = preprocessor.validate_and_gatekeep(tiny_img)
    assert gatekeeper.is_plant is False
    assert "resolution too low" in gatekeeper.message
    assert pil_img is None


def test_blurry_image_rejected():
    """Verify smooth out-of-focus blur is rejected."""
    preprocessor = ImagePreprocessor(blur_threshold=50.0)
    # Solid smooth color has near-zero Laplacian variance
    smooth_arr = np.full((256, 256, 3), [34, 139, 34], dtype=np.uint8)
    img = Image.fromarray(smooth_arr)
    buf = BytesIO()
    img.save(buf, format="JPEG")

    gatekeeper, pil_img = preprocessor.validate_and_gatekeep(buf.getvalue())
    assert gatekeeper.is_plant is False
    assert gatekeeper.is_blurred is True
    assert "blurry" in gatekeeper.message.lower()


def test_invalid_bytes_handled():
    """Verify random corrupted bytes don't crash the preprocessor."""
    preprocessor = ImagePreprocessor()
    gatekeeper, pil_img = preprocessor.validate_and_gatekeep(b"not an image file at all")
    assert gatekeeper.is_plant is False
    assert "Invalid image format" in gatekeeper.message
