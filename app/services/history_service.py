"""
KiranaStore - History & Historical Purchases Service
Implements dynamic, zero-hardcoding quantity normalization and financial rate separation
across every line item in the KiranaStore pipeline.
"""
import re
import datetime
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import GroceryTrip, TripItem, ProductCatalog, SavedGroceryList
from app.services.normalizer import parse_measurement, normalize_line_item, NormalizedLine, to_ascii_digits, DEV_DIGITS

def parse_dynamic_quantity(quantity_str: str) -> Tuple[float, str]:
    """
    DYNAMIC QUANTITY PARSER FUNCTION (Zero Hardcoded Commodity Names):
    - Input: Raw quantity string (e.g., '15 किलो', '7 kg', '250 ग्रॅम', 'अर्धा किलो', '4 पाकीट').
    - Parsing Rules:
      * Extract numerical float Q. If string contains 'अर्धा' or '1/2', Q = 0.5.
      * Identify unit type:
        - If unit contains ['ग्रॅम', 'g', 'gm']: Normalize normalized_qty = Q / 1000.0, base_unit = 'किलो'.
        - If unit contains ['किलो', 'kg', 'k.g.', 'ली', 'ltr']: normalized_qty = Q, base_unit = 'किलो' (or 'ली').
        - If unit contains ['पाकीट', 'नग', 'डबा', 'तोळा']: normalized_qty = Q, base_unit = matched_unit.
    Returns: (normalized_qty, base_unit)
    """
    if not quantity_str:
        return 1.0, "किलो"

    norm_str = to_ascii_digits(str(quantity_str).strip().lower())

    # 1. Colloquial Marathi Fractions / Words (purely numeric & unit scaling)
    Q = None
    if any(f in norm_str for f in ["अर्धा", "1/2", "१/२", "आधा"]):
        if "दीड" in norm_str:
            Q = 1.5
        elif "अडीच" in norm_str:
            Q = 2.5
        else:
            Q = 0.5
    elif any(f in norm_str for f in ["पाव किलो", "1/4", "१/४", "पाव"]):
        Q = 0.25
    elif any(f in norm_str for f in ["पाऊण", "3/4", "३/४"]):
        Q = 0.75
    elif "सव्वा" in norm_str:
        Q = 1.25
    elif "दीड" in norm_str:
        Q = 1.5
    elif "अडीच" in norm_str:
        Q = 2.5

    # If Q is not resolved by colloquial fractions, extract numerical float
    if Q is None:
        # Check composite packaging like "२ + २ (४ पाकीट)"
        composite_m = re.search(r'\((\d+(?:\.\d+)?)\s*(?:पाकीट|पॅकेट|नग|डबा)?\)', norm_str)
        if composite_m:
            Q = float(composite_m.group(1))
        else:
            num_m = re.search(r'(\d+(?:\.\d+)?)', norm_str)
            if num_m:
                Q = float(num_m.group(1))
            else:
                Q = 1.0

    if Q <= 0:
        Q = 1.0

    # 2. Identify unit type & standardize to base scales (kilogram, liter, or countable packaging)
    # Liquid scales
    if any(u in norm_str for u in ["मिली", "ml"]):
        normalized_qty = round(Q / 1000.0, 4)
        base_unit = "ली"
    elif any(u in norm_str for u in ["ली", "ltr", "liter", "लिटर"]) or re.search(r'\b(?:l)\b', norm_str):
        normalized_qty = Q
        base_unit = "ली"

    # Weight scales: Kilograms vs Grams
    elif any(u in norm_str for u in ["किलो", "kg", "k.g.", "kilo"]):
        normalized_qty = Q
        base_unit = "किलो"
    elif any(u in norm_str for u in ["ग्रॅम", "ग्राम", "gm", "gram", "grams"]) or re.search(r'\b(?:g|gms)\b', norm_str):
        # Scale grams to base kilogram scale
        normalized_qty = round(Q / 1000.0, 4)
        base_unit = "किलो"

    # Packaging / Discrete Countable units
    elif any(u in norm_str for u in ["पाकीट", "पॅकेट", "pkt", "packet"]):
        normalized_qty = Q
        base_unit = "पाकीट"
    elif any(u in norm_str for u in ["नग", "pcs", "piece", "pieces"]):
        normalized_qty = Q
        base_unit = "नग"
    elif any(u in norm_str for u in ["डबा", "डबे", "tin"]):
        normalized_qty = Q
        base_unit = "डबा"
    elif any(u in norm_str for u in ["तोळा", "तोल"]):
        normalized_qty = Q
        base_unit = "तोळा"
    elif any(u in norm_str for u in ["डझन", "dozen"]):
        normalized_qty = Q
        base_unit = "डझन"
    else:
        normalized_qty = Q
        base_unit = "किलो"

    return normalized_qty, base_unit

