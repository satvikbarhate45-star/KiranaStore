import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any

# Marathi Fraction word mappings
FRACTION_MAP = {
    "पाव": 0.25,
    "अर्धा": 0.5,
    "अर्धी": 0.5,
    "अर्धे": 0.5,
    "पाऊण": 0.75,
    "सव्वा": 1.25,
    "दीड": 1.5,
    "अडीच": 2.5,
}

# Devanagari digit to ASCII digit translation
DEV_DIGIT_MAP = str.maketrans("०१२३४५६७८९", "0123456789")

# Canonical & Display Unit Metadata
# Format: raw_key -> (canonical_unit, factor_to_canon, display_unit_mr, unit_code)
UNIT_METADATA = {
    # Weight (Grams & Kilograms)
    "g": ("kg", 0.001, "ग्रॅम", "gm"),
    "gm": ("kg", 0.001, "ग्रॅम", "gm"),
    "gms": ("kg", 0.001, "ग्रॅम", "gm"),
    "gram": ("kg", 0.001, "ग्रॅम", "gm"),
    "grams": ("kg", 0.001, "ग्रॅम", "gm"),
    "ग्रॅम": ("kg", 0.001, "ग्रॅम", "gm"),
    "ग्राम": ("kg", 0.001, "ग्रॅम", "gm"),
    "kg": ("kg", 1.0, "किलो", "kg"),
    "kgs": ("kg", 1.0, "किलो", "kg"),
    "kilo": ("kg", 1.0, "किलो", "kg"),
    "किलो": ("kg", 1.0, "किलो", "kg"),
    "कि.": ("kg", 1.0, "किलो", "kg"),

    # Volume (Milliliters & Liters)
    "ml": ("L", 0.001, "मिली", "ml"),
    "मिली": ("L", 0.001, "मिली", "ml"),
    "मि.ली.": ("L", 0.001, "मिली", "ml"),
    "l": ("L", 1.0, "लिटर", "L"),
    "ltr": ("L", 1.0, "लिटर", "L"),
    "liter": ("L", 1.0, "लिटर", "L"),
    "litre": ("L", 1.0, "लिटर", "L"),
    "लिटर": ("L", 1.0, "लिटर", "L"),

    # Count & Packages
    "dozen": ("dozen", 1.0, "डझन", "dozen"),
    "डझन": ("dozen", 1.0, "डझन", "dozen"),
    "doz": ("dozen", 1.0, "डझन", "dozen"),
    "pcs": ("pcs", 1.0, "नग", "pcs"),
    "नग": ("pcs", 1.0, "नग", "pcs"),
    "तुकडे": ("pcs", 1.0, "नग", "pcs"),
    "piece": ("pcs", 1.0, "नग", "pcs"),
    "pieces": ("pcs", 1.0, "नग", "pcs"),
    "packet": ("packet", 1.0, "पाकीट", "packet"),
    "packets": ("packet", 1.0, "पाकीट", "packet"),
    "पाकीट": ("packet", 1.0, "पाकीट", "packet"),
    "पाकिटे": ("packet", 1.0, "पाकीट", "packet"),
    "pouch": ("packet", 1.0, "पाकीट", "packet"),
    "pouches": ("packet", 1.0, "पाकीट", "packet"),
    "pkt": ("packet", 1.0, "पाकीट", "packet"),
    "पेंढी": ("bunch", 1.0, "पेंढी", "पेंढी"),
    "पेंढ्या": ("bunch", 1.0, "पेंढी", "पेंढी"),
    "bunch": ("bunch", 1.0, "पेंढी", "पेंढी"),
    "bunches": ("bunch", 1.0, "पेंढी", "पेंढी"),
    "pendhi": ("bunch", 1.0, "पेंढी", "पेंढी"),
}

CURRENCY_REGEX = r"(?:₹|rs\.?|rupees?|रुपये|रुपयांचे|रुपयांची|रुपयाचे|रु\.?|inr)"

