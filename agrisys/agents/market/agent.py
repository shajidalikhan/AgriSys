"""Master Market Price Intelligence Agent coordinating forecasting, MSP analysis, and mandi ranking."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from agrisys.agents.market.models import (
    MandiRecord,
    PriceForecastPoint,
    MSPComparison,
    MarketAdvisoryReport,
)
from agrisys.agents.market.msp_database import compare_msp
from agrisys.agents.market.anomaly_filter import IQRAnomalyFilter
from agrisys.agents.market.haversine_ranker import HaversineMandiRanker
from agrisys.agents.market.forecaster import get_price_forecaster, BasePriceForecaster
from agrisys.agents.market.data_client import MandiDataClient
from agrisys.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class MarketAgent:
    """Coordinates mandi price intelligence, 7-day forecasting, and Sell/Hold advisories."""

    def __init__(
        self,
        forecaster: BasePriceForecaster | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.forecaster = forecaster or get_price_forecaster()
        self.llm_provider = llm_provider
        self.data_client = MandiDataClient()
        self.anomaly_filter = IQRAnomalyFilter()
        self.ranker = HaversineMandiRanker()

    async def advise(
        self,
        commodity: str = "Tomato",
        origin_lat: float = 26.8467,  # Default: Lucknow center
        origin_lon: float = 80.9462,
        location_name: str = "Lucknow, Uttar Pradesh",
        language: str = "en",
    ) -> MarketAdvisoryReport:
        """
        Executes end-to-end market price intelligence analysis.
        """
        # 1. Fetch raw mandi records
        feed = await self.data_client.fetch_mandi_prices(commodity=commodity, state="Uttar Pradesh")
        raw_prices = [float(item["modal_price"]) for item in feed]

        # 2. Filter statistical anomalies with IQR
        filtered_prices = self.anomaly_filter.filter_outliers(raw_prices)
        current_modal_quintal = filtered_prices[0] if filtered_prices else 2000.0
        current_modal_kg = round(current_modal_quintal / 100.0, 2)

        # 3. Rank surrounding APMC mandis by net realization price
        price_lookup = {item["mandi"]: float(item["modal_price"]) for item in feed}
        ranked_mandis = self.ranker.rank_mandis(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            commodity=commodity,
            price_lookup=price_lookup,
            top_k=5,
        )

        # 4. Generate 7-day price forecast
        forecast_7d = self.forecaster.forecast(
            base_price=current_modal_quintal,
            history_prices=filtered_prices,
            horizon_days=7,
        )

        # Determine price trajectory trend
        first_proj = forecast_7d[0].projected_modal_price
        last_proj = forecast_7d[-1].projected_modal_price
        trend_pct = round(((last_proj - first_proj) / first_proj) * 100.0, 1)

        if trend_pct >= 4.0:
            trend_dir = "RISING"
        elif trend_pct <= -4.0:
            trend_dir = "FALLING"
        else:
            trend_dir = "STABLE"

        # 5. CACP MSP benchmark comparison
        msp_analysis = compare_msp(commodity=commodity, current_price_quintal=current_modal_quintal)

        # 6. Strategic Sell / Hold / Transport Recommendation
        best_mandi = ranked_mandis[0] if ranked_mandis else None
        nearest_mandi = min(ranked_mandis, key=lambda m: m.distance_km) if ranked_mandis else None

        if best_mandi and nearest_mandi and best_mandi.mandi_name != nearest_mandi.mandi_name and (best_mandi.net_realization_price - nearest_mandi.net_realization_price > 75.0):
            recommendation = "TRANSPORT_TO_MANDI"
        elif trend_dir == "RISING" and trend_pct >= 6.0:
            recommendation = "HOLD"
        else:
            recommendation = "SELL_NOW"

        # 7. Compose Farmer Advisory Text
        advisory_text = self._format_advisory(
            commodity=commodity,
            location_name=location_name,
            current_modal_kg=current_modal_kg,
            current_modal_quintal=current_modal_quintal,
            trend_dir=trend_dir,
            trend_pct=trend_pct,
            recommendation=recommendation,
            best_mandi=best_mandi,
            msp_analysis=msp_analysis,
            language=language,
        )

        citations = [
            "Agmarknet Directorate of Marketing & Inspection (DMI)",
            "eNAM (National Agriculture Market) Price Feed",
            "CACP (Commission for Agricultural Costs & Prices) MSP Database",
        ]

        return MarketAdvisoryReport(
            commodity=commodity,
            farmer_location=location_name,
            current_modal_price_kg=current_modal_kg,
            current_modal_price_quintal=current_modal_quintal,
            recommendation=recommendation,
            trend_direction=trend_dir,
            trend_percentage=trend_pct,
            msp_analysis=msp_analysis,
            top_mandis=ranked_mandis,
            forecast_7d=forecast_7d,
            advisory_text=advisory_text,
            citations=citations,
        )

    def _format_advisory(
        self,
        commodity: str,
        location_name: str,
        current_modal_kg: float,
        current_modal_quintal: float,
        trend_dir: str,
        trend_pct: float,
        recommendation: str,
        best_mandi: MandiRecord | None,
        msp_analysis: MSPComparison,
        language: str,
    ) -> str:
        """Constructs clear actionable advisory text."""
        best_str = f"{best_mandi.mandi_name} ({best_mandi.distance_km} km, Net: ₹{best_mandi.net_realization_price:,.0f}/q)" if best_mandi else location_name

        if language == "hi":
            action_map = {
                "HOLD": "रोकें (HOLD) — 3 से 5 दिन प्रतीक्षा करें",
                "SELL_NOW": "अभी बेचें (SELL NOW)",
                "TRANSPORT_TO_MANDI": f"परिवहन करें — {best_str} में बेचें",
            }
            trend_sym = "बढ़ने (↑)" if trend_dir == "RISING" else ("गिरने (↓)" if trend_dir == "FALLING" else "स्थिर (→)")
            return (
                f"फसल: {commodity} | वर्तमान भाव: ₹{current_modal_kg:.1f}/किग्रा (₹{current_modal_quintal:,.0f}/क्विंटल)\n"
                f"7 दिवसीय मूल्य रुझान: {trend_sym} {abs(trend_pct)}% अनुमानित।\n"
                f"सर्वोत्तम मंडी: {best_str}\n"
                f"रणनीतिक सलाह: {action_map.get(recommendation, recommendation)}\n"
                f"एमएसपी स्थिति: {msp_analysis.guidance}"
            )
        else:
            action_map = {
                "HOLD": "HOLD — Wait 3 to 5 days for peak price realization if safe storage is accessible.",
                "SELL_NOW": "SELL NOW — Current market rates are optimal; prevent loss from impending arrivals.",
                "TRANSPORT_TO_MANDI": f"TRANSPORT TO MANDI — Route produce to {best_str} for maximum net realization after logistics.",
            }
            trend_sym = "↑ RISING" if trend_dir == "RISING" else ("↓ FALLING" if trend_dir == "FALLING" else "→ STABLE")
            return (
                f"{commodity} trading at ₹{current_modal_kg:.1f}/kg (₹{current_modal_quintal:,.0f}/quintal) in {location_name}.\n"
                f"Price Velocity: {trend_sym} by {abs(trend_pct)}% over the next 7 days.\n"
                f"Highest Net Profit Mandi: {best_str}.\n"
                f"Strategic Recommendation: {action_map.get(recommendation, recommendation)}\n"
                f"MSP Context: {msp_analysis.guidance}"
            )
