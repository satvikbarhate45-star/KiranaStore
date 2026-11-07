import datetime
import uuid
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models import GroceryTrip, TripItem, ProductCatalog, KiranaTripAnalytics, CachedCommodityPrice
from app.schemas import (
    SimulatorRequest,
    SimulatorResponse,
    SimulatedItemResult,
    MarketRateItem,
    MarketRatesResponse,
    Audit3WayRequest,
    Audit3WayResponse,
    TripAnalyticsCreate,
    TripAnalyticsResponse,
    ItemVarianceAudit,
    CommodityAuditPredictionResponse
)
from app.services.regex_parser import normalize_canonical_commodity, extract_brand_and_commodity
from app.services.volatility_engine import get_rolling_median_baseline, get_display_unit
from app.services.gov_price_service import (
    get_commodity_market_rate,
    get_all_benchmark_rates,
    calculate_govt_expected_total,
    get_festival_surge_advice
)
from app.services.analytics_engine import (
    calculate_fair_retail_baseline,
    evaluate_margin_indicator,
    analyze_item_retail_pricing
)

router = APIRouter(prefix="/api/v1/analyzer", tags=["Analyzer"])

@router.get("/trends")
def get_price_trends(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db)
):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    # Query items in date range
    recent_items = (
        db.query(TripItem, GroceryTrip.trip_date)
        .join(GroceryTrip, GroceryTrip.trip_id == TripItem.trip_id)
        .filter(GroceryTrip.trip_date >= cutoff, GroceryTrip.status == "settled")
        .order_by(GroceryTrip.trip_date.asc())
        .all()
    )

    # Group by SKU
    sku_history: Dict[int, List[Dict]] = {}
    for item, trip_date in recent_items:
        if item.sku_id not in sku_history:
            sku_history[item.sku_id] = []
        u_rate = float(item.unit_base_rate if getattr(item, "unit_base_rate", None) and item.unit_base_rate > 0 else item.derived_rate)
        l_total = float(item.line_total_amount if getattr(item, "line_total_amount", None) and item.line_total_amount > 0 else item.entered_total)
        n_qty = float(item.normalized_quantity if getattr(item, "normalized_quantity", None) and item.normalized_quantity > 0 else item.quantity_norm)
        sku_history[item.sku_id].append({
            "date": trip_date.strftime("%Y-%m-%d"),
            "rate": u_rate,
            "unit_base_rate": u_rate,
            "total": l_total,
            "line_total_amount": l_total,
            "qty": n_qty,
            "normalized_quantity": n_qty,
            "unit": item.unit
        })

    surges = []
    dips = []
    series_data = []

    for sku_id, records in sku_history.items():
        prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == sku_id).first()
        if not prod or len(records) < 2:
            continue

        first_rate = records[0]["rate"]
        last_rate = records[-1]["rate"]
        pct_change = round(((last_rate - first_rate) / first_rate) * 100.0, 2)
        diff_val = round(last_rate - first_rate, 2)

        entry = {
            "sku_id": sku_id,
            "name": prod.marathi_name,
            "unit": get_display_unit(prod.canonical_unit),
            "old_rate": first_rate,
            "new_rate": last_rate,
            "diff_amount": diff_val,
            "pct_change": pct_change,
            "records_count": len(records)
        }

        if pct_change > 2.0:
            surges.append(entry)
        elif pct_change < -1.0:
            dips.append(entry)

        # Build chart series (first 6 prominent products)
        if len(series_data) < 6:
            series_data.append({
                "sku_id": sku_id,
                "name": prod.marathi_name,
                "unit": get_display_unit(prod.canonical_unit),
                "points": [{"date": r["date"], "rate": r["rate"]} for r in records]
            })

    surges.sort(key=lambda x: x["pct_change"], reverse=True)
    dips.sort(key=lambda x: x["pct_change"])

    return {
        "days": days,
        "surges": surges[:8],
        "dips": dips[:8],
        "series": series_data
    }

