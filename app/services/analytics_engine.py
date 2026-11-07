"""
Realistic Retail Margin Pricing Engine (MODULE 2)
Calculates fair retail price benchmarks accounting for legitimate kirana merchant margins (20-25%),
transportation, freight, and shop overheads, preventing false overcharging alerts against wholesale APMC rates.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models import GroceryTrip, TripItem, ProductCatalog, SavedGroceryList
from app.services.regex_parser import normalize_canonical_commodity
import datetime

def calculate_handling_freight(commodity_name: str) -> float:
    """
    Computes freight and handling overhead in INR per unit based on commodity characteristics.
    """
    c_lower = commodity_name.lower()
    if any(k in c_lower for k in ["तेल", "oil", "तूप", "ghee"]):
        return 7.0  # Pouch/tin leak-proof transport & storage overhead
    elif any(k in c_lower for k in ["साबुदाणा", "sabudana", "शाबू"]):
        return 3.0  # Clean dry granule bagging & freight
    elif any(k in c_lower for k in ["डाळ", "dal", "तांदूळ", "गहू", "पीठ", "साखर", "sugar", "रवा", "शेंगदाणे"]):
        return 4.0  # Heavy sack transport, weighment, dusting loss
    elif any(k in c_lower for k in ["मसाले", "हळद", "जिरे", "मोहरी", "मीठ", "salt"]):
        return 3.0  # Small packet logistics
    return 3.0

def calculate_fair_retail_baseline(
    mandi_base_rate: float,
    commodity_name: str = "",
    unit: str = "kg",
    retail_margin_pct: float = 0.22
) -> float:
    """
    3-tier retail baseline formula:
    fair_retail_baseline = mandi_base_rate * (1 + 0.22) + handling_freight
    """
    freight = calculate_handling_freight(commodity_name)
    fair_rate = round(mandi_base_rate * (1.0 + retail_margin_pct) + freight, 2)
    return fair_rate

def evaluate_margin_indicator(
    billed_rate: float,
    fair_retail_baseline: float
) -> Dict[str, Any]:
    """
    Dynamic Margin Indicators:
    1. billed_rate < fair_retail_baseline - 5: "सवलत / उत्तम ऑफर (Good Deal)" (green badge)
    2. billed_rate <= fair_retail_baseline + 5: "वाजवी दर (Fair Retail Price)" (neutral/green badge)
    3. billed_rate > fair_retail_baseline + 10: "अपेक्षित दरापेक्षा जास्त" (red variance alert)
    4. fair_retail_baseline + 5 < billed_rate <= fair_retail_baseline + 10: "अल्प वाढ (Moderate Variance)"
    """
    variance = round(billed_rate - fair_retail_baseline, 2)

    if billed_rate < fair_retail_baseline - 5.0:
        return {
            "status": "deal",
            "indicator": "सवलत / उत्तम ऑफर (Good Deal)",
            "remark": "बचत",
            "badge_color": "green",
            "variance": variance,
            "is_fair": True,
            "savings": abs(variance)
        }
    elif billed_rate <= fair_retail_baseline + 5.0:
        return {
            "status": "fair",
            "indicator": "वाजवी दर (Fair Retail Price)",
            "remark": "वाजवी दर",
            "badge_color": "neutral",
            "variance": variance,
            "is_fair": True,
            "savings": 0.0
        }
    elif billed_rate > fair_retail_baseline + 10.0:
        return {
            "status": "expensive",
            "indicator": "अपेक्षित दरापेक्षा जास्त",
            "remark": "महाग",
            "badge_color": "red",
            "variance": variance,
            "is_fair": False,
            "savings": 0.0
        }
    else:
        # Between +5 and +10: mild premium
        return {
            "status": "moderate",
            "indicator": "अपेक्षित दरापेक्षा किंचित जास्त",
            "remark": "किंचित महाग",
            "badge_color": "orange",
            "variance": variance,
            "is_fair": False,
            "savings": 0.0
        }

def analyze_item_retail_pricing(
    commodity_name: str,
    mandi_rate: float,
    billed_rate: float,
    quantity: float = 1.0,
    unit: str = "kg"
) -> Dict[str, Any]:
    """
    Complete analysis for a single line item comparing wholesale mandi rate,
    fair retail price, and billed shopkeeper rate.
    """
    fair_rate = calculate_fair_retail_baseline(mandi_rate, commodity_name, unit)
    margin_eval = evaluate_margin_indicator(billed_rate, fair_rate)

    mandi_amount = round(mandi_rate * quantity, 2)
    fair_amount = round(fair_rate * quantity, 2)
    billed_amount = round(billed_rate * quantity, 2)
    variance_amount = round(billed_amount - fair_amount, 2)
    variance_pct = round((variance_amount / fair_amount) * 100.0, 2) if fair_amount > 0 else 0.0

    return {
        "commodity_name": commodity_name,
        "quantity": quantity,
        "unit": unit,
        "mandi_base_rate": mandi_rate,
        "mandi_amount": mandi_amount,
        "fair_retail_rate": fair_rate,
        "fair_retail_amount": fair_amount,
        "billed_rate": billed_rate,
        "billed_amount": billed_amount,
        "variance_amount": variance_amount,
        "variance_percentage": variance_pct,
        "margin_indicator": margin_eval["indicator"],
        "margin_status": margin_eval["status"],
        "badge_color": margin_eval["badge_color"],
        "remark": margin_eval["remark"],
        "is_fair": margin_eval["is_fair"]
    }

def calculate_live_3way_audit(
    commodity_name: str,
    live_mandi_rate: float,
    live_retail_shelf_rate: float,
    billed_rate: Optional[float] = None,
    quantity: float = 1.0,
    unit: str = "kg"
) -> Dict[str, Any]:
    """
    MODULE 2: Real-Time 3-Way Financial Audit Pipeline with Live Grounded Baselines.
    1. live_mandi_rate: Live verified APMC wholesale procurement price per unit from web search.
    2. fair_retail: Calculated dynamically as live_mandi_rate * 1.22 + handling_freight.
    3. store_rate: Actual billed rate from counter or live web retail shelf rate.

    Calculates:
    - दुकानदाराचा निव्वळ नफा (Shopkeeper Net Margin): store_rate - live_mandi_rate
    - ग्राहकाची खरी तफावत (Customer Real Variance): store_rate - fair_retail
    """
    freight = calculate_handling_freight(commodity_name)
    fair_retail = round(live_mandi_rate * 1.22 + freight, 2)
    store_rate = round(float(billed_rate) if (billed_rate is not None and billed_rate > 0) else live_retail_shelf_rate, 2)

    # Unit Normalization: Scale down grams/ml to standard base unit (kg/ltr) to prevent inflated totals
    unit_str = str(unit or "").strip().lower()
    norm_qty = float(quantity)
    if unit_str in ["ग्रॅम", "gm", "gram", "grams", "g"]:
        norm_qty = norm_qty / 1000.0
    elif unit_str in ["मिली", "ml", "milli"]:
        norm_qty = norm_qty / 1000.0
    elif unit_str in ["क्विंटल", "quintal"]:
        norm_qty = norm_qty * 100.0

    is_liquid = any(k in commodity_name.lower() for k in ["तेल", "oil", "तूप", "ghee", "दूध", "milk"])
    standard_base_unit = "लिटर" if is_liquid else "किलो"

    shopkeeper_net_profit = round(store_rate - live_mandi_rate, 2)
    customer_variance = round(store_rate - fair_retail, 2)

    shopkeeper_profit_pct = round((shopkeeper_net_profit / live_mandi_rate) * 100.0, 2) if live_mandi_rate > 0 else 0.0
    customer_variance_pct = round((customer_variance / fair_retail) * 100.0, 2) if fair_retail > 0 else 0.0

    mandi_total = round(live_mandi_rate * norm_qty, 2)
    fair_total = round(fair_retail * norm_qty, 2)
    store_total = round(store_rate * norm_qty, 2)
    total_customer_variance = round(store_total - fair_total, 2)
    total_shopkeeper_profit = round(store_total - mandi_total, 2)

    margin_eval = evaluate_margin_indicator(store_rate, fair_retail)

    return {
        "commodity": commodity_name,
        "quantity": quantity,
        "unit": unit,
        "standard_base_unit": standard_base_unit,
        "normalized_quantity": norm_qty,
        "live_mandi_rate": live_mandi_rate,
        "mandi_total": mandi_total,
        "row_apmc_total": mandi_total,
        "fair_retail_rate": fair_retail,
        "fair_total": fair_total,
        "row_fair_total": fair_total,
        "store_rate": store_rate,
        "store_total": store_total,
        "row_store_total": store_total,
        "shopkeeper_net_profit": shopkeeper_net_profit,
        "shopkeeper_profit_percentage": shopkeeper_profit_pct,
        "total_shopkeeper_profit": total_shopkeeper_profit,
        "customer_variance": customer_variance,
        "customer_variance_percentage": customer_variance_pct,
        "total_customer_variance": total_customer_variance,
        "margin_indicator": margin_eval["indicator"],
        "margin_status": margin_eval["status"],
        "badge_color": margin_eval["badge_color"],
        "remark": margin_eval["remark"],
        "is_fair": margin_eval["is_fair"]
    }

def get_festival_countdown_advisory(ref_date: Optional[Any] = None) -> Dict[str, Any]:
    """
    MODULE 6: Dynamic Festival Countdown & Surge Advisory.
    Calculates remaining days dynamically: (target_date - datetime.date.today()).days.
    Never returns static '0 days remaining'.
    """
    import datetime
    if ref_date is None:
        ref_date = datetime.date.today()
    elif isinstance(ref_date, str):
        ref_date = datetime.date.fromisoformat(ref_date)

    cur_year = ref_date.year
    festivals = [
        {"name": "मकर संक्रांती", "month": 1, "day": 14, "surge_oil": 10.0, "surge_sugar": 3.0},
        {"name": "गुढीपाडवा व चैत्र उत्सव", "month": 3, "day": 25, "surge_oil": 10.0, "surge_sugar": 2.0},
        {"name": "गणेशोत्सव", "month": 9, "day": 10, "surge_oil": 15.0, "surge_sugar": 3.0},
        {"name": "नवरात्रोत्सव व दसरा", "month": 10, "day": 15, "surge_oil": 18.0, "surge_sugar": 4.0},
        {"name": "दिवाळी व भाऊबीज", "month": 11, "day": 12, "surge_oil": 20.0, "surge_sugar": 5.0},
        {"name": "लग्नसराई व हिवाळी हंगाम", "month": 11, "day": 25, "surge_oil": 15.0, "surge_sugar": 3.0},
    ]

    upcoming = []
    for f in festivals:
        f_date = datetime.date(cur_year, f["month"], f["day"])
        days_left = (f_date - ref_date).days
        if days_left >= 0:
            upcoming.append((days_left, f, f_date))
        else:
            f_date_next = datetime.date(cur_year + 1, f["month"], f["day"])
            days_left_next = (f_date_next - ref_date).days
            upcoming.append((days_left_next, f, f_date_next))

    upcoming.sort(key=lambda x: x[0])
    days_left, active_fest, target_f_date = upcoming[0]

    header_title = f"{active_fest['name']} स्मार्ट खरेदी सल्ला ({days_left} दिवस बाकी)"
    advice_text = (
        f"💡 {active_fest['name']} सल्ला: पुढील दिवसांत खाद्यतेल व साखरेचे भाव वाढण्याची शक्यता आहे. "
        f"अंदाजे {days_left} दिवस शिल्लक आहेत. आधीच खरेदी केल्यास ₹१५० ते ₹२०० पर्यंत बचत शक्य आहे."
    )

    return {
        "festival_name": active_fest["name"],
        "days_left": days_left,
        "days_until": days_left,
        "header_title": header_title,
        "target_date": target_f_date.isoformat(),
        "advice_card_mr": advice_text,
        "affected_commodities": ["गोडतेल", "शेंगदाणा तेल", "साखर", "काजू", "बदाम", "रवा", "बेसन"]
    }


# ==============================================================================
# PILLARS 1 & 3: INTERNAL TIME-SERIES PREDICTIVE ENGINE & HISTORICAL AUDIT
# ==============================================================================

def get_commodity_historical_benchmark(db: Session, commodity_name: str, unit: str = "kg") -> Dict[str, Any]:
    """
    PILLAR 1: Strictly queries the user's internal historical purchase database.
    Never queries external Google Search Grounding, Wikipedia, or external scrapers.
    If no prior record exists: previous_rate = None (displays as "-"), badge = "नवीन वस्तू (इतिहास उपलब्ध नाही)".
    """
    norm_name = normalize_canonical_commodity(commodity_name)

    records = (
        db.query(TripItem, GroceryTrip)
        .join(GroceryTrip, TripItem.trip_id == GroceryTrip.trip_id)
        .outerjoin(ProductCatalog, TripItem.sku_id == ProductCatalog.sku_id)
        .filter(
            (ProductCatalog.marathi_name == commodity_name) |
            (ProductCatalog.canonical_name == commodity_name) |
            (ProductCatalog.marathi_name == norm_name) |
            (TripItem.raw_input.ilike(f"%{commodity_name}%")) |
            (TripItem.raw_input.ilike(f"%{norm_name}%"))
        )
        .order_by(GroceryTrip.trip_date.asc())
        .all()
    )

    if not records:
        return {
            "has_history": False,
            "commodity_name": commodity_name,
            "previous_rate": None,
            "previous_rate_display": "-",
            "badge": "नवीन वस्तू (इतिहास उपलब्ध नाही)",
            "badge_color": "neutral",
            "notice_mr": "ही वस्तू मागील खरेदी इतिहासामध्ये उपलब्ध नाही (नवीन वस्तू).",
            "history_points": [],
            "moving_avg": None,
            "rate_change_pct": 0.0,
            "predicted_rate": None
        }

    points = []
    rates = []
    for itm, trip in records:
        u_rate = itm.unit_base_rate if getattr(itm, "unit_base_rate", None) and itm.unit_base_rate > 0 else itm.derived_rate
        norm_q = itm.normalized_quantity if getattr(itm, "normalized_quantity", None) and itm.normalized_quantity > 0 else itm.quantity_norm
        l_total = itm.line_total_amount if getattr(itm, "line_total_amount", None) and itm.line_total_amount > 0 else itm.entered_total

        if u_rate and u_rate > 0:
            d_str = trip.purchase_date.strftime("%Y-%m-%d") if getattr(trip, "purchase_date", None) else trip.trip_date.strftime("%Y-%m-%d")
            rates.append(u_rate)
            points.append({
                "date": d_str,
                "rate": round(u_rate, 2),
                "unit_base_rate": round(u_rate, 2),
                "qty": norm_q,
                "normalized_quantity": norm_q,
                "unit": itm.unit,
                "line_total_amount": round(l_total, 2),
                "trip_id": trip.trip_id,
                "title": getattr(trip, "title", "नियमित किराणा") or "नियमित किराणा",
                "occasion_type": getattr(trip, "occasion_type", "regular") or "regular"
            })

    if not rates:
        return {
            "has_history": False,
            "commodity_name": commodity_name,
            "previous_rate": None,
            "previous_rate_display": "-",
            "badge": "नवीन वस्तू (इतिहास उपलब्ध नाही)",
            "badge_color": "neutral",
            "notice_mr": "ही वस्तू मागील खरेदी इतिहासामध्ये उपलब्ध नाही (नवीन वस्तू).",
            "history_points": [],
            "moving_avg": None,
            "rate_change_pct": 0.0,
            "predicted_rate": None
        }

    latest_rate = rates[-1]
    latest_point = points[-1]

    # Moving average and rate of change over user's recorded purchase dates
    window_rates = rates[-5:]
    moving_avg = round(sum(window_rates) / len(window_rates), 2)

    if len(rates) >= 2:
        oldest_rate = rates[0]
        rate_change_pct = round(((latest_rate - oldest_rate) / oldest_rate) * 100.0, 2)
    else:
        rate_change_pct = 0.0

    if len(rates) >= 3:
        weights = list(range(1, len(window_rates) + 1))
        weighted_sum = sum(r * w for r, w in zip(window_rates, weights))
        predicted_rate = round(weighted_sum / sum(weights), 2)
    else:
        predicted_rate = latest_rate

    badge = "संतुलित दर"
    badge_color = "neutral"
    if rate_change_pct > 5.0:
        badge = f"भाववाढ (+{rate_change_pct}%)"
        badge_color = "red"
    elif rate_change_pct < -5.0:
        badge = f"स्वस्त ({rate_change_pct}%)"
        badge_color = "green"

    return {
        "has_history": True,
        "commodity_name": commodity_name,
        "previous_rate": latest_rate,
        "previous_rate_display": f"₹{latest_rate:.2f}",
        "previous_date": latest_point["date"],
        "badge": badge,
        "badge_color": badge_color,
        "notice_mr": None,
        "history_points": points,
        "moving_avg": moving_avg,
        "rate_change_pct": rate_change_pct,
        "predicted_rate": predicted_rate
    }


def calculate_internal_receipt_audit(items: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
    """
    Pillars 1 & 3: 100% Internal Historical Audit Pipeline.
    Audits items strictly against user-owned past purchase database.
    """
    audited_items = []
    total_store = 0.0
    total_historical = 0.0
    has_any_history = False

    for idx, it in enumerate(items):
        name = it.get("commodity_name") or it.get("name") or it.get("item_name") or f"वस्तू #{idx+1}"
        qty = float(it.get("quantity") or it.get("qty") or 1.0)
        unit = str(it.get("unit") or "किलो")
        store_rate = float(it.get("billed_rate") or it.get("store_rate") or it.get("price") or 0.0)

        unit_str = unit.strip().lower()
        norm_qty = qty
        if unit_str in ["ग्रॅम", "gm", "gram", "g", "मिली", "ml"]:
            norm_qty = norm_qty / 1000.0

        item_store_total = round(store_rate * norm_qty, 2)
        total_store += item_store_total

        benchmark = get_commodity_historical_benchmark(db, name, unit)
        if benchmark["has_history"]:
            has_any_history = True
            prev_rate = benchmark["previous_rate"]
            item_hist_total = round(prev_rate * norm_qty, 2)
            total_historical += item_hist_total
            diff = round(store_rate - prev_rate, 2)
            diff_pct = round((diff / prev_rate) * 100.0, 2) if prev_rate > 0 else 0.0

            if diff > 5.0:
                badge = f"+₹{diff:.2f} भाववाढ"
                badge_cls = "badge-surge"
            elif diff < -5.0:
                badge = f"-₹{abs(diff):.2f} बचत / सवलत"
                badge_cls = "badge-dip"
            else:
                badge = "संतुलित दर"
                badge_cls = "badge-balanced"

            audited_items.append({
                "commodity": name,
                "commodity_name": name,
                "quantity": qty,
                "unit": unit,
                "store_rate": store_rate,
                "store_total": item_store_total,
                "previous_rate": prev_rate,
                "previous_rate_display": f"₹{prev_rate:.2f}",
                "previous_total": item_hist_total,
                "variance": diff,
                "variance_percentage": diff_pct,
                "badge": badge,
                "badge_class": badge_cls,
                "is_new": False,
                "has_history": True,
                "history_points": benchmark["history_points"],
                "predicted_rate": benchmark["predicted_rate"]
            })
        else:
            audited_items.append({
                "commodity": name,
                "commodity_name": name,
                "quantity": qty,
                "unit": unit,
                "store_rate": store_rate,
                "store_total": item_store_total,
                "previous_rate": None,
                "previous_rate_display": "-",
                "previous_total": None,
                "variance": None,
                "variance_percentage": None,
                "badge": "नवीन वस्तू (इतिहास उपलब्ध नाही)",
                "badge_class": "badge-new",
                "is_new": True,
                "has_history": False,
                "history_points": [],
                "predicted_rate": None
            })

    total_store = round(total_store, 2)
    total_historical = round(total_historical, 2)
    overall_variance = round(total_store - total_historical, 2) if has_any_history else 0.0
    overall_var_pct = round((overall_variance / total_historical) * 100.0, 2) if (has_any_history and total_historical > 0) else 0.0

    return {
        "status": "success",
        "items": audited_items,
        "total_store_amount": total_store,
        "total_historical_amount": total_historical if has_any_history else None,
        "overall_variance": overall_variance,
        "overall_variance_percentage": overall_var_pct,
        "has_history": has_any_history,
        "audit_source": "मागील खरेदी इतिहास (Internal Purchase Ledger)"
    }


def compute_personal_inflation_index(db: Session, buyer_id: int = 1) -> Dict[str, Any]:
    """
    Pillar 3: Personal Inflation Index.
    Calculates month-over-month shift in actual household spend across recorded purchase dates.
    """
    from collections import defaultdict
    trips = db.query(GroceryTrip).filter(GroceryTrip.buyer_id == buyer_id).order_by(GroceryTrip.trip_date.asc()).all()

    monthly_spends = defaultdict(lambda: {"total": 0.0, "count": 0})
    for t in trips:
        d = t.purchase_date if getattr(t, "purchase_date", None) else t.trip_date
        m_key = d.strftime("%Y-%m")
        monthly_spends[m_key]["total"] += t.settled_total
        monthly_spends[m_key]["count"] += 1

    months = sorted(monthly_spends.keys())
    inflation_series = []
    prev_avg = None
    for m in months:
        data = monthly_spends[m]
        avg_spend = round(data["total"] / data["count"], 2) if data["count"] > 0 else 0.0
        mom_pct = round(((avg_spend - prev_avg) / prev_avg) * 100.0, 2) if (prev_avg and prev_avg > 0) else 0.0
        inflation_series.append({
            "month": m,
            "total_spend": round(data["total"], 2),
            "trips_count": data["count"],
            "avg_spend_per_trip": avg_spend,
            "mom_inflation_pct": mom_pct
        })
        prev_avg = avg_spend

    overall_inflation = inflation_series[-1]["mom_inflation_pct"] if inflation_series else 0.0
    return {
        "status": "success",
        "months_tracked": len(months),
        "overall_inflation_pct": overall_inflation,
        "series": inflation_series
    }


def query_seasonal_event_replay(db: Session, occasion: str = "", occasion_type: str = "festive") -> Dict[str, Any]:
    """
    Pillar 3: Seasonal / Event Replay.
    When a user initiates a festive/event list (e.g., "दिवाळी फराळ"),
    query the previous year's list under that same occasion title/type and suggest matching items and quantities.
    """
    query = db.query(GroceryTrip).order_by(GroceryTrip.trip_date.desc())
    if occasion:
        query = query.filter(GroceryTrip.title.ilike(f"%{occasion}%"))
    elif occasion_type and occasion_type != "regular":
        query = query.filter(GroceryTrip.occasion_type == occasion_type)

    trip = query.first()
    if trip and trip.items:
        items = []
        for it in trip.items:
            prod_name = it.product.marathi_name if it.product else (it.raw_input or f"वस्तू #{it.item_id}")
            norm_q = it.normalized_quantity if getattr(it, "normalized_quantity", None) and it.normalized_quantity > 0 else it.quantity_norm
            u_rate = it.unit_base_rate if getattr(it, "unit_base_rate", None) and it.unit_base_rate > 0 else it.derived_rate
            l_total = it.line_total_amount if getattr(it, "line_total_amount", None) and it.line_total_amount > 0 else it.entered_total
            items.append({
                "name": prod_name,
                "commodity_name": prod_name,
                "qty": norm_q,
                "quantity": norm_q,
                "normalized_quantity": norm_q,
                "unit": it.unit,
                "previous_rate": u_rate,
                "price": u_rate,
                "unit_base_rate": u_rate,
                "entered_total": l_total,
                "line_total_amount": l_total
            })
        d_str = trip.purchase_date.strftime("%d-%m-%Y") if getattr(trip, "purchase_date", None) else trip.trip_date.strftime("%d-%m-%Y")
        return {
            "found": True,
            "event_title": getattr(trip, "title", occasion) or occasion,
            "occasion_type": getattr(trip, "occasion_type", occasion_type),
            "event_date": d_str,
            "total_items": len(items),
            "suggested_items": items
        }

    q_saved = db.query(SavedGroceryList).order_by(SavedGroceryList.created_at.desc())
    if occasion:
        q_saved = q_saved.filter((SavedGroceryList.title.ilike(f"%{occasion}%")) | (SavedGroceryList.list_name.ilike(f"%{occasion}%")))
    elif occasion_type and occasion_type != "regular":
        q_saved = q_saved.filter(SavedGroceryList.occasion_type == occasion_type)

    saved = q_saved.first()
    if saved and saved.items_payload:
        d_str = saved.purchase_date.strftime("%d-%m-%Y") if getattr(saved, "purchase_date", None) else saved.created_at.strftime("%d-%m-%Y")
        return {
            "found": True,
            "event_title": getattr(saved, "title", saved.list_name) or occasion,
            "occasion_type": getattr(saved, "occasion_type", occasion_type),
            "event_date": d_str,
            "total_items": len(saved.items_payload),
            "suggested_items": saved.items_payload
        }

    return {
        "found": False,
        "event_title": occasion,
        "occasion_type": occasion_type,
        "event_date": None,
        "total_items": 0,
        "suggested_items": []
    }


