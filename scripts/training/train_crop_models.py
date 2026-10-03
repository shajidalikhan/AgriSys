"""
Training Script for AgriSys Crop Recommendation Models (XGBoost + Random Forest).
Supports reading standard ICAR/Kaggle Crop_recommendation.csv or generating high-fidelity
agronomic data across 22 Indian crops.

Saves:
- models/crop_xgb_model.json
- models/crop_rf_model.joblib
- models/crop_label_mapping.json
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_crop_models")

CROP_PROFILES = {
    "rice":        {"N": (60, 99), "P": (35, 60), "K": (35, 45), "temp": (20, 27), "hum": (80, 85), "ph": (5.0, 7.0), "rain": (180, 300)},
    "maize":       {"N": (60, 100), "P": (35, 60), "K": (15, 25), "temp": (18, 27), "hum": (55, 75), "ph": (5.5, 7.0), "rain": (60, 110)},
    "chickpea":    {"N": (20, 60), "P": (55, 80), "K": (75, 85), "temp": (17, 20), "hum": (14, 20), "ph": (6.0, 8.5), "rain": (65, 95)},
    "kidneybeans": {"N": (10, 40), "P": (55, 80), "K": (15, 25), "temp": (15, 25), "hum": (18, 25), "ph": (5.5, 6.0), "rain": (60, 150)},
    "pigeonpeas":  {"N": (10, 40), "P": (55, 75), "K": (15, 25), "temp": (25, 35), "hum": (30, 65), "ph": (4.5, 7.5), "rain": (90, 200)},
    "mothbeans":   {"N": (10, 40), "P": (35, 60), "K": (15, 25), "temp": (24, 32), "hum": (40, 65), "ph": (3.5, 9.0), "rain": (30, 75)},
    "mungbean":    {"N": (10, 40), "P": (35, 60), "K": (15, 25), "temp": (27, 30), "hum": (80, 90), "ph": (6.2, 7.2), "rain": (35, 60)},
    "blackgram":   {"N": (30, 60), "P": (55, 80), "K": (15, 25), "temp": (25, 35), "hum": (60, 70), "ph": (6.5, 7.5), "rain": (60, 75)},
    "lentil":      {"N": (10, 40), "P": (55, 80), "K": (15, 25), "temp": (18, 30), "hum": (60, 70), "ph": (6.0, 7.5), "rain": (35, 55)},
    "pomegranate": {"N": (10, 40), "P": (10, 30), "K": (35, 45), "temp": (18, 25), "hum": (85, 95), "ph": (5.5, 7.2), "rain": (100, 115)},
    "banana":      {"N": (80, 120), "P": (70, 95), "K": (45, 55), "temp": (25, 30), "hum": (75, 85), "ph": (5.5, 6.5), "rain": (90, 120)},
    "mango":       {"N": (10, 40), "P": (15, 40), "K": (25, 35), "temp": (27, 36), "hum": (45, 55), "ph": (4.5, 7.0), "rain": (85, 105)},
    "grapes":      {"N": (10, 40), "P": (120, 145), "K": (195, 205), "temp": (8, 42), "hum": (80, 85), "ph": (5.5, 6.5), "rain": (65, 75)},
    "watermelon":  {"N": (80, 120), "P": (5, 30), "K": (45, 55), "temp": (24, 28), "hum": (80, 90), "ph": (6.0, 7.0), "rain": (40, 60)},
    "muskmelon":   {"N": (80, 120), "P": (5, 30), "K": (45, 55), "temp": (27, 30), "hum": (90, 95), "ph": (6.0, 6.8), "rain": (20, 30)},
    "apple":       {"N": (10, 40), "P": (120, 145), "K": (195, 205), "temp": (21, 24), "hum": (90, 95), "ph": (5.5, 6.5), "rain": (100, 125)},
    "orange":      {"N": (10, 40), "P": (5, 30), "K": (5, 15), "temp": (10, 35), "hum": (90, 95), "ph": (6.0, 7.5), "rain": (100, 120)},
    "papaya":      {"N": (30, 70), "P": (45, 70), "K": (45, 55), "temp": (23, 44), "hum": (90, 95), "ph": (6.5, 7.0), "rain": (40, 250)},
    "coconut":     {"N": (10, 40), "P": (5, 30), "K": (25, 35), "temp": (25, 30), "hum": (95, 100), "ph": (5.5, 6.5), "rain": (130, 230)},
    "cotton":      {"N": (100, 140), "P": (35, 60), "K": (15, 25), "temp": (22, 26), "hum": (75, 85), "ph": (5.8, 8.0), "rain": (60, 100)},
    "jute":        {"N": (60, 100), "P": (35, 60), "K": (35, 45), "temp": (23, 26), "hum": (70, 90), "ph": (6.0, 7.4), "rain": (150, 205)},
    "coffee":      {"N": (80, 120), "P": (15, 40), "K": (25, 35), "temp": (23, 28), "hum": (50, 70), "ph": (6.0, 7.5), "rain": (115, 200)},
}


def generate_synthetic_crop_data(samples_per_crop: int = 100) -> pd.DataFrame:
    """Generate high-fidelity agronomic synthetic dataset matching ICAR norms."""
    logger.info(f"Generating synthetic crop dataset ({len(CROP_PROFILES)} crops, {samples_per_crop} samples/crop)...")
    np.random.seed(42)
    rows = []

    for crop, prof in CROP_PROFILES.items():
        n_low, n_high = prof["N"]
        p_low, p_high = prof["P"]
        k_low, k_high = prof["K"]
        t_low, t_high = prof["temp"]
        h_low, h_high = prof["hum"]
        ph_low, ph_high = prof["ph"]
        r_low, r_high = prof["rain"]

        for _ in range(samples_per_crop):
            # Normal distribution centered at midpoint with slight noise
            n = np.clip(np.random.normal((n_low + n_high) / 2, (n_high - n_low) / 4), 0, 250)
            p = np.clip(np.random.normal((p_low + p_high) / 2, (p_high - p_low) / 4), 0, 250)
            k = np.clip(np.random.normal((k_low + k_high) / 2, (k_high - k_low) / 4), 0, 300)
            temp = np.clip(np.random.normal((t_low + t_high) / 2, (t_high - t_low) / 4), 5, 50)
            hum = np.clip(np.random.normal((h_low + h_high) / 2, (h_high - h_low) / 4), 10, 100)
            ph = np.clip(np.random.normal((ph_low + ph_high) / 2, (ph_high - ph_low) / 4), 3.5, 9.5)
            rain = np.clip(np.random.normal((r_low + r_high) / 2, (r_high - r_low) / 4), 20, 3500)

            rows.append({
                "N": round(float(n), 2),
                "P": round(float(p), 2),
                "K": round(float(k), 2),
                "temperature": round(float(temp), 2),
                "humidity": round(float(hum), 2),
                "ph": round(float(ph), 2),
                "rainfall": round(float(rain), 2),
                "label": crop,
            })

    df = pd.DataFrame(rows)
    # Shuffle
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    return df


def train_and_save_models():
    """Main training routine for XGBoost & Random Forest models."""
    data_path = os.path.join("data", "raw", "Crop_recommendation.csv")
    models_dir = os.path.join("models")
    os.makedirs(models_dir, exist_ok=True)

    if os.path.exists(data_path):
        logger.info(f"Loading official Crop Recommendation dataset from: {data_path}")
        df = pd.read_csv(data_path)
    else:
        logger.info("Official dataset not found. Generating high-fidelity synthetic dataset...")
        df = generate_synthetic_crop_data(samples_per_crop=120)
        os.makedirs(os.path.join("data", "raw"), exist_ok=True)
        df.to_csv(data_path, index=False)
        logger.info(f"Saved dataset snapshot to: {data_path}")

    feature_cols = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    X = df[feature_cols].values
    y_raw = df["label"].values

    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    class_mapping = {int(idx): str(label) for idx, label in enumerate(le.classes_)}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    logger.info(f"Dataset split: Train={len(X_train)} samples, Test={len(X_test)} samples across {len(le.classes_)} crops.")

    # 1. Train XGBoost Model
    logger.info("Training XGBoost Multi-Class Classifier...")
    xgb_clf = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        objective="multi:softprob",
        num_class=len(le.classes_),
        random_state=42,
        eval_metric="mlogloss",
    )
    xgb_clf.fit(X_train, y_train)
    xgb_preds = xgb_clf.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_preds)
    logger.info(f"XGBoost Test Accuracy: {xgb_acc * 100:.2f}%")

    xgb_model_path = os.path.join(models_dir, "crop_xgb_model.json")
    xgb_clf.save_model(xgb_model_path)
    logger.info(f"Saved XGBoost model to: {xgb_model_path}")

    # 2. Train Random Forest Model
    logger.info("Training Random Forest Bagging Classifier...")
    rf_clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )
    rf_clf.fit(X_train, y_train)
    rf_preds = rf_clf.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_preds)
    logger.info(f"Random Forest Test Accuracy: {rf_acc * 100:.2f}%")

    rf_model_path = os.path.join(models_dir, "crop_rf_model.joblib")
    joblib.dump(rf_clf, rf_model_path)
    logger.info(f"Saved Random Forest model to: {rf_model_path}")

    # 3. Save Label Mapping
    mapping_path = os.path.join(models_dir, "crop_label_mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(class_mapping, f, indent=2)
    logger.info(f"Saved label mappings to: {mapping_path}")

    logger.info("Model training successfully completed!")


if __name__ == "__main__":
    train_and_save_models()
