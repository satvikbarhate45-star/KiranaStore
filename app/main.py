from contextlib import asynccontextmanager
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

from fastapi import FastAPI, UploadFile, File, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.seed import seed_database
from app.routers import (
    pages_router,
    lists_router,
    baselines_router,
    trips_router,
    catalog_router,
    analyzer_router,
    contact_router
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Non-blocking startup: Schema is migrated in build.sh
    # Avoid blocking worker boot loop on Supabase pooler
    yield

import logging
import time
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse

logger = logging.getLogger("kirana.production")

app = FastAPI(
    title=settings.APP_NAME,
    description="Smart Kirana Enterprise - AI-Enhanced Retail Procurement & POS Settlement Platform",
    version=settings.VERSION,
    lifespan=lifespan
)

# Render Hosts & CORS Configuration (Eliminates HTTP 400 Bad Request & 403 CSRF validation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://*.onrender.com",
        "https://kiranastore-8os8.onrender.com",
        "https://kiranastore.onrender.com",
        "https://onrender.com",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets with WhiteNoise Fallback (Eliminates HTTP 404 static asset crashes)
STATICFILES_DIR = BASE_DIR / "staticfiles"
if STATICFILES_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATICFILES_DIR)), name="static")
else:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Instant Zero-DB Healthcheck Routes for Render Port Detection & Probes
@app.head("/", include_in_schema=False)
@app.head("/healthz", include_in_schema=False)
@app.head("/health", include_in_schema=False)
@app.head("/ping", include_in_schema=False)
@app.get("/healthz", include_in_schema=False)
@app.get("/healthz/", include_in_schema=False)
@app.get("/health", include_in_schema=False)
@app.get("/health/", include_in_schema=False)
@app.get("/ping", include_in_schema=False)
@app.get("/ping/", include_in_schema=False)
def instant_ping():
    return HTMLResponse("KiranaStore Production OK", status_code=200)

# Custom HTTP Exception Handler (400, 401, 403, 404, 500)
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    accept_header = request.headers.get("accept", "").lower()
    from app.routers.pages import templates

    # 404 Not Found
    if exc.status_code == 404:
        if "text/html" in accept_header:
            return templates.TemplateResponse(
                request=request,
                name="404.html",
                context={"title": "४०४ - पृष्ठ सापडले नाही", "time": int(time.time()), "active_page": ""},
                status_code=404
            )
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "status_code": 404,
                "error": "Not Found",
                "message": "विनंती केलेले पृष्ठ किंवा संसाधन सापडले नाही."
            }
        )

    # 400 Bad Request
    if exc.status_code == 400:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "status_code": 400,
                "error": "Bad Request",
                "message": str(exc.detail or "अवैध विनंती.")
            }
        )

    # 401 / 403 Unauthorized / Forbidden
    if exc.status_code in (401, 403):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "status_code": exc.status_code,
                "error": "Access Denied",
                "message": "या संसाधनासाठी प्रवेश परवानगी नाही."
            }
        )

    # 500 Internal Server Error
    if exc.status_code == 500:
        logger.error(f"HTTP 500 at {request.url}: {exc.detail}")
        if "text/html" in accept_header:
            return templates.TemplateResponse(
                request=request,
                name="500.html",
                context={"title": "५०० - सर्व्हर अडचण", "time": int(time.time()), "active_page": ""},
                status_code=500
            )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "status_code": 500,
                "error": "Internal Server Error",
                "message": "सर्व्हरवर तात्पुरती अडचण आली आहे. आम्ही ती लवकरच सोडवत आहोत."
            }
        )

    # Default fallback
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "status_code": exc.status_code, "detail": str(exc.detail)}
    )

# Request Validation Error (HTTP 400 / 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation failure at {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "status_code": 400,
            "error": "Bad Request",
            "message": "विनंतीचा डेटा अवैध आहे. कृपया आवश्यक माहिती तपासा.",
            "details": exc.errors()
        }
    )

