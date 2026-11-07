import re
import urllib.parse
from typing import Dict, Optional, Tuple

VPA_REGEX = re.compile(r"^[\w.\-]{2,256}@[A-Za-z]{2,64}$")

def validate_vpa(vpa: str) -> bool:
    if not vpa:
        return False
    return bool(VPA_REGEX.match(vpa.strip()))

def parse_upi_uri(raw_uri: str) -> Tuple[bool, Dict[str, str], Optional[str]]:
    """
    Parses a raw scanned QR string or upi://pay URI.
    Returns (is_valid, parsed_params, error_message_mr)
    """
    if not raw_uri:
        return False, {}, "QR कोड रिकामा आहे"

    raw_uri = raw_uri.strip()
    
    # Check if raw_uri is just a VPA string like shopkeeper@okaxis
    if validate_vpa(raw_uri):
        return True, {"pa": raw_uri, "pn": "किराणा व्यावसायिक"}, None

    if not raw_uri.startswith("upi://pay"):
        return False, {}, "हा UPI QR कोड नाही"

    try:
        parsed = urllib.parse.urlparse(raw_uri)
        query_params = urllib.parse.parse_qs(parsed.query)
        params: Dict[str, str] = {}
        for k, v in query_params.items():
            if v:
                params[k] = v[0]
                
        pa = params.get("pa", "").strip()
        if not pa:
            return False, {}, "QR मध्ये UPI आयडी सापडला नाही"

        if not validate_vpa(pa):
            return False, {}, "अवैध UPI आयडी स्वरूप"

        return True, params, None

    except Exception as e:
        return False, {}, "QR कोड वाचता आला नाही"

def construct_upi_deep_link(
    vpa: str,
    merchant_name: str,
    grand_total: float,
    trip_id_or_session: str
) -> str:
    """
    Constructs NPCI-compliant zero-friction UPI deep link:
    upi://pay?pa=<VPA>&pn=<Name>&am=<GrandTotal>&cu=INR&tn=<LocalizedNote>
    Ensures 'am' has strictly 2 decimal places and overrides any QR-supplied amount.
    """
    amount_str = f"{float(grand_total):.2f}"
    clean_name = merchant_name.strip() or "किराणा व्यावसायिक"
    short_ref = str(trip_id_or_session)[:8]
    note = f"किराणा बिल - {short_ref}"[:50]

    params = {
        "pa": vpa.strip(),
        "pn": clean_name,
        "am": amount_str,
        "cu": "INR",
        "tn": note
    }

    query_str = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"upi://pay?{query_str}"