# Known Commercial Kirana Brands (longest first for greedy matching)
KNOWN_BRANDS = [
    ("नंबर १", ["नंबर १", "नंबर 1", "नं १", "नं. १", "no 1", "no. 1", "number 1", "number one", "godrej no 1"]),
    ("झेड ब्लॅक", ["झेड ब्लॅक", "zed black", "zedblack"]),
    ("वाघ बकरी", ["वाघ बकरी", "wagh bakri", "waghbakri"]),
    ("रेड लेबल", ["रेड लेबल", "red label", "redlabel"]),
    ("ताजमहल", ["ताजमहल", "taj mahal", "tajmahal"]),
    ("सर्फ एक्सेल", ["सर्फ एक्सेल", "surf excel", "surfexcel"]),
    ("क्लोजअप", ["क्लोजअप", "close up", "closeup"]),
    ("पारले-जी", ["पारले-जी", "पारले जी", "parle-g", "parle g", "parleg"]),
    ("फॉर्च्यून", ["फॉर्च्यून", "fortune"]),
    ("धारा", ["धारा", "dhara"]),
    ("जेमिनी", ["जेमिनी", "gemini"]),
    ("सफोला", ["सफोला", "saffola"]),
    ("महाकोश", ["महाकोश", "mahakosh"]),
    ("सनरिच", ["सनरिच", "sunrich"]),
    ("रुचि", ["रुचि", "ruchi"]),
    ("तिरुपती", ["तिरुपती", "tirupati"]),
    ("विनर", ["विनर", "winner"]),
    ("विलास", ["विलास", "vilas"]),
    ("मंगलदीप", ["मंगलदीप", "mangaldeep"]),
    ("मोक्ष", ["मोक्ष", "moksh"]),
    ("सायकल", ["सायकल", "cycle"]),
    ("संतूर", ["संतूर", "santoor"]),
    ("लक्स", ["लक्स", "lux"]),
    ("लाइफबॉय", ["लाइफबॉय", "lifebuoy"]),
    ("डेटॉल", ["डेटॉल", "dettol"]),
    ("हमाम", ["हमाम", "hamam"]),
    ("मेडीमिक्स", ["मेडीमिक्स", "medimix"]),
    ("डव्ह", ["डव्ह", "dove"]),
    ("विम", ["विम", "vim"]),
    ("निरमा", ["निरमा", "nirma"]),
    ("घडी", ["घडी", "ghadi"]),
    ("रिन", ["रिन", "rin"]),
    ("एरियल", ["एरियल", "ariel"]),
    ("व्हील", ["व्हील", "wheel"]),
    ("टाटा", ["टाटा", "tata"]),
    ("सोसायटी", ["सोसायटी", "society"]),
    ("एव्हरेस्ट", ["एव्हरेस्ट", "everest"]),
    ("सुहाना", ["सुहाना", "suhana"]),
    ("रामबंधू", ["रामबंधू", "rambandhu"]),
    ("एमडीएच", ["एमडीएच", "mdh"]),
    ("बादशाह", ["बादशाह", "badshah"]),
    ("कॅच", ["कॅच", "catch"]),
    ("आशीर्वाद", ["आशीर्वाद", "aashirvaad", "ashirwad"]),
    ("पतंजली", ["पतंजली", "patanjali"]),
    ("कोलगेट", ["कोलगेट", "colgate"]),
    ("पेप्सोडेंट", ["पेप्सोडेंट", "pepsodent"]),
    ("डाबर", ["डाबर", "dabur"]),
    ("पारले", ["पारले", "parle"]),
    ("ब्रिटानिया", ["ब्रिटानिया", "britannia"]),
    ("किसान", ["किसान", "kissan"]),
    ("मॅगी", ["मॅगी", "maggi"]),
]

# Canonical Commodity Normalization Mappings
COMMODITY_MAPPINGS = [
    # Strict Commodity Separation Rule 1: "गोडतेल" / "godtel" / "god tel" / "खाद्यतेल" -> "गोडतेल"
    ("गोडतेल", ["गोडतेल", "godtel", "god tel", "खाद्यतेल", "गोड तेल", "cooking oil", "refined oil"]),
    # Strict Peanuts Rule: Raw peanuts without oil -> "शेंगदाणे"
    ("शेंगदाणे", ["shengdane", "peanuts", "दाणे", "शेंगदाणा", "shengdana"]),
    ("अगरबत्ती", ["अगरबत्ती", "agarbatti", "incense sticks", "अगरबत्या", "धूप"]),
    ("साबण", ["साबण", "saban", "soap"]),
    ("साखर", ["साखर", "सक्कर", "sakhar", "sakkar", "sugar"]),
    ("मीठ", ["मीठ", "मिट", "mit", "salt", "mitha", "mith"]),
    ("चहा पावडर", ["चहा पावडर", "चहापत्ती", "tea powder", "चाय", "tea"]),
    ("तूर डाळ", ["तूर डाळ", "तुरीची डाल", "तुरीची डाळ", "tur dal", "toor dal", "turdaal"]),
    ("तांदूळ", ["तांदूळ", "तांदुल", "tandul", "rice", "kolam rice", "भात"]),
    ("गहू पीठ", ["गहू पीठ", "कणिक", "गव्हाचे पीठ", "wheat flour", "atta", "आटा", "गव्हाच पीठ", "गहूचे पीठ", "गव्हाचेपीठ", "गव्हाचपीठ"]),
    ("हळद", ["हळद", "हलद", "halad", "turmeric", "haldi"]),
    ("जिरे", ["जिरे", "जिरं", "jire", "jeera", "cumin"]),
    ("मोहरी", ["मोहरी", "mohari", "rai", "mustard"]),
    ("साजूक तूप", ["तूप", "साजूक तूप", "ghee", "sajuk tup", "pure ghee"]),
    ("मूग डाळ", ["मूग डाळ", "मुगाची डाळ", "moong dal", "mung dal"]),
    ("चणा डाळ", ["चणा डाळ", "हरभरा डाळ", "chana dal", "चना दाल"]),
    ("पोहे", ["पोहे", "जाड पोहे", "pohe", "poha"]),
    ("गूळ", ["गूळ", "गुल", "gul", "jaggery"]),
    ("बेसन", ["बेसन", "हरभरा पीठ", "gram flour", "besan"]),
    ("रवा", ["रवा", "सुजी", "rava", "sooji", "बारीक रवा"]),
    ("कांदा", ["कांदा", "कांदे", "kanda", "onion"]),
    ("बटाटा", ["बटाटा", "बटाटे", "batata", "potato", "आलू"]),
    ("कोथिंबीर", ["कोथिंबीर", "kothimbir", "coriander"]),
    ("मेथी", ["मेथी", "methi"]),
    ("पालक", ["पालक", "palak"]),
    ("बिस्कीट", ["बिस्कीट", "बिस्किट", "biscuit", "biscuits", "marie", "parle-g"]),
]