@router.post("/simulate", response_model=SimulatorResponse)
def simulate_grocery_budget(req: SimulatorRequest, db: Session = Depends(get_db)):
    if not req.items:
        raise HTTPException(status_code=400, detail="सिम्युलेटरसाठी किमान एक वस्तू निवडा.")

    from app.services.simulator_service import simulate_budget_pipeline
    raw_items = [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in req.items]
    buyer_id = getattr(req, "buyer_id", None) or settings.DEFAULT_BUYER_ID
    sim_data = simulate_budget_pipeline(db, raw_items, buyer_id=buyer_id)

    results: List[SimulatedItemResult] = [
        SimulatedItemResult(
            sku_id=it["sku_id"],
            marathi_name=it["marathi_name"],
            quantity=it["quantity"],
            unit=it["unit"],
            display_unit=it["display_unit"],
            baseline_unit_rate=it["baseline_unit_rate"],
            estimated_total=it["estimated_total"],
            confidence_range_low=it["confidence_range_low"],
            confidence_range_high=it["confidence_range_high"],
            has_history=it["has_history"],
            manual_price_required=it["manual_price_required"],
            manual_price=it["manual_price"]
        )
        for it in sim_data["items"]
    ]

    return SimulatorResponse(
        total_estimated=sim_data["total_estimated"],
        total_range_low=sim_data["total_range_low"],
        total_range_high=sim_data["total_range_high"],
        items=results,
        has_missing_history=sim_data["has_missing_history"],
        missing_items_count=sim_data["missing_items_count"],
        notice_mr=sim_data["notice_mr"]
    )

@router.get("/compare-trips")
def compare_trips(
    trip_a_id: int = Query(..., description="First trip ID"),
    trip_b_id: int = Query(..., description="Second trip ID"),
    db: Session = Depends(get_db)
):
    trip_a = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip_a_id).first()
    trip_b = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip_b_id).first()

    if not trip_a or not trip_b:
        raise HTTPException(status_code=404, detail="तुलनेसाठी निवडलेली खरेदी नोंद सापडली नाही.")

    items_a = {it.sku_id: it for it in trip_a.items}
    items_b = {it.sku_id: it for it in trip_b.items}

    all_skus = set(items_a.keys()).union(set(items_b.keys()))
    comparison_rows = []

    for sku_id in all_skus:
        prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == sku_id).first()
        p_name = prod.marathi_name if prod else f"वस्तू #{sku_id}"
        p_unit = get_display_unit(prod.canonical_unit) if prod else "युनिट"

        it_a = items_a.get(sku_id)
        it_b = items_b.get(sku_id)

        rate_a = (it_a.unit_base_rate if getattr(it_a, "unit_base_rate", None) and it_a.unit_base_rate > 0 else it_a.derived_rate) if it_a else None
        rate_b = (it_b.unit_base_rate if getattr(it_b, "unit_base_rate", None) and it_b.unit_base_rate > 0 else it_b.derived_rate) if it_b else None
        qty_a = (it_a.normalized_quantity if getattr(it_a, "normalized_quantity", None) and it_a.normalized_quantity > 0 else it_a.quantity_norm) if it_a else None
        qty_b = (it_b.normalized_quantity if getattr(it_b, "normalized_quantity", None) and it_b.normalized_quantity > 0 else it_b.quantity_norm) if it_b else None
        total_a = (it_a.line_total_amount if getattr(it_a, "line_total_amount", None) and it_a.line_total_amount > 0 else it_a.entered_total) if it_a else None
        total_b = (it_b.line_total_amount if getattr(it_b, "line_total_amount", None) and it_b.line_total_amount > 0 else it_b.entered_total) if it_b else None

        var_pct = None
        rate_diff = None
        if rate_a and rate_b and rate_a > 0:
            var_pct = round(((rate_b - rate_a) / rate_a) * 100.0, 2)
            rate_diff = round(rate_b - rate_a, 2)

        comparison_rows.append({
            "sku_id": sku_id,
            "name": p_name,
            "unit": p_unit,
            "trip_a_qty": qty_a,
            "trip_a_rate": rate_a,
            "trip_a_unit_base_rate": rate_a,
            "trip_a_total": total_a,
            "trip_a_line_total": total_a,
            "trip_b_qty": qty_b,
            "trip_b_rate": rate_b,
            "trip_b_unit_base_rate": rate_b,
            "trip_b_total": total_b,
            "trip_b_line_total": total_b,
            "rate_diff": rate_diff,
            "var_pct": var_pct
        })

    basket_diff = round(trip_b.settled_total - trip_a.settled_total, 2)
    basket_var_pct = round(((trip_b.settled_total - trip_a.settled_total) / trip_a.settled_total) * 100.0, 2) if trip_a.settled_total > 0 else 0.0

    return {
        "trip_a": {
            "id": trip_a.trip_id,
            "date": trip_a.trip_date.strftime("%d-%m-%Y"),
            "merchant": trip_a.merchant_name,
            "total": trip_a.settled_total
        },
        "trip_b": {
            "id": trip_b.trip_id,
            "date": trip_b.trip_date.strftime("%d-%m-%Y"),
            "merchant": trip_b.merchant_name,
            "total": trip_b.settled_total
        },
        "basket_diff": basket_diff,
        "basket_var_pct": basket_var_pct,
        "rows": comparison_rows
    }