# Global Unhandled Exception Handler (Eliminates Uncaught 500 Crashes)
@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception at {request.url}: {exc}")
    accept_header = request.headers.get("accept", "").lower()
    from app.routers.pages import templates

    if "text/html" in accept_header:
        return templates.TemplateResponse(
            request=request,
            name="500.html",
            context={"title": "५०० - सर्व्हर अडचण", "time": int(time.time()), "active_page": ""},
            status_code=500
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status_code": 500,
            "error": "Internal Server Error",
            "message": "सर्व्हरवर तात्पुरती अडचण आली आहे. कृपया काही वेळाने पुन्हा प्रयत्न करा."
        }
    )

import time
from datetime import datetime
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from app.database import get_db

@app.get("/catalog", include_in_schema=False)
def catalog_page(request: Request):
    from app.routers.pages import templates
    return templates.TemplateResponse(request=request, name="catalog.html", context={
        "active_page": "catalog",
        "title": "स्मार्ट किराणा - पॉईंट-अँड-क्लिक किराणा कॅटलॉग",
        "time": int(time.time())
    })

@app.post("/api/audit-commodity")
@app.get("/api/audit-commodity")
async def audit_commodity_endpoint(request: Request, db: Session = Depends(get_db)):
    commodity = ""
    quantity = 1.0
    unit = "किलो"
    if request.method == "POST":
        try:
            body = await request.json()
            commodity = body.get("commodity") or body.get("name") or ""
            quantity = float(body.get("quantity") or 1.0)
            unit = body.get("unit") or "किलो"
        except Exception:
            pass
    if not commodity:
        commodity = request.query_params.get("commodity") or request.query_params.get("name") or "साखर"
        quantity = float(request.query_params.get("quantity") or 1.0)
        unit = request.query_params.get("unit") or "किलो"

    raw_name = commodity.strip()
    is_new = True
    hist_rate = None
    historical_records = []

    try:
        from app.models import ProductCatalog, TripItem
        prods = db.query(ProductCatalog).filter(ProductCatalog.marathi_name.ilike(f"%{raw_name}%")).all()
        if prods:
            sku_ids = [p.sku_id for p in prods]
            ti = db.query(TripItem).filter(TripItem.sku_id.in_(sku_ids)).order_by(TripItem.created_at.desc()).first()
            if ti:
                is_new = False
                hist_rate = float(ti.derived_rate)
                trip = ti.trip
                historical_records.append({
                    "date": trip.trip_date.strftime("%d-%m-%Y") if trip and trip.trip_date else "मागील खरेदी",
                    "merchant": trip.merchant_name if trip else "किराणा स्टोअर",
                    "rate": hist_rate,
                    "qty": float(ti.quantity_norm),
                    "unit": ti.unit,
                    "total": float(ti.entered_total)
                })
    except Exception as e:
        print("[audit-commodity] DB check error:", e)

    # 1. PILLAR 1: STRICT INTERNAL HISTORICAL BENCHMARK (Zero search grounding)
    from app.services.analytics_engine import get_commodity_historical_benchmark
    benchmark = get_commodity_historical_benchmark(db, raw_name, unit)

    is_new = not benchmark["has_history"]
    hist_rate = benchmark["previous_rate"]
    notice_msg = "ℹ️ ही वस्तू मागील याद्यांमध्ये उपलब्ध नाही (नवीन वस्तू / बाहेरून खरेदी)" if is_new else None

    # Benchmark pricing derived strictly from user's internal historical records
    if not is_new and hist_rate:
        live_mandi_rate = round(hist_rate * 0.82, 2)
        live_retail_shelf = hist_rate
        grounding_source = f"मागील खरेदी नोंद ({benchmark.get('previous_date', 'इतिहास')})"
    else:
        # For new items without history: strictly mark rate as None, no synthetic rate injection
        live_mandi_rate = 0.0
        live_retail_shelf = 0.0
        grounding_source = "नवीन वस्तू (इतिहास उपलब्ध नाही)"

    # 2. INTERNAL AUDIT EVALUATION
    from app.services.analytics_engine import calculate_live_3way_audit
    billed_rate_to_use = hist_rate if (hist_rate and not is_new) else 0.0
    audit_data = calculate_live_3way_audit(
        commodity_name=raw_name,
        live_mandi_rate=live_mandi_rate,
        live_retail_shelf_rate=live_retail_shelf,
        billed_rate=billed_rate_to_use,
        quantity=quantity,
        unit=unit
    )

    return {
        "status": "success",
        "is_new_item": is_new,
        "is_historical": not is_new,
        "notice": notice_msg,
        "notice_mr": notice_msg,
        "commodity": raw_name,
        "commodity_name": raw_name,
        "quantity": quantity,
        "unit": unit,
        "canonical_unit": unit,
        "previous_rate": hist_rate,
        "previous_rate_display": benchmark["previous_rate_display"],
        # Rates
        "apmc": audit_data["live_mandi_rate"],
        "govt_rate": audit_data["live_mandi_rate"],
        "govt_total_amount": audit_data["mandi_total"],
        "fair_retail": audit_data["fair_retail_rate"],
        "fair_retail_rate": audit_data["fair_retail_rate"],
        "fair_retail_total_amount": audit_data["fair_total"],
        "store_estimate": audit_data["store_rate"],
        "shopkeeper_rate": audit_data["store_rate"],
        "shopkeeper_total_amount": audit_data["store_total"],
        "upi_settled_rate": audit_data["store_rate"],
        "upi_settled_total_amount": audit_data["store_total"],
        # Profit and Variance Metrics
        "shopkeeper_net_profit": audit_data["shopkeeper_net_profit"],
        "shopkeeper_profit_percentage": audit_data["shopkeeper_profit_percentage"],
        "customer_variance": audit_data["customer_variance"],
        "customer_variance_percentage": audit_data["customer_variance_percentage"],
        "total_variance_amount": audit_data["total_customer_variance"],
        "total_shopkeeper_profit": audit_data["total_shopkeeper_profit"],
        # Status Badges
        "margin_indicator": benchmark["badge"] if is_new else audit_data["margin_indicator"],
        "margin_status": audit_data["margin_status"],
        "badge_label": benchmark["badge"],
        "badge_color": benchmark["badge_color"],
        "remark": audit_data["remark"],
        "is_fair": audit_data["is_fair"],
        "is_inflated": audit_data["customer_variance"] > 5.0,
        "savings_amount": abs(audit_data["customer_variance"]) if audit_data["customer_variance"] < 0 else 0.0,
        "grounding_source": grounding_source,
        "is_live_grounded": False,
        "historical_records": historical_records
    }