def extract_brand_and_commodity(raw_text: str) -> str:
    """
    Extracts commercial brand name and maps canonical commodity:
    - If brand present: '<वस्तूचे नाव> [<ब्रँड नाव>]' (e.g. 'अगरबत्ती [विलास]', 'साबण [नंबर १]', 'गोडतेल [फॉर्च्यून]')
    - If no brand: canonical product name without brackets (e.g. 'गोडतेल', 'साखर')
    - Strict Commodity Separation:
      * 'गोडतेल' / 'godtel' / 'god tel' / 'खाद्यतेल' MUST map strictly to 'गोडतेल'.
      * Only map to 'शेंगदाणा तेल' if BOTH words ('शेंगदाणा' / 'shengdana' AND 'तेल' / 'tel' / 'oil') appear together.
      * Raw peanuts ('शेंगदाणा' / 'shengdana') remain categorized as nuts/seeds ('शेंगदाणे'), never oil.
    """
    cleaned = normalize_text(raw_text).strip(" -:–x×\t")
    if not cleaned:
        return ""

    # Check if already in bracketed format: e.g. "अगरबत्ती [विलास]" or "साबण [नंबर १] (बॅच 2)"
    bracket_m = re.match(r"^(.*?)\s*\[(.*?)\](?:\s*\((.*?)\))?$", cleaned)
    if bracket_m:
        c_part = bracket_m.group(1).strip()
        b_part = bracket_m.group(2).strip()
        p_part = bracket_m.group(3)
        note_s = f" ({p_part.strip()})" if p_part else ""
        norm_c = extract_brand_and_commodity(c_part)
        norm_c_clean = re.sub(r"\s*\[.*?\]", "", norm_c).strip()
        norm_c_clean = re.sub(r"\s*\(.*?\)", "", norm_c_clean).strip()
        return f"{norm_c_clean} [{b_part}]{note_s}" if b_part else f"{norm_c_clean}{note_s}"

    # Extract optional parenthetical note
    note_m = re.search(r'\((.*?)\)', cleaned)
    note_suffix = f" ({note_m.group(1).strip()})" if note_m else ""

    lower_text = cleaned.lower()

    # 1. Detect Brand
    detected_brand: Optional[str] = None
    remaining_text = cleaned

    for brand_canon, aliases in KNOWN_BRANDS:
        for al in aliases:
            al_lower = al.lower()
            # Word boundary matching
            pat = re.compile(rf"(?:^|\b|\s){re.escape(al_lower)}(?:\b|\s|$)", re.IGNORECASE)
            if pat.search(lower_text):
                detected_brand = brand_canon
                # Remove matched alias from remaining text
                remaining_text = re.sub(rf"(?:^|\b|\s){re.escape(al)}(?:\b|\s|$)", " ", remaining_text, flags=re.IGNORECASE).strip()
                break
        if detected_brand:
            break

    rem_clean = normalize_text(remaining_text).strip(" -:–x×\t")
    rem_lower = rem_clean.lower()

    # 2. Strict Commodity Classification
    canonical_commodity: Optional[str] = None

    # Strict Rule 1: Groundnut Oil vs Godtel vs Raw Peanuts
    has_shengdana = bool(re.search(r"शेंगदाणा|शेंगदाणे|दाणे|shengdana|shengdane|groundnut", rem_lower if rem_lower else lower_text))
    has_oil = bool(re.search(r"तेल|tel|oil", rem_lower if rem_lower else lower_text))
    has_godtel = bool(re.search(r"गोडतेल|godtel|god\s*tel|खाद्यतेल|गोड\s*तेल|cooking\s*oil|refined\s*oil", rem_lower if rem_lower else lower_text))

    if has_godtel:
        canonical_commodity = "गोडतेल"
    elif has_shengdana and has_oil:
        canonical_commodity = "शेंगदाणा तेल"
    elif has_shengdana and not has_oil:
        canonical_commodity = "शेंगदाणे"
    elif has_oil and not has_shengdana and not has_godtel:
        # Default generic cooking oil maps to गोडतेल
        canonical_commodity = "गोडतेल"
    else:
        # Match against COMMODITY_MAPPINGS
        search_target = rem_lower if rem_lower else lower_text
        for comm_canon, aliases in COMMODITY_MAPPINGS:
            for al in aliases:
                al_lower = al.lower()
                pat = re.compile(rf"(?:^|\b|\s){re.escape(al_lower)}(?:\b|\s|$)", re.IGNORECASE)
                if pat.search(search_target) or search_target == al_lower:
                    canonical_commodity = comm_canon
                    break
            if canonical_commodity:
                break

    final_commodity = canonical_commodity or rem_clean or cleaned
    final_commodity_clean = re.sub(r"\s*\(.*?\)", "", final_commodity).strip()

    if detected_brand:
        return f"{final_commodity_clean} [{detected_brand}]{note_suffix}"
    if has_godtel:
        return f"गोडतेल{note_suffix}"
    if has_shengdana and has_oil:
        return f"शेंगदाणा तेल{note_suffix}"
    base_raw = rem_clean or cleaned
    if note_suffix and note_suffix not in base_raw:
        return f"{base_raw}{note_suffix}"
    return base_raw

def dev_to_ascii_digits(text: str) -> str:
    """Translates Devanagari numerals to ASCII digits."""
    if not text:
        return ""
    return text.translate(DEV_DIGIT_MAP)

