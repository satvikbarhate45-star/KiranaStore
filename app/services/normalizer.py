"""
KiranaStore Enterprise Central Normalization Utility (SSOT)
Deterministic, zero-overflow measurement parser and financial normalization engine.
Enforces strict mathematical normalization across all KiranaStore components:
- OCR parsing & tokenization
- Database persistence & migrations
- Budget simulation engine
- Reverse POS counter billing
- 3-Way audit, comparator & time-series trends
"""

import re
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any

DEV_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Max realistic Kirana retail rate per kg/L/unit before anomaly tripwire
RATE_ANOMALY_LIMIT = 50000.0

@dataclass
class NormalizedMeasurement:
    base_quantity: float      # Standardized metric scale: kg, L, or discrete count (float)
    standard_unit: str      # Canonical base unit: 'किलो', 'ली', 'पाकीट', 'नग', 'डबा', 'तोळा', 'डझन'
    display_unit: str       # Display metric label: 'ग्रॅम', 'मिली', 'किलो', 'ली', 'पाकीट', etc.
    raw_quantity_str: str   # Cleaned input string (e.g., '250 ग्रॅम', '15 किलो')

@dataclass
class NormalizedLine:
    line_total: float         # Exact currency sum billed for the item
    normalized_quantity: float# Converted base quantity in kg, Ltr, or count
    unit_base_rate: float     # Standardized rate per kg, Ltr, or unit (₹/किलो, ₹/ली)
    display_unit: str         # Standard metric label ('किलो', 'ली', 'नग', 'पाकीट')
    raw_quantity_str: str     # Preserved original measurement text
    is_anomaly: bool = False  # Flagged if rate exceeds RATE_ANOMALY_LIMIT or <= 0
    anomaly_reason: Optional[str] = None

def to_ascii_digits(text: str) -> str:
    """Converts Devanagari numerals ०-९ to standard ASCII 0-9."""
    if not text:
        return ""
    for dev, asc in DEV_DIGITS.items():
        text = text.replace(dev, asc)
    return text

