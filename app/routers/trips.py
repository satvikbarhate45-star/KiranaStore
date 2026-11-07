import datetime
import uuid
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.models import GroceryTrip, TripItem, ProductCatalog, AliasCandidate, KiranaTripAnalytics
from app.schemas import TripCreate, TripResponse, TripItemResponse
from app.services.gov_price_service import calculate_govt_expected_total
from app.services.volatility_engine import (
    get_rolling_median_baseline,
    calculate_volatility_badge,
    calculate_basket_status,
    get_display_unit
)

router = APIRouter(prefix="/api/v1/trips", tags=["Trips"])

@router.post("", response_model=TripResponse)
def commit_trip(trip_data: TripCreate, db: Session = Depends(get_db)):
    # 1. Idempotency check on session_id
    sess_id = trip_data.session_id or f"trip-{int(datetime.datetime.utcnow().timestamp()*1000)}-{uuid.uuid4().hex[:6]}"
    existing_trip = db.query(GroceryTrip).filter(GroceryTrip.session_id == sess_id).first()
    if existing_trip:
        return _format_trip_response(existing_trip, db)

    # 2. Compute basket status and variance if not supplied
    items_summary = [item.dict() for item in trip_data.items]
    computed_status, computed_variance, _ = calculate_basket_status(items_summary)
    
    basket_status = trip_data.basket_status or computed_status
    basket_variance = trip_data.basket_variance if trip_data.basket_variance is not None else computed_variance

    # Support backdated purchase dates (ISO or localized datepicker formats)
    p_date = datetime.datetime.utcnow()
    if trip_data.purchase_date:
        try:
            if isinstance(trip_data.purchase_date, str):
                p_str = trip_data.purchase_date.strip().replace("Z", "+00:00")
                if "-" in p_str:
                    p_date = datetime.datetime.fromisoformat(p_str)
                elif "/" in p_str:
                    parts = p_str.split("/")
                    if len(parts) == 3:
                        p_date = datetime.datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            elif isinstance(trip_data.purchase_date, (datetime.date, datetime.datetime)):
                p_date = trip_data.purchase_date
        except Exception:
            pass

    new_trip = GroceryTrip(
        session_id=sess_id,
        buyer_id=settings.DEFAULT_BUYER_ID,
        title=trip_data.title or "नियमित किराणा",
        occasion_type=trip_data.occasion_type or "regular",
        purchase_date=p_date,
        merchant_vpa=trip_data.merchant_vpa or "store@upi",
        merchant_name=trip_data.merchant_name or "किराणा व्यावसायिक",
        trip_date=p_date,
        settled_total=round(trip_data.settled_total, 2),
        basket_variance=basket_variance,
        basket_status=basket_status,
        status="settled",
        upi_ref=trip_data.upi_ref or "OFFLINE-RECORD"
    )
    db.add(new_trip)
    db.flush()  # assign trip_id

    # 3. Insert items
    for item in trip_data.items:
        actual_sku = item.sku_id
        if not actual_sku:
            item_name = (item.name or item.raw_input or "किराणा वस्तू").strip()
            existing_p = db.query(ProductCatalog).filter(ProductCatalog.marathi_name == item_name).first()
            if existing_p:
                actual_sku = existing_p.sku_id
            else:
                new_prod = ProductCatalog(
                    canonical_name=item_name,
                    marathi_name=item_name,
                    aliases=[item.raw_input] if item.raw_input else [],
                    canonical_unit=item.unit or "kg",
                    category="इतर",
                    is_active=True
                )
                db.add(new_prod)
                db.flush()
                actual_sku = new_prod.sku_id

        # Re-verify or fetch baseline if missing
        baseline = item.baseline_rate
        if baseline is None and actual_sku:
            baseline = get_rolling_median_baseline(db, actual_sku, buyer_id=settings.DEFAULT_BUYER_ID)
            
        badge, var_pct = calculate_volatility_badge(item.derived_rate, baseline)

        q_str = str(item.quantity or item.quantity_str or item.qty or f"{item.quantity_norm} {item.unit}").strip()
        l_total = round(float(item.line_total_amount if item.line_total_amount is not None else item.entered_total or 0.0), 2)
        n_qty = round(float(item.normalized_quantity if item.normalized_quantity is not None else item.quantity_norm or 1.0), 4)
        u_rate = round(float(item.unit_base_rate if item.unit_base_rate is not None else item.derived_rate or (l_total / n_qty if n_qty > 0 else 0.0)), 4)

        trip_item = TripItem(
            trip_id=new_trip.trip_id,
            sku_id=actual_sku,
            line_total_amount=l_total,
            normalized_quantity=n_qty,
            unit_base_rate=u_rate,
            quantity_norm=n_qty,
            quantity_str=q_str,
            unit=item.unit or "किलो",
            entered_total=l_total,
            derived_rate=u_rate,
            baseline_rate=baseline,
            variance_pct=var_pct,
            badge=item.badge or badge or "संतुलित",
            raw_input=item.raw_input or f"{item.name or 'वस्तू'} {q_str}",
            parse_source=item.parse_source or "regex",
            ai_confidence=item.ai_confidence,
            created_at=p_date
        )
        db.add(trip_item)

        # Queue candidate alias if raw input was modified
        if item.raw_input and item.parse_source in ["gemini", "regex"] and actual_sku:
            cand = db.query(AliasCandidate).filter(
                AliasCandidate.raw_text == item.raw_input.strip(),
                AliasCandidate.suggested_sku == actual_sku
            ).first()
            if cand:
                cand.times_seen += 1
            else:
                db.add(AliasCandidate(
                    raw_text=item.raw_input.strip(),
                    suggested_sku=actual_sku,
                    times_seen=1,
                    status="pending"
                ))

    # Auto-generate closed-loop 3-way analytics record if missing
    try:
        analytics_exist = db.query(KiranaTripAnalytics).filter(KiranaTripAnalytics.session_id == trip_data.session_id).first()
        if not analytics_exist:
            items_for_calc = []
            for itm in trip_data.items:
                items_for_calc.append({
                    "name": itm.name or itm.raw_input or "किराणा वस्तू",
                    "qty": itm.quantity_norm,
                    "quantity_norm": itm.quantity_norm,
                    "unit": itm.unit,
                    "entered_total": itm.entered_total
                })
            calc = calculate_govt_expected_total(db, items_for_calc)
            govt_tot = calc["govt_total_amount"]
            shop_tot = round(trip_data.settled_total, 2)
            upi_tot = shop_tot
            var_amt = round(shop_tot - govt_tot, 2)
            var_pct = round((var_amt / govt_tot) * 100.0, 2) if govt_tot > 0 else 0.0

            db.add(KiranaTripAnalytics(
                session_id=trip_data.session_id,
                buyer_id=settings.DEFAULT_BUYER_ID,
                govt_total_amount=govt_tot,
                shopkeeper_total_amount=shop_tot,
                upi_settled_amount=upi_tot,
                total_variance_amount=var_amt,
                variance_percentage=var_pct,
                items_breakdown=calc["items_breakdown"]
            ))
    except Exception as e:
        print(f"[Trips API] Warning: Could not auto-generate trip analytics: {e}")

    db.commit()
    db.refresh(new_trip)

    return _format_trip_response(new_trip, db)