def normalize_text(text: str) -> str:
    """NFC normalization, strip zero-width chars, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_fraction_string(val_str: str) -> Optional[float]:
    """Parses '1/2', '3/4', '1.5', '250', Devanagari numerals, etc."""
    if not val_str:
        return None
    val_str = dev_to_ascii_digits(val_str.strip())
    if "/" in val_str:
        parts = val_str.split("/")
        if len(parts) == 2:
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
                if den != 0:
                    return num / den
            except ValueError:
                pass
    try:
        return float(val_str.replace(",", "."))
    except ValueError:
        return None

def determine_retail_unit_for_currency(name_str: str) -> str:
    """Selects contextual retail packaging for currency-based grocery items."""
    lower = name_str.lower()
    if any(w in lower for w in ["kothimbir", "कोथिंबीर", "coriander", "मेथी", "methi", "पालक", "palak", "पुदिना", "pudina"]):
        return "पेंढी"
    elif any(w in lower for w in ["साबण", "soap", "पेन", "pen", "ब्रश", "brush"]):
        return "नग"
    return "पाकीट"

def extract_tokens_from_line(raw_line: str) -> Dict[str, Any]:
    """
    Parses a single grocery line into item name, quantity, unit, and optional budget target price.
    Guarantees zero-loss: under no circumstances is any line dropped or unhandled.
    """
    cleaned = normalize_text(raw_line)
    if not cleaned:
        return {
            "name": "",
            "qty": 1.0,
            "unit_str": "नग",
            "target_price": None
        }

    # Extract optional trailing parenthetical notes: e.g. "(बॅच 1)", "(बारीक)", "(पिशवी 2)"
    trailing_note = ""
    paren_match = re.search(r"\s*\(([^)]+)\)\s*$", cleaned)
    if paren_match:
        trailing_note = f" ({paren_match.group(1).strip()})"
        cleaned_for_parsing = cleaned[:paren_match.start()].strip()
    else:
        cleaned_for_parsing = cleaned

    # 1. Currency Token Intent: e.g. "mitha 10rupees", "20 rs kothimbir", "अगरबत्ती 50 रुपये", "10 रुपयांचे मीठ"
    # Trailing currency: [name] [number] [currency] OR [name] [currency] [number]
    cur_end_match = re.search(
        rf"(?:[\-:–x×]\s*|\s+)(?P<price>[0-9०-९]+(?:\.[0-9०-९]+)?)\s*(?P<cur>{CURRENCY_REGEX})\s*$",
        cleaned_for_parsing,
        re.IGNORECASE
    )
    if cur_end_match:
        name_part = cleaned_for_parsing[:cur_end_match.start()].strip(" -:–x×\t")
        price_val = parse_fraction_string(cur_end_match.group("price"))
        retail_unit = determine_retail_unit_for_currency(name_part)
        norm_name = extract_brand_and_commodity(name_part or cleaned_for_parsing)
        final_name = f"{norm_name or name_part or cleaned_for_parsing}{trailing_note}"
        return {
            "name": final_name,
            "qty": 1.0,
            "unit_str": retail_unit,
            "target_price": price_val
        }

    # Trailing currency reversed: [name] [currency] [number]
    cur_end_rev = re.search(
        rf"(?:[\-:–x×]\s*|\s+)(?P<cur>{CURRENCY_REGEX})\s*(?P<price>[0-9०-९]+(?:\.[0-9०-९]+)?)\s*$",
        cleaned_for_parsing,
        re.IGNORECASE
    )
    if cur_end_rev:
        name_part = cleaned_for_parsing[:cur_end_rev.start()].strip(" -:–x×\t")
        price_val = parse_fraction_string(cur_end_rev.group("price"))
        retail_unit = determine_retail_unit_for_currency(name_part)
        norm_name = extract_brand_and_commodity(name_part or cleaned_for_parsing)
        final_name = f"{norm_name or name_part or cleaned_for_parsing}{trailing_note}"
        return {
            "name": final_name,
            "qty": 1.0,
            "unit_str": retail_unit,
            "target_price": price_val
        }

    # Leading currency: e.g. "10 rs salt", "50 रुपये अगरबत्ती", "10 रुपयांचे मीठ", "10 rs बिस्कीट"
    cur_start_match = re.match(
        rf"^(?P<price>[0-9०-९]+(?:\.[0-9०-९]+)?)\s*(?P<cur>{CURRENCY_REGEX})\s*(?:[\-:–x×]\s*|\s+)(?P<name>.+)$",
        cleaned_for_parsing,
        re.IGNORECASE
    )
    if cur_start_match:
        name_part = cur_start_match.group("name").strip(" -:–x×\t")
        price_val = parse_fraction_string(cur_start_match.group("price"))
        retail_unit = determine_retail_unit_for_currency(name_part)
        norm_name = extract_brand_and_commodity(name_part or cleaned_for_parsing)
        final_name = f"{norm_name or name_part or cleaned_for_parsing}{trailing_note}"
        return {
            "name": final_name,
            "qty": 1.0,
            "unit_str": retail_unit,
            "target_price": price_val
        }

    # 2. Separator pattern with quantity and unit: e.g. "भगर - 1 किलो", "जिरे - 100 gm", "साखर - 5 kg"
    sep_match = re.search(
        r"[\-:–x×]\s*(?P<qty>[0-9०-९]+(?:[.,][0-9०-९]+)?|[0-9०-९]+\/[0-9०-९]+)\s*(?P<unit>[^\d०-९]*?)$",
        cleaned_for_parsing
    )
    if sep_match:
        name_part = cleaned_for_parsing[:sep_match.start()].strip(" -:–x×\t")
        qty_val = parse_fraction_string(sep_match.group("qty"))
        unit_str = sep_match.group("unit").strip()
        if name_part and qty_val is not None and qty_val > 0:
            norm_name = extract_brand_and_commodity(name_part)
            final_name = f"{norm_name or name_part}{trailing_note}"
            return {
                "name": final_name,
                "qty": qty_val,
                "unit_str": unit_str or "पाकीट",
                "target_price": None
            }

    # 3. Standalone Marathi fraction words: e.g. "साखर अर्धा किलो", "हळद पाव किलो"
    for f_word, f_val in FRACTION_MAP.items():
        pat = re.compile(rf'(?<![\u0900-\u097F]){re.escape(f_word)}(?![\u0900-\u097F])')
        m_frac = pat.search(cleaned_for_parsing)
        if m_frac:
            start, end = m_frac.span()
            name_part = cleaned_for_parsing[:start].strip(" -:–x×\t")
            rest = cleaned_for_parsing[end:].strip(" -:–x×\t")
            raw_n = name_part or cleaned_for_parsing.replace(f_word, "").strip()
            norm_name = extract_brand_and_commodity(raw_n)
            final_name = f"{norm_name or raw_n}{trailing_note}"
            return {
                "name": final_name,
                "qty": f_val,
                "unit_str": rest or "पाकीट",
                "target_price": None
            }

    # 4. Trailing quantity and unit without separator: e.g. "साखर२किलो", "shengdanatel2L", "तांदूळ 500 gm", "साबण ४ नग", "तांदूळ५००ग्रॅम", "नंबर १ साबण २ नग"
    trailing_match = re.search(
        r"(?<=\S)\s*(?P<qty>[0-9०-९]+(?:[.,][0-9०-९]+)?|[0-9०-९]+\/[0-9०-९]+)\s*(?P<unit>[^\d०-९]*?)$",
        cleaned_for_parsing
    )
    if trailing_match:
        name_part = cleaned_for_parsing[:trailing_match.start()].strip(" -:–x×\t")
        qty_val = parse_fraction_string(trailing_match.group("qty"))
        unit_str = trailing_match.group("unit").strip()
        if name_part and qty_val is not None and qty_val > 0:
            norm_name = extract_brand_and_commodity(name_part)
            final_name = f"{norm_name or name_part}{trailing_note}"
            return {
                "name": final_name,
                "qty": qty_val,
                "unit_str": unit_str or "पाकीट",
                "target_price": None
            }

    # 5. Leading quantity and unit: e.g. "2 kg साखर", "500 gm जिरे", "२ नग साबण"
    leading_match = re.match(
        r"^(?P<qty>[0-9०-९]+(?:[.,][0-9०-९]+)?|[0-9०-९]+\/[0-9०-९]+)\s*(?P<unit>[A-Za-z\u0900-\u097F.]+)?\s*[\-:–x×]?\s*(?P<name>.+)$",
        cleaned_for_parsing
    )
    if leading_match:
        name_part = leading_match.group("name").strip(" -:–x×\t")
        qty_val = parse_fraction_string(leading_match.group("qty"))
        unit_str = (leading_match.group("unit") or "").strip()
        if name_part and qty_val is not None and qty_val > 0:
            norm_name = extract_brand_and_commodity(name_part)
            final_name = f"{norm_name or name_part}{trailing_note}"
            return {
                "name": final_name,
                "qty": qty_val,
                "unit_str": unit_str or "पाकीट",
                "target_price": None
            }

    # 6. Generic Catch-All: preserve raw text as item label, default quantity: 1, unit: 'नग'
    catch_name = cleaned_for_parsing.strip(" -:–x×\t") or "किराणा वस्तू"
    norm_name = extract_brand_and_commodity(catch_name)
    final_name = f"{norm_name or catch_name}{trailing_note}"
    return {
        "name": final_name,
        "qty": 1.0,
        "unit_str": "नग",
        "target_price": None
    }

def parse_quantity_and_units(raw_qty: float, raw_unit_str: str, default_canonical: str = "kg") -> Dict[str, Any]:
    """
    Preserves original entered unit and display value without destructive scaling:
    - 'gm' / 'ग्रॅम' -> qty stays in grams (e.g. 100, 250, 500), display_unit='ग्रॅम', unit='gm', norm=0.001*qty
    - 'kg' / 'किलो' -> qty in kg, display_unit='किलो', unit='kg', norm=qty
    - 'L' / 'लिटर'  -> qty in L, display_unit='लिटर', unit='L', norm=qty
    - 'ml' / 'मिली' -> qty in ml (e.g. 500), display_unit='मिली', unit='ml', norm=0.001*qty
    - 'पाकीट'/'packet' -> qty in packets, display_unit='पाकीट', unit='packet', norm=qty
    - 'नग'/'pcs'    -> qty in pcs, display_unit='नग', unit='pcs', norm=qty
    - 'डझन'/'dozen' -> qty in dozens, display_unit='डझन', unit='dozen', norm=qty
    - 'पेंढी'/'bunch'-> qty in bunches, display_unit='पेंढी', unit='bunch', norm=qty
    """
    clean_unit = (raw_unit_str or "").lower().strip(" .\t")

    if clean_unit in UNIT_METADATA:
        canonical_unit, factor, display_unit, unit_code = UNIT_METADATA[clean_unit]
    else:
        if any(w in clean_unit for w in ["पाकीट", "पाकिटे", "packet", "pouch", "pkt"]):
            canonical_unit = "packet"
            factor = 1.0
            display_unit = "पाकीट"
            unit_code = "packet"
        elif any(w in clean_unit for w in ["नग", "pcs", "piece", "तुकडे"]):
            canonical_unit = "pcs"
            factor = 1.0
            display_unit = "नग"
            unit_code = "pcs"
        elif any(w in clean_unit for w in ["ग्रॅम", "ग्राम", "gm", "g"]):
            canonical_unit = "kg"
            factor = 0.001
            display_unit = "ग्रॅम"
            unit_code = "gm"
        elif any(w in clean_unit for w in ["किलो", "kg", "kilo"]):
            canonical_unit = "kg"
            factor = 1.0
            display_unit = "किलो"
            unit_code = "kg"
        elif any(w in clean_unit for w in ["लिटर", "ltr", "l", "liter", "litre"]):
            canonical_unit = "L"
            factor = 1.0
            display_unit = "लिटर"
            unit_code = "L"
        elif any(w in clean_unit for w in ["मिली", "ml"]):
            canonical_unit = "L"
            factor = 0.001
            display_unit = "मिली"
            unit_code = "ml"
        elif any(w in clean_unit for w in ["डझन", "dozen", "doz"]):
            canonical_unit = "dozen"
            factor = 1.0
            display_unit = "डझन"
            unit_code = "dozen"
        elif any(w in clean_unit for w in ["पेंढी", "पेंढ्या", "bunch", "pendhi"]):
            canonical_unit = "bunch"
            factor = 1.0
            display_unit = "पेंढी"
            unit_code = "bunch"
        else:
            canonical_unit = default_canonical
            factor = 1.0
            display_unit = "किलो" if default_canonical == "kg" else ("लिटर" if default_canonical == "L" else ("नग" if default_canonical == "pcs" else "पाकीट"))
            unit_code = default_canonical

    # Critical Guard: If small mass was entered erroneously as fraction of a gram or ml (e.g. 0.25 gm), fix to 250 gm
    if unit_code in ["gm", "ml"] and 0 < raw_qty < 1.0:
        raw_qty = round(raw_qty * 1000.0, 2)

    quantity_norm = round(raw_qty * factor, 4)
    display_qty = int(raw_qty) if raw_qty == int(raw_qty) else round(raw_qty, 2)

    return {
        "qty": display_qty,
        "unit": unit_code,
        "display_qty": display_qty,
        "display_unit": display_unit,
        "quantity_norm": quantity_norm,
        "canonical_unit": canonical_unit
    }

def normalize_unit_and_quantity(raw_qty: float, raw_unit_str: str, default_unit: str = "kg") -> Tuple[float, str]:
    """Backwards compatible wrapper returning (quantity_norm, canonical_unit)"""
    res = parse_quantity_and_units(raw_qty, raw_unit_str, default_unit)
    return res["quantity_norm"], res["canonical_unit"]

def calculate_similarity(s1: str, s2: str) -> float:
    """Computes a token/character similarity score between 0.0 and 1.0."""
    if not s1 or not s2:
        return 0.0
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0

    # Strict Commodity Separation Guards:
    # 1. "गोडतेल" / "godtel" must NEVER collide with "शेंगदाणा तेल"
    godtel_terms = {"गोडतेल", "godtel", "god tel", "खाद्यतेल", "गोड तेल"}
    shengdana_oil_terms = {"शेंगदाणा तेल", "shengdana tel", "shengdanatel", "groundnut oil", "shengdana oil", "शेंगदाणातेल"}

    is_s1_godtel = any(t in s1 for t in godtel_terms)
    is_s2_godtel = any(t in s2 for t in godtel_terms)
    is_s1_sheng_oil = any(t in s1 for t in shengdana_oil_terms)
    is_s2_sheng_oil = any(t in s2 for t in shengdana_oil_terms)

    if (is_s1_godtel and is_s2_sheng_oil) or (is_s2_godtel and is_s1_sheng_oil):
        return 0.0

    # 2. Raw Peanuts (nuts/seeds) must strictly NOT match oil
    is_s1_peanuts = ("शेंगदाणा" in s1 or "shengdana" in s1 or "शेंगदाणे" in s1) and not is_s1_sheng_oil
    is_s2_peanuts = ("शेंगदाणा" in s2 or "shengdana" in s2 or "शेंगदाणे" in s2) and not is_s2_sheng_oil

    if (is_s1_peanuts and is_s2_sheng_oil) or (is_s2_peanuts and is_s1_sheng_oil):
        return 0.0

    if s1 in s2 or s2 in s1:
        # Avoid short generic substring matches like "तेल" dominating specific items
        if min(len(s1), len(s2)) <= 3:
            return 0.60
        return 0.85

    # Filter out units, numbers and common packaging words from token intersection
    stop_tokens = {
        "पाकीट", "packet", "pkt", "pouch", "किलो", "kg", "ग्रॅम", "gm", "g",
        "लिटर", "l", "ltr", "नग", "pcs", "डबी", "box", "१", "२", "३", "४", "५",
        "1", "2", "3", "4", "5", "विशेष", "बॅच", "रुपये", "rs"
    }
    t1 = {w for w in s1.split() if w not in stop_tokens}
    t2 = {w for w in s2.split() if w not in stop_tokens}
    if t1 and t2:
        inter = len(t1.intersection(t2))
        union = len(t1.union(t2))
        if inter > 0:
            jaccard = inter / union
            return 0.4 + 0.6 * jaccard
    bigrams1 = set(s1[i:i+2] for i in range(len(s1)-1))
    bigrams2 = set(s2[i:i+2] for i in range(len(s2)-1))
    if not bigrams1 or not bigrams2:
        return 0.0
    inter = len(bigrams1.intersection(bigrams2))
    return (2.0 * inter) / (len(bigrams1) + len(bigrams2))


def normalize_canonical_commodity(name: str) -> str:
    """
    Normalizes product names for canonical comparison and deduplication.
    Strips bracketed brand markers, maps base Devanagari words to canonical commodity,
    and strips extra whitespace and punctuation.
    Example: 'गव्हाचे पीठ' -> 'गहू पीठ', 'कणिक' -> 'गहू पीठ', 'अगरबत्ती [विलास]' -> 'अगरबत्ती'
    """
    if not name:
        return ""
    # Strip brackets e.g. "अगरबत्ती [विलास]" -> "अगरबत्ती"
    base = re.sub(r'\[.*?\]', '', name).strip()
    clean = normalize_text(base).lower()

    # Check godtel & peanuts
    if any(t in clean for t in ["गोडतेल", "godtel", "god tel", "खाद्यतेल", "गोड तेल", "refined oil", "cooking oil"]):
        return "गोडतेल"
    if any(t in clean for t in ["शेंगदाणा तेल", "shengdana tel"]):
        return "शेंगदाणा तेल"
    if any(t in clean for t in ["शेंगदाणे", "शेंगदाणा", "shengdana", "shengdane"]):
        return "शेंगदाणे"

    for comm_canon, aliases in COMMODITY_MAPPINGS:
        for al in aliases:
            al_lower = al.lower()
            pat = re.compile(rf"(?:^|\b|\s){re.escape(al_lower)}(?:\b|\s|$)", re.IGNORECASE)
            if pat.search(clean) or clean == al_lower:
                return comm_canon.lower()

    return clean


def classify_item_complexity(raw_line: str, brand_cache: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """
    Classifies a raw grocery line as Clean & Confident (False) or Ambiguous/Complex (True).
    Clean & Confident:
      - Clear numeric/fraction quantity + standard unit + recognized commodity (e.g., "साखर 2 किलो", "तांदूळ 5 kg", "रवा 1 किलो").
      - Processes instantly via local regex parser (0-second fast pass).
    Ambiguous / Complex:
      - Freeform currency notation (e.g., "अगरबत्ती 50 रुपये", "10 rs salt").
      - Unbracketed brand markers (e.g., "नंबर १ साबण", "विलास अगरबत्ती") not yet in brand cache.
      - Unknown compound units or uncataloged commodities.
    """
    cleaned = normalize_text(raw_line).strip(" -:–x×\t")
    if not cleaned:
        return False, "empty"

    # 1. Check Currency notation
    if re.search(CURRENCY_REGEX, cleaned, re.IGNORECASE):
        return True, "currency_notation"

    # 2. Check if already cached in brand cache
    if brand_cache:
        c_lower = cleaned.lower()
        if cleaned in brand_cache or c_lower in brand_cache:
            return False, "cached_brand_commodity"
        for k in brand_cache:
            k_lower = str(k).lower().strip()
            if k_lower and (k_lower in c_lower or c_lower in k_lower):
                return False, "cached_brand_commodity"

    # 3. Check if brand is already bracketed e.g. "अगरबत्ती [विलास]"
    bracket_m = re.search(r'\[(.*?)\]', cleaned)
    has_bracketed_brand = bool(bracket_m)

    # 4. Check for unbracketed commercial brand markers
    lower_text = cleaned.lower()
    has_unbracketed_brand = False
    if not has_bracketed_brand:
        for brand_canon, aliases in KNOWN_BRANDS:
            for al in aliases:
                pat = re.compile(rf"(?:^|\b|\s){re.escape(al.lower())}(?:\b|\s|$)", re.IGNORECASE)
                if pat.search(lower_text):
                    has_unbracketed_brand = True
                    break
            if has_unbracketed_brand:
                break

    if has_unbracketed_brand:
        return True, "unbracketed_brand_marker"

    # 5. Extract tokens locally to verify commodity and unit
    extracted = extract_tokens_from_line(cleaned)
    raw_name = extracted.get("name", "").strip()
    qty = extracted.get("qty", 1.0)
    unit_str = (extracted.get("unit_str") or "").lower().strip()

    # Base commodity check
    base_name = re.sub(r'\[.*?\]', '', raw_name).strip()
    base_lower = base_name.lower()

    # Check if commodity matches known dictionary
    is_known_commodity = False
    if any(t in base_lower for t in ["गोडतेल", "godtel", "god tel", "खाद्यतेल", "गोड तेल", "refined oil", "cooking oil"]):
        is_known_commodity = True
    elif any(t in base_lower for t in ["शेंगदाणा", "शेंगदाणे", "दाणे", "shengdana", "shengdane"]):
        is_known_commodity = True
    else:
        for comm_canon, aliases in COMMODITY_MAPPINGS:
            for al in aliases:
                al_lower = al.lower()
                pat = re.compile(rf"(?:^|\b|\s){re.escape(al_lower)}(?:\b|\s|$)", re.IGNORECASE)
                if pat.search(base_lower) or base_lower == al_lower:
                    is_known_commodity = True
                    break
            if is_known_commodity:
                break

    if not is_known_commodity:
        return True, "uncataloged_commodity"

    # Check unit validity
    is_standard_unit = (unit_str in UNIT_METADATA) or any(
        u in unit_str for u in ["kg", "gm", "किलो", "ग्रॅम", "लिटर", "मिली", "l", "ml", "पाकीट", "packet", "नग", "pcs", "डझन", "dozen", "पेंढी", "bunch"]
    )
    if not is_standard_unit:
        return True, "ambiguous_unit"

    # Has clear quantity > 0
    if qty <= 0:
        return True, "invalid_quantity"

    return False, "clean_confident"


def deduplicate_parsed_items(
    items: List[Any],
    merge_duplicates: bool = False,
    return_notifications: bool = False
) -> Any:
    """
    MODULE 1: ELIMINATE REPETITION & STRICT DEDUPLICATION
    1. Normalization & Canonical Key Mapping:
       - Normalizes product names before appending (strips extra spaces, maps base Devanagari words).
       - Enforces unique slot identity so overlapping chunks or duplicate fallback remediation never produce duplicate rows.
       - If identical items (e.g. 'गव्हाचे पीठ' repeated twice, or identical quantity and commodity) occur, eliminates repetition.
       - If deliberate multiple lines with different quantities are entered, preserves unique entries or merges as configured.
    """
    if not items:
        return ([], []) if return_notifications else []

    seen_line_indices = set()
    seen_canonical: Dict[str, Tuple[int, Any]] = {}
    deduped = []
    notifications: List[str] = []

    for item in items:
        # 1. Normalize Canonical Name
        raw_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", "")
        norm_name = extract_brand_and_commodity(raw_name)
        if norm_name:
            if isinstance(item, dict):
                item["name"] = norm_name
            else:
                setattr(item, "name", norm_name)

        # 2. Check Overlapping Chunk Duplicate by line_index
        l_idx = item.get("line_index") if isinstance(item, dict) else getattr(item, "line_index", None)
        if l_idx is not None and l_idx in seen_line_indices:
            # Duplicate line index from overlapping chunk batch: discard
            continue
        if l_idx is not None:
            seen_line_indices.add(l_idx)

        # 3. Canonical Identity Check
        effective_name = norm_name or raw_name
        c_comm = normalize_canonical_commodity(effective_name)
        raw_u = str(item.get("canonical_unit", item.get("unit", "")) if isinstance(item, dict) else getattr(item, "canonical_unit", getattr(item, "unit", ""))).strip().lower()
        if raw_u in UNIT_METADATA:
            c_unit = UNIT_METADATA[raw_u][0]
        elif raw_u in ["किलो", "kg"]:
            c_unit = "kg"
        elif raw_u in ["लिटर", "l", "ltr", "liter", "litre"]:
            c_unit = "L"
        elif raw_u in ["पाकीट", "packet", "pouch", "pkt"]:
            c_unit = "packet"
        elif raw_u in ["नग", "pcs", "piece", "pieces"]:
            c_unit = "pcs"
        else:
            c_unit = raw_u

        brand_m = re.search(r'\[(.*?)\]', effective_name)
        b_tag = brand_m.group(1).strip().lower() if brand_m else ""
        note_m = re.search(r'\((.*?)\)', effective_name)
        note_tag = note_m.group(1).strip().lower() if note_m else ""
        canon_key = f"{c_comm}:{b_tag}:{note_tag}:{c_unit}"

        if canon_key in seen_canonical:
            ex_idx, ex_item = seen_canonical[canon_key]
            ex_qty = ex_item.get("qty", 1.0) if isinstance(ex_item, dict) else getattr(ex_item, "qty", 1.0)
            cur_qty = item.get("qty", 1.0) if isinstance(item, dict) else getattr(item, "qty", 1.0)
            ex_raw = (ex_item.get("original_raw") if isinstance(ex_item, dict) else getattr(ex_item, "original_raw", "")) or ""
            cur_raw = (item.get("original_raw") if isinstance(item, dict) else getattr(item, "original_raw", "")) or ""

            # Check if this is an identical repetition (e.g. repeated lines or identical items)
            if ex_raw.strip() == cur_raw.strip() or ex_qty == cur_qty:
                # Eliminate repetition
                notifications.append(f"पुनरावृत्ती झालेली वस्तू '{raw_name}' हटवून एकच नोंद ठेवली आहे.")
                continue
            elif merge_duplicates:
                # Merge quantities into existing record
                new_qty = ex_qty + cur_qty
                if isinstance(ex_item, dict):
                    ex_item["qty"] = new_qty
                    ex_item["display_qty"] = new_qty
                    if "quantity_norm" in ex_item and "quantity_norm" in item:
                        ex_item["quantity_norm"] = (ex_item.get("quantity_norm") or 0.0) + (item.get("quantity_norm") or 0.0)
                    if item.get("target_price"):
                        ex_item["target_price"] = (ex_item.get("target_price") or 0.0) + (item.get("target_price") or 0.0)
                else:
                    setattr(ex_item, "qty", new_qty)
                    setattr(ex_item, "display_qty", new_qty)
                    if hasattr(ex_item, "quantity_norm") and hasattr(item, "quantity_norm"):
                        setattr(ex_item, "quantity_norm", (getattr(ex_item, "quantity_norm") or 0.0) + (getattr(item, "quantity_norm") or 0.0))
                    if getattr(item, "target_price", None):
                        setattr(ex_item, "target_price", (getattr(ex_item, "target_price") or 0.0) + (getattr(item, "target_price") or 0.0))

                u_disp = ex_item.get("display_unit", ex_item.get("unit", "")) if isinstance(ex_item, dict) else getattr(ex_item, "display_unit", getattr(ex_item, "unit", ""))
                notifications.append(f"'{effective_name}' च्या वेगवेगळ्या ओळींवरील नोंदी एकत्र करून एकूण {new_qty} {u_disp} केले.")
                continue
            else:
                # Deliberate separate line entries with distinct quantities: preserve with unique row
                deduped.append(item)
                continue
        else:
            seen_canonical[canon_key] = (len(deduped), item)
            deduped.append(item)

    if return_notifications:
        return deduped, notifications
    return deduped

