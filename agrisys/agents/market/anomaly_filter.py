"""Interquartile Range (IQR) Anomaly Filter for daily APMC mandi price series."""

from __future__ import annotations
import logging
from typing import List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class IQRAnomalyFilter:
    """Filters statistical price anomalies and fat-finger data entry errors using the IQR method."""

    def __init__(self, iqr_multiplier: float = 1.5):
        self.iqr_multiplier = iqr_multiplier

    def filter_outliers(self, prices: list[float]) -> list[float]:
        """
        Removes values outside [Q1 - k*IQR, Q3 + k*IQR].
        If fewer than 4 values are provided, returns original prices.
        """
        if len(prices) < 4:
            return [float(p) for p in prices if p > 0.0]

        arr = np.array(prices, dtype=np.float64)
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1

        lower_bound = max(0.0, q1 - (self.iqr_multiplier * iqr))
        upper_bound = q3 + (self.iqr_multiplier * iqr)

        filtered = [float(p) for p in arr if lower_bound <= p <= upper_bound]

        if not filtered:
            # Safeguard: If all filtered out (e.g. identical outliers), fallback to median
            median_val = float(np.median(arr))
            return [median_val]

        logger.debug(
            "IQR Anomaly Filter: %d -> %d prices (Bounds: [%.1f, %.1f])",
            len(prices), len(filtered), lower_bound, upper_bound
        )
        return filtered

    def detect_anomalies(self, prices: list[float]) -> list[bool]:
        """Returns boolean mask where True indicates an anomalous outlier price."""
        if len(prices) < 4:
            return [False] * len(prices)

        arr = np.array(prices, dtype=np.float64)
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1

        lower_bound = max(0.0, q1 - (self.iqr_multiplier * iqr))
        upper_bound = q3 + (self.iqr_multiplier * iqr)

        return [not (lower_bound <= p <= upper_bound) for p in arr]
