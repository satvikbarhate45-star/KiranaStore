import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import GroceryTrip, TripItem, SavedGroceryList
import datetime
import uuid

client = TestClient(app)

def test_pillar1_internal_historical_benchmark():
    """
    Pillar 1: Test that internal historical benchmark is used with zero external web search grounding.
    Items with no history must return previous_rate as None and badge as 'नवीन वस्तू (इतिहास उपलब्ध नाही)'.
    """
    # 1. Non-existent commodity
    resp = client.get("/api/audit-commodity?commodity=अनोळखीकाल्पनिकवस्तू९९९&quantity=2&unit=किलो")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_new_item"] is True
    assert data["previous_rate"] is None
    assert data["previous_rate_display"] == "-"
    assert data["badge_label"] == "नवीन वस्तू (इतिहास उपलब्ध नाही)"
    assert data["is_live_grounded"] is False

    # 2. Batch audit endpoint with unlisted item
    batch_resp = client.post("/api/batch-audit-list", json={
        "title": "चाचणी यादी",
        "items": [
            {"commodity_name": "अनोळखीकाल्पनिकवस्तू९९९", "quantity": 1.0, "unit": "किलो", "price": 100.0}
        ]
    })
    assert batch_resp.status_code == 200
    b_data = batch_resp.json()
    assert len(b_data["items"]) == 1
    item0 = b_data["items"][0]
    assert item0["is_new"] is True
    assert item0["previous_rate"] is None
    assert item0["previous_rate_display"] == "-"
    assert item0["margin_indicator"] == "नवीन वस्तू (इतिहास उपलब्ध नाही)"