# ==============================================================================
# MODULE 3 & 4: ZERO-KYC APMC RATES & CLOSED-LOOP 3-WAY COMPARATIVE AUDIT API
# ==============================================================================

@router.get("/market-rates", response_model=MarketRatesResponse)
def get_market_rates(db: Session = Depends(get_db)):
    """
    Returns Maharashtra APMC retail benchmark rates for staples without requiring KYC.
    """
    raw_rates = get_all_benchmark_rates(db)
    items = []
    for r in raw_rates:
        items.append(MarketRateItem(
            commodity_name=r["commodity_name"],
            canonical_unit=r["canonical_unit"],
            retail_modal_rate=r["retail_modal_rate"],
            min_price=r.get("min_price"),
            max_price=r.get("max_price"),
            source=r["source"],
            market_location=r["market_location"],
            last_updated=r["last_updated"],
            is_live_grounded=(r["source"] == "gemini_search_grounding")
        ))
    return MarketRatesResponse(
        state="Maharashtra",
        source="Maharashtra APMC Modal Retail Benchmark Engine",
        rates=items
    )

@router.post("/audit-3way", response_model=Audit3WayResponse)
def audit_3way_session(req: Audit3WayRequest, db: Session = Depends(get_db)):
    """
    Computes 3-way Closed-Loop Price Variance:
    1. Baseline (Govt APMC retail modal rate).
    2. Counter Reality (Shopkeeper's entered rate/amount).
    3. Settlement (UPI paid amount).
    """
    session_id = req.session_id or str(uuid.uuid4())
    govt_calc = calculate_govt_expected_total(db, req.items)
    govt_total = govt_calc["govt_total_amount"]
    govt_breakdown = govt_calc["items_breakdown"]

    shopkeeper_total = 0.0
    fair_retail_total = 0.0
    item_audits: List[ItemVarianceAudit] = []

    for idx, item in enumerate(req.items):
        g_info = govt_breakdown[idx] if idx < len(govt_breakdown) else {}
        g_rate = g_info.get("govt_rate", 50.0)
        g_amount = g_info.get("govt_amount", 50.0)

        raw_name = item.get("name") or item.get("item_name") or g_info.get("name") or f"वस्तू {idx+1}"
        qty = float(item.get("qty") or item.get("quantity") or 1.0)
        norm_qty = float(item.get("quantity_norm") or qty)
        unit = str(item.get("unit") or item.get("canonical_unit") or "kg")

        # MODULE 2: Realistic Retail Margin Pricing Formula
        fair_rate = calculate_fair_retail_baseline(g_rate, raw_name, unit)
        fair_amount = round(fair_rate * norm_qty, 2)
        fair_retail_total += fair_amount

        # Shopkeeper values
        entered_tot = float(item.get("enteredTotal") or item.get("entered_total") or 0.0)
        if entered_tot <= 0 and item.get("shopkeeper_rate"):
            entered_tot = round(float(item.get("shopkeeper_rate")) * norm_qty, 2)
        elif entered_tot <= 0 and item.get("target_price"):
            entered_tot = float(item.get("target_price"))

        shopkeeper_total += entered_tot
        s_rate = round(entered_tot / norm_qty, 2) if norm_qty > 0 else 0.0

        # Evaluate margin indicators against fair retail price
        margin_eval = evaluate_margin_indicator(s_rate, fair_rate)

        var_amount = round(entered_tot - fair_amount, 2)
        var_pct = round(((entered_tot - fair_amount) / fair_amount) * 100.0, 2) if fair_amount > 0 else 0.0

        item_audits.append(ItemVarianceAudit(
            item_index=idx,
            name=raw_name,
            quantity=qty,
            unit=unit,
            govt_rate=g_rate,
            govt_amount=g_amount,
            fair_retail_rate=fair_rate,
            fair_retail_amount=fair_amount,
            shopkeeper_rate=s_rate,
            shopkeeper_amount=entered_tot,
            margin_indicator=margin_eval["indicator"],
            margin_status=margin_eval["status"],
            variance_amount=var_amount,
            variance_percentage=var_pct,
            remark=margin_eval["remark"]
        ))

    final_shopkeeper_total = req.shopkeeper_total if (req.shopkeeper_total is not None and req.shopkeeper_total > 0) else round(shopkeeper_total, 2)
    upi_settled = req.upi_settled_amount if (req.upi_settled_amount is not None and req.upi_settled_amount > 0) else final_shopkeeper_total

    fair_retail_total_round = round(fair_retail_total, 2)
    total_var_amount = round(final_shopkeeper_total - fair_retail_total_round, 2)
    var_percentage = round(((final_shopkeeper_total - fair_retail_total_round) / fair_retail_total_round) * 100.0, 2) if fair_retail_total_round > 0 else 0.0

    is_inflated = total_var_amount > 5.0
    savings_amount = abs(total_var_amount) if total_var_amount < -5.0 else 0.0

    if final_shopkeeper_total <= fair_retail_total_round + 5.0:
        if final_shopkeeper_total < fair_retail_total_round - 5.0:
            badge_label = f"₹{abs(total_var_amount):.2f} सवलत / उत्तम ऑफर (Good Deal)"
        else:
            badge_label = "वाजवी दर (Fair Retail Price)"
    elif total_var_amount > 10.0:
        badge_label = f"+₹{abs(total_var_amount):.2f} (+{var_percentage}%) अपेक्षित दरापेक्षा जास्त"
    else:
        badge_label = "वाजवी दर (किंचित फरक)"

    return Audit3WayResponse(
        session_id=session_id,
        govt_total_amount=govt_total,
        fair_retail_total_amount=fair_retail_total_round,
        shopkeeper_total_amount=final_shopkeeper_total,
        upi_settled_amount=upi_settled,
        total_variance_amount=total_var_amount,
        variance_percentage=var_percentage,
        badge_label=badge_label,
        is_inflated=is_inflated,
        savings_amount=savings_amount,
        items_breakdown=item_audits
    )