def parse_measurement(quantity_str: str, default_unit: str = "किलो") -> NormalizedMeasurement:
    """
    Robust Regex Tokenizer & Measurement Normalizer (SSOT):
    - Accurately parses mixed Devanagari/English numerical values, decimals, and fractional text.
    - NEVER drops multi-digit quantities (e.g. '250' never falls back to '1').
    - Mass: Grams are standardized to fractional kilograms (base_quantity = grams / 1000.0), standard_unit = 'किलो'.
    - Volume: Milliliters are standardized to fractional liters (base_quantity = ml / 1000.0), standard_unit = 'ली'.
    - Counts: Packets, pcs, boxes, bunches, dozens, tola are mapped to integer/float scale.
    """
    raw_input = str(quantity_str or "").strip()
    if not raw_input:
        return NormalizedMeasurement(
            base_quantity=1.0,
            standard_unit=default_unit,
            display_unit=default_unit,
            raw_quantity_str="1 किलो"
        )

    norm_str = to_ascii_digits(raw_input.lower())

    # 1. Colloquial Marathi Fractions & Fraction Strings
    Q: Optional[float] = None
    if any(f in norm_str for f in ["अर्धा", "आधा", "1/2", "१/२"]):
        if "दीड" in norm_str:
            Q = 1.5
        elif "अडीच" in norm_str:
            Q = 2.5
        else:
            Q = 0.5
    elif any(f in norm_str for f in ["पाव किलो", "1/4", "१/४", "पाव"]):
        Q = 0.25
    elif any(f in norm_str for f in ["पावणे", "पाऊण", "3/4", "३/४"]):
        Q = 0.75
    elif "सव्वा" in norm_str or "1.25" in norm_str or "१.२५" in norm_str:
        Q = 1.25
    elif "दीड" in norm_str or "1.5" in norm_str:
        Q = 1.5
    elif "अडीच" in norm_str or "2.5" in norm_str:
        Q = 2.5

    # 2. Multi-digit Number Extraction (Strictly Preserve 250, 500, 100, 15, etc.)
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

    if Q is None or Q <= 0:
        Q = 1.0

    # 3. Unit Classification & Scaling
    # Liquid Volume: ml vs L
    if any(u in norm_str for u in ["मिली", "ml", "milli"]):
        base_qty = round(Q / 1000.0, 4)
        standard_unit = "ली"
        display_unit = "मिली" if Q < 1000.0 else "ली"
    elif any(u in norm_str for u in ["लिटर", "लीटर", "ली", "ltr", "liter", "litre"]) or re.search(r'\b(?:l)\b', norm_str):
        base_qty = float(Q)
        standard_unit = "ली"
        display_unit = "ली"

    # Mass: Kilograms vs Grams
    elif any(u in norm_str for u in ["किलो", "kg", "k.g.", "kilo"]):
        base_qty = float(Q)
        standard_unit = "किलो"
        display_unit = "किलो"
    elif any(u in norm_str for u in ["ग्रॅम", "ग्राम", "gm", "gram", "grams"]) or re.search(r'\b(?:g|gms)\b', norm_str):
        # Strictly scale grams to kilograms: 250 gm -> 0.25 kg
        base_qty = round(Q / 1000.0, 4)
        standard_unit = "किलो"
        display_unit = "ग्रॅम" if Q < 1000.0 else "किलो"

    # Discrete Count Units: Packets, Pieces, Boxes, Tola, Dozen
    elif any(u in norm_str for u in ["पाकीट", "पॅकेट", "पॅक", "pkt", "packet", "pouch"]):
        base_qty = float(round(Q))
        standard_unit = "पाकीट"
        display_unit = "पाकीट"
    elif any(u in norm_str for u in ["नग", "pcs", "piece", "pieces", "तुकडे"]):
        base_qty = float(round(Q))
        standard_unit = "नग"
        display_unit = "नग"
    elif any(u in norm_str for u in ["डबा", "डबे", "tin", "box", "खोके"]):
        base_qty = float(round(Q))
        standard_unit = "डबा"
        display_unit = "डबा"
    elif any(u in norm_str for u in ["तोळा", "तोल"]):
        base_qty = float(round(Q))
        standard_unit = "तोळा"
        display_unit = "तोळा"
    elif any(u in norm_str for u in ["डझन", "dozen", "doz"]):
        base_qty = float(Q)
        standard_unit = "डझन"
        display_unit = "डझन"
    elif any(u in norm_str for u in ["पेंढी", "पेंढ्या", "bunch"]):
        base_qty = float(round(Q))
        standard_unit = "पेंढी"
        display_unit = "पेंढी"
    else:
        # Default fallback to kg
        base_qty = float(Q)
        standard_unit = default_unit
        display_unit = default_unit

    return NormalizedMeasurement(
        base_quantity=base_qty,
        standard_unit=standard_unit,
        display_unit=display_unit,
        raw_quantity_str=raw_input
    )

def normalize_line_item(
    line_total: float,
    quantity_str: str,
    raw_unit: Optional[str] = None
) -> NormalizedLine:
    """
    STRICT MATHEMATICAL NORMALIZATION (SSOT):
    1. Extracts numerical base_quantity (scaled to base kg, L, or count).
    2. Derives unit_base_rate = line_total / base_quantity.
       - NEVER divides by raw gram values (e.g. 100 / 250 = 0.4 ₹/gm is ILLEGAL).
       - Rate is strictly ₹/किलो: 100 / 0.25 = ₹400.00 / किलो.
    3. Overflow & Anomaly Guard:
       - Flag if unit_base_rate > 50,000 or <= 0.
    """
    total = round(float(line_total or 0.0), 2)
    measurement = parse_measurement(quantity_str, default_unit=raw_unit or "किलो")
    base_qty = measurement.base_quantity if measurement.base_quantity > 0 else 1.0

    raw_rate = total / base_qty
    unit_base_rate = round(raw_rate, 4)

    # Anomaly tripwire
    is_anomaly = False
    anomaly_reason = None
    if unit_base_rate > RATE_ANOMALY_LIMIT:
        is_anomaly = True
        anomaly_reason = f"असामान्य दर: ₹{unit_base_rate:.2f}/{measurement.standard_unit} मर्यादा (₹{RATE_ANOMALY_LIMIT}) पेक्षा जास्त आहे."
    elif unit_base_rate <= 0 and total > 0:
        is_anomaly = True
        anomaly_reason = "अवैध दर: प्रमाण शून्य किंवा ऋण असू शकत नाही."

    return NormalizedLine(
        line_total=total,
        normalized_quantity=round(base_qty, 4),
        unit_base_rate=unit_base_rate,
        display_unit=measurement.standard_unit,
        raw_quantity_str=measurement.raw_quantity_str,
        is_anomaly=is_anomaly,
        anomaly_reason=anomaly_reason
    )