# Backward compatibility alias
def parse_quantity_magnitude(quantity_str: str, *args, **kwargs) -> Tuple[float, str]:
    return parse_dynamic_quantity(quantity_str)

def normalize_measurement(
    line_total_amount: float,
    quantity_str: str,
    unit: Optional[str] = None
) -> Tuple[float, float, str]:
    """
    GENERALIZED REGEX-BASED UNIT CONVERSION & RATE CALCULATION ENGINE:
    - Extracts numeric magnitudes & fractions (including Devanagari numerals, decimals, fractions).
    - Detects mass units: Standardizes grams to fractional kilograms by dividing by 1000; preserves kg.
    - Detects volume units: Standardizes milliliters to fractional liters by dividing by 1000; preserves liters.
    - Detects discrete count units: Maps packets, pieces, boxes, bunches, dozens, tola to integer scale.
    - Dynamically calculates:
        unit_base_rate = round(line_total_amount / normalized_quantity, 4)
    Returns: (normalized_quantity, unit_base_rate, base_unit)
    """
    total = float(line_total_amount or 0.0)
    normalized_qty, detected_unit = parse_dynamic_quantity(quantity_str)
    base_unit = unit or detected_unit or "किलो"

    if normalized_qty > 0:
        unit_rate = round(total / normalized_qty, 4)
    else:
        unit_rate = round(total, 4)

    return normalized_qty, unit_rate, base_unit

def calculate_unit_price(
    total_price: float,
    quantity_str: str,
    unit: Optional[str] = None,
    *args,
    **kwargs
) -> Tuple[float, float, str]:
    """
    MATHEMATICAL DERIVATION LOGIC:
    - total_price = Raw billed line amount from receipt (line_total_amount).
    - unit_rate = total_price / normalized_qty (unit_base_rate).
    Returns: (normalized_qty, unit_rate, base_unit)
    """
    norm_qty, unit_rate, base_unit = normalize_measurement(total_price, quantity_str, unit)
    return norm_qty, round(unit_rate, 2), base_unit