@router.get("", response_model=List[TripResponse])
def list_trips(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    merchant: Optional[str] = Query(None),
    basket_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(GroceryTrip).order_by(desc(GroceryTrip.trip_date))

    if merchant and merchant.strip():
        query = query.filter(GroceryTrip.merchant_name.ilike(f"%{merchant.strip()}%"))

    if basket_status and basket_status.strip() and basket_status != "सर्व":
        query = query.filter(GroceryTrip.basket_status == basket_status.strip())

    if start_date:
        try:
            s_dt = datetime.datetime.fromisoformat(start_date)
            query = query.filter(GroceryTrip.trip_date >= s_dt)
        except ValueError:
            pass

    if end_date:
        try:
            e_dt = datetime.datetime.fromisoformat(end_date)
            # include entire end day
            query = query.filter(GroceryTrip.trip_date <= e_dt + datetime.timedelta(days=1))
        except ValueError:
            pass

    trips = query.limit(limit).all()
    return [_format_trip_response(t, db, include_items=False) for t in trips]

@router.get("/{trip_id}", response_model=TripResponse)
def get_trip_detail(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="खरेदी नोंद सापडली नाही")
    return _format_trip_response(trip, db, include_items=True)

@router.delete("/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="खरेदी नोंद सापडली नाही")
    
    db.delete(trip)
    db.commit()
    return {"success": True, "message_mr": "खरेदी नोंद यशस्वीरित्या हटवली आहे आणि बेसलाईन अपडेट केली आहे."}

@router.patch("/items/{item_id}")
def update_trip_item_endpoint(
    item_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    from app.services.history_service import update_history_item
    try:
        res = update_history_item(
            db=db,
            item_id=item_id,
            quantity_str=payload.get("quantity", "1 किलो"),
            total_price=float(payload.get("total_price", 0.0)),
            unit_price=float(payload.get("unit_price")) if payload.get("unit_price") is not None else None,
            session_id=payload.get("session_id")
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _format_trip_response(trip: GroceryTrip, db: Session, include_items: bool = True) -> TripResponse:
    items_list = None
    items_count = len(trip.items)
    
    if include_items:
        items_list = []
        for itm in trip.items:
            prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == itm.sku_id).first()
            p_name = prod.marathi_name if prod else f"वस्तू #{itm.sku_id}"
            norm_q = itm.normalized_quantity if getattr(itm, "normalized_quantity", None) is not None else itm.quantity_norm
            u_rate = itm.unit_base_rate if getattr(itm, "unit_base_rate", None) is not None else itm.derived_rate
            l_total = itm.line_total_amount if getattr(itm, "line_total_amount", None) is not None else itm.entered_total
            items_list.append(TripItemResponse(
                item_id=itm.item_id,
                sku_id=itm.sku_id,
                name=p_name,
                quantity_norm=norm_q,
                normalized_quantity=norm_q,
                quantity_str=getattr(itm, "quantity_str", None) or f"{norm_q} {itm.unit}",
                unit=itm.unit,
                display_unit=get_display_unit(itm.unit),
                entered_total=l_total,
                line_total_amount=l_total,
                derived_rate=u_rate,
                unit_base_rate=u_rate,
                baseline_rate=itm.baseline_rate,
                variance_pct=itm.variance_pct,
                badge=itm.badge,
                raw_input=itm.raw_input,
                parse_source=itm.parse_source,
                ai_confidence=itm.ai_confidence
            ))

    # Format date in IST-friendly string
    date_str = trip.trip_date.strftime("%d-%m-%Y %I:%M %p")
    p_date_str = trip.purchase_date.strftime("%Y-%m-%d") if getattr(trip, "purchase_date", None) else trip.trip_date.strftime("%Y-%m-%d")

    return TripResponse(
        trip_id=trip.trip_id,
        session_id=trip.session_id,
        buyer_id=trip.buyer_id,
        title=getattr(trip, "title", "नियमित किराणा") or "नियमित किराणा",
        occasion_type=getattr(trip, "occasion_type", "regular") or "regular",
        purchase_date=p_date_str,
        merchant_vpa=trip.merchant_vpa,
        merchant_name=trip.merchant_name,
        trip_date=date_str,
        settled_total=trip.settled_total,
        basket_variance=trip.basket_variance,
        basket_status=trip.basket_status or "संतुलित बजेट",
        status=trip.status,
        upi_ref=trip.upi_ref,
        items_count=items_count,
        items=items_list
    )
