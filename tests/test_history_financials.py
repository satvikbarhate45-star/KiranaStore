"""
KiranaStore - History Financial Logic & System-Wide Architectural Data Contract Tests
Validates:
1. Strict schema-level entity separation: line_total_amount, normalized_quantity, unit_base_rate.
2. Generalized regex-based unit conversion & rate calculation engine (normalize_measurement).
3. Simulator consumption: projected_item_cost = requested_quantity * unit_base_rate.
4. In-line row mutation persistence & live synchronization via PATCH /api/history/update-item.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import GroceryTrip, TripItem, ProductCatalog
from app.services.history_service import (
    parse_dynamic_quantity,
    normalize_measurement,
    calculate_unit_price,
    update_history_item,
    sanitize_historical_database
)
from app.services.normalizer import parse_measurement, normalize_line_item, RATE_ANOMALY_LIMIT
from app.services.simulator_service import simulate_budget_pipeline, calculate_item_projection

client = TestClient(app)

def test_dynamic_quantity_normalization_zero_hardcoding():
    """
    Validates dynamic, zero-hardcoding quantity parser function:
    - Kilograms: '15 किलो', '7 kg' -> normalized_qty: 15.0 / 7.0, base_unit: 'किलो'
    - Grams to Kilograms: '250 ग्रॅम', '500 gm', '100g' -> normalized_qty: 0.25 / 0.5 / 0.1, base_unit: 'किलो'
    - Liters: '5 ली', '15 ltr' -> normalized_qty: 5.0 / 15.0, base_unit: 'ली'
    - Milliliters to Liters: '500 मिली', '200 ml' -> normalized_qty: 0.5 / 0.2, base_unit: 'ली'
    - Colloquial fractions: 'अर्धा किलो' -> 0.5, 'पाव किलो' -> 0.25, 'पाऊण किलो' -> 0.75, 'दीड किलो' -> 1.5, 'अडीच किलो' -> 2.5
    - Countable packaging units: '4 पाकीट' -> 4.0, 'पाकीट'; '1 तोळा' -> 1.0, 'तोळा'; '2 डबा' -> 2.0, 'डबा'
    """
    # 1. Kilograms
    mag, unit = parse_dynamic_quantity("15 किलो")
    assert mag == 15.0
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("7 kg")
    assert mag == 7.0
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("७ किलो")
    assert mag == 7.0
    assert unit == "किलो"

    # 2. Grams converted to base kilogram scale (Q / 1000.0)
    mag, unit = parse_dynamic_quantity("250 ग्रॅम")
    assert mag == 0.25
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("500 gm")
    assert mag == 0.5
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("100 ग्रॅम")
    assert mag == 0.1
    assert unit == "किलो"

    # 3. Liters and Milliliters
    mag, unit = parse_dynamic_quantity("15 ltr")
    assert mag == 15.0
    assert unit == "ली"

    mag, unit = parse_dynamic_quantity("५ ली")
    assert mag == 5.0
    assert unit == "ली"

    mag, unit = parse_dynamic_quantity("500 मिली")
    assert mag == 0.5
    assert unit == "ली"

    # 4. Fractions
    mag, unit = parse_dynamic_quantity("अर्धा किलो")
    assert mag == 0.5
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("पाव किलो")
    assert mag == 0.25
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("पाऊण किलो")
    assert mag == 0.75
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("दीड किलो")
    assert mag == 1.5
    assert unit == "किलो"

    mag, unit = parse_dynamic_quantity("अडीच किलो")
    assert mag == 2.5
    assert unit == "किलो"

    # 5. Discrete Packaging Units
    mag, unit = parse_dynamic_quantity("4 पाकीट")
    assert mag == 4.0
    assert unit == "पाकीट"

    mag, unit = parse_dynamic_quantity("२ + २ (४ पाकीट)")
    assert mag == 4.0
    assert unit == "पाकीट"

    mag, unit = parse_dynamic_quantity("1 तोळा")
    assert mag == 1.0
    assert unit == "तोळा"

    mag, unit = parse_dynamic_quantity("2 डबा")
    assert mag == 2.0
    assert unit == "डबा"


def test_mathematical_derivation_logic_across_all_data():
    """
    Validates generalized regex-based unit conversion utility:
    - line_total_amount = Raw billed line amount
    - unit_base_rate = line_total_amount / normalized_quantity
    """
    # 1. 15 kg for ₹2180 -> rate ₹145.3333 / किलो
    norm_q, base_rate, base_unit = normalize_measurement(2180.0, "15 किलो")
    assert norm_q == 15.0
    assert abs(base_rate - 145.3333) < 0.01
    assert base_unit == "किलो"

    # 2. 7 kg for ₹354 -> rate ₹50.5714 / किलो
    norm_q, base_rate, base_unit = normalize_measurement(354.0, "7 kg")
    assert norm_q == 7.0
    assert abs(base_rate - 50.5714) < 0.01
    assert base_unit == "किलो"

    # 3. 250 ग्रॅम for ₹100 -> rate ₹400.00 / किलो (100 / 0.25)
    norm_q, base_rate, base_unit = normalize_measurement(100.0, "250 ग्रॅम")
    assert norm_q == 0.25
    assert base_rate == 400.00
    assert base_unit == "किलो"

    # 4. अर्धा किलो for ₹43 -> rate ₹86.00 / किलो (43 / 0.5)
    norm_q, base_rate, base_unit = normalize_measurement(43.0, "अर्धा किलो")
    assert norm_q == 0.5
    assert base_rate == 86.00
    assert base_unit == "किलो"

    # 5. 4 पाकीट for ₹240 -> rate ₹60.00 / पाकीट (240 / 4)
    norm_q, base_rate, base_unit = normalize_measurement(240.0, "4 पाकीट")
    assert norm_q == 4.0
    assert base_rate == 60.00
    assert base_unit == "पाकीट"

    # 6. 1 तोळा for ₹48 -> rate ₹48.00 / तोळा (48 / 1)
    norm_q, base_rate, base_unit = normalize_measurement(48.0, "1 तोळा")
    assert norm_q == 1.0
    assert base_rate == 48.00
    assert base_unit == "तोळा"

    # 7. 5 ली for ₹700 -> rate ₹140.00 / ली (700 / 5)
    norm_q, base_rate, base_unit = normalize_measurement(700.0, "5 ली")
    assert norm_q == 5.0
    assert base_rate == 140.00
    assert base_unit == "ली"


def test_historical_bill_persistence_strict_separation():
    """
    Validates that saving a historical receipt via /api/save-historical-bill records:
    - line_total_amount: Raw billed line total
    - normalized_quantity: Base metric quantity
    - unit_base_rate: Normalized unit base rate
    """
    db = SessionLocal()
    unique_title = f"पावती चाचणी {uuid.uuid4().hex[:6]}"
    payload = {
        "title": unique_title,
        "occasion_type": "regular",
        "purchase_date": "2026-03-10",
        "merchant_name": "गणेश किराणा",
        "items": [
            {
                "name": "गोडतेल",
                "quantity": "15 किलो",
                "price": 2180.0
            },
            {
                "name": "साखर",
                "quantity": "7 kg",
                "price": 354.0
            },
            {
                "name": "चहापावडर",
                "quantity": "250 ग्रॅम",
                "price": 100.0
            }
        ]
    }

    resp = client.post("/api/save-historical-bill", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["settled_total"] == 2634.0  # 2180 + 354 + 100

    trip_id = data["trip_id"]
    trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip_id).first()
    assert trip is not None
    assert trip.settled_total == 2634.0

    items_by_name = {i.product.marathi_name: i for i in trip.items}

    # Item 1: 15 kg for ₹2180 -> rate 145.33
    oil_item = items_by_name["गोडतेल"]
    assert oil_item.line_total_amount == 2180.0
    assert oil_item.entered_total == 2180.0
    assert oil_item.normalized_quantity == 15.0
    assert oil_item.quantity_norm == 15.0
    assert abs(oil_item.unit_base_rate - 145.33) < 0.05
    assert abs(oil_item.derived_rate - 145.33) < 0.05
    assert oil_item.quantity_str == "15 किलो"

    # Item 2: 7 kg for ₹354 -> rate 50.57
    sugar_item = items_by_name["साखर"]
    assert sugar_item.line_total_amount == 354.0
    assert sugar_item.entered_total == 354.0
    assert sugar_item.normalized_quantity == 7.0
    assert abs(sugar_item.unit_base_rate - 50.57) < 0.05

    # Item 3: 250 gm for ₹100 -> normalized to 0.25 kg, rate 400.0
    tea_item = items_by_name["चहापावडर"]
    assert tea_item.line_total_amount == 100.0
    assert tea_item.entered_total == 100.0
    assert tea_item.normalized_quantity == 0.25
    assert abs(tea_item.unit_base_rate - 400.0) < 0.05

    db.close()


def test_in_line_row_editing_patch_endpoint():
    """
    Validates instant in-line row editing directly inside the history modal:
    - PATCH /api/history/update-item
    - Synchronously persists line_total_amount, normalized_quantity, unit_base_rate,
      and recalculates parent trip settled_total.
    """
    db = SessionLocal()

    sess_id = f"test-edit-{uuid.uuid4().hex[:8]}"
    trip = GroceryTrip(
        session_id=sess_id,
        buyer_id=1,
        title="संपादन चाचणी",
        occasion_type="regular",
        merchant_name="चाचणी दुकान",
        settled_total=2180.0,
        status="settled"
    )
    db.add(trip)
    db.flush()

    prod = db.query(ProductCatalog).filter(ProductCatalog.marathi_name == "गोडतेल").first()
    sku = prod.sku_id if prod else 1

    item = TripItem(
        trip_id=trip.trip_id,
        sku_id=sku,
        line_total_amount=2180.0,
        normalized_quantity=5.0,
        unit_base_rate=436.0,
        quantity_str="5 किलो",
        unit="किलो",
        baseline_rate=436.0
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    db.refresh(trip)

    item_id = item.item_id

    # Simulate user editing row in History Modal (changing 5 kg -> 15 kg @ ₹2180)
    patch_payload = {
        "session_id": sess_id,
        "item_id": item_id,
        "quantity": "15 किलो",
        "line_total_amount": 2180.0,
        "unit_base_rate": 145.33
    }

    patch_resp = client.patch("/api/history/update-item", json=patch_payload)
    assert patch_resp.status_code == 200
    res_data = patch_resp.json()
    assert res_data["success"] is True
    assert res_data["quantity"] == "15 किलो"
    assert res_data["normalized_quantity"] == 15.0
    assert res_data["line_total_amount"] == 2180.0
    assert abs(res_data["unit_base_rate"] - 145.33) < 0.05
    assert res_data["trip_settled_total"] == 2180.0
    assert "नोंद यशस्वीरीत्या अद्ययावत केली!" in res_data["message"]

    db.expire_all()
    updated_item = db.query(TripItem).filter(TripItem.item_id == item_id).first()
    assert updated_item.quantity_str == "15 किलो"
    assert updated_item.normalized_quantity == 15.0
    assert updated_item.line_total_amount == 2180.0
    assert abs(updated_item.unit_base_rate - 145.33) < 0.05

    db.close()


def test_budget_simulator_consumption_of_unit_base_rate():
    """
    Validates Simulator consumption:
    - Baseline retrieval selects unit_base_rate.
    - projected_item_cost = requested_quantity * unit_base_rate.
    - Total simulated budget is aggregate sum of individually computed item costs.
    """
    db = SessionLocal()
    # Ensure product catalog has test item with established baseline
    prod = db.query(ProductCatalog).filter(ProductCatalog.marathi_name == "गोडतेल").first()
    assert prod is not None

    sim_payload = {
        "buyer_id": 1,
        "items": [
            {
                "sku_id": prod.sku_id,
                "quantity": 2.0  # User requests 2 units
            }
        ]
    }

    resp = client.post("/api/v1/analyzer/simulate", json=sim_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["items"]) == 1
    item_res = data["items"][0]
    assert item_res["has_history"] is True
    unit_rate = item_res["baseline_unit_rate"]
    assert unit_rate is not None and unit_rate > 0

    # projected_item_cost = requested_quantity * unit_base_rate
    expected_line = round(2.0 * unit_rate, 2)
    assert item_res["estimated_total"] == expected_line
    # Total simulated budget = aggregate sum
    assert data["total_estimated"] == expected_line

    db.close()


def test_normalizer_ssot_edge_cases_and_anomaly_guard():
    """
    Validates app.services.normalizer:
    1. Grams -> Kg: 250 ग्रॅम @ ₹100 -> ₹400/किलो (never 0.4 ₹/g).
    2. Milliliters -> Liters: 500 मिली @ ₹50 -> ₹100/ली.
    3. Discrete counts: 4 पाकीट @ ₹240 -> ₹60/पाकीट.
    4. Multi-digit quantity preservation: Ensures 250, 500, 1500 don't collapse to 1.
    5. Anomaly Guard: Rates > 50,000 or <= 0 flagged with explanation.
    """
    # 1. Grams to Kg normalization & rate
    norm_gram = normalize_line_item(line_total=100.0, quantity_str="250 ग्रॅम")
    assert norm_gram.line_total == 100.0
    assert norm_gram.normalized_quantity == 0.25
    assert norm_gram.unit_base_rate == 400.0
    assert norm_gram.display_unit == "किलो"
    assert norm_gram.is_anomaly is False

    # 2. Milliliters to Liters normalization & rate
    norm_ml = normalize_line_item(line_total=50.0, quantity_str="500 मिली")
    assert norm_ml.line_total == 50.0
    assert norm_ml.normalized_quantity == 0.5
    assert norm_ml.unit_base_rate == 100.0
    assert norm_ml.display_unit == "ली"
    assert norm_ml.is_anomaly is False

    # 3. Discrete Counts
    norm_pkt = normalize_line_item(line_total=240.0, quantity_str="4 पाकीट")
    assert norm_pkt.line_total == 240.0
    assert norm_pkt.normalized_quantity == 4.0
    assert norm_pkt.unit_base_rate == 60.0
    assert norm_pkt.display_unit == "पाकीट"
    assert norm_pkt.is_anomaly is False

    # 4. Multi-digit preservation across various inputs
    meas_250 = parse_measurement("250 g")
    assert meas_250.base_quantity == 0.25
    assert meas_250.standard_unit == "किलो"

    meas_500 = parse_measurement("500 gm")
    assert meas_500.base_quantity == 0.5
    assert meas_500.standard_unit == "किलो"

    meas_1500 = parse_measurement("1500 ग्रॅम")
    assert meas_1500.base_quantity == 1.5
    assert meas_1500.standard_unit == "किलो"

    # 5. Anomaly Guard: Runaway Rate > 50,000
    norm_inflated = normalize_line_item(line_total=60000.0, quantity_str="1 किलो")
    assert norm_inflated.unit_base_rate == 60000.0
    assert norm_inflated.is_anomaly is True
    assert "असामान्य दर" in norm_inflated.anomaly_reason

    # Normal within limit
    norm_valid = normalize_line_item(line_total=49999.0, quantity_str="1 किलो")
    assert norm_valid.is_anomaly is False


def test_simulate_budget_pipeline_mathematical_guarantees():
    """
    Validates simulate_budget_pipeline and calculate_item_projection:
    - Projection: projected_item_cost = requested_quantity * unit_base_rate.
    - Low bound = -5% (0.95), High bound = +7% (1.07).
    - Pipeline aggregates total strictly as the sum of projected items.
    """
    # 1. Direct unit math check
    proj = calculate_item_projection(requested_quantity=3.0, unit_base_rate=150.0)
    assert proj["estimated_total"] == 450.0  # 3 * 150
    assert proj["confidence_range_low"] == round(450.0 * 0.95, 2)  # 427.5
    assert proj["confidence_range_high"] == round(450.0 * 1.07, 2)  # 481.5

    # 2. Database pipeline execution with multiple items
    db = SessionLocal()
    products = db.query(ProductCatalog).limit(2).all()
    assert len(products) >= 2, "Product catalog must contain at least 2 items for test"

    p1, p2 = products[0], products[1]
    requested_items = [
        {"sku_id": p1.sku_id, "quantity": 2.0, "manual_price": 100.0},
        {"sku_id": p2.sku_id, "quantity": 4.0, "manual_price": 50.0}
    ]

    sim_res = simulate_budget_pipeline(db=db, requested_items=requested_items, buyer_id=1)
    db.close()

    assert sim_res["items_count"] == 2
    # Item 1: 2 * 100 = 200
    assert sim_res["items"][0]["projected_item_cost"] == 200.0
    # Item 2: 4 * 50 = 200
    assert sim_res["items"][1]["projected_item_cost"] == 200.0
    # Total = 200 + 200 = 400
    assert sim_res["total_estimated"] == 400.0
    assert sim_res["confidence_range_low"] == round(400.0 * 0.95, 2)
    assert sim_res["confidence_range_high"] == round(400.0 * 1.07, 2)


def test_sanitize_historical_database_pipeline():
    """
    Validates sanitize_historical_database:
    - Creates unnormalized or corrupted trip items.
    - Executes sanitize_historical_database(db).
    - Verifies items are normalized, unit rates are accurate (₹/kg), and trip total settled.
    """
    db = SessionLocal()

    sess_id = f"test-sanitize-{uuid.uuid4().hex[:8]}"
    trip = GroceryTrip(
        session_id=sess_id,
        buyer_id=1,
        title="डेटा स्वच्छता चाचणी",
        occasion_type="regular",
        merchant_name="चाचणी दुकान",
        settled_total=0.0,
        status="settled"
    )
    db.add(trip)
    db.flush()

    prod = db.query(ProductCatalog).first()
    sku = prod.sku_id if prod else 1

    # Insert Item with legacy raw total = 200, raw quantity = '500 gm'
    # Unnormalized legacy state might have unit_base_rate = 200 or 0.4
    item1 = TripItem(
        trip_id=trip.trip_id,
        sku_id=sku,
        line_total_amount=200.0,
        entered_total=200.0,
        normalized_quantity=1.0,  # Incorrect unnormalized
        unit_base_rate=200.0,     # Incorrect
        quantity_str="500 gm",
        unit="किलो"
    )

    # Insert Item with 15 kg oil for 2180
    item2 = TripItem(
        trip_id=trip.trip_id,
        sku_id=sku,
        line_total_amount=2180.0,
        entered_total=2180.0,
        normalized_quantity=1.0,  # Legacy 1.0
        unit_base_rate=2180.0,    # Legacy unnormalized rate
        quantity_str="15 किलो",
        unit="किलो"
    )

    db.add_all([item1, item2])
    db.commit()

    # Run sanitization
    report = sanitize_historical_database(db)
    assert report["status"] == "success"
    assert report["items_sanitized"] >= 2

    db.expire_all()
    refreshed_item1 = db.query(TripItem).filter(TripItem.item_id == item1.item_id).first()
    # 500 gm = 0.5 kg, line_total = 200, unit_base_rate = 200 / 0.5 = 400.0
    assert refreshed_item1.normalized_quantity == 0.5
    assert refreshed_item1.unit_base_rate == 400.0
    assert refreshed_item1.line_total_amount == 200.0

    refreshed_item2 = db.query(TripItem).filter(TripItem.item_id == item2.item_id).first()
    # 15 kg = 15.0 kg, line_total = 2180, unit_base_rate = 2180 / 15 = 145.3333
    assert refreshed_item2.normalized_quantity == 15.0
    assert abs(refreshed_item2.unit_base_rate - 145.33) < 0.05
    assert refreshed_item2.line_total_amount == 2180.0

    refreshed_trip = db.query(GroceryTrip).filter(GroceryTrip.trip_id == trip.trip_id).first()
    assert refreshed_trip.settled_total == 2380.0  # 200 + 2180

    db.close()
