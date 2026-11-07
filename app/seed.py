import datetime
import uuid
from sqlalchemy.orm import Session
from app.models import ProductCatalog, GroceryTrip, TripItem, VolatilityConfig

CATALOG_SEED = [
    {
        "canonical_name": "sugar",
        "marathi_name": "साखर",
        "canonical_unit": "kg",
        "category": "दैनंदिन वस्तू",
        "aliases": ["सक्कर", "sakhar", "sakkar", "sugar", "साखर२किलो", "साखर 1 किलो"]
    },
    {
        "canonical_name": "groundnut_oil",
        "marathi_name": "शेंगदाणा तेल",
        "canonical_unit": "L",
        "category": "तेल व तूप",
        "aliases": ["shengdana tel", "shengdanatel", "शेंगदाणातेल", "groundnut oil", "shengdana oil", "शेंगदाणा तेल 2 ltr"]
    },
    {
        "canonical_name": "cooking_oil",
        "marathi_name": "गोडतेल",
        "canonical_unit": "L",
        "category": "तेल व तूप",
        "aliases": ["godtel", "god tel", "गोड तेल", "खाद्यतेल", "cooking oil", "refined oil", "तेल", "tel", "गोडतेल [खाद्यतेल]", "गोड तेल 1 ltr"]
    },
    {
        "canonical_name": "agarbatti",
        "marathi_name": "अगरबत्ती",
        "canonical_unit": "packet",
        "category": "पूजा साहित्य",
        "aliases": ["agarbatti", "incense sticks", "अगरबत्या", "धूप", "अगरबत्ती पाकीट", "अगरबत्ती 50 रुपये"]
    },
    {
        "canonical_name": "toor_dal",
        "marathi_name": "तूर डाळ",
        "canonical_unit": "kg",
        "category": "डाळी व कडधान्ये",
        "aliases": ["तुरीची डाल", "तुरीची डाळ", "tur dal", "toor dal", "turdaal", "डाळ"]
    },
    {
        "canonical_name": "rice",
        "marathi_name": "तांदूळ",
        "canonical_unit": "kg",
        "category": "धान्य",
        "aliases": ["तांदुल", "tandul", "rice", "kolam rice", "तांदूळ५००ग्रॅम", "भात"]
    },
    {
        "canonical_name": "wheat_flour",
        "marathi_name": "गहू पीठ",
        "canonical_unit": "kg",
        "category": "धान्य",
        "aliases": ["कणिक", "गव्हाचे पीठ", "wheat flour", "atta", "आटा"]
    },
    {
        "canonical_name": "moong_dal",
        "marathi_name": "मूग डाळ",
        "canonical_unit": "kg",
        "category": "डाळी व कडधान्ये",
        "aliases": ["मुगाची डाळ", "moong dal", "mung dal"]
    },
    {
        "canonical_name": "chana_dal",
        "marathi_name": "चणा डाळ",
        "canonical_unit": "kg",
        "category": "डाळी व कडधान्ये",
        "aliases": ["हरभरा डाळ", "chana dal", "चना दाल"]
    },
    {
        "canonical_name": "turmeric",
        "marathi_name": "हळद",
        "canonical_unit": "kg",
        "category": "मसाले",
        "aliases": ["हलद", "halad", "turmeric", "haldi"]
    },
    {
        "canonical_name": "mustard_seeds",
        "marathi_name": "मोहरी",
        "canonical_unit": "kg",
        "category": "मसाले",
        "aliases": ["mohari", "rai", "mustard"]
    },
    {
        "canonical_name": "cumin",
        "marathi_name": "जिरे",
        "canonical_unit": "kg",
        "category": "मसाले",
        "aliases": ["जिरं", "jire", "jeera", "cumin"]
    },
    {
        "canonical_name": "salt",
        "marathi_name": "मीठ",
        "canonical_unit": "kg",
        "category": "दैनंदिन वस्तू",
        "aliases": ["मिट", "mit", "salt", "tata salt", "mitha", "mith", "मीठ पाकीट"]
    },
    {
        "canonical_name": "tea_powder",
        "marathi_name": "चहा पावडर",
        "canonical_unit": "kg",
        "category": "दैनंदिन वस्तू",
        "aliases": ["चहापत्ती", "tea powder", "चाय", "tea"]
    },
    {
        "canonical_name": "peanuts",
        "marathi_name": "शेंगदाणे",
        "canonical_unit": "kg",
        "category": "डाळी व कडधान्ये",
        "aliases": ["shengdane", "peanuts", "दाणे", "शेंगदाणा", "shengdana"]
    },
    {
        "canonical_name": "poha",
        "marathi_name": "पोहे",
        "canonical_unit": "kg",
        "category": "धान्य",
        "aliases": ["जाड पोहे", "pohe", "poha"]
    },
    {
        "canonical_name": "jaggery",
        "marathi_name": "गूळ",
        "canonical_unit": "kg",
        "category": "दैनंदिन वस्तू",
        "aliases": ["गुल", "gul", "jaggery", "कोल्हापुरी गूळ"]
    },
    {
        "canonical_name": "besan",
        "marathi_name": "बेसन",
        "canonical_unit": "kg",
        "category": "धान्य",
        "aliases": ["हरभरा पीठ", "gram flour", "besan"]
    },
    {
        "canonical_name": "rava",
        "marathi_name": "रवा",
        "canonical_unit": "kg",
        "category": "धान्य",
        "aliases": ["सुजी", "rava", "sooji", "बारीक रवा"]
    },
    {
        "canonical_name": "onion",
        "marathi_name": "कांदा",
        "canonical_unit": "kg",
        "category": "भाजीपाला",
        "aliases": ["kanda", "onion", "कांदे"]
    },
    {
        "canonical_name": "potato",
        "marathi_name": "बटाटा",
        "canonical_unit": "kg",
        "category": "भाजीपाला",
        "aliases": ["batata", "potato", "बटाटे", "आलू"]
    },
    {
        "canonical_name": "pure_ghee",
        "marathi_name": "साजूक तूप",
        "canonical_unit": "kg",
        "category": "तेल व तूप",
        "aliases": ["तूप", "ghee", "sajuk tup", "pure ghee"]
    },
    {
        "canonical_name": "bathing_soap",
        "marathi_name": "साबण",
        "canonical_unit": "pcs",
        "category": "स्वच्छता साहित्य",
        "aliases": ["saban", "soap", "lux", "dettol"]
    },
    {
        "canonical_name": "eggs",
        "marathi_name": "अंडी",
        "canonical_unit": "dozen",
        "category": "दैनंदिन वस्तू",
        "aliases": ["andi", "eggs", "अंड"]
    },
    {
        "canonical_name": "coriander",
        "marathi_name": "कोथिंबीर",
        "canonical_unit": "bunch",
        "category": "भाजीपाला",
        "aliases": ["kothimbir", "coriander", "कोथिंबीर पेंढी", "dhanya", "sambhar"]
    }
]

