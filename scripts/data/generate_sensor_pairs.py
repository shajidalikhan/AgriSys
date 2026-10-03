"""Synthetic Soil Sensor & Nutrition Deficiency Pair Generator.

Generates realistic multimodal sensor paired data aligned with ICAR Soil Health Card (SHC)
empirical distributions to train and validate Stage 4 Nutrition Cross-Modal models.
"""

from __future__ import annotations
import argparse
import csv
import logging
import math
import random
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CROPS = ["Tomato", "Wheat", "Rice", "Maize", "Potato", "Cotton", "Sugarcane", "Banana"]

DEFICIENCY_MAPPING = [
    ("Nitrogen (N) Deficiency", "N", (60.0, 240.0), (10.0, 30.0), (120.0, 300.0)),
    ("Phosphorus (P) Deficiency", "P", (280.0, 500.0), (2.0, 9.5), (120.0, 300.0)),
    ("Potassium (K) Deficiency", "K", (280.0, 500.0), (12.0, 30.0), (30.0, 100.0)),
    ("Calcium (Ca) Deficiency", "Ca", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Magnesium (Mg) Deficiency", "Mg", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Sulfur (S) Deficiency", "S", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Iron (Fe) Deficiency", "Fe", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Zinc (Zn) Deficiency", "Zn", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Manganese (Mn) Deficiency", "Mn", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Boron (B) Deficiency", "B", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Copper (Cu) Deficiency", "Cu", (280.0, 500.0), (12.0, 30.0), (120.0, 300.0)),
    ("Healthy / Optimal", "None", (290.0, 520.0), (14.0, 28.0), (140.0, 320.0)),
]


def generate_synthetic_nutrition_dataset(
    output_path: Path,
    num_samples: int = 1000,
    seed: int = 42,
) -> Path:
    """Generates synthetic sensor readings and corresponding ICAR SHC target doses."""
    random.seed(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "sample_id",
        "crop",
        "nitrogen",
        "phosphorus",
        "potassium",
        "ph",
        "electrical_conductivity",
        "soil_moisture",
        "deficiency_class",
        "affected_nutrient",
        "target_n_dose",
        "target_p_dose",
        "target_k_dose",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in range(1, num_samples + 1):
            sample_id = f"NUT_{i:05d}"
            crop = random.choice(CROPS)

            # Choose deficiency class
            def_class, nutrient, n_range, p_range, k_range = random.choice(DEFICIENCY_MAPPING)

            nitrogen = round(random.uniform(*n_range), 2)
            phosphorus = round(random.uniform(*p_range), 2)
            potassium = round(random.uniform(*k_range), 2)

            # Soil pH and EC
            if nutrient == "Fe" or nutrient == "Zn":
                # Micronutrient deficiency often exacerbated in alkaline soils
                ph = round(random.uniform(7.8, 8.8), 2)
            elif nutrient == "P":
                # Phosphorus fixated in acidic or high alkaline
                ph = round(random.choice([random.uniform(4.5, 5.8), random.uniform(8.0, 8.6)]), 2)
            else:
                ph = round(random.uniform(6.0, 7.6), 2)

            ec = round(random.uniform(0.3, 1.4), 2)
            moisture = round(random.uniform(25.0, 65.0), 1)

            # Target doses based on deficits
            target_n = max(0.0, round(300.0 - nitrogen, 1)) if nitrogen < 280 else 0.0
            target_p = max(0.0, round(25.0 - phosphorus, 1)) if phosphorus < 15 else 0.0
            target_k = max(0.0, round(200.0 - potassium, 1)) if potassium < 140 else 0.0

            writer.writerow([
                sample_id,
                crop,
                nitrogen,
                phosphorus,
                potassium,
                ph,
                ec,
                moisture,
                def_class,
                nutrient,
                target_n,
                target_p,
                target_k,
            ])

    logger.info("Generated %d synthetic nutrition pairs at %s", num_samples, output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic nutrition sensor pairs.")
    parser.add_argument("--samples", type=int, default=1000, help="Number of records to synthesize")
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/synthetic_sensor_nutrition_pairs.csv",
        help="Target CSV output path",
    )
    args = parser.parse_args()

    out_file = Path(args.output)
    generate_synthetic_nutrition_dataset(out_file, num_samples=args.samples)


if __name__ == "__main__":
    main()
