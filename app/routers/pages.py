from pathlib import Path
import time
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GroceryTrip, ProductCatalog
from app.services.volatility_engine import get_display_unit

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals['time'] = lambda: int(time.time())

router = APIRouter(include_in_schema=False)

@router.get("/")
def home_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={
        "active_page": "home",
        "title": "स्मार्ट किराणा - मुख्यपृष्ठ | बिलिंग व यादी शुद्धीकरण",
        "time": int(time.time())
    })

@router.get("/catalog")
@router.get("/catalog/")
def catalog_page(request: Request):
    return templates.TemplateResponse(request=request, name="catalog.html", context={
        "active_page": "catalog",
        "title": "स्मार्ट किराणा - पॉईंट-अँड-क्लिक व्हिज्युअल किराणा कॅटलॉग",
        "time": int(time.time())
    })

@router.get("/history")
@router.get("/history/")
def history_page(request: Request):
    return templates.TemplateResponse(request=request, name="history.html", context={
        "active_page": "history",
        "title": "स्मार्ट किराणा - खरेदी इतिहास | मागील पावत्या व हिशोब",
        "time": int(time.time())
    })

@router.get("/analyzer")
@router.get("/analyzer/")
def analyzer_page(request: Request):
    return templates.TemplateResponse(request=request, name="analyzer.html", context={
        "active_page": "analyzer",
        "title": "स्मार्ट किराणा - दर विश्लेषक व बजेट सिम्युलेटर",
        "time": int(time.time())
    })

@router.get("/about")
@router.get("/about/")
def about_page(request: Request):
    return templates.TemplateResponse(request=request, name="about.html", context={
        "active_page": "about",
        "title": "स्मार्ट किराणा - आमच्याबद्दल | सिस्टीम कार्यप्रणाली",
        "time": int(time.time())
    })

@router.get("/contact")
@router.get("/contact/")
def contact_page(request: Request):
    return templates.TemplateResponse(request=request, name="contact.html", context={
        "active_page": "contact",
        "title": "स्मार्ट किराणा - संपर्क व ग्राहक सेवा",
        "time": int(time.time())
    })

@router.get("/receipt/{trip_id}")
def receipt_page(trip_id: int, request: Request, db: Session = Depends(get_db)):
    trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="खरेदी नोंद सापडली नाही")

    items_detail = []
    for itm in trip.items:
        prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == itm.sku_id).first()
        items_detail.append({
            "name": prod.marathi_name if prod else f"वस्तू #{itm.sku_id}",
            "quantity_norm": itm.quantity_norm,
            "unit": itm.unit,
            "display_unit": get_display_unit(itm.unit),
            "entered_total": itm.entered_total,
            "derived_rate": itm.derived_rate,
            "baseline_rate": itm.baseline_rate,
            "variance_pct": itm.variance_pct,
            "badge": itm.badge
        })

    return templates.TemplateResponse(request=request, name="receipt.html", context={
        "trip": trip,
        "items": items_detail,
        "date_formatted": trip.trip_date.strftime("%d-%m-%Y %I:%M %p"),
        "title": f"पावती - {trip.merchant_name} | स्मार्ट किराणा"
    })