def update_history_item(
    db: Session,
    item_id: int,
    quantity_str: str,
    total_price: float,
    unit_price: Optional[float] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persists edited historical items with strict separation between line_total_amount and unit_base_rate.
    Recalculates parent trip settled_total.
    """
    item = db.query(TripItem).filter(TripItem.item_id == item_id).first()
    if not item and session_id:
        trip = db.query(GroceryTrip).filter(GroceryTrip.session_id == session_id).first()
        if trip and trip.items:
            for itm in trip.items:
                if itm.item_id == item_id:
                    item = itm
                    break
    if not item:
        raise ValueError(f"TripItem #{item_id} सापडला नाही")

    norm = normalize_line_item(
        line_total=total_price,
        quantity_str=quantity_str,
        raw_unit=item.unit
    )

    final_unit_price = float(unit_price) if (unit_price is not None and unit_price > 0) else norm.unit_base_rate

    # Update item fields - strictly synchronizing line_total, normalized_quantity, and unit_base_rate
    item.quantity_str = str(quantity_str).strip()
    item.normalized_quantity = norm.normalized_quantity
    item.quantity_norm = norm.normalized_quantity
    item.line_total = norm.line_total
    item.line_total_amount = norm.line_total
    item.entered_total = norm.line_total
    item.unit_base_rate = round(final_unit_price, 4)
    item.derived_rate = round(final_unit_price, 4)
    item.unit = norm.display_unit
    item.display_unit = norm.display_unit

    if item.baseline_rate and item.baseline_rate > 0 and abs(item.baseline_rate - total_price) > 0.01:
        item.variance_pct = round(((final_unit_price - item.baseline_rate) / item.baseline_rate) * 100.0, 2)
    else:
        item.baseline_rate = round(final_unit_price, 2)
        item.variance_pct = 0.0

    # Recalculate trip total
    parent_trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == item.trip_id).first()
    new_settled_total = 0.0
    if parent_trip:
        new_settled_total = round(sum((i.line_total_amount or i.entered_total) for i in parent_trip.items), 2)
        parent_trip.settled_total = new_settled_total

    # Sync SavedGroceryList if present
    if parent_trip:
        prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == item.sku_id).first()
        prod_name = prod.marathi_name if prod else (item.raw_input or "")
        saved_list = db.query(SavedGroceryList).filter(
            (SavedGroceryList.title == parent_trip.title) |
            (SavedGroceryList.id == parent_trip.trip_id)
        ).first()
        if saved_list and isinstance(saved_list.items_payload, list):
            updated_payload = []
            for p_item in saved_list.items_payload:
                p_name = p_item.get("name") or p_item.get("item_name")
                if p_name == prod_name:
                    p_item["quantity"] = str(quantity_str).strip()
                    p_item["price"] = round(total_price, 2)
                    p_item["line_total_amount"] = round(total_price, 2)
                    p_item["normalized_quantity"] = round(norm.normalized_quantity, 4)
                    p_item["unit_base_rate"] = round(final_unit_price, 4)
                updated_payload.append(p_item)
            saved_list.items_payload = updated_payload
            saved_list.estimated_budget = new_settled_total

    db.commit()
    db.refresh(item)
    if parent_trip:
        db.refresh(parent_trip)

    return {
        "success": True,
        "item_id": item.item_id,
        "trip_id": item.trip_id,
        "session_id": parent_trip.session_id if parent_trip else None,
        "quantity": item.quantity_str,
        "quantity_norm": item.quantity_norm,
        "normalized_quantity": item.normalized_quantity,
        "unit": item.unit,
        "total_price": item.line_total_amount,
        "line_total": item.line_total_amount,
        "line_total_amount": item.line_total_amount,
        "unit_price": item.unit_base_rate,
        "unit_base_rate": item.unit_base_rate,
        "display_unit": item.unit,
        "trip_settled_total": new_settled_total,
        "message": "नोंद यशस्वीरीत्या अद्ययावत केली!"
    }

def sanitize_historical_database(db: Session) -> Dict[str, Any]:
    """
    Historical Data Sanitization Migration (SSOT):
    - Iterates over all stored purchase records in TripItem and GroceryTrip.
    - Re-processes every item through app.services.normalizer.normalize_line_item.
    - Corrects unnormalized totals, micro-gram rates, and inflated numbers permanently.
    """
    items = db.query(TripItem).all()
    updated_count = 0
    anomalies_flagged = 0

    for itm in items:
        qty_input = itm.quantity_str or itm.raw_input or f"{itm.normalized_quantity or itm.quantity_norm or 1.0} {itm.unit or 'किलो'}"
        total_val = itm.line_total_amount if itm.line_total_amount is not None and itm.line_total_amount > 0 else (itm.entered_total or 0.0)

        norm = normalize_line_item(line_total=total_val, quantity_str=qty_input, raw_unit=itm.unit)

        itm.line_total = norm.line_total
        itm.line_total_amount = norm.line_total
        itm.entered_total = norm.line_total
        itm.normalized_quantity = norm.normalized_quantity
        itm.quantity_norm = norm.normalized_quantity
        itm.unit_base_rate = norm.unit_base_rate
        itm.derived_rate = norm.unit_base_rate
        itm.unit = norm.display_unit
        itm.display_unit = norm.display_unit
        if not itm.quantity_str or not itm.quantity_str.strip():
            itm.quantity_str = norm.raw_quantity_str

        if norm.is_anomaly:
            anomalies_flagged += 1
            print(f"[Sanitize Anomaly] Item #{itm.item_id}: {norm.anomaly_reason}")

        updated_count += 1

    # Recalculate all trip totals
    trips = db.query(GroceryTrip).all()
    for t in trips:
        if t.items:
            t.settled_total = round(sum((i.line_total_amount or i.entered_total or 0.0) for i in t.items), 2)

    db.commit()
    return {
        "status": "success",
        "items_sanitized": updated_count,
        "anomalies_flagged": anomalies_flagged,
        "trips_recalculated": len(trips)
    }