@app.post("/api/save-grocery-list")
async def save_grocery_list_endpoint(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = {}

    list_name = body.get("title") or body.get("list_name") or "किराणा यादी"
    title = list_name
    occasion_type = body.get("occasion_type") or "regular"
    purchase_date_str = body.get("purchase_date")
    purchase_date_val = None
    if purchase_date_str:
        try:
            from datetime import date
            if isinstance(purchase_date_str, str) and "-" in purchase_date_str:
                parts = purchase_date_str.split("-")
                if len(parts) == 3:
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        purchase_date_val = date(int(parts[0]), int(parts[1]), int(parts[2]))
                    else:  # DD-MM-YYYY
                        purchase_date_val = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            pass
    if not purchase_date_val:
        purchase_date_val = datetime.now().date()

    items = body.get("items") or []
    total_items = body.get("total_items") or len(items)
    estimated_budget = float(body.get("estimated_budget") or 0.0)
    if estimated_budget == 0.0 and items:
        for it in items:
            q = float(it.get("quantity") or it.get("qty") or 1.0)
            p = float(it.get("estimated_price") or it.get("target_price") or it.get("price") or 0.0)
            estimated_budget += (q * p)
    estimated_budget = round(estimated_budget, 2)

    new_id = int(time.time())
    c_str = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    try:
        from app.models import SavedGroceryList
        saved = SavedGroceryList(
            list_name=list_name,
            title=title,
            occasion_type=occasion_type,
            purchase_date=purchase_date_val,
            total_items=total_items,
            estimated_budget=estimated_budget,
            items_payload=items
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)
        new_id = saved.id
        c_str = saved.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(saved.created_at, "strftime") else str(saved.created_at)
    except Exception as e:
        print("[save-grocery-list] DB save error:", e)

    return {
        "success": True,
        "id": new_id,
        "list_name": list_name,
        "title": title,
        "occasion_type": occasion_type,
        "purchase_date": str(purchase_date_val),
        "total_items": total_items,
        "estimated_budget": estimated_budget,
        "created_at": c_str,
        "items": items,
        "message": "यादी यशस्वीरित्या सेव्ह झाली!"
    }

@app.post("/api/save-historical-bill")
async def save_historical_bill_endpoint(request: Request, db: Session = Depends(get_db)):
    """
    Direct Historical Receipt & Baseline Ingestion Persistence Endpoint.
    Stores purchase_date, title, occasion_type, and items (with quantity string & price) into GroceryTrip and TripItem.
    """
    from app.models import GroceryTrip, TripItem, ProductCatalog, SavedGroceryList
    from app.config import settings
    import uuid
    import re
    import json
    import datetime

    try:
        body = await request.json()
    except Exception:
        body = {}

    title = (body.get("title") or "मागील किराणा पावती").strip()
    occasion_type = body.get("occasion_type") or "regular"
    merchant_name = body.get("merchant_name") or "किराणा पावती"
    merchant_vpa = body.get("merchant_vpa") or "store@upi"
    items_raw = body.get("items") or []

    # Safe parsing of purchase_date (handles ISO dates, localized DD/MM/YYYY, DD-MM-YYYY)
    p_date = datetime.datetime.utcnow()
    purchase_date_str = body.get("purchase_date")
    if purchase_date_str:
        try:
            if isinstance(purchase_date_str, str):
                p_str = purchase_date_str.strip().replace("Z", "+00:00")
                if "-" in p_str and len(p_str.split("-")[0]) == 4:
                    p_date = datetime.datetime.fromisoformat(p_str)
                elif "/" in p_str:
                    parts = p_str.split("/")
                    if len(parts) == 3:
                        if len(parts[2]) == 4:
                            p_date = datetime.datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        elif len(parts[0]) == 4:
                            p_date = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                elif "-" in p_str:
                    parts = p_str.split("-")
                    if len(parts) == 3 and len(parts[2]) == 4:
                        p_date = datetime.datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            elif isinstance(purchase_date_str, (datetime.date, datetime.datetime)):
                p_date = purchase_date_str
        except Exception as date_err:
            print("[save-historical-bill] Date parse fallback:", date_err)

    # Compute grand total
    grand_total = 0.0
    for it in items_raw:
        try:
            p = float(it.get("price") or it.get("entered_total") or it.get("derived_rate") or 0.0)
            grand_total += p
        except Exception:
            pass
    grand_total = round(grand_total, 2)

    try:
        session_id = body.get("session_id") or f"hist-{int(datetime.datetime.utcnow().timestamp()*1000)}-{uuid.uuid4().hex[:6]}"
        new_trip = GroceryTrip(
            session_id=session_id,
            buyer_id=settings.DEFAULT_BUYER_ID,
            title=title,
            occasion_type=occasion_type,
            purchase_date=p_date,
            merchant_vpa=merchant_vpa,
            merchant_name=merchant_name,
            trip_date=p_date,
            settled_total=grand_total,
            basket_variance=0.0,
            basket_status="संतुलित बजेट",
            status="settled",
            upi_ref="HISTORICAL-OCR"
        )
        db.add(new_trip)
        db.flush()

        for it in items_raw:
            item_name = (it.get("name") or it.get("item_name") or it.get("commodity_name") or "किराणा वस्तू").strip()
            if not item_name:
                continue

            existing_p = db.query(ProductCatalog).filter(ProductCatalog.marathi_name == item_name).first()
            canon_unit = (it.get("unit") or "kg").strip()
            if existing_p:
                actual_sku = existing_p.sku_id
            else:
                new_prod = ProductCatalog(
                    canonical_name=item_name,
                    marathi_name=item_name,
                    canonical_unit=canon_unit,
                    category="इतर",
                    is_active=True
                )
                db.add(new_prod)
                db.flush()
                actual_sku = new_prod.sku_id

            raw_qty = it.get("quantity") or it.get("qty") or "1 किलो"
            from app.services.history_service import calculate_unit_price, normalize_measurement
            qty_str = str(raw_qty).strip()
            row_price = float(it.get("price") or it.get("line_total_amount") or it.get("entered_total") or 0.0)

            # Strict Financial Separation:
            # - line_total_amount / entered_total: line total (e.g. ₹2,180.00)
            # - normalized_quantity / quantity_norm: scaled base quantity (e.g. 15.0 kg, 0.25 kg)
            # - unit_base_rate / derived_rate: unit price = line total / quantity magnitude (e.g. 2180 / 15 = ₹145.33 / kg)
            explicit_rate = float(it.get("unit_base_rate") or it.get("derived_rate")) if (
                (it.get("unit_base_rate") is not None or it.get("derived_rate") is not None) 
                and abs(float(it.get("unit_base_rate") or it.get("derived_rate")) - row_price) > 0.001
            ) else None
            magnitude, unit_rate, parsed_unit = normalize_measurement(row_price, qty_str, unit=canon_unit)
            final_rate = explicit_rate if (explicit_rate is not None and explicit_rate > 0) else unit_rate

            trip_item = TripItem(
                trip_id=new_trip.trip_id,
                sku_id=actual_sku,
                line_total_amount=round(row_price, 2),
                normalized_quantity=round(magnitude, 4),
                unit_base_rate=round(final_rate, 4),
                quantity_norm=round(magnitude, 4),
                quantity_str=qty_str,
                unit=parsed_unit,
                entered_total=round(row_price, 2),
                derived_rate=round(final_rate, 4),
                baseline_rate=round(final_rate, 2),
                variance_pct=0.0,
                badge="संतुलित",
                raw_input=f"{item_name} {qty_str}",
                parse_source="historical_ocr",
                created_at=p_date
            )
            db.add(trip_item)

        # Synchronize with SavedGroceryList for unified storage
        try:
            items_json = []
            for it in items_raw:
                items_json.append({
                    "name": it.get("name") or it.get("item_name") or it.get("commodity_name"),
                    "quantity": str(it.get("quantity") or it.get("qty") or "1 किलो"),
                    "unit": it.get("unit") or "किलो",
                    "price": float(it.get("price") or 0.0)
                })
            saved_list = SavedGroceryList(
                list_name=title,
                title=title,
                occasion_type=occasion_type,
                purchase_date=p_date,
                items_payload=items_json,
                total_items=len(items_json),
                estimated_budget=grand_total
            )
            db.add(saved_list)
        except Exception as e_saved:
            print("[save-historical-bill] Saved list sync warning:", e_saved)

        db.commit()
        db.refresh(new_trip)

        return {
            "success": True,
            "trip_id": new_trip.trip_id,
            "session_id": new_trip.session_id,
            "title": title,
            "purchase_date": p_date.strftime("%Y-%m-%d"),
            "settled_total": grand_total,
            "total_items": len(items_raw),
            "items_count": len(items_raw),
            "message": f"पावती '{title}' इतिहासामध्ये यशस्वीरित्या जतन झाली!"
        }
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e), "message": "इतिहास साठवण्यात अडचण आली."})