@router.get("/festival-surge-advice")
def get_festival_surge_recommendations():
    """
    MODULE 6: Festival Surge Predictor & Bulk Stocking Advice.
    Returns impending festival price spikes and actionable savings alert card.
    """
    return get_festival_surge_advice()

@router.post("/save-trip-analytics", response_model=TripAnalyticsResponse)
def save_trip_analytics(data: TripAnalyticsCreate, db: Session = Depends(get_db)):
    """
    Saves completed session analytics to PostgreSQL/SQLite kirana_trip_analytics table.
    """
    # Calculate variances
    total_var = round(data.shopkeeper_total_amount - data.govt_total_amount, 2)
    var_pct = round((total_var / data.govt_total_amount) * 100.0, 2) if data.govt_total_amount > 0 else 0.0

    existing = db.query(KiranaTripAnalytics).filter(KiranaTripAnalytics.session_id == data.session_id).first()
    if existing:
        existing.govt_total_amount = data.govt_total_amount
        existing.shopkeeper_total_amount = data.shopkeeper_total_amount
        existing.upi_settled_amount = data.upi_settled_amount
        existing.total_variance_amount = total_var
        existing.variance_percentage = var_pct
        if data.items_breakdown:
            existing.items_breakdown = data.items_breakdown
        db.commit()
        db.refresh(existing)
        c_str = existing.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(existing.created_at, "strftime") else str(existing.created_at)
        return TripAnalyticsResponse(
            analytics_id=existing.analytics_id,
            session_id=existing.session_id,
            govt_total_amount=existing.govt_total_amount,
            shopkeeper_total_amount=existing.shopkeeper_total_amount,
            upi_settled_amount=existing.upi_settled_amount,
            total_variance_amount=existing.total_variance_amount,
            variance_percentage=existing.variance_percentage,
            items_breakdown=existing.items_breakdown,
            created_at=c_str
        )

    new_rec = KiranaTripAnalytics(
        session_id=data.session_id,
        buyer_id=settings.DEFAULT_BUYER_ID,
        govt_total_amount=data.govt_total_amount,
        shopkeeper_total_amount=data.shopkeeper_total_amount,
        upi_settled_amount=data.upi_settled_amount,
        total_variance_amount=total_var,
        variance_percentage=var_pct,
        items_breakdown=data.items_breakdown or []
    )
    db.add(new_rec)
    db.commit()
    db.refresh(new_rec)

    c_str = new_rec.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(new_rec.created_at, "strftime") else str(new_rec.created_at)
    return TripAnalyticsResponse(
        analytics_id=new_rec.analytics_id,
        session_id=new_rec.session_id,
        govt_total_amount=new_rec.govt_total_amount,
        shopkeeper_total_amount=new_rec.shopkeeper_total_amount,
        upi_settled_amount=new_rec.upi_settled_amount,
        total_variance_amount=new_rec.total_variance_amount,
        variance_percentage=new_rec.variance_percentage,
        items_breakdown=new_rec.items_breakdown,
        created_at=c_str
    )

