"""Official CACP Minimum Support Price (MSP) benchmarks and comparison engine."""

from __future__ import annotations
from typing import Dict, Optional
from agrisys.agents.market.models import MSPComparison

# Official CACP MSP Rates in ₹/quintal (1 quintal = 100 kg)
CACP_MSP_DATABASE: dict[str, float] = {
    "paddy": 2300.0,
    "rice": 2300.0,
    "paddy_grade_a": 2320.0,
    "wheat": 2275.0,
    "maize": 2090.0,
    "cotton": 7121.0,
    "cotton_long_staple": 7521.0,
    "soyabean": 4892.0,
    "soybean": 4892.0,
    "mustard": 5650.0,
    "rapeseed": 5650.0,
    "gram": 5440.0,
    "chana": 5440.0,
    "tur": 7550.0,
    "arhar": 7550.0,
    "moong": 8682.0,
    "urad": 7400.0,
    "groundnut": 6783.0,
    "sugarcane": 3400.0,  # Fair and Remunerative Price (FRP) basis per tonne converted
}


def compare_msp(commodity: str, current_price_quintal: float) -> MSPComparison:
    """Compares current transaction modal price against official government MSP floor."""
    clean_comm = commodity.lower().strip()
    msp_val = CACP_MSP_DATABASE.get(clean_comm)

    if msp_val is None:
        # Check partial matching (e.g. "hybrid maize" -> "maize")
        for k, v in CACP_MSP_DATABASE.items():
            if k in clean_comm:
                msp_val = v
                break

    if msp_val is None:
        return MSPComparison(
            commodity=commodity,
            msp_price=None,
            current_market_price=round(current_price_quintal, 2),
            difference=None,
            diff_percentage=None,
            status="NO_MSP_ANNOUNCED",
            guidance=f"{commodity} is a non-MSP commodity (market-driven or covered under Operation Greens/MIS). Base sales purely on mandi supply-demand dynamics.",
        )

    diff = current_price_quintal - msp_val
    diff_pct = (diff / msp_val) * 100.0

    if diff > 50.0:
        status = "ABOVE_MSP"
        guidance = (
            f"Trading {diff_pct:.1f}% ABOVE official CACP MSP (₹{msp_val:,.0f}/q). "
            f"Open market realization is profitable. Favorable for open APMC or eNAM auction sale."
        )
    elif diff < -50.0:
        status = "BELOW_MSP"
        guidance = (
            f"Trading {abs(diff_pct):.1f}% BELOW official CACP MSP (₹{msp_val:,.0f}/q). "
            f"Avoid distress sales to local intermediaries. Recommend selling at government procurement centres (FCI/NAFED/State Agencies) to secure guaranteed MSP."
        )
    else:
        status = "AT_MSP"
        guidance = (
            f"Trading at parity with official CACP MSP (₹{msp_val:,.0f}/q). "
            f"Compare local APMC mandi deductions against direct procurement center payment terms."
        )

    return MSPComparison(
        commodity=commodity,
        msp_price=msp_val,
        current_market_price=round(current_price_quintal, 2),
        difference=round(diff, 2),
        diff_percentage=round(diff_pct, 2),
        status=status,
        guidance=guidance,
    )