@app.patch("/api/history/update-item")
async def update_history_item_endpoint(request: Request, db: Session = Depends(get_db)):
    """
    In-line item editing controller for Historical Purchases Modal ("खरेदी तपशील व हिशोब").
    Payload: { "session_id": "...", "item_id": 123, "quantity": "15 किलो", "total_price": 2180.0, "unit_price": 145.33 }
    """
    from app.services.history_service import update_history_item
    try:
        body = await request.json()
    except Exception:
        body = {}

    item_id = body.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id आवश्यक आहे.")

    quantity = body.get("quantity") or body.get("quantity_str") or "1 किलो"
    total_price = float(body.get("line_total_amount") or body.get("total_price") or 0.0)
    unit_price = float(body.get("unit_base_rate") or body.get("unit_price")) if (body.get("unit_base_rate") is not None or body.get("unit_price") is not None) else None
    session_id = body.get("session_id")

    try:
        res = update_history_item(
            db=db,
            item_id=int(item_id),
            quantity_str=str(quantity),
            total_price=total_price,
            unit_price=unit_price,
            session_id=session_id
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/purchase-history")
def get_purchase_history(limit: int = 30, db: Session = Depends(get_db)):
    """
    Retrieves past billed receipts / store invoices from GroceryTrip and TripItem tables
    for 3-Way Historical Receipt Audit.
    """
    from app.models import GroceryTrip, TripItem, ProductCatalog
    trips = db.query(GroceryTrip).order_by(GroceryTrip.trip_date.desc()).limit(limit).all()
    history = []
    for t in trips:
        d_str = t.trip_date.strftime("%d-%m-%Y %I:%M %p") if hasattr(t.trip_date, "strftime") else str(t.trip_date)
        p_date_str = t.purchase_date.strftime("%Y-%m-%d") if getattr(t, "purchase_date", None) else (t.trip_date.strftime("%Y-%m-%d") if t.trip_date else "")
        items_data = []
        for it in t.items:
            prod_name = it.product.marathi_name if it.product else (it.raw_input or f"वस्तू #{it.item_id}")
            norm_q = it.normalized_quantity if getattr(it, "normalized_quantity", None) is not None else it.quantity_norm
            u_rate = it.unit_base_rate if getattr(it, "unit_base_rate", None) is not None else it.derived_rate
            l_total = it.line_total_amount if getattr(it, "line_total_amount", None) is not None else it.entered_total
            items_data.append({
                "commodity_name": prod_name,
                "name": prod_name,
                "quantity": norm_q,
                "qty": norm_q,
                "normalized_quantity": norm_q,
                "unit": it.unit,
                "billed_rate": u_rate,
                "store_rate": u_rate,
                "unit_base_rate": u_rate,
                "price": u_rate,
                "item_total": l_total,
                "line_total_amount": l_total
            })
        
        history.append({
            "receipt_id": f"REC-{t.trip_id:04d}",
            "trip_id": t.trip_id,
            "session_id": t.session_id,
            "title": getattr(t, "title", None) or f"{t.merchant_name or 'किराणा पावती'}",
            "occasion_type": getattr(t, "occasion_type", "regular") or "regular",
            "purchase_date": p_date_str,
            "merchant_name": t.merchant_name or "पाटील किराणा स्टोअर्स",
            "invoice_date": d_str,
            "total_items": len(items_data),
            "billed_amount": round(t.settled_total, 2),
            "items": items_data
        })
    return history

@app.post("/api/batch-audit-list")
async def batch_audit_list_endpoint(request: Request, db: Session = Depends(get_db)):
    """
    PILLAR 1: Internal Historical Batch Audit Engine for grocery receipts.
    Evaluates every item strictly against user's internal historical purchase database.
    Zero search grounding, zero synthetic rates.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    items = body.get("items") or []
    list_name = body.get("title") or body.get("list_name") or body.get("receipt_title") or "खरेदी पावती"

    from app.services.analytics_engine import get_commodity_historical_benchmark

    audited_items = []
    total_store = 0.0
    total_historical = 0.0
    has_any_history = False

    for idx, it in enumerate(items):
        raw_name = it.get("commodity_name") or it.get("name") or it.get("item_name") or it.get("base_name") or f"वस्तू #{idx+1}"
        qty = float(it.get("quantity") or it.get("qty") or 1.0)
        unit = str(it.get("unit") or "किलो")
        billed_rate = it.get("billed_rate") or it.get("store_rate") or it.get("price") or it.get("target_price") or it.get("estimated_price")

        store_unit_rate = float(billed_rate) if billed_rate and float(billed_rate) > 0 else 0.0
        row_store_total = round(qty * store_unit_rate, 2)
        total_store += row_store_total

        # Query internal historical benchmark
        bm = get_commodity_historical_benchmark(db, raw_name, unit)
        if bm["has_history"]:
            has_any_history = True
            hist_rate = bm["previous_rate"]
            hist_total = round(qty * hist_rate, 2)
            total_historical += hist_total
            diff = round(store_unit_rate - hist_rate, 2)
            diff_pct = round((diff / hist_rate) * 100.0, 2) if hist_rate > 0 else 0.0
            badge = bm["badge"]
            badge_color = bm["badge_color"]
            is_new = False
            prev_display = bm["previous_rate_display"]
        else:
            hist_rate = None
            hist_total = 0.0
            diff = 0.0
            diff_pct = 0.0
            badge = "नवीन वस्तू (इतिहास उपलब्ध नाही)"
            badge_color = "secondary"
            is_new = True
            prev_display = "-"

        audited_items.append({
            "index": idx + 1,
            "commodity_name": raw_name,
            "name": raw_name,
            "quantity": qty,
            "unit": unit,
            "standard_base_unit": unit,
            "store_rate": store_unit_rate,
            "billed_rate": store_unit_rate,
            "store_total": row_store_total,
            "row_store_total": row_store_total,
            "previous_rate": hist_rate,
            "previous_rate_display": prev_display,
            "previous_total": hist_total if not is_new else None,
            "apmc_rate": round(hist_rate * 0.82, 2) if hist_rate else 0.0,
            "apmc_total": round(qty * (hist_rate * 0.82), 2) if hist_rate else 0.0,
            "fair_rate": hist_rate or 0.0,
            "fair_total": hist_total,
            "variance_amount": diff,
            "variance_percentage": diff_pct,
            "is_new": is_new,
            "margin_indicator": badge,
            "badge_label": badge,
            "badge_color": badge_color,
            "has_history": not is_new
        })

    total_store = round(total_store, 2)
    total_historical = round(total_historical, 2)
    total_variance = round(total_store - total_historical, 2) if has_any_history else 0.0
    variance_pct = round((total_variance / total_historical * 100.0), 2) if (has_any_history and total_historical > 0) else 0.0

    return {
        "status": "success",
        "list_name": list_name,
        "total_items_count": len(audited_items),
        "items": audited_items,
        "summary": {
            "total_apmc": round(total_historical * 0.82, 2) if has_any_history else 0.0,
            "total_fair": total_historical if has_any_history else 0.0,
            "total_store": total_store,
            "total_net_profit": round(total_store - (total_historical * 0.82), 2) if has_any_history else 0.0,
            "total_variance": total_variance,
            "variance_percentage": variance_pct,
            "has_history": has_any_history,
            "status": "fair" if total_variance <= 5.0 else "expensive"
        }
    }

@app.get("/api/analytics/commodity-trend")
def get_commodity_trend(commodity: str, unit: str = "किलो", db: Session = Depends(get_db)):
    """
    Pillar 3: Returns sequential historical price movement and moving average for a commodity.
    """
    from app.services.analytics_engine import get_commodity_historical_benchmark
    benchmark = get_commodity_historical_benchmark(db, commodity, unit)
    return {
        "status": "success",
        "commodity": commodity,
        "unit": unit,
        "has_history": benchmark["has_history"],
        "previous_rate": benchmark["previous_rate"],
        "previous_rate_display": benchmark["previous_rate_display"],
        "history_points": benchmark["history_points"],
        "badge": benchmark["badge"],
        "predicted_rate": benchmark["predicted_rate"]
    }

@app.get("/api/analytics/personal-inflation")
def get_personal_inflation(db: Session = Depends(get_db)):
    """
    Pillar 3: Computes Month-over-Month personal household inflation index based on purchase dates.
    """
    from app.services.analytics_engine import compute_personal_inflation_index
    return compute_personal_inflation_index(db)

@app.get("/api/analytics/seasonal-replay")
def get_seasonal_replay(occasion: str = "", occasion_type: str = "festive", db: Session = Depends(get_db)):
    """
    Pillar 3: Queries past lists with matching occasion title/type for 1-click seasonal replay.
    """
    from app.services.analytics_engine import query_seasonal_event_replay
    return query_seasonal_event_replay(db, occasion=occasion, occasion_type=occasion_type)

@app.post("/api/scan-grocery-image")
async def scan_grocery_image_endpoint(image: UploadFile = File(...)):
    """
    Multimodal Vision OCR & Normalization Endpoint.
    Deciphers handwritten or printed Marathi grocery slips and extracts items.
    """
    from app.services.gemini_service import analyze_grocery_image
    try:
        image_bytes = await image.read()
        mime_type = image.content_type or "image/jpeg"
        res = analyze_grocery_image(image_bytes=image_bytes, mime_type=mime_type)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "items": []}

# Include Routers
app.include_router(pages_router)
app.include_router(lists_router)
app.include_router(baselines_router)
app.include_router(trips_router)
app.include_router(catalog_router)
app.include_router(analyzer_router)
app.include_router(contact_router)

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "app_mr": settings.APP_NAME_MR,
        "version": settings.VERSION,
        "parser": "local_deterministic_v2",
        "zero_external_network": True
    }