@router.get("/trip-analytics", response_model=List[TripAnalyticsResponse])
def list_trip_analytics(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Retrieves past trip analytics sessions."""
    records = db.query(KiranaTripAnalytics).order_by(KiranaTripAnalytics.created_at.desc()).limit(limit).all()
    results = []
    for r in records:
        c_str = r.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(r.created_at, "strftime") else str(r.created_at)
        results.append(TripAnalyticsResponse(
            analytics_id=r.analytics_id,
            session_id=r.session_id,
            govt_total_amount=r.govt_total_amount,
            shopkeeper_total_amount=r.shopkeeper_total_amount,
            upi_settled_amount=r.upi_settled_amount,
            total_variance_amount=r.total_variance_amount,
            variance_percentage=r.variance_percentage,
            items_breakdown=r.items_breakdown,
            created_at=c_str
        ))
    return results

@router.get("/trip-analytics/{session_id}", response_model=TripAnalyticsResponse)
def get_single_trip_analytics(session_id: str, db: Session = Depends(get_db)):
    """Retrieves analytics record for a specific session."""
    r = db.query(KiranaTripAnalytics).filter(KiranaTripAnalytics.session_id == session_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="सदर खरेदीचे दर विश्लेषण सापडले नाही.")
    c_str = r.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(r.created_at, "strftime") else str(r.created_at)
    return TripAnalyticsResponse(
        analytics_id=r.analytics_id,
        session_id=r.session_id,
        govt_total_amount=r.govt_total_amount,
        shopkeeper_total_amount=r.shopkeeper_total_amount,
        upi_settled_amount=r.upi_settled_amount,
        total_variance_amount=r.total_variance_amount,
        variance_percentage=r.variance_percentage,
        items_breakdown=r.items_breakdown,
        created_at=c_str
    )


# ==============================================================================
# DYNAMIC COMMODITY 3-WAY AUDIT ENGINE & INSTANT SEARCH API
# ==============================================================================

@router.get("/historical-commodities", response_model=List[str])
def get_historical_commodities(db: Session = Depends(get_db)):
    """
    Returns a distinct list of commodity names across historical sessions,
    the product catalog, and local APMC mandi benchmarks for the Smart Autocomplete Input.
    """
    commodities_set = set()
    
    # 1. Product catalog
    for p in db.query(ProductCatalog).filter(ProductCatalog.is_active == True).all():
        if p.marathi_name:
            commodities_set.add(p.marathi_name)
        if p.aliases and isinstance(p.aliases, list):
            for al in p.aliases:
                if isinstance(al, str) and len(al.strip()) > 1:
                    commodities_set.add(al.strip())

    # 2. Past trips
    trip_items = db.query(TripItem).limit(100).all()
    for ti in trip_items:
        if ti.product and ti.product.marathi_name:
            commodities_set.add(ti.product.marathi_name)
        if ti.raw_input:
            commodities_set.add(ti.raw_input.split()[0])

    # 3. Trip analytics breakdown
    analytics = db.query(KiranaTripAnalytics).order_by(KiranaTripAnalytics.created_at.desc()).limit(20).all()
    for a in analytics:
        if a.items_breakdown and isinstance(a.items_breakdown, list):
            for it in a.items_breakdown:
                name = it.get("name") or it.get("item_name")
                if name:
                    commodities_set.add(name)

    # 4. Standard Maharashtra staples
    staples = [
        "साखर", "गोडतेल", "शेंगदाणा तेल", "शेंगदाणे", "तूर डाळ", "तांदूळ", "गव्हाचे पीठ",
        "रवा", "चना डाळ", "चणा डाळ", "मूग डाळ", "कांदा", "बटाटा", "पोहे", "गूळ", "बेसन",
        "हळद", "जिरे", "मोहरी", "मीठ", "चहा पावडर", "अगरबत्ती", "साबण", "कापूर", "वाती"
    ]
    for s in staples:
        commodities_set.add(s)

    sorted_list = sorted(list(commodities_set))
    return sorted_list


@router.get("/commodity-audit", response_model=CommodityAuditPredictionResponse)
def get_commodity_audit_prediction(
    commodity: str = Query(..., description="Commodity name to audit"),
    quantity: float = Query(1.0, ge=0.01, description="Quantity"),
    unit: Optional[str] = Query(None, description="Packaging unit"),
    force_online: bool = Query(False, description="Force online Gemini grounding"),
    db: Session = Depends(get_db)
):
    """
    MODULE 4 OVERHAUL: Dynamic Commodity 3-Way Audit Engine
    - Evaluates any commodity, whether from historical grocery lists OR completely unlisted/new.
    - If unlisted (e.g. 'चना डाळ' यादीत नसताना):
        * Automatically triggers Gemini API / Grounding Engine.
        * Displays subtle badge: 'ℹ️ ही वस्तू मागील याद्यांमध्ये उपलब्ध नाही (नवीन वस्तू / बाहेरून खरेदी)'.
        * Does NOT throw a 404 error!
        * Predicts APMC Mandi Wholesale rate, Fair Retail Price (20-25% Margin), and Predicted Store Shelf Rate.
    - If historical:
        * Auto-populates actual store billed rate and UPI settlement history from previous trips.
    """
    raw_name = commodity.strip()
    if not raw_name:
        raise HTTPException(status_code=400, detail="कृपया वस्तूचे नाव टाका.")

    canon_commodity = normalize_canonical_commodity(raw_name)

    # 1. Check Historical Trips
    historical_records = []
    hist_billed_rates = []

    # Search in GroceryTrip / TripItem
    matched_prods = db.query(ProductCatalog).filter(
        (ProductCatalog.marathi_name.ilike(f"%{raw_name}%")) |
        (ProductCatalog.canonical_name.ilike(f"%{raw_name}%")) |
        (ProductCatalog.marathi_name.ilike(f"%{canon_commodity}%"))
    ).all()
    sku_ids = [p.sku_id for p in matched_prods]

    if sku_ids:
        t_items = db.query(TripItem).filter(TripItem.sku_id.in_(sku_ids)).order_by(TripItem.created_at.desc()).limit(5).all()
        for ti in t_items:
            trip = ti.trip
            d_str = trip.trip_date.strftime("%d-%m-%Y") if trip and trip.trip_date else "मागील खरेदी"
            m_name = trip.merchant_name if trip else "किराणा स्टोअर"
            historical_records.append({
                "date": d_str,
                "merchant": m_name,
                "rate": float(ti.derived_rate),
                "qty": float(ti.quantity_norm),
                "unit": ti.unit,
                "total": float(ti.entered_total)
            })
            hist_billed_rates.append(float(ti.derived_rate))

    # Also search in KiranaTripAnalytics
    recent_analytics = db.query(KiranaTripAnalytics).order_by(KiranaTripAnalytics.created_at.desc()).limit(20).all()
    for a in recent_analytics:
        if a.items_breakdown and isinstance(a.items_breakdown, list):
            for it in a.items_breakdown:
                it_name = it.get("name", "")
                if raw_name.lower() in it_name.lower() or canon_commodity.lower() in it_name.lower():
                    d_str = a.created_at.strftime("%d-%m-%Y") if hasattr(a.created_at, "strftime") else "मागील खरेदी"
                    s_rate = float(it.get("shopkeeper_rate") or it.get("entered_total") or 0.0)
                    if s_rate > 0 and len(historical_records) < 5:
                        historical_records.append({
                            "date": d_str,
                            "merchant": "मागील खरेदी सत्र",
                            "rate": s_rate,
                            "qty": float(it.get("quantity") or it.get("qty") or 1.0),
                            "unit": it.get("unit", "kg"),
                            "total": float(it.get("shopkeeper_amount") or s_rate)
                        })
                        hist_billed_rates.append(s_rate)

    is_historical = len(historical_records) > 0
    notice_mr = None if is_historical else "ℹ️ ही वस्तू मागील याद्यांमध्ये उपलब्ध नाही (नवीन वस्तू / बाहेरून खरेदी)"

    # 2. Fetch APMC Market Rate (Local APMC or Gemini Grounding)
    market_info = get_commodity_market_rate(
        db,
        canon_commodity or raw_name,
        force_refresh=force_online,
        use_online_grounding=True
    )
    govt_rate = float(market_info.get("retail_modal_rate", 55.0))
    canonical_unit = unit or market_info.get("canonical_unit", "kg")
    grounding_src = market_info.get("source", "apmc_local")

    # 3. Calculate Fair Retail Price (with 22% legitimate retailer margin + freight)
    fair_rate = calculate_fair_retail_baseline(govt_rate, raw_name, canonical_unit)

    # 4. Determine Counter POS & Settlement Rates
    if is_historical and hist_billed_rates:
        # Use actual historical rate from store trips
        shopkeeper_rate = hist_billed_rates[0]
        upi_settled_rate = shopkeeper_rate
    else:
        # Predicted local store shelf price (fair retail + normal kirana handling)
        shopkeeper_rate = round(fair_rate * 1.04, 2)
        upi_settled_rate = shopkeeper_rate

    # 5. Compute Totals for Entered Quantity
    govt_total = round(govt_rate * quantity, 2)
    fair_retail_total = round(fair_rate * quantity, 2)
    shopkeeper_total = round(shopkeeper_rate * quantity, 2)
    upi_settled_total = round(upi_settled_rate * quantity, 2)

    total_var = round(shopkeeper_total - fair_retail_total, 2)
    var_pct = round((total_var / fair_retail_total) * 100.0, 2) if fair_retail_total > 0 else 0.0

    margin_eval = evaluate_margin_indicator(shopkeeper_rate, fair_rate)

    if shopkeeper_total <= fair_retail_total + 5.0:
        if shopkeeper_total < fair_retail_total - 5.0:
            badge_label = f"₹{abs(total_var):.2f} सवलत / उत्तम ऑफर (Good Deal)"
        else:
            badge_label = "वाजवी दर (Fair Retail Price)"
    elif total_var > 10.0:
        badge_label = f"+₹{abs(total_var):.2f} (+{var_pct}%) अपेक्षित दरापेक्षा जास्त"
    else:
        badge_label = "वाजवी दर (किंचित फरक)"

    is_inflated = total_var > 5.0
    savings_amt = abs(total_var) if total_var < -5.0 else 0.0

    return CommodityAuditPredictionResponse(
        commodity_name=raw_name,
        canonical_unit=canonical_unit,
        quantity=quantity,
        is_historical=is_historical,
        historical_sessions_count=len(historical_records),
        notice_mr=notice_mr,
        govt_rate=govt_rate,
        govt_total_amount=govt_total,
        fair_retail_rate=fair_rate,
        fair_retail_total_amount=fair_retail_total,
        shopkeeper_rate=shopkeeper_rate,
        shopkeeper_total_amount=shopkeeper_total,
        upi_settled_rate=upi_settled_rate,
        upi_settled_total_amount=upi_settled_total,
        total_variance_amount=total_var,
        variance_percentage=var_pct,
        margin_indicator=margin_eval["indicator"],
        margin_status=margin_eval["status"],
        badge_label=badge_label,
        is_inflated=is_inflated,
        savings_amount=savings_amt,
        grounding_source=grounding_src,
        historical_records=historical_records
    )


