"""7-Day Mandi Price Forecasting Engine with Prophet & Statistical Trend Decomposition."""

from __future__ import annotations
import abc
import datetime
import logging
from typing import List, Tuple
import numpy as np

from agrisys.agents.market.models import PriceForecastPoint

logger = logging.getLogger(__name__)


class BasePriceForecaster(abc.ABC):
    """Abstract interface for commodity price forecasting engines."""

    @abc.abstractmethod
    def forecast(
        self,
        base_price: float,
        history_prices: list[float] | None = None,
        horizon_days: int = 7,
    ) -> list[PriceForecastPoint]:
        """Generates multi-day price projection points."""
        pass


class StatisticalPriceForecaster(BasePriceForecaster):
    """
    High-speed robust statistical forecaster using polynomial trend regression,
    7-day weekly arrival seasonality, and residual standard error confidence bands.
    """

    def forecast(
        self,
        base_price: float,
        history_prices: list[float] | None = None,
        horizon_days: int = 7,
    ) -> list[PriceForecastPoint]:
        today = datetime.date.today()
        history = history_prices if history_prices and len(history_prices) >= 4 else [
            base_price * (1.0 + 0.01 * math_sin)
            for math_sin in [-2.1, -1.0, 0.4, 0.9, 1.2, 0.8, 1.5]
        ]

        x_hist = np.arange(len(history), dtype=np.float64)
        y_hist = np.array(history, dtype=np.float64)

        # 1. Fit linear slope (trend)
        slope, intercept = np.polyfit(x_hist, y_hist, 1)

        # 2. Residual variance for confidence intervals
        fitted = intercept + slope * x_hist
        residuals = y_hist - fitted
        std_err = float(np.std(residuals)) if len(residuals) > 1 else (base_price * 0.03)
        conf_margin = max(std_err * 1.28, base_price * 0.02)  # ~80% confidence interval

        # Weekly cyclical arrival adjustment factor (sinusoidal pattern)
        forecast_points: list[PriceForecastPoint] = []
        last_x = len(history)

        for day in range(1, horizon_days + 1):
            future_date = today + datetime.timedelta(days=day)
            x_future = last_x + day - 1

            # Baseline trend
            raw_proj = intercept + (slope * x_future)

            # Weekly arrival fluctuation (±2% seasonal rhythm)
            day_of_week = future_date.weekday()
            seasonality = 1.0 + (0.015 * np.sin(2 * np.pi * day_of_week / 7.0))
            projected = max(100.0, raw_proj * seasonality)

            lower = max(50.0, projected - conf_margin)
            upper = projected + conf_margin

            forecast_points.append(
                PriceForecastPoint(
                    day_offset=day,
                    date=future_date.isoformat(),
                    projected_modal_price=round(projected, 2),
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                )
            )

        return forecast_points


class ProphetPriceForecaster(BasePriceForecaster):
    """Prophet time-series adapter with automatic statistical fallback."""

    def __init__(self):
        self._has_prophet = False
        self._fallback = StatisticalPriceForecaster()
        try:
            import prophet  # type: ignore # noqa: F401
            self._has_prophet = True
        except ImportError:
            self._has_prophet = False

    def forecast(
        self,
        base_price: float,
        history_prices: list[float] | None = None,
        horizon_days: int = 7,
    ) -> list[PriceForecastPoint]:
        if not self._has_prophet:
            return self._fallback.forecast(base_price, history_prices, horizon_days)

        try:
            import pandas as pd
            from prophet import Prophet

            today = datetime.date.today()
            n_hist = len(history_prices) if history_prices else 7
            dates = [today - datetime.timedelta(days=n_hist - i) for i in range(n_hist)]
            prices = history_prices if history_prices else [base_price] * n_hist

            df = pd.DataFrame({"ds": dates, "y": prices})
            model = Prophet(daily_seasonality=False, weekly_seasonality=True)
            model.fit(df)

            future = model.make_future_dataframe(periods=horizon_days)
            forecast_df = model.predict(future).tail(horizon_days)

            points: list[PriceForecastPoint] = []
            for idx, (_, row) in enumerate(forecast_df.iterrows(), start=1):
                points.append(
                    PriceForecastPoint(
                        day_offset=idx,
                        date=row["ds"].strftime("%Y-%m-%d"),
                        projected_modal_price=round(float(row["yhat"]), 2),
                        lower_bound=round(float(row["yhat_lower"]), 2),
                        upper_bound=round(float(row["yhat_upper"]), 2),
                    )
                )
            return points
        except Exception as err:
            logger.warning("Prophet inference failed (%s), using statistical fallback.", err)
            return self._fallback.forecast(base_price, history_prices, horizon_days)


def get_price_forecaster() -> BasePriceForecaster:
    """Factory returning configured price forecaster."""
    return ProphetPriceForecaster()