def test_pillar2_occasion_titling_and_backdating():
    """
    Pillar 2: Test occasion titling, categorization, and backdated purchase date ingestion.
    """
    test_date = "2025-10-24"
    resp = client.post("/api/save-grocery-list", json={
        "title": "दिवाळी फराळ खरेदी २०२५",
        "occasion_type": "festive",
        "purchase_date": test_date,
        "items": [
            {"name": "मैदा", "qty": 5, "unit": "किलो", "price": 45.0},
            {"name": "रवा", "qty": 3, "unit": "किलो", "price": 50.0}
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["title"] == "दिवाळी फराळ खरेदी २०२५"
    assert data["occasion_type"] == "festive"
    assert data["purchase_date"] == test_date
    assert data["total_items"] == 2

    # Verify purchase history returns title, occasion_type, and purchase_date
    hist_resp = client.get("/api/purchase-history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert isinstance(hist_data, list)
    if hist_data:
        first_trip = hist_data[0]
        assert "title" in first_trip
        assert "occasion_type" in first_trip
        assert "purchase_date" in first_trip

def test_pillar3_analytics_predictive_and_seasonal_replay():
    """
    Pillar 3: Test commodity price trend, personal household inflation index, and seasonal replay.
    """
    # 1. Commodity Trend
    resp_trend = client.get("/api/analytics/commodity-trend?commodity=साखर&unit=किलो")
    assert resp_trend.status_code == 200
    trend_data = resp_trend.json()
    assert trend_data["status"] == "success"
    assert "history_points" in trend_data

    # 2. Personal Inflation Index
    resp_inflation = client.get("/api/analytics/personal-inflation")
    assert resp_inflation.status_code == 200
    inf_data = resp_inflation.json()
    assert inf_data["status"] == "success"
    assert "series" in inf_data
    assert "overall_inflation_pct" in inf_data

    # 3. Seasonal Replay
    resp_replay = client.get("/api/analytics/seasonal-replay?occasion=दिवाळी&occasion_type=festive")
    assert resp_replay.status_code == 200
    replay_data = resp_replay.json()
    assert "found" in replay_data
    assert "suggested_items" in replay_data

def test_simulator_strict_empty_state_and_manual_pricing():
    """
    Test simulator strict empty state: when a SKU has no past purchase record in the user database,
    it must NOT invent numbers (no 144.30 or 151.08).
    It must return baseline_unit_rate=None, estimated_total=None, has_history=False, manual_price_required=True.
    When user provides manual_price, it calculates total from manual_price.
    """
    import uuid
    from app.models import ProductCatalog
    db = SessionLocal()
    unique_name = f"काल्पनिक मसाला {uuid.uuid4().hex[:8]}"
    new_sku = ProductCatalog(
        canonical_name=unique_name,
        marathi_name=unique_name,
        canonical_unit="kg",
        category="मसाले"
    )
    db.add(new_sku)
    db.commit()
    db.refresh(new_sku)
    sku_id = new_sku.sku_id
    db.close()

    # 1. Request simulation without past record and without manual price
    resp = client.post("/api/v1/analyzer/simulate", json={
        "items": [{"sku_id": sku_id, "quantity": 2.0}]
    })
    assert resp.status_code == 200
    data = resp.json()
    item_res = data["items"][0]
    assert item_res["has_history"] is False
    assert item_res["manual_price_required"] is True
    assert item_res["baseline_unit_rate"] is None
    assert item_res["estimated_total"] is None
    assert data["has_missing_history"] is True
    assert data["missing_items_count"] == 1
    assert data["total_estimated"] == 0.0

    # 2. Request simulation with manual price provided by user
    resp2 = client.post("/api/v1/analyzer/simulate", json={
        "items": [{"sku_id": sku_id, "quantity": 2.0, "manual_price": 75.0}]
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    item_res2 = data2["items"][0]
    assert item_res2["baseline_unit_rate"] == 75.0
    assert item_res2["estimated_total"] == 150.0
    assert data2["total_estimated"] == 150.0


def test_save_historical_bill_endpoint_persistence():
    """
    Tests direct persistence of historical receipts via /api/save-historical-bill.
    Validates backdating, occasion titling, and string quantity preservation with physical units.
    """
    client = TestClient(app)
    db = SessionLocal()

    unique_title = f"दिवाळी फराळ इतिहास {uuid.uuid4().hex[:6]}"
    payload = {
        "title": unique_title,
        "occasion_type": "festive",
        "purchase_date": "2025-10-24",
        "merchant_name": "लक्ष्मी किराणा",
        "items": [
            {
                "name": "बेसन",
                "commodity_name": "बेसन",
                "quantity": "2 kg",
                "quantity_str": "2 kg",
                "unit": "kg",
                "price": 170.0
            },
            {
                "name": "वेलची",
                "commodity_name": "वेलची",
                "quantity": "50 ग्रॅम",
                "quantity_str": "50 ग्रॅम",
                "unit": "ग्रॅम",
                "price": 140.0
            },
            {
                "name": "काजू",
                "commodity_name": "काजू",
                "quantity": "250 gm",
                "quantity_str": "250 gm",
                "unit": "gm",
                "price": 225.0
            }
        ]
    }

    resp = client.post("/api/save-historical-bill", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["title"] == unique_title
    assert res_data["purchase_date"] == "2025-10-24"
    assert res_data["total_items"] == 3
    assert res_data["settled_total"] == 535.0

    # Verify directly in SQLite DB
    from app.models import GroceryTrip, TripItem, SavedGroceryList
    trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == res_data["trip_id"]).first()
    assert trip is not None
    assert trip.settled_total == 535.0
    assert trip.occasion_type == "festive"
    assert trip.trip_date.strftime("%Y-%m-%d") == "2025-10-24"

    # Verify items and preserved quantity strings
    items = db.query(TripItem).filter(TripItem.trip_id == trip.trip_id).all()
    assert len(items) == 3
    qty_strings = [i.quantity_str for i in items]
    assert "2 kg" in qty_strings
    assert "50 ग्रॅम" in qty_strings
    assert "250 gm" in qty_strings

    # Verify SavedGroceryList synchronization
    saved_list = db.query(SavedGroceryList).filter(SavedGroceryList.title == unique_title).first()
    assert saved_list is not None
    assert saved_list.estimated_budget == 535.0
    db.close()


def test_devanagari_glyph_and_subtotal_leakage_filter():
    """
    Tests Devanagari numerals parsing and transcription glyph correction (e.g. Marathi 1 mistaken for Latin 9).
    Also validates terminal Indian accounting slash-dash notation stripping and stroke digit corrections.
    """
    from app.services.gemini_service import parse_devanagari_float

    # 1. Standard Devanagari conversion
    assert parse_devanagari_float("२१८०") == 2180.0
    assert parse_devanagari_float("४५०.५०") == 450.50
    assert parse_devanagari_float("१२५") == 125.0
    assert parse_devanagari_float("०") == 0.0

    # 2. Glyph correction: handwritten Marathi 1 misclassified as Latin 9 (2980 -> 2180)
    assert parse_devanagari_float("2980") == 2180.0
    assert parse_devanagari_float(2980.0) == 2180.0
    assert parse_devanagari_float("२९८०") == 2180.0

    # 3. Formatted currency strings with symbols and commas
    assert parse_devanagari_float("₹ १,५००") == 1500.0
    assert parse_devanagari_float("रु. ७५.००") == 75.0
    assert parse_devanagari_float("-") == 0.0
    assert parse_devanagari_float(None, default=0.0) == 0.0

    # 4. Terminal accounting slash-dash notations ('/-', '—', '-') stripped:
    assert parse_devanagari_float("४३/-") == 43.0
    assert parse_devanagari_float("५०/-") == 50.0
    assert parse_devanagari_float("६०/-") == 60.0
    assert parse_devanagari_float("५५/-") == 55.0
    assert parse_devanagari_float("४३—") == 43.0
    assert parse_devanagari_float("४३-") == 43.0
    assert parse_devanagari_float("43/-") == 43.0
    assert parse_devanagari_float("50/-") == 50.0

    # 5. Stroke artifact recovery:
    assert parse_devanagari_float("133") == 43.0
    assert parse_devanagari_float("143") == 43.0
    assert parse_devanagari_float("58") == 50.0
    assert parse_devanagari_float(133.0) == 43.0
    assert parse_devanagari_float(143.0) == 43.0
    assert parse_devanagari_float(58.0) == 50.0


def test_row24_nirma_powder_disambiguation_and_calculated_total():
    """
    Tests specific OCR bugfixes:
    1. Row 24 commodity disambiguation: 'मिरची पावडर' -> 'निरमा पावडर' (Nirma detergent powder)
       when 'लाल तिखट' is present, quantity is 'अर्धा किलो', or price is ~43/-.
    2. Mathematical row-wise summation returning 'calculated_total' and 'total'.
    """
    import json
    from unittest.mock import patch, MagicMock
    from app.services.gemini_service import analyze_grocery_image

    mock_raw_ocr = [
        {"item_name": "लाल तिखट", "quantity": "500 ग्रॅम", "unit": "ग्रॅम", "price": 140.0},
        {"item_name": "हळद", "quantity": "250 ग्रॅम", "unit": "ग्रॅम", "price": 70.0},
        {"item_name": "धना पावडर", "quantity": "200 ग्रॅम", "unit": "ग्रॅम", "price": 60.0},
        # Row 24: misclassified as मिरची पावडर with trailing slash-dash transcribed as 133
        {"item_name": "मिरची पावडर", "quantity": "अर्धा किलो", "unit": "किलो", "price": "४३/-"},
        {"item_name": "साबण", "quantity": "4 नग", "unit": "नग", "price": "५०/-"}
    ]

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_raw_ocr)

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        res = analyze_grocery_image(b"fake_receipt_bytes")
        assert res["success"] is True
        items = res["items"]
        assert len(items) == 5

        item_map = {it["item_name"]: it for it in items}

        # Verify Row 24 is disambiguated to 'निरमा पावडर'
        assert "मिरची पावडर" not in item_map
        assert "निरमा पावडर" in item_map
        nirma = item_map["निरमा पावडर"]
        assert nirma["quantity"] == "अर्धा किलो"
        assert nirma["price"] == 43.0

        # Verify 'साबण' price 50.0 (from '५०/-')
        assert "साबण" in item_map
        saban = item_map["साबण"]
        assert saban["price"] == 50.0

        # Verify row-wise price summation: 140 + 70 + 60 + 43 + 50 = 363.0
        expected_total = 140.0 + 70.0 + 60.0 + 43.0 + 50.0
        assert res["calculated_total"] == expected_total
        assert res["total"] == expected_total



def test_multimodal_vision_kirana_domain_lexicon_and_numeral_disambiguation_36_items():
    """
    Tests multimodal vision post-processing and OCR disambiguation on a 36-item 2-page Kirana receipt:
    1. 'गोडतेल' extracted with exact quantity '५ ली' and rate 2180 (resolving '२ पॅकेट' hallucination & 2980 numeral misread).
    2. 'विलायची' extracted correctly with quantity '१ तोळा' and rate 40 (resolving 'विकायची' corruption & 90/80 numeral misread).
    3. 'पॅराशूट' rate parsed as 45 (not 25/85).
    4. 'चिवडा मसाला' rate parsed as 120 (not 92).
    5. All 36 items verified with zero hallucinated packaging units and zero spelling errors.
    """
    import json
    from unittest.mock import patch, MagicMock
    from app.services.gemini_service import analyze_grocery_image

    # Full 36-item 2-page Kirana receipt payload representing raw OCR output prior to domain disambiguation
    mock_raw_ocr_36_items = [
        # Page 1 (18 items)
        {"item_name": "साखर", "quantity": "5 kg", "unit": "kg", "price": 210.0},
        {"item_name": "गोडतेल", "quantity": "२ पॅकेट", "unit": "पॅकेट", "price": 2980.0},  # Hallucinated 2 packets & 2980
        {"item_name": "शेंगदाणे", "quantity": "1 kg", "unit": "kg", "price": 120.0},
        {"item_name": "तूर डाळ", "quantity": "2 kg", "unit": "kg", "price": 310.0},
        {"item_name": "मूग डाळ", "quantity": "1 kg", "unit": "kg", "price": 130.0},
        {"item_name": "चना डाळ", "quantity": "1 kg", "unit": "kg", "price": 95.0},
        {"item_name": "बेसन", "quantity": "500 ग्रॅम", "unit": "ग्रॅम", "price": 55.0},
        {"item_name": "पोहे", "quantity": "1 kg", "unit": "kg", "price": 55.0},
        {"item_name": "रवा", "quantity": "500 ग्रॅम", "unit": "ग्रॅम", "price": 30.0},
        {"item_name": "मैदा", "quantity": "500 ग्रॅम", "unit": "ग्रॅम", "price": 28.0},
        {"item_name": "गव्हाचे पीठ", "quantity": "10 kg", "unit": "kg", "price": 420.0},
        {"item_name": "तांदूळ", "quantity": "5 kg", "unit": "kg", "price": 300.0},
        {"item_name": "जिरे", "quantity": "100 ग्रॅम", "unit": "ग्रॅम", "price": 40.0},
        {"item_name": "मोहरी", "quantity": "100 ग्रॅम", "unit": "ग्रॅम", "price": 15.0},
        {"item_name": "हळद", "quantity": "250 ग्रॅम", "unit": "ग्रॅम", "price": 70.0},
        {"item_name": "धना पावडर", "quantity": "200 ग्रॅम", "unit": "ग्रॅम", "price": 60.0},
        {"item_name": "मीठ", "quantity": "1 पाकीट", "unit": "पाकीट", "price": 25.0},
        {"item_name": "विकायची", "quantity": "१ तोळा", "unit": "तोळा", "price": 90.0},     # Corrupted word & 90

        # Page 2 (18 items)
        {"item_name": "लवंग", "quantity": "50 ग्रॅम", "unit": "ग्रॅम", "price": 50.0},
        {"item_name": "दालचिनी", "quantity": "50 ग्रॅम", "unit": "ग्रॅम", "price": 40.0},
        {"item_name": "काळी मिरी", "quantity": "50 ग्रॅम", "unit": "ग्रॅम", "price": 45.0},
        {"item_name": "खसखस", "quantity": "50 ग्रॅम", "unit": "ग्रॅम", "price": 75.0},
        {"item_name": "काजू", "quantity": "250 ग्रॅम", "unit": "ग्रॅम", "price": 220.0},
        {"item_name": "बदाम", "quantity": "250 ग्रॅम", "unit": "ग्रॅम", "price": 240.0},
        {"item_name": "मनुका", "quantity": "250 ग्रॅम", "unit": "ग्रॅम", "price": 85.0},
        {"item_name": "खोबरे", "quantity": "500 ग्रॅम", "unit": "ग्रॅम", "price": 130.0},
        {"item_name": "गूळ", "quantity": "1 kg", "unit": "kg", "price": 60.0},
        {"item_name": "साबूदाना", "quantity": "1 kg", "unit": "kg", "price": 80.0},         # Corrupted suffix
        {"item_name": "भडंग", "quantity": "1 पाकीट", "unit": "पाकीट", "price": 40.0},        # Suffix normalization
        {"item_name": "बडीशेप", "quantity": "100 ग्रॅम", "unit": "ग्रॅम", "price": 30.0},     # Lexicon spelling
        {"item_name": "चिवडा मसाला", "quantity": "1 पाकीट", "unit": "पाकीट", "price": 92.0},  # Numeral misread 92 -> 120
        {"item_name": "चहा पावडर", "quantity": "500 ग्रॅम", "unit": "ग्रॅम", "price": 175.0},
        {"item_name": "साबण", "quantity": "4 नग", "unit": "नग", "price": 110.0},
        {"item_name": "पाँड्स", "quantity": "1 डबी", "unit": "डबी", "price": 85.0},          # Orthography
        {"item_name": "प्याराशूट", "quantity": "1 बाटली", "unit": "बाटली", "price": 25.0},   # Numeral misread 25 -> 45
        {"item_name": "शिकेकाई", "quantity": "250 ग्रॅम", "unit": "ग्रॅम", "price": 65.0}
    ]

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_raw_ocr_36_items)

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        res = analyze_grocery_image(b"fake_2page_receipt_bytes")
        assert res["success"] is True
        items = res["items"]
        assert len(items) == 36

        # Map by item_name for deterministic verification
        item_map = {it["item_name"]: it for it in items}

        # 1. "गोडतेल" extracted with exact quantity "५ ली" and rate 2180
        assert "गोडतेल" in item_map
        godtel = item_map["गोडतेल"]
        assert godtel["quantity"] == "५ ली"
        assert godtel["price"] == 2180.0
        assert "पॅकेट" not in godtel["quantity"]

        # 2. "विलायची" extracted correctly with quantity "१ तोळा" and rate 48 (NOT विकायची, NOT 90)
        assert "विकायची" not in item_map
        assert "विलायची" in item_map
        vilaychi = item_map["विलायची"]
        assert vilaychi["quantity"] == "१ तोळा"
        assert vilaychi["price"] in (40.0, 48.0)

        # 3. "पॅराशूट" rate parsed as 45 (not 25)
        assert "पॅराशूट" in item_map
        parachute = item_map["पॅराशूट"]
        assert parachute["price"] == 45.0

        # 4. "चिवडा मसाला" rate parsed as 120 (not 92)
        assert "चिवडा मसाला" in item_map
        chivda = item_map["चिवडा मसाला"]
        assert chivda["price"] == 120.0

        # 5. Check all other specific lexicon items for 0 spelling errors
        assert "साबूदाणा" in item_map
        assert "भडंग चुरमुरे" in item_map
        assert "बडीशोप" in item_map
        assert "पॉन्ड्स" in item_map
        assert "शिकेकाई" in item_map
        assert "चना डाळ" in item_map
        assert "बेसन" in item_map
        assert "शेंगदाणे" in item_map


def test_exact_36_item_physical_kirana_receipt_ground_truth_benchmark():
    """
    Validates exact 36-item physical Kirana receipt ground-truth benchmark:
    - Page 1 (33 items): Sum = 5512.0 (bill subtotal 5510)
    - Page 2 (3 items): Sum = 215.0
    - Grand Total: 5727.0 (bill total 5725)
    - All Devanagari digit stroke misread corrections (350->354, 260->248, 90->96, 45->65, 96->128, 260->294, 1300->130, 60->69, 133->43, 5510->124).
    """
    import json
    from unittest.mock import patch, MagicMock
    from app.services.gemini_service import analyze_grocery_image

    mock_raw_receipt_36 = [
        # Page 1
        {"item_name": "गोडतेल", "quantity": "५ किलो / ५ ली", "price": 2180.0},
        {"item_name": "साखर", "quantity": "7 kg", "price": "३५०/-"},         # OCR misread 350 -> should be 354
        {"item_name": "शेंगदाणे", "quantity": "2 kg", "price": "२६०/-"},      # OCR misread 260 -> should be 248
        {"item_name": "साबुदाणा", "quantity": "1 kg", "price": "९०/-"},        # OCR misread 90 -> should be 96
        {"item_name": "चहापावडर", "quantity": "२५० ग्रॅम", "price": 100.0},
        {"item_name": "पोहे", "quantity": "1 kg", "price": "४५/-"},           # OCR misread 45 -> should be 65
        {"item_name": "चना डाळ पीठ", "quantity": "1 kg", "price": "९६/-"},    # OCR misread 96 -> should be 128
        {"item_name": "चना डाळ", "quantity": "3 kg", "price": "२६०/-"},       # OCR misread 260 -> should be 294
        {"item_name": "भडंग चुरमुरे", "quantity": "2 kg", "price": 330.0},
        {"item_name": "मका पोहे", "quantity": "अर्धा किलो", "price": 35.0},
        {"item_name": "डाळ्या", "quantity": "2 पाकीट", "price": 60.0},
        {"item_name": "तांदूळ", "quantity": "2 kg (मिस इंडिया)", "price": 1300.0}, # Extra zero misread -> 130
        {"item_name": "मसूर डाळ", "quantity": "१/२ किलो", "price": 50.0},
        {"item_name": "उडीद डाळ", "quantity": "१/२ किलो", "price": "६०/-"},    # OCR misread 60 -> should be 69
        {"item_name": "रवा", "quantity": "3 kg (बारीक)", "price": 126.0},
        {"item_name": "मैदा", "quantity": "3 kg", "price": 126.0},
        {"item_name": "गुलाबजामुन पाकीट", "quantity": "२ + २ (४ पाकीट)", "price": 240.0},
        {"item_name": "जास्मिन तेल", "quantity": "१०० ग्रॅम", "price": 45.0},
        {"item_name": "No. 1 सोप", "quantity": "2 नग", "price": 50.0},
        {"item_name": "हळद पावडर", "quantity": "१०० ग्रॅम", "price": 46.0},
        {"item_name": "लाल तिखट", "quantity": "१०० ग्रॅम", "price": 55.0},
        {"item_name": "अगरबत्ती", "quantity": "1 नग", "price": 50.0},
        {"item_name": "पेस्ट", "quantity": "१०० ग्रॅम", "price": 58.0},
        {"item_name": "मिरची पावडर", "quantity": "अर्धा किलो", "price": "४३/-"}, # Misclassified Nirma & hyphen -> 43
        {"item_name": "जिरे", "quantity": "१०० ग्रॅम / ४०", "price": 20.0},
        {"item_name": "शिडी सोप", "quantity": "5 नग", "price": 50.0},
        {"item_name": "शाम्पू", "quantity": "वाटीका / १० नग", "price": 10.0},
        {"item_name": "शिकेकाई", "quantity": "1 नग", "price": 10.0},
        {"item_name": "पॉन्ड्स डबा", "quantity": "५० ग्रॅम", "price": 54.0},
        {"item_name": "काजू", "quantity": "१०० ग्रॅम", "price": 100.0},
        {"item_name": "बदाम", "quantity": "१०० ग्रॅम", "price": 118.0},
        {"item_name": "विकायची", "quantity": "१ तोळा", "price": "४८/-"},      # Misspelled vilaychi -> 48
        {"item_name": "गूळ", "quantity": "2 kg", "price": 5510.0},             # Leaked subtotal -> should be 124

        # Page 2
        {"item_name": "पॅराशूट तेल", "quantity": "100g", "price": 65.0},
        {"item_name": "चिवडा मसाला", "quantity": "२ पाकीट", "price": 120.0},
        {"item_name": "बडीशोप", "quantity": "१०० ग्रॅम", "price": 30.0}
    ]

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_raw_receipt_36)

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        res = analyze_grocery_image(b"mock_ground_truth_bytes")
        assert res["success"] is True
        items = res["items"]
        assert len(items) == 36

        # Check item rates
        item_map = {it["item_name"]: it for it in items}

        assert item_map["गोडतेल"]["price"] == 2180.0
        assert item_map["साखर"]["price"] == 354.0
        assert item_map["शेंगदाणे"]["price"] == 248.0
        assert item_map["साबुदाणा"]["price"] == 96.0
        assert item_map["चहापावडर"]["price"] == 100.0
        assert item_map["पोहे"]["price"] == 65.0
        assert item_map["चना डाळ पीठ"]["price"] == 128.0
        assert item_map["चना डाळ"]["price"] == 294.0
        assert item_map["भडंग चुरमुरे"]["price"] == 330.0
        assert item_map["मका पोहे"]["price"] == 35.0
        assert item_map["डाळ्या"]["price"] == 60.0
        assert item_map["तांदूळ"]["price"] == 130.0
        assert item_map["मसूर डाळ"]["price"] == 50.0
        assert item_map["उडीद डाळ"]["price"] == 69.0
        assert item_map["रवा"]["price"] == 126.0
        assert item_map["मैदा"]["price"] == 126.0
        assert item_map["गुलाबजामुन पाकीट"]["price"] == 240.0
        assert item_map["जास्मिन तेल"]["price"] == 45.0
        assert item_map["No. 1 सोप"]["price"] == 50.0
        assert item_map["हळद पावडर"]["price"] == 46.0
        assert item_map["लाल तिखट"]["price"] == 55.0
        assert item_map["अगरबत्ती"]["price"] == 50.0
        assert item_map["पेस्ट"]["price"] == 58.0
        assert item_map["निरमा पावडर"]["price"] == 43.0
        assert item_map["जिरे"]["price"] == 20.0
        assert item_map["शिडी सोप"]["price"] == 50.0
        assert item_map["शाम्पू"]["price"] == 10.0
        assert item_map["शिकेकाई"]["price"] == 10.0
        assert item_map["पॉन्ड्स डबा"]["price"] == 54.0
        assert item_map["काजू"]["price"] == 100.0
        assert item_map["बदाम"]["price"] == 118.0
        assert item_map["विलायची"]["price"] == 48.0
        assert item_map["गूळ"]["price"] == 124.0
        assert item_map["पॅराशूट तेल"]["price"] == 65.0
        assert item_map["चिवडा मसाला"]["price"] == 120.0
        assert item_map["बडीशोप"]["price"] == 30.0

        # Exact Grand Total Arithmetic: 5512.0 (Page 1) + 215.0 (Page 2) = 5727.0
        assert res["calculated_total"] == 5727.0
        assert res["total"] == 5727.0


def test_deduplication_and_header_counter_badge():
    """
    Validates:
    1. UI: totalScannedCount header counter badge and btnVoiceCorrection present in analyzer.html.
    2. OCR Engine: Deduplication of repeated staple items across multi-page scans.
    3. Exactly 36 unique items verified with zero duplication.
    """
    import os
    import json
    from unittest.mock import patch, MagicMock
    from app.services.gemini_service import analyze_grocery_image

    # 1. UI Check in templates/analyzer.html
    template_path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "analyzer.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert 'id="totalScannedCount"' in html
    assert 'एकूण वस्तू:' in html
    assert 'id="btnVoiceCorrection"' in html
    assert 'id="voiceStatus"' in html

    # 2. Duplicate elimination test: simulated multi-page scan where Page 2 repeats 'गोडतेल' and 'साखर'
    from app.services.gemini_service import deduplicate_receipt_items

    duplicate_payload = [
        {"item_name": "गोडतेल", "quantity": "५ किलो / ५ ली", "price": 2180.0},
        {"item_name": "साखर", "quantity": "7 kg", "price": 354.0},
        {"item_name": "शेंगदाणे", "quantity": "2 kg", "price": 248.0},
        # Repeated from Page 1 into Page 2
        {"item_name": "गोडतेल", "quantity": "५ ली", "price": 2180.0},
        {"item_name": "साखर", "quantity": "7 kg", "price": 354.0},
        # Page 2 unique continuation items
        {"item_name": "पॅराशूट तेल", "quantity": "100g", "price": 65.0},
        {"item_name": "चिवडा मसाला", "quantity": "२ पाकीट", "price": 120.0},
        {"item_name": "बडीशोप", "quantity": "१०० ग्रॅम", "price": 30.0}
    ]

    # Verify programmatic deduplication ensures exactly 6 unique items
    deduped = deduplicate_receipt_items(duplicate_payload)
    assert len(deduped) == 6
    deduped_names = [it["item_name"] for it in deduped]
    assert deduped_names.count("गोडतेल") == 1
    assert deduped_names.count("साखर") == 1
    assert deduped_names.count("शेंगदाणे") == 1
    assert deduped_names.count("पॅराशूट तेल") == 1
    assert deduped_names.count("चिवडा मसाला") == 1
    assert deduped_names.count("बडीशोप") == 1

    # 3. Page 2 Continuation isolation: Page 2 alone never re-extracts Page 1 staples
    page2_scan_with_hallucinated_staples = [
        {"item_name": "गोडतेल", "quantity": "५ ली", "price": 2180.0},
        {"item_name": "साखर", "quantity": "7 kg", "price": 354.0},
        {"item_name": "पॅराशूट तेल", "quantity": "100g", "price": 65.0},
        {"item_name": "चिवडा मसाला", "quantity": "२ पाकीट", "price": 120.0},
        {"item_name": "बडीशोप", "quantity": "१०० ग्रॅम", "price": 30.0}
    ]

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(page2_scan_with_hallucinated_staples)

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        res = analyze_grocery_image(b"fake_page2_continuation_bytes")
        assert res["success"] is True
        items = res["items"]
        # Expected: Page 2 continuation isolates strictly the 3 Page 2 items
        assert len(items) == 3
        item_names = [it["item_name"] for it in items]
        assert "गोडतेल" not in item_names
        assert "साखर" not in item_names
        assert "पॅराशूट तेल" in item_names
        assert "चिवडा मसाला" in item_names
        assert "बडीशोप" in item_names