def seed_database(db: Session):
    # 1. Volatility Config
    cfg = db.query(VolatilityConfig).filter(VolatilityConfig.id == 1).first()
    if not cfg:
        db.add(VolatilityConfig(
            id=1,
            balanced_abs=5.0,
            surge_gt=6.0,
            dip_lt=-2.0,
            median_window=5
        ))
        db.commit()

    # 2. Product Catalog (Upsert to guarantee latest catalog and alias updates)
    sku_map = {}
    for item in CATALOG_SEED:
        existing = db.query(ProductCatalog).filter(ProductCatalog.canonical_name == item["canonical_name"]).first()
        if existing:
            existing.marathi_name = item["marathi_name"]
            existing.canonical_unit = item["canonical_unit"]
            existing.category = item["category"]
            existing.aliases = item["aliases"]
            existing.is_active = True
        else:
            p = ProductCatalog(
                canonical_name=item["canonical_name"],
                marathi_name=item["marathi_name"],
                canonical_unit=item["canonical_unit"],
                category=item["category"],
                aliases=item["aliases"],
                is_active=True
            )
            db.add(p)
    db.commit()

    # Re-fetch catalog mapping
    for p in db.query(ProductCatalog).all():
        sku_map[p.canonical_name] = p.sku_id

    # 3. Seed Realistic Historical Trips if none exist
    trips_count = db.query(GroceryTrip).count()
    if trips_count == 0:
        now = datetime.datetime.utcnow()

        # Trip 1: 30 days ago
        t1_date = now - datetime.timedelta(days=30)
        t1 = GroceryTrip(
            session_id=str(uuid.uuid4()),
            buyer_id=1,
            merchant_vpa="patil.kirana@upi",
            merchant_name="पाटील सुपर किराणा स्टोअर्स",
            trip_date=t1_date,
            settled_total=1120.00,
            basket_variance=0.0,
            basket_status="संतुलित बजेट",
            status="settled",
            upi_ref="UPI-20261001-998811"
        )
        db.add(t1)
        db.flush()

        t1_items = [
            (sku_map.get("sugar"), 5.0, "kg", 200.0, 40.0, 40.0, 0.0, "संतुलित", "साखर - 5 kg"),
            (sku_map.get("groundnut_oil"), 2.0, "L", 340.0, 170.0, 170.0, 0.0, "संतुलित", "शेंगदाणा तेल 2 L"),
            (sku_map.get("toor_dal"), 2.0, "kg", 280.0, 140.0, 140.0, 0.0, "संतुलित", "तूर डाळ 2 kg"),
            (sku_map.get("rice"), 5.0, "kg", 300.0, 60.0, 60.0, 0.0, "संतुलित", "तांदूळ 5 kg")
        ]
        for sid, q, u, tot, dr, br, var, bdg, raw in t1_items:
            if sid:
                db.add(TripItem(
                    trip_id=t1.trip_id,
                    sku_id=sid,
                    quantity_norm=q,
                    unit=u,
                    entered_total=tot,
                    derived_rate=dr,
                    baseline_rate=br,
                    variance_pct=var,
                    badge=bdg,
                    raw_input=raw,
                    parse_source="regex",
                    ai_confidence=0.98,
                    created_at=t1_date
                ))

        # Trip 2: 15 days ago
        t2_date = now - datetime.timedelta(days=15)
        t2 = GroceryTrip(
            session_id=str(uuid.uuid4()),
            buyer_id=1,
            merchant_vpa="shree.ganesh@okaxis",
            merchant_name="श्री गणेश किराणा भांडार",
            trip_date=t2_date,
            settled_total=1390.00,
            basket_variance=4.12,
            basket_status="संतुलित बजेट",
            status="settled",
            upi_ref="UPI-20261015-442299"
        )
        db.add(t2)
        db.flush()

        t2_items = [
            (sku_map.get("sugar"), 5.0, "kg", 210.0, 42.0, 40.0, 5.0, "संतुलित", "साखर 5 kg"),
            (sku_map.get("groundnut_oil"), 2.0, "L", 360.0, 180.0, 170.0, 5.88, "संतुलित", "shengdana tel 2 L"),
            (sku_map.get("toor_dal"), 2.0, "kg", 310.0, 155.0, 140.0, 10.71, "भाववाढ", "तुरीची डाल 2kg"),
            (sku_map.get("wheat_flour"), 10.0, "kg", 380.0, 38.0, 38.0, 0.0, "नवीन नोंद", "कणिक 10 kg"),
            (sku_map.get("tea_powder"), 0.5, "kg", 130.0, 260.0, 260.0, 0.0, "नवीन नोंद", "चहा 500 gm")
        ]
        for sid, q, u, tot, dr, br, var, bdg, raw in t2_items:
            if sid:
                db.add(TripItem(
                    trip_id=t2.trip_id,
                    sku_id=sid,
                    quantity_norm=q,
                    unit=u,
                    entered_total=tot,
                    derived_rate=dr,
                    baseline_rate=br,
                    variance_pct=var,
                    badge=bdg,
                    raw_input=raw,
                    parse_source="gemini",
                    ai_confidence=0.96,
                    created_at=t2_date
                ))

        # Trip 3: 4 days ago
        t3_date = now - datetime.timedelta(days=4)
        t3 = GroceryTrip(
            session_id=str(uuid.uuid4()),
            buyer_id=1,
            merchant_vpa="om.trading@ybl",
            merchant_name="ओम ट्रेडिंग कंपनी",
            trip_date=t3_date,
            settled_total=1245.00,
            basket_variance=2.89,
            basket_status="संतुलित बजेट",
            status="settled",
            upi_ref="UPI-20261020-773311"
        )
        db.add(t3)
        db.flush()

        t3_items = [
            (sku_map.get("sugar"), 5.0, "kg", 205.0, 41.0, 41.0, 0.0, "संतुलित", "सक्कर 5 kg"),
            (sku_map.get("groundnut_oil"), 2.0, "L", 350.0, 175.0, 175.0, 0.0, "संतुलित", "शेंगदाणातेल 2 L"),
            (sku_map.get("toor_dal"), 2.0, "kg", 300.0, 150.0, 147.5, 1.69, "संतुलित", "तूर डाळ 2 किलो"),
            (sku_map.get("rice"), 5.0, "kg", 290.0, 58.0, 60.0, -3.33, "स्वस्त", "तांदूळ 5 किलो"),
            (sku_map.get("salt"), 2.0, "kg", 50.0, 25.0, 25.0, 0.0, "नवीन नोंद", "मीठ 2 kg"),
            (sku_map.get("turmeric"), 0.25, "kg", 50.0, 200.0, 200.0, 0.0, "नवीन नोंद", "हळद पाव किलो")
        ]
        for sid, q, u, tot, dr, br, var, bdg, raw in t3_items:
            if sid:
                db.add(TripItem(
                    trip_id=t3.trip_id,
                    sku_id=sid,
                    quantity_norm=q,
                    unit=u,
                    entered_total=tot,
                    derived_rate=dr,
                    baseline_rate=br,
                    variance_pct=var,
                    badge=bdg,
                    raw_input=raw,
                    parse_source="gemini",
                    ai_confidence=0.99,
                    created_at=t3_date
                ))

        db.commit()
