import os
import json
import re
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.config import settings
from app.models import CachedCommodityPrice, ProductCatalog
from app.services.regex_parser import normalize_text, normalize_canonical_commodity

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RATES_FILE_PATH = BASE_DIR / "data" / "maharashtra_mandi_rates.json"

# In-memory fallback dataset for staples
FALLBACK_APMC_RATES: Dict[str, Dict[str, Any]] = {
    "साखर": {"canonical_unit": "kg", "modal_price": 40.0, "min_price": 38.0, "max_price": 42.0, "market": "पुणे / मुंबई APMC"},
    "गोडतेल": {"canonical_unit": "L", "modal_price": 130.0, "min_price": 125.0, "max_price": 138.0, "market": "सोलापूर / लातूर APMC"},
    "शेंगदाणा तेल": {"canonical_unit": "L", "modal_price": 185.0, "min_price": 175.0, "max_price": 198.0, "market": "जळगाव / सांगली APMC"},
    "तूर डाळ": {"canonical_unit": "kg", "modal_price": 155.0, "min_price": 145.0, "max_price": 168.0, "market": "लातूर / अकोला APMC"},
    "तांदूळ": {"canonical_unit": "kg", "modal_price": 48.0, "min_price": 42.0, "max_price": 58.0, "market": "नागपूर / कोल्हापूर APMC"},
    "गव्हाचे पीठ": {"canonical_unit": "kg", "modal_price": 36.0, "min_price": 32.0, "max_price": 40.0, "market": "नाशिक / अहिल्यानगर APMC"},
    "रवा": {"canonical_unit": "kg", "modal_price": 38.0, "min_price": 34.0, "max_price": 42.0, "market": "पुणे APMC"},
    "मूग डाळ": {"canonical_unit": "kg", "modal_price": 118.0, "min_price": 110.0, "max_price": 126.0, "market": "जालना / बीड APMC"},
    "कांदा": {"canonical_unit": "kg", "modal_price": 28.0, "min_price": 22.0, "max_price": 35.0, "market": "लासलगाव / पिंपळगाव APMC"},
    "बटाटा": {"canonical_unit": "kg", "modal_price": 26.0, "min_price": 20.0, "max_price": 32.0, "market": "मंचर / खेड APMC"},
    "शेंगदाणे": {"canonical_unit": "kg", "modal_price": 115.0, "min_price": 105.0, "max_price": 125.0, "market": "कराड / सांगली APMC"},
    "पोहे": {"canonical_unit": "kg", "modal_price": 45.0, "min_price": 40.0, "max_price": 50.0, "market": "नागपूर APMC"},
    "गूळ": {"canonical_unit": "kg", "modal_price": 52.0, "min_price": 48.0, "max_price": 58.0, "market": "कोल्हापूर APMC"},
    "बेसन": {"canonical_unit": "kg", "modal_price": 85.0, "min_price": 78.0, "max_price": 92.0, "market": "पुणे APMC"},
    "चणा डाळ": {"canonical_unit": "kg", "modal_price": 82.0, "min_price": 76.0, "max_price": 90.0, "market": "लातूर APMC"},
    "हळद": {"canonical_unit": "kg", "modal_price": 220.0, "min_price": 200.0, "max_price": 240.0, "market": "सांगली APMC"},
    "जिरे": {"canonical_unit": "kg", "modal_price": 320.0, "min_price": 290.0, "max_price": 350.0, "market": "उंझा / मुंबई APMC"},
    "मोहरी": {"canonical_unit": "kg", "modal_price": 90.0, "min_price": 80.0, "max_price": 100.0, "market": "सोलापूर APMC"},
    "मीठ": {"canonical_unit": "kg", "modal_price": 22.0, "min_price": 18.0, "max_price": 28.0, "market": "मुंबई APMC"},
    "चहा पावडर": {"canonical_unit": "kg", "modal_price": 360.0, "min_price": 320.0, "max_price": 420.0, "market": "मुंबई APMC"},
    "अगरबत्ती": {"canonical_unit": "packet", "modal_price": 45.0, "min_price": 30.0, "max_price": 60.0, "market": "स्थानिक घाऊक बाजार"},
    "साबण": {"canonical_unit": "pcs", "modal_price": 35.0, "min_price": 25.0, "max_price": 45.0, "market": "स्थानिक घाऊक बाजार"},
}

