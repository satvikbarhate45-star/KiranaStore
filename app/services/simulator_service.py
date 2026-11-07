"""
KiranaStore Budget Simulation Service (SSOT)
Calculates projected basket costs strictly using historical baseline unit_base_rate.
Projection Formula: projected_item_cost = requested_input_quantity * unit_base_rate
Total simulated budget = sum(projected_item_cost)
Range estimates: -5% (low) to +7% (high)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import ProductCatalog
from app.services.volatility_engine import get_rolling_median_baseline, get_display_unit
from app.services.analytics_engine import get_commodity_historical_benchmark
from app.config import settings

def calculate_item_projection(
    requested_quantity: float,
    unit_base_rate: Optional[float]
) -> Dict[str, Optional[float]]:
    """
    Strict mathematical projection:
    projected_item_cost = requested_quantity * unit_base_rate
    """
    if unit_base_rate is None or unit_base_rate <= 0 or requested_quantity <= 0:
        return {
            "estimated_total": None,
            "confidence_range_low": None,
            "confidence_range_high": None
        }

    est = round(requested_quantity * unit_base_rate, 2)
    low = round(est * 0.95, 2)
    high = round(est * 1.07, 2)

    return {
        "estimated_total": est,
        "confidence_range_low": low,
        "confidence_range_high": high
    }

def simulate_budget_pipeline(
    db: Session,
    requested_items: List[Dict[str, Any]],
    buyer_id: int = 1
) -> Dict[str, Any]:
    """
    Executes the budget simulation pipeline across all requested items:
    1. Fetches historical baseline querying strictly unit_base_rate.
    2. Computes projected_item_cost for each line.
    3. Aggregates grand total strictly as the sum of projected_item_costs.
    """
    results = []
    missing_items_count = 0

    for it in requested_items:
        sku_id = it.get("sku_id")
        qty = float(it.get("quantity") or 0.0)
        manual_price = float(it.get("manual_price")) if (it.get("manual_price") is not None and float(it.get("manual_price")) > 0) else None

        prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == sku_id).first() if sku_id else None
        if not prod or qty <= 0:
            continue

        if manual_price is not None:
            baseline = manual_price
            has_history = False
            manual_required = False
        else:
            # Strictly select unit_base_rate from sanitized records
            hist_median = get_rolling_median_baseline(db, prod.sku_id, buyer_id=buyer_id)
            if hist_median is not None and hist_median > 0:
                baseline = float(hist_median)
                has_history = True
                manual_required = False
            else:
                bm = get_commodity_historical_benchmark(db, prod.marathi_name, prod.canonical_unit)
                if bm["has_history"] and bm["previous_rate"] and bm["previous_rate"] > 0:
                    baseline = float(bm["previous_rate"])
                    has_history = True
                    manual_required = False
                else:
                    baseline = None
                    has_history = False
                    manual_required = True
                    missing_items_count += 1

        proj = calculate_item_projection(requested_quantity=qty, unit_base_rate=baseline)
        display_u = get_display_unit(prod.canonical_unit)

        results.append({
            "sku_id": prod.sku_id,
            "marathi_name": prod.marathi_name,
            "quantity": qty,
            "unit": prod.canonical_unit,
            "display_unit": display_u,
            "baseline_unit_rate": baseline,
            "unit_base_rate": baseline,
            "rate_badge_mr": f"₹{baseline:.2f}/{display_u}" if baseline else "—",
            "estimated_total": proj["estimated_total"],
            "projected_item_cost": proj["estimated_total"],
            "confidence_range_low": proj["confidence_range_low"],
            "confidence_range_high": proj["confidence_range_high"],
            "has_history": has_history,
            "manual_price_required": manual_required,
            "manual_price": manual_price
        })

    # Total simulated budget = aggregate sum of individually computed item costs
    total_est = round(sum(r["estimated_total"] for r in results if r["estimated_total"] is not None), 2)
    total_low = round(total_est * 0.95, 2)
    total_high = round(total_est * 1.07, 2)

    has_missing = missing_items_count > 0
    notice = "काही वस्तूंचा इतिहास उपलब्ध नाही, कृपया दर टाका." if has_missing else None

    return {
        "total_estimated": total_est,
        "total_range_low": total_low,
        "total_range_high": total_high,
        "confidence_range_low": total_low,
        "confidence_range_high": total_high,
        "items": results,
        "items_count": len(results),
        "has_missing_history": has_missing,
        "missing_items_count": missing_items_count,
        "notice_mr": notice
    }
