from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import VolatilityConfig, ProductCatalog
from app.services.volatility_engine import get_rolling_median_baseline, get_display_unit

router = APIRouter(prefix="/api/v1/baselines", tags=["Baselines"])

@router.get("")
def get_baselines(
    sku_ids: str = Query(..., description="Comma-separated SKU IDs"),
    buyer_id: int = Query(settings.DEFAULT_BUYER_ID),
    db: Session = Depends(get_db)
):
    ids = []
    for part in sku_ids.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))

    results: Dict[int, Dict] = {}
    for sid in ids:
        prod = db.query(ProductCatalog).filter(ProductCatalog.sku_id == sid).first()
        if prod:
            base = get_rolling_median_baseline(db, sid, buyer_id=buyer_id)
            results[sid] = {
                "sku_id": sid,
                "marathi_name": prod.marathi_name,
                "canonical_unit": prod.canonical_unit,
                "display_unit": get_display_unit(prod.canonical_unit),
                "baseline_rate": base
            }

    return {"baselines": results}

@router.get("/config")
def get_volatility_config(db: Session = Depends(get_db)):
    cfg = db.query(VolatilityConfig).filter(VolatilityConfig.id == 1).first()
    if not cfg:
        return {
            "balanced_abs": settings.VOLATILITY_BALANCED_ABS,
            "surge_gt": settings.VOLATILITY_SURGE_GT,
            "dip_lt": settings.VOLATILITY_DIP_LT,
            "median_window": settings.VOLATILITY_MEDIAN_WINDOW
        }
    return {
        "balanced_abs": cfg.balanced_abs,
        "surge_gt": cfg.surge_gt,
        "dip_lt": cfg.dip_lt,
        "median_window": cfg.median_window
    }