def load_local_apmc_rates() -> Dict[str, Dict[str, Any]]:
    """
    Strategy A: Reads benchmark rates from local data/maharashtra_mandi_rates.json.
    """
    if RATES_FILE_PATH.exists():
        try:
            with open(RATES_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("commodities", {})
        except Exception as e:
            print(f"[GovPriceService] Failed reading {RATES_FILE_PATH}: {e}")
    return FALLBACK_APMC_RATES

def query_gemini_search_grounding(commodity_name: str) -> Optional[Dict[str, Any]]:
    """
    PURGED UNDER PILLAR 1: No external search grounding or online scrapers.
    """
    return None

def get_canonical_commodity_key(name: str) -> str:
    """Normalizes commodity query string to match APMC benchmarks."""
    if not name:
        return ""
    base = re.sub(r'\[.*?\]', '', name).strip()
    norm = normalize_canonical_commodity(base)

    # Specific commodity mappings for APMC keys
    if norm in ["गहू पीठ", "गव्हाचे पीठ", "कणिक", "आटा"]:
        return "गव्हाचे पीठ"
    if norm in ["गोडतेल", "खाद्यतेल"]:
        return "गोडतेल"
    if norm in ["शेंगदाणा तेल"]:
        return "शेंगदाणा तेल"
    if norm in ["शेंगदाणे", "शेंगदाणा"]:
        return "शेंगदाणे"
    if norm in ["साखर", "सक्कर"]:
        return "साखर"
    if norm in ["तूर डाळ", "तुरीची डाळ"]:
        return "तूर डाळ"
    if norm in ["तांदूळ", "भात"]:
        return "तांदूळ"
    if norm in ["मूग डाळ"]:
        return "मूग डाळ"
    if norm in ["चणा डाळ"]:
        return "चणा डाळ"
    if norm in ["रवा", "सुजी"]:
        return "रवा"
    if norm in ["कांदा", "कांदे"]:
        return "कांदा"
    if norm in ["बटाटा", "बटाटे"]:
        return "बटाटा"
    if norm in ["पोहे"]:
        return "पोहे"
    if norm in ["गूळ"]:
        return "गूळ"
    if norm in ["बेसन"]:
        return "बेसन"
    if norm in ["हळद"]:
        return "हळद"
    if norm in ["जिरे"]:
        return "जिरे"
    if norm in ["मोहरी"]:
        return "मोहरी"
    if norm in ["मीठ"]:
        return "मीठ"
    if norm in ["चहा पावडर"]:
        return "चहा पावडर"
    if norm in ["अगरबत्ती"]:
        return "अगरबत्ती"
    if norm in ["साबुदाणा", "शाबूदाणा", "शाबू"]:
        return "साबुदाणा"
    if norm in ["साबण"]:
        return "साबण"
    return norm or base

def get_commodity_market_rate(
    db: Session,
    commodity_name: str,
    force_refresh: bool = False,
    use_online_grounding: bool = False
) -> Dict[str, Any]:
    """
    MODULE 3: Zero-KYC Government & APMC Market Price Resolver
    Checks 12-hour cached rates in cached_commodity_prices.
    Strategy A (Default): Local Maharashtra APMC retail benchmark rates from data/maharashtra_mandi_rates.json (0ms latency, zero KYC).
    Strategy B: Optional live Gemini Search grounding if use_online_grounding=True.
    """
    key = get_canonical_commodity_key(commodity_name)
    now = datetime.datetime.utcnow()

    # 1. Check DB Cache
    cached = db.query(CachedCommodityPrice).filter(
        CachedCommodityPrice.commodity_name == key
    ).first()

    if cached and not force_refresh and cached.expires_at > now:
        return {
            "commodity_name": cached.commodity_name,
            "canonical_unit": cached.canonical_unit,
            "retail_modal_rate": cached.retail_modal_rate,
            "min_price": cached.min_price,
            "max_price": cached.max_price,
            "source": cached.source,
            "market_location": cached.market_location,
            "last_updated": cached.last_updated.isoformat(),
            "is_cached": True
        }

    # 2. Strategy A: Load Local Maharashtra APMC Rates first (fast & reliable)
    local_rates = load_local_apmc_rates()
    commodity_info = local_rates.get(key)
    if not commodity_info:
        for k, val in local_rates.items():
            if k in key or key in k:
                commodity_info = val
                break

    grounded = None  # Online search grounding permanently purged under Pillar 1

    if grounded:
        rate_val = grounded["modal_price"]
        min_p = grounded["min_price"]
        max_p = grounded["max_price"]
        unit = grounded["canonical_unit"]
        src = "gemini_search_grounding"
        market = grounded["market"]
    elif commodity_info:
        rate_val = float(commodity_info.get("modal_price", 50.0))
        min_p = float(commodity_info.get("min_price", rate_val * 0.95))
        max_p = float(commodity_info.get("max_price", rate_val * 1.05))
        unit = commodity_info.get("canonical_unit", "kg")
        src = "apmc_local"
        market = commodity_info.get("market_center", "Maharashtra APMC Modal")
    else:
        # Safe default fallback
        rate_val = 50.0
        min_p = 45.0
        max_p = 55.0
        unit = "kg"
        src = "apmc_default"
        market = "Maharashtra Modal Average"

    expires_at = now + datetime.timedelta(hours=12)

    # Save/Update Cache in DB
    if cached:
        cached.retail_modal_rate = rate_val
        cached.min_price = min_p
        cached.max_price = max_p
        cached.canonical_unit = unit
        cached.source = src
        cached.market_location = market
        cached.last_updated = now
        cached.expires_at = expires_at
    else:
        new_cache = CachedCommodityPrice(
            commodity_name=key,
            canonical_unit=unit,
            retail_modal_rate=rate_val,
            min_price=min_p,
            max_price=max_p,
            source=src,
            market_location=market,
            last_updated=now,
            expires_at=expires_at
        )
        db.add(new_cache)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[GovPriceService] DB cache commit error: {e}")

    return {
        "commodity_name": key,
        "canonical_unit": unit,
        "retail_modal_rate": rate_val,
        "min_price": min_p,
        "max_price": max_p,
        "source": src,
        "market_location": market,
        "last_updated": now.isoformat(),
        "is_cached": False
    }

def get_all_benchmark_rates(db: Session) -> List[Dict[str, Any]]:
    """Returns all standard Maharashtra APMC staple benchmark rates."""
    local_data = load_local_apmc_rates()
    results = []
    for comm_name in local_data.keys():
        rate_info = get_commodity_market_rate(db, comm_name, force_refresh=False)
        results.append(rate_info)
    return results

def calculate_govt_expected_total(
    db: Session,
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    MODULE 4 (Baseline Simulator):
    Calculates expected cost based on Government APMC benchmark rates for a list of items.
    Returns govt_total_amount and individual item breakdown.
    """
    govt_total = 0.0
    breakdown = []

    for idx, item in enumerate(items):
        raw_name = item.get("name") or item.get("item_name") or item.get("original_raw") or f"वस्तू {idx+1}"
        qty = float(item.get("qty") or item.get("quantity") or 1.0)
        norm_qty = float(item.get("quantity_norm") or qty)
        unit = str(item.get("unit") or item.get("canonical_unit") or "kg")

        rate_info = get_commodity_market_rate(db, raw_name)
        bench_rate = rate_info["retail_modal_rate"]

        # Calculate expected item amount
        # If item has small grams / milliliters, normalize correctly
        item_expected = round(bench_rate * norm_qty, 2)
        govt_total += item_expected

        breakdown.append({
            "item_index": idx,
            "name": raw_name,
            "qty": qty,
            "quantity_norm": norm_qty,
            "unit": unit,
            "govt_rate": bench_rate,
            "govt_amount": item_expected,
            "market_location": rate_info["market_location"]
        })

    return {
        "govt_total_amount": round(govt_total, 2),
        "items_breakdown": breakdown
    }


def get_festival_surge_advice(ref_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    MODULE 6: Festival Surge Predictor & Bulk Stocking Advice Engine.
    Tracks major Maharashtra festival timelines (Ganesh Utsav, Navratri, Diwali, Wedding Season).
    Computes impending wholesale surge risks on edible oils, sugar, and dry fruits.
    Provides actionable smart buying advice:
    "💡 सणासुदीचा स्मार्ट खरेदी सल्ला: पुढील महिन्यात गोडतेलाचे भाव ₹१५ ते ₹२५ ने वाढण्याची शक्यता आहे.
    आत्ताच खरेदी केल्यास अंदाजे ₹१५० ते ₹२०० वाचू शकतात!"
    """
    if ref_date is None:
        ref_date = datetime.date.today()

    cur_year = ref_date.year
    # Festival approximate calendar for Maharashtra
    festivals = [
        {"name": "गुढीपाडवा व चैत्र उत्सव", "month": 3, "day": 25, "surge_oil": 10.0, "surge_sugar": 2.0},
        {"name": "गणेशोत्सव", "month": 9, "day": 10, "surge_oil": 15.0, "surge_sugar": 3.0},
        {"name": "नवरात्रोत्सव व दसरा", "month": 10, "day": 15, "surge_oil": 18.0, "surge_sugar": 4.0},
        {"name": "दिवाळी व भाऊबीज", "month": 11, "day": 1, "surge_oil": 20.0, "surge_sugar": 5.0},
        {"name": "लग्नसराई व हिवाळी हंगाम", "month": 11, "day": 25, "surge_oil": 15.0, "surge_sugar": 3.0},
        {"name": "मकर संक्रांती", "month": 1, "day": 14, "surge_oil": 10.0, "surge_sugar": 3.0},
    ]

    # Find upcoming festival dynamically based on target_date - ref_date
    upcoming_candidates = []
    for f in festivals:
        f_date = datetime.date(cur_year, f["month"], f["day"])
        diff_days = (f_date - ref_date).days
        if diff_days >= 0:
            upcoming_candidates.append((diff_days, f, f_date))
        else:
            f_date_next = datetime.date(cur_year + 1, f["month"], f["day"])
            diff_days_next = (f_date_next - ref_date).days
            upcoming_candidates.append((diff_days_next, f, f_date_next))

    upcoming_candidates.sort(key=lambda x: x[0])
    min_days_diff, active_festival, target_f_date = upcoming_candidates[0]

    oil_min_surge = active_festival.get("surge_oil", 15.0)
    oil_max_surge = oil_min_surge + 10.0
    sugar_min_surge = active_festival.get("surge_sugar", 3.0)
    sugar_max_surge = sugar_min_surge + 2.0

    advice_text = (
        f"💡 सणासुदीचा स्मार्ट खरेदी सल्ला: पुढील महिन्यात गोडतेलाचे भाव ₹{int(oil_min_surge)} ते ₹{int(oil_max_surge)} ने "
        f"वाढण्याची शक्यता आहे. आत्ताच खरेदी केल्यास अंदाजे ₹१५० ते ₹२०० वाचू शकतात!"
    )

    surge_details = [
        {
            "commodity": "गोडतेल (खाद्यतेल)",
            "expected_surge": f"₹{int(oil_min_surge)} - ₹{int(oil_max_surge)} / लिटर",
            "historical_spike": "+14%",
            "reason": f"{active_festival['name']} काळात फराळ व तळणाच्या पदार्थांमुळे राज्यभरात मोठी मागणी."
        },
        {
            "commodity": "शेंगदाणा तेल",
            "expected_surge": "₹२० - ₹३० / लिटर",
            "historical_spike": "+16%",
            "reason": "सणासुदीच्या काळात शुद्ध शेंगदाणा तेलाचा घाऊक तुटवडा निर्माण होतो."
        },
        {
            "commodity": "साखर व गूळ",
            "expected_surge": f"₹{int(sugar_min_surge)} - ₹{int(sugar_max_surge)} / किलो",
            "historical_spike": "+8%",
            "reason": "मिठाई, लाडू व सणांच्या गोड पदार्थांसाठी साखर कारखान्यांकडून दरात वाढ."
        },
        {
            "commodity": "काजू, बदाम व सुका मेवा",
            "expected_surge": "₹५० - ₹१०० / किलो",
            "historical_spike": "+12%",
            "reason": "भेटवस्तू पाकिटे (Gifting packs) व ड्रायफ्रूट लाडूसाठी प्रचंड मागणी."
        }
    ]

    return {
        "festival_name": active_festival["name"],
        "days_until": max(0, min_days_diff),
        "is_active_window": True,
        "affected_commodities": ["गोडतेल", "शेंगदाणा तेल", "साखर", "काजू", "बदाम", "रवा", "बेसन"],
        "advice_card_mr": advice_text,
        "estimated_savings_min": 150.0,
        "estimated_savings_max": 200.0,
        "surge_details": surge_details
    }

