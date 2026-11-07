from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductCatalog, AliasCandidate
from app.schemas import AcceptAliasRequest
from app.services.regex_parser import normalize_text, calculate_similarity
from app.services.volatility_engine import get_display_unit

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])

@router.get("")
def list_catalog(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(ProductCatalog).filter(ProductCatalog.is_active == True)
    if category:
        query = query.filter(ProductCatalog.category == category)
        
    prods = query.order_by(ProductCatalog.category, ProductCatalog.marathi_name).all()
    return [
        {
            "sku_id": p.sku_id,
            "canonical_name": p.canonical_name,
            "marathi_name": p.marathi_name,
            "canonical_unit": p.canonical_unit,
            "display_unit": get_display_unit(p.canonical_unit),
            "category": p.category,
            "aliases": p.aliases
        }
        for p in prods
    ]

@router.get("/search")
def search_catalog(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    cleaned = normalize_text(q).lower()
    prods = db.query(ProductCatalog).filter(ProductCatalog.is_active == True).all()

    scored = []
    for p in prods:
        score = calculate_similarity(cleaned, p.marathi_name)
        if p.aliases:
            for al in p.aliases:
                al_score = calculate_similarity(cleaned, str(al))
                if al_score > score:
                    score = al_score
        if score > 0.35:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "sku_id": p.sku_id,
            "marathi_name": p.marathi_name,
            "canonical_unit": p.canonical_unit,
            "display_unit": get_display_unit(p.canonical_unit),
            "category": p.category,
            "similarity": round(score, 3)
        }
        for score, p in scored[:10]
    ]

@router.post("/accept-alias")
def accept_alias(req: AcceptAliasRequest, db: Session = Depends(get_db)):
    clean_raw = req.raw_text.strip()
    cand = db.query(AliasCandidate).filter(
        AliasCandidate.raw_text == clean_raw,
        AliasCandidate.suggested_sku == req.sku_id
    ).first()
    
    if cand:
        cand.status = "approved"
    else:
        cand = AliasCandidate(
            raw_text=clean_raw,
            suggested_sku=req.sku_id,
            times_seen=1,
            status="approved"
        )
        db.add(cand)

    # Add to catalog aliases safely if not already present
    prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == req.sku_id).first()
    if prod:
        curr_aliases = list(prod.aliases or [])
        if clean_raw not in curr_aliases:
            curr_aliases.append(clean_raw)
            prod.aliases = curr_aliases

    db.commit()
    return {"success": True, "message_mr": "उर्फनाव (Alias) यशस्वीरित्या स्वीकारले."}


@router.get("/visual-groceries")
def get_visual_grocery_catalog():
    """
    MODULE 3: Point-and-Click Visual Grocery Catalog.
    Returns 6 distinct category tabs of Maharashtra staples for zero-error selection.
    """
    import json
    from pathlib import Path
    data_path = Path(__file__).resolve().parent.parent.parent / "data" / "maharashtra_groceries.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"categories": [], "pinned_essentials": []}

