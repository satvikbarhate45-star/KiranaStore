import statistics
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import TripItem, GroceryTrip, VolatilityConfig

UNIT_DISPLAY_MAP = {
    "gm": "ग्रॅम",
    "g": "ग्रॅम",
    "kg": "किलो",
    "ml": "मिली",
    "L": "लिटर",
    "l": "लिटर",
    "pcs": "नग",
    "dozen": "डझन",
    "packet": "पाकीट",
    "पाकीट": "पाकीट",
    "bunch": "पेंढी",
    "पेंढी": "पेंढी"
}

def get_display_unit(unit: str) -> str:
    clean = (unit or "").strip()
    return UNIT_DISPLAY_MAP.get(clean.lower(), UNIT_DISPLAY_MAP.get(clean, clean or "किलो"))

def format_quantity_display(qty: float, unit: str) -> str:
    """Formats quantity and unit for human-friendly Marathi UI."""
    d_unit = get_display_unit(unit)
    if qty == int(qty):
        return f"{int(qty)} {d_unit}"
    return f"{round(qty, 2)} {d_unit}"

def get_rolling_median_baseline(
    db: Session,
    sku_id: int,
    buyer_id: int = 1,
    window_size: int = 5
) -> Optional[float]:
    """
    Computes rolling median of the last N settled derived_rate values
    for the canonical SKU, scoped by buyer.
    """
    recent_items = (
        db.query(TripItem.unit_base_rate, TripItem.derived_rate)
        .join(GroceryTrip, GroceryTrip.trip_id == TripItem.trip_id)
        .filter(
            TripItem.sku_id == sku_id,
            GroceryTrip.buyer_id == buyer_id,
            GroceryTrip.status == "settled"
        )
        .order_by(desc(TripItem.created_at))
        .limit(window_size)
        .all()
    )
    
    if not recent_items:
        return None
    
    rates = [
        float(item[0]) if (item[0] is not None and item[0] > 0) else float(item[1])
        for item in recent_items 
        if (item[0] is not None and item[0] > 0) or (item[1] is not None and item[1] > 0)
    ]
    if not rates:
        return None
        
    median_val = statistics.median(rates)
    return round(float(median_val), 2)

def calculate_volatility_badge(
    derived_rate: float,
    baseline_rate: Optional[float],
    config: Optional[VolatilityConfig] = None
) -> Tuple[str, Optional[float]]:
    """
    Calculates badge according to PRD Section 2.3 normative gap-band precedence:
    1. No baseline -> 'नवीन नोंद'
    2. Variance > +6% -> 'भाववाढ'
    3. Variance < -2% -> 'स्वस्त'
    4. Otherwise (|Variance| <= 5%) -> 'संतुलित'
    """
    if baseline_rate is None or baseline_rate <= 0:
        return "नवीन नोंद", None
        
    variance_pct = ((derived_rate - baseline_rate) / baseline_rate) * 100.0
    variance_pct = round(variance_pct, 2)
    
    surge_gt = config.surge_gt if config else 6.0
    dip_lt = config.dip_lt if config else -2.0
    balanced_abs = config.balanced_abs if config else 5.0
    
    if variance_pct > surge_gt:
        badge = "भाववाढ"
    elif variance_pct < dip_lt:
        badge = "स्वस्त"
    else:
        badge = "संतुलित"
        
    return badge, variance_pct

def calculate_basket_status(
    items_summary: List[Dict]
) -> Tuple[str, Optional[float], int]:
    """
    Weighted basket variance = sum(entered_total) vs sum(baseline_rate * quantity)
    for items with historical baselines.
    Returns: (basket_status, basket_variance_pct, new_items_count)
    """
    total_entered_with_baseline = 0.0
    total_expected_baseline = 0.0
    new_items_count = 0
    
    for item in items_summary:
        entered = float(item.get("entered_total", 0.0))
        baseline = item.get("baseline_rate")
        qty = float(item.get("quantity_norm", 0.0))
        
        if baseline is not None and baseline > 0 and qty > 0:
            total_entered_with_baseline += entered
            total_expected_baseline += (baseline * qty)
        else:
            new_items_count += 1
            
    if total_expected_baseline <= 0:
        return "संतुलित बजेट", 0.0, new_items_count
        
    basket_variance = ((total_entered_with_baseline - total_expected_baseline) / total_expected_baseline) * 100.0
    basket_variance = round(basket_variance, 2)
    
    # <= +5% is 'संतुलित बजेट', else 'असंतुलित खर्च'
    if basket_variance <= 5.0:
        status = "संतुलित बजेट"
    else:
        status = "असंतुलित खर्च"
        
    return status, basket_variance, new_items_count
