import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.seed import seed_database

class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        seed_database(db)
        db.close()
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["app_mr"], "स्मार्ट किराणा")

    def test_page_routes(self):
        # Page 1: Home
        r1 = self.client.get("/")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("स्मार्ट किराणा", r1.text)

        # Page 2: History
        r2 = self.client.get("/history/")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("खरेदी इतिहास", r2.text)

        # Page 3: Analyzer
        r3 = self.client.get("/analyzer/")
        self.assertEqual(r3.status_code, 200)
        self.assertIn("दर विश्लेषक", r3.text)

        # Page 4: About
        r4 = self.client.get("/about/")
        self.assertEqual(r4.status_code, 200)
        self.assertIn("आमच्याबद्दल", r4.text)

        # Page 5: Contact
        r5 = self.client.get("/contact/")
        self.assertEqual(r5.status_code, 200)
        self.assertIn("ग्राहक व व्यापारी सहाय्य केंद्र", r5.text)

    def test_parse_list_api(self):
        payload = {
            "session_id": "test-sess-101",
            "raw_text": "साखर - 5 kg\nशेंगदाणा तेल - 2 L",
            "mode": "local_only"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["name"], "साखर")
        self.assertEqual(data["items"][0]["qty"], 5.0)

    def test_simulator_api(self):
        payload = {
            "items": [
                {"sku_id": 1, "quantity": 5.0}, # साखर 5 kg
                {"sku_id": 2, "quantity": 2.0}  # शेंगदाणा तेल 2 L
            ]
        }
        resp = self.client.post("/api/v1/analyzer/simulate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["total_estimated"], 0)
        self.assertEqual(len(data["items"]), 2)

    def test_contact_submit_api(self):
        payload = {
            "name": "अनिकेत जोशी",
            "mobile": "9876543210",
            "category": "बिलिंग गणना अडचण",
            "message": "चाचणी तक्रार संदेश नोंदणी"
        }
        resp = self.client.post("/api/v1/contact", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("SK-TKT-", data["ticket_number"])

    def test_parse_list_api_fallback_zero_drop(self):
        # 4 lines submitted in local_only/fallback mode must yield exactly 4 item records
        payload = {
            "session_id": "test-sess-zero-drop",
            "raw_text": "साखर 2 kg\nmitha 10rupees\nजिरे 100 gm\nअनोखी नवीन वस्तू ५ नग",
            "mode": "local_only"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Zero-loss assertion: 4 lines in = 4 items out
        self.assertEqual(len(data["items"]), 4)
        self.assertTrue(data["ai_fallback"])
        self.assertEqual(data["fallback_notice_mr"], "स्मार्ट सुधारणा उपलब्ध नाही, साधा पार्सर वापरला आहे.")

        # Line 0: साखर 2 kg
        self.assertEqual(data["items"][0]["name"], "साखर")
        self.assertEqual(data["items"][0]["qty"], 2.0)

        # Line 1: mitha 10rupees (currency intent preserved)
        self.assertEqual(data["items"][1]["qty"], 1.0)
        self.assertEqual(data["items"][1]["target_price"], 10.0)

        # Line 2: जिरे 100 gm (unit preserved in grams, not 0.1 kg)
        self.assertEqual(data["items"][2]["qty"], 100)
        self.assertEqual(data["items"][2]["unit"], "gm")

        # Line 3: Generic / uncataloged item preserved
        self.assertIn("अनोखी नवीन वस्तू", data["items"][3]["name"])

    def test_parse_list_api_multi_delimiters(self):
        # Multi-delimiter list: commas, semicolons, Marathi connectors आणि, तसेच
        raw_text = "साखर 2 kg, शेंगदाणा तेल 2 L; जिरे 100 gm आणि चहा पावडर 250 gm तसेच पोहे 1 kg"
        payload = {
            "session_id": "test-sess-delims",
            "raw_text": raw_text,
            "mode": "local_only"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["items"][0]["name"], "साखर")
        self.assertEqual(data["items"][1]["name"], "शेंगदाणा तेल")
        self.assertEqual(data["items"][2]["name"], "जिरे")
        self.assertEqual(data["items"][3]["name"], "चहा पावडर")
        self.assertEqual(data["items"][4]["name"], "पोहे")

    def test_parse_list_api_large_scale_75_items(self):
        # Large-scale list with 75 items: ensures >50 items are supported with zero token drops
        items = [f"साखर {i+1} kg" for i in range(75)]
        payload = {
            "session_id": "test-sess-75-items",
            "raw_items": items,
            "mode": "local_only"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["items"]), 75)
        self.assertEqual(data["items"][0]["line_index"], 0)
        self.assertEqual(data["items"][74]["line_index"], 74)

    def test_commit_and_persist_trip(self):
        # Module 4: Persistence and data integrity
        trip_payload = {
            "session_id": "trip-sess-persist-999",
            "merchant_vpa": "store@upi",
            "merchant_name": "गणेश किराणा",
            "settled_total": 450.0,
            "basket_variance": 2.5,
            "basket_status": "संतुलित बजेट",
            "status": "settled",
            "upi_ref": "UPI-12345678",
            "items": [
                {
                    "sku_id": 1,
                    "name": "साखर",
                    "quantity_norm": 5.0,
                    "unit": "kg",
                    "entered_total": 210.0,
                    "derived_rate": 42.0,
                    "baseline_rate": 40.0,
                    "variance_pct": 5.0,
                    "badge": "संतुलित",
                    "raw_input": "साखर 5 kg",
                    "parse_source": "regex",
                    "ai_confidence": 0.95
                },
                {
                    "sku_id": None, # uncataloged custom item
                    "name": "अगरबत्ती विशेष",
                    "quantity_norm": 2.0,
                    "unit": "packet",
                    "entered_total": 240.0,
                    "derived_rate": 120.0,
                    "baseline_rate": None,
                    "variance_pct": None,
                    "badge": "नवीन नोंद",
                    "raw_input": "अगरबत्ती विशेष २ पाकीट",
                    "parse_source": "regex",
                    "ai_confidence": 0.85
                }
            ]
        }
        post_resp = self.client.post("/api/v1/trips", json=trip_payload)
        self.assertEqual(post_resp.status_code, 200)
        trip_res = post_resp.json()
        trip_id = trip_res["trip_id"]
        self.assertEqual(trip_res["settled_total"], 450.0)
        self.assertEqual(len(trip_res["items"]), 2)

        # Retrieve and verify database persistence
        get_resp = self.client.get(f"/api/v1/trips/{trip_id}")
        self.assertEqual(get_resp.status_code, 200)
        saved_data = get_resp.json()
        self.assertEqual(saved_data["session_id"], "trip-sess-persist-999")
        self.assertEqual(saved_data["merchant_name"], "गणेश किराणा")
        self.assertEqual(len(saved_data["items"]), 2)
        self.assertEqual(saved_data["items"][0]["derived_rate"], 42.0)
        self.assertEqual(saved_data["items"][1]["name"], "अगरबत्ती विशेष")

    def test_parse_list_api_brand_and_commodity_separation(self):
        raw_text = (
            "विलास अगरबत्ती 50 रुपये\n"
            "फॉर्च्यून गोडतेल 2 L\n"
            "गोडतेल 2 L\n"
            "शेंगदाणा तेल 2 L\n"
            "shengdana 1 kg\n"
            "नंबर १ साबण 4 pcs\n"
            "संतूर साबण 2 pcs\n"
            "साखर 2 किलो"
        )
        payload = {
            "session_id": "test-sess-brand-commodity",
            "raw_text": raw_text,
            "mode": "local_only"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"]
        self.assertEqual(len(items), 8)

        # 1. विलास अगरबत्ती 50 रुपये -> अगरबत्ती [विलास], qty: 1.0, unit: packet / पाकीट, target_price: 50.0, sku_id: 25
        self.assertEqual(items[0]["name"], "अगरबत्ती [विलास]")
        self.assertEqual(items[0]["qty"], 1.0)
        self.assertEqual(items[0]["unit"], "packet")
        self.assertEqual(items[0]["display_unit"], "पाकीट")
        self.assertEqual(items[0]["target_price"], 50.0)
        self.assertEqual(items[0]["sku_id"], 25)

        # 2. फॉर्च्यून गोडतेल 2 L -> गोडतेल [फॉर्च्यून], qty: 2.0, unit: L, sku_id: 24 (गोडतेल)
        self.assertEqual(items[1]["name"], "गोडतेल [फॉर्च्यून]")
        self.assertEqual(items[1]["qty"], 2.0)
        self.assertEqual(items[1]["unit"], "L")
        self.assertEqual(items[1]["sku_id"], 24)

        # 3. गोडतेल 2 L -> गोडतेल, qty: 2.0, unit: L, sku_id: 24 (NOT 2)
        self.assertEqual(items[2]["name"], "गोडतेल")
        self.assertEqual(items[2]["qty"], 2.0)
        self.assertEqual(items[2]["unit"], "L")
        self.assertEqual(items[2]["sku_id"], 24)
        self.assertNotIn("[", items[2]["name"])

        # 4. शेंगदाणा तेल 2 L -> शेंगदाणा तेल, qty: 2.0, unit: L, sku_id: 2
        self.assertEqual(items[3]["name"], "शेंगदाणा तेल")
        self.assertEqual(items[3]["qty"], 2.0)
        self.assertEqual(items[3]["unit"], "L")
        self.assertEqual(items[3]["sku_id"], 2)

        # 5. shengdana 1 kg -> शेंगदाणे, qty: 1.0, unit: kg, sku_id: 13 (NOT 2)
        self.assertIn("शेंगदाण", items[4]["name"])
        self.assertNotIn("तेल", items[4]["name"])
        self.assertEqual(items[4]["sku_id"], 13)

        # 6. नंबर १ साबण 4 pcs -> साबण [नंबर १], qty: 4.0, sku_id: 21 (साबण)
        self.assertEqual(items[5]["name"], "साबण [नंबर १]")
        self.assertEqual(items[5]["qty"], 4.0)
        self.assertEqual(items[5]["sku_id"], 21)

        # 7. संतूर साबण 2 pcs -> साबण [संतूर], qty: 2.0, sku_id: 21
        self.assertEqual(items[6]["name"], "साबण [संतूर]")
        self.assertEqual(items[6]["qty"], 2.0)
        self.assertEqual(items[6]["sku_id"], 21)

        # 8. साखर 2 किलो -> साखर, qty: 2.0, sku_id: 1, no brackets
        self.assertEqual(items[7]["name"], "साखर")
        self.assertEqual(items[7]["qty"], 2.0)
        self.assertEqual(items[7]["sku_id"], 1)
        self.assertNotIn("[", items[7]["name"])

    def test_symbiotic_pipeline_end_to_end_deduplication(self):
        # Repeated "गव्हाचे पीठ" should be strictly deduplicated to 1 item
        payload = {
            "session_id": "test-sess-dedup-api",
            "raw_text": "गव्हाचे पीठ\nसाखर 2 किलो\nगव्हाचे पीठ",
            "mode": "auto"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"]
        
        # Exactly 2 unique items out of 3 submitted lines
        self.assertEqual(len(items), 2)
        names = [it["name"] for it in items]
        self.assertIn("गहू पीठ", names)
        self.assertIn("साखर", names)
        self.assertEqual(len(data.get("merged_duplicates", [])), 1)

    def test_symbiotic_pipeline_clean_items_bypass_gemini(self):
        # 100% clean items are parsed instantly without calling Gemini (0s fast pass)
        payload = {
            "session_id": "test-sess-clean-pass",
            "raw_text": "साखर 2 किलो\nतांदूळ 5 kg\nरवा 1 किलो",
            "mode": "auto"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"]

        self.assertEqual(len(items), 3)
        self.assertEqual(data["pipeline"]["source"], "regex")
        self.assertFalse(data["pipeline"]["degraded"])
        self.assertFalse(data["ai_fallback"])
        self.assertLess(data["pipeline"]["latency_ms"], 1000)

    def test_draft_lists_crud_api(self):
        # 1. Create Draft
        draft_payload = {
            "session_id": "draft-sess-test-101",
            "title": "घरगुती मासिक किराणा",
            "raw_text": "साखर 5 kg\nगोडतेल 2 L",
            "items": [
                {"name": "साखर", "qty": 5.0, "unit": "kg", "target_price": 200.0},
                {"name": "गोडतेल", "qty": 2.0, "unit": "L", "target_price": 260.0}
            ]
        }
        res_post = self.client.post("/api/v1/lists/drafts", json=draft_payload)
        self.assertEqual(res_post.status_code, 200)
        draft_data = res_post.json()
        draft_id = draft_data["draft_id"]
        self.assertEqual(draft_data["title"], "घरगुती मासिक किराणा")
        self.assertEqual(draft_data["total_items"], 2)

        # 2. List Drafts
        res_list = self.client.get("/api/v1/lists/drafts")
        self.assertEqual(res_list.status_code, 200)
        drafts = res_list.json()
        self.assertTrue(any(d["draft_id"] == draft_id for d in drafts))

        # 3. Get Single Draft
        res_get = self.client.get(f"/api/v1/lists/drafts/{draft_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["session_id"], "draft-sess-test-101")

        # 4. Delete Draft
        res_del = self.client.delete(f"/api/v1/lists/drafts/{draft_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["success"])

    def test_apmc_market_rates_api(self):
        # Zero-KYC APMC rates endpoint
        res = self.client.get("/api/v1/analyzer/market-rates")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["state"], "Maharashtra")
        rates = data["rates"]
        self.assertGreater(len(rates), 5)
        rate_names = [r["commodity_name"] for r in rates]
        self.assertIn("साखर", rate_names)
        self.assertIn("गोडतेल", rate_names)
        self.assertIn("शेंगदाणा तेल", rate_names)

    def test_audit_3way_api_and_persistence(self):
        # 3-Way Audit calculation
        audit_payload = {
            "session_id": "audit-sess-test-301",
            "items": [
                {"name": "साखर", "qty": 2.0, "quantity_norm": 2.0, "unit": "kg", "enteredTotal": 90.0},
                {"name": "गोडतेल", "qty": 2.0, "quantity_norm": 2.0, "unit": "L", "enteredTotal": 280.0}
            ],
            "shopkeeper_total": 370.0,
            "upi_settled_amount": 370.0
        }
        res_audit = self.client.post("/api/v1/analyzer/audit-3way", json=audit_payload)
        self.assertEqual(res_audit.status_code, 200)
        audit_res = res_audit.json()
        self.assertEqual(audit_res["session_id"], "audit-sess-test-301")
        self.assertGreater(audit_res["govt_total_amount"], 0)
        self.assertEqual(audit_res["shopkeeper_total_amount"], 370.0)
        self.assertEqual(audit_res["upi_settled_amount"], 370.0)
        self.assertEqual(len(audit_res["items_breakdown"]), 2)

        # Save to kirana_trip_analytics table
        save_payload = {
            "session_id": "audit-sess-test-301",
            "govt_total_amount": audit_res["govt_total_amount"],
            "shopkeeper_total_amount": 370.0,
            "upi_settled_amount": 370.0,
            "items_breakdown": [it for it in audit_res["items_breakdown"]]
        }
        res_save = self.client.post("/api/v1/analyzer/save-trip-analytics", json=save_payload)
        self.assertEqual(res_save.status_code, 200)
        saved = res_save.json()
        self.assertEqual(saved["session_id"], "audit-sess-test-301")
        self.assertIn("analytics_id", saved)

        # Retrieve single analytics
        res_get = self.client.get("/api/v1/analyzer/trip-analytics/audit-sess-test-301")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["shopkeeper_total_amount"], 370.0)

    def test_all_html_template_routes_render_200(self):
        for route in ["/", "/analyzer/", "/history/", "/about/", "/contact/"]:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Route {route} failed with status {resp.status_code}")
            self.assertIn("text/html", resp.headers["content-type"])

    def test_godtel_170_yields_fair_price_margin_indicator(self):
        """
        MODULE 2 Verification Criterion:
        Ensure entering a retail rate of ₹170 for गोडतेल yields a "वाजवी दर" badge instead of an overcharging alert.
        """
        payload = {
            "session_id": "test-godtel-fair-margin-170",
            "items": [
                {"name": "गोडतेल", "qty": 1.0, "quantity_norm": 1.0, "unit": "L", "shopkeeper_rate": 170.0}
            ],
            "shopkeeper_total": 170.0,
            "upi_settled_amount": 170.0
        }
        resp = self.client.post("/api/v1/analyzer/audit-3way", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        item_audit = data["items_breakdown"][0]
        
        # Verify fair retail price calculation
        self.assertIsNotNone(item_audit.get("fair_retail_rate"))
        # Verify remark is "वाजवी दर" (Fair Retail Price)
        self.assertEqual(item_audit["remark"], "वाजवी दर")
        self.assertIn("वाजवी दर", item_audit["margin_indicator"])
        # Verify badge label indicates fair retail price
        self.assertIn("वाजवी दर", data["badge_label"])
        self.assertFalse(data["is_inflated"])

    def test_saved_grocery_lists_crud_api(self):
        """
        MODULE 5: Persistent Saved Grocery Lists ("सेव्ह केलेल्या याद्या") API
        """
        create_payload = {
            "list_name": "दिवाळी विशेष किराणा यादी",
            "items": [
                {"name": "साखर", "qty": 5.0, "unit": "किलो", "estimated_price": 210.0},
                {"name": "गोडतेल [फॉर्च्यून]", "qty": 2.0, "unit": "लिटर", "estimated_price": 340.0},
                {"name": "काजू", "qty": 250, "unit": "ग्रॅम", "estimated_price": 240.0}
            ],
            "estimated_budget": 790.0
        }
        # 1. Create saved list
        res_create = self.client.post("/api/v1/lists/saved", json=create_payload)
        self.assertEqual(res_create.status_code, 200)
        saved_data = res_create.json()
        saved_id = saved_data["id"]
        self.assertEqual(saved_data["list_name"], "दिवाळी विशेष किराणा यादी")
        self.assertEqual(saved_data["total_items"], 3)
        self.assertEqual(saved_data["estimated_budget"], 790.0)

        # 2. List all saved lists
        res_list = self.client.get("/api/v1/lists/saved")
        self.assertEqual(res_list.status_code, 200)
        all_saved = res_list.json()
        self.assertGreater(len(all_saved), 0)
        self.assertTrue(any(s["id"] == saved_id for s in all_saved))

        # 3. Retrieve single saved list
        res_single = self.client.get(f"/api/v1/lists/saved/{saved_id}")
        self.assertEqual(res_single.status_code, 200)
        single_data = res_single.json()
        self.assertEqual(single_data["id"], saved_id)
        self.assertEqual(len(single_data["items"]), 3)

        # 4. Delete saved list
        res_del = self.client.delete(f"/api/v1/lists/saved/{saved_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["success"])

    def test_visual_grocery_catalog_endpoint(self):
        """
        MODULE 3: Point-and-Click Visual Grocery Catalog API
        """
        resp = self.client.get("/api/v1/catalog/visual-groceries")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        categories = data["categories"]
        self.assertEqual(len(categories), 8)
        cat_ids = [c["id"] for c in categories]
        self.assertIn("grains_pulses", cat_ids)
        self.assertIn("flours_fasting", cat_ids)
        self.assertIn("oils_ghee", cat_ids)
        self.assertIn("spices_pickles", cat_ids)
        self.assertIn("dry_fruits", cat_ids)
        self.assertIn("beverages_breakfast", cat_ids)
        self.assertIn("personal_care", cat_ids)
        self.assertIn("cleaning_puja", cat_ids)
        self.assertIn("pinned_essentials", data)
        self.assertGreater(len(data["pinned_essentials"]), 0)

    def test_festival_surge_advice_endpoint(self):
        """
        MODULE 6: Festival Surge Predictor API
        """
        resp = self.client.get("/api/v1/analyzer/festival-surge-advice")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("festival_name", data)
        self.assertIn("advice_card_mr", data)
        self.assertIn("सणासुदीचा स्मार्ट खरेदी सल्ला", data["advice_card_mr"])
        self.assertIn("गोडतेलाचे भाव", data["advice_card_mr"])
        self.assertIn("affected_commodities", data)
        self.assertIn("surge_details", data)
        self.assertGreater(len(data["surge_details"]), 0)

    def test_batch_processing_large_scale_55_items_zero_drop(self):
        """
        MODULE 1 Verification Criterion:
        Verify batch processing on 50+ mixed Devanagari lines with zero dropped items ($N$ in -> $N$ out).
        """
        commodities = [
            "साखर २ किलो", "गोडतेल १ लिटर", "शेंगदाणा तेल १ लिटर", "शेंगदाणे ५०० ग्रॅम",
            "तूर डाळ १ किलो", "तांदूळ ५ किलो", "गव्हाचे पीठ १० किलो", "रवा ५०० ग्रॅम",
            "मूग डाळ १ किलो", "कांदा २ किलो", "बटाटा २ किलो", "पोहे १ किलो",
            "गूळ १ किलो", "बेसन ५०० ग्रॅम", "चणा डाळ १ किलो", "हळद १०० ग्रॅम",
            "जिरे १०० ग्रॅम", "मोहरी १०० ग्रॅम", "मीठ १ पाकीट", "चहा पावडर २५० ग्रॅम",
            "अगरबत्ती ५० रुपये", "१० rs बिस्कीट", "साबण [नंबर १] २ नग", "धने पावडर १०० ग्रॅम",
            "गरम मसाला १ पाकीट", "काडेपेटी १ पाकीट", "वाती १ पाकीट", "कापूर १ डबी"
        ]
        # Duplicate with different indexing to make 56 distinct items
        lines_56 = [f"{c} (बॅच {i//len(commodities) + 1})" for i, c in enumerate(commodities * 2)]
        self.assertEqual(len(lines_56), 56)

        payload = {
            "session_id": "test-batch-56-lines",
            "raw_items": lines_56,
            "mode": "local_only"
        }
        resp = self.client.post("/api/v1/lists/parse", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Verify exact 1-to-1 parity: 56 input lines strictly produce 56 verified output items
        self.assertEqual(len(data["items"]), 56, "Zero item loss guarantee violated!")

    def test_historical_commodities_autocomplete_api(self):
        """
        MODULE 4: Dynamic Commodity 3-Way Audit Autocomplete Endpoint
        """
        resp = self.client.get("/api/v1/analyzer/historical-commodities")
        self.assertEqual(resp.status_code, 200)
        commodities = resp.json()
        self.assertIsInstance(commodities, list)
        self.assertGreater(len(commodities), 10)
        self.assertIn("साखर", commodities)
        self.assertIn("चना डाळ", commodities)
        self.assertIn("गोडतेल", commodities)

    def test_unlisted_commodity_dynamic_3way_audit_zero_404(self):
        """
        MODULE 4: Critical Overhaul Requirement
        When querying an unlisted commodity (उदा. 'चना डाळ' यादीत नसताना):
        - Never throws 404
        - Returns subtle notice badge: "ही वस्तू मागील याद्यांमध्ये उपलब्ध नाही (नवीन वस्तू / बाहेरून खरेदी)"
        - Predicts APMC Mandi wholesale rate, Fair Retail Price (20-25% Margin), and Predicted Store Shelf Rate
        """
        resp = self.client.get("/api/v1/analyzer/commodity-audit?commodity=चना+डाळ&quantity=2.0&unit=किलो")
        self.assertEqual(resp.status_code, 200, "Unlisted commodity threw an error instead of 200 OK!")
        data = resp.json()
        self.assertEqual(data["commodity_name"], "चना डाळ")
        self.assertEqual(data["quantity"], 2.0)
        # Verify non-zero predicted prices
        self.assertGreater(data["govt_rate"], 0.0)
        self.assertGreater(data["fair_retail_rate"], 0.0)
        self.assertGreater(data["shopkeeper_rate"], 0.0)
        self.assertGreater(data["upi_settled_rate"], 0.0)
        # Check totals math
        self.assertAlmostEqual(data["govt_total_amount"], round(data["govt_rate"] * 2.0, 2), places=1)
        self.assertAlmostEqual(data["fair_retail_total_amount"], round(data["fair_retail_rate"] * 2.0, 2), places=1)
        # Verify notice when unlisted
        if not data["is_historical"]:
            self.assertIsNotNone(data["notice_mr"])
            self.assertIn("ही वस्तू मागील याद्यांमध्ये उपलब्ध नाही", data["notice_mr"])
        # Verify margin indicator and badge label
        self.assertIn("badge_label", data)
        self.assertIn("margin_indicator", data)

    def test_scan_grocery_image_endpoint(self):
        """Verify POST /api/scan-grocery-image endpoint with image upload."""
        from unittest.mock import patch
        mock_res = {
            "success": True,
            "items": [
                {"item_name": "साखर", "brand": "", "quantity": 5.0, "unit": "किलो"},
                {"item_name": "गोडतेल", "brand": "फॉर्च्यून", "quantity": 1.0, "unit": "लिटर"}
            ]
        }
        with patch("app.services.gemini_service.analyze_grocery_image", return_value=mock_res):
            fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF"
            resp = self.client.post(
                "/api/scan-grocery-image",
                files={"image": ("test.jpg", fake_img, "image/jpeg")}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertEqual(len(data["items"]), 2)
            self.assertEqual(data["items"][0]["item_name"], "साखर")
            self.assertEqual(data["items"][1]["brand"], "फॉर्च्यून")

    def test_scan_grocery_image_price_extraction_no_skipping(self):
        """Verify price extraction, zero row dropping, and summary total line filtering in analyze_grocery_image."""
        import json
        from unittest.mock import patch, MagicMock
        from app.services.gemini_service import analyze_grocery_image
        
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {"item_name": "तूर डाळ", "quantity": 2.0, "unit": "किलो", "price": 310.0},
            {"item_name": "काजू", "quantity": 250.0, "unit": "ग्रॅम", "price": 240.0},
            # Second distinct entry of same commodity must NOT be dropped
            {"item_name": "तूर डाळ", "quantity": 2.0, "unit": "किलो", "price": 310.0},
            # Summary total line must be excluded from item rows
            {"item_name": "एकूण", "quantity": 1.0, "unit": "नग", "price": 860.0}
        ])
        
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client
            
            res = analyze_grocery_image(b"fake_image_bytes")
            self.assertTrue(res["success"])
            # All 3 physical purchase rows preserved without dropping repeated items; summary total excluded
            self.assertEqual(len(res["items"]), 3)
            self.assertEqual(res["items"][0]["item_name"], "तूर डाळ")
            self.assertEqual(res["items"][0]["price"], 310.0)
            self.assertEqual(res["items"][1]["item_name"], "काजू")
            self.assertEqual(res["items"][1]["price"], 240.0)
            self.assertEqual(res["items"][2]["item_name"], "तूर डाळ")
            self.assertEqual(res["items"][2]["price"], 310.0)

    def test_scan_grocery_image_strict_zero_price_and_header_filtering(self):
        """Verify unpriced items get strictly 0.0 price, and store headers/dues are excluded."""
        import json
        from unittest.mock import patch, MagicMock
        from app.services.gemini_service import analyze_grocery_image

        mock_response = MagicMock()
        mock_response.text = json.dumps([
            # Store Header lines (must be filtered out)
            {"item_name": "पावती क्र", "quantity": 1.0, "unit": "नग", "price": 0.0},
            {"item_name": "दिनांक", "quantity": 1.0, "unit": "नग", "price": 0.0},
            {"item_name": "नाव", "quantity": 1.0, "unit": "नग", "price": 0.0},
            # Real item with explicit price
            {"item_name": "सोयाबीन तेल", "quantity": 1.0, "unit": "डबा", "price": 2150.0},
            # Real item without price written on paper (blank/dash/None) -> strictly 0.0
            {"item_name": "जिरे", "quantity": 100.0, "unit": "ग्रॅम", "price": None},
            {"item_name": "मोहरी", "quantity": 100.0, "unit": "ग्रॅम", "price": "-"},
            # Bill Summary lines (must be filtered out)
            {"item_name": "उधारी", "quantity": 1.0, "unit": "नग", "price": 500.0},
            {"item_name": "शिल्लक", "quantity": 1.0, "unit": "नग", "price": 1650.0}
        ])

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            res = analyze_grocery_image(b"fake_image_bytes")
            self.assertTrue(res["success"])
            # Only the 3 actual grocery line items must remain
            self.assertEqual(len(res["items"]), 3)
            self.assertEqual(res["items"][0]["item_name"], "सोयाबीन तेल")
            self.assertEqual(res["items"][0]["price"], 2150.0)
            self.assertEqual(res["items"][1]["item_name"], "जिरे")
            self.assertEqual(res["items"][1]["price"], 0.0)
            self.assertEqual(res["items"][2]["item_name"], "मोहरी")
            self.assertEqual(res["items"][2]["price"], 0.0)

    def test_scan_grocery_image_preserves_string_quantity_with_units(self):
        """Verify quantity is strictly a string with preserved written units (kg, ग्रॅम, ली, पाकीट, अर्धा किलो)."""
        import json
        from unittest.mock import patch, MagicMock
        from app.services.gemini_service import analyze_grocery_image

        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {"item_name": "साखर", "quantity": "2 kg", "unit": "kg", "price": 84.0},
            {"item_name": "वेलची", "quantity": "100 ग्रॅम", "unit": "ग्रॅम", "price": 280.0},
            {"item_name": "गोडतेल", "quantity": "5 ली", "unit": "लिटर", "price": 680.0},
            {"item_name": "मॅगी", "quantity": "2 पाकीट", "unit": "पाकीट", "price": 24.0},
            {"item_name": "तूप", "quantity": "अर्धा किलो", "unit": "किलो", "price": 320.0}
        ])

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            res = analyze_grocery_image(b"fake_image_bytes")
            self.assertTrue(res["success"])
            self.assertEqual(len(res["items"]), 5)
            self.assertEqual(res["items"][0]["quantity"], "2 kg")
            self.assertIsInstance(res["items"][0]["quantity"], str)
            self.assertEqual(res["items"][1]["quantity"], "100 ग्रॅम")
            self.assertIsInstance(res["items"][1]["quantity"], str)
            self.assertEqual(res["items"][2]["quantity"], "5 ली")
            self.assertIsInstance(res["items"][2]["quantity"], str)
            self.assertEqual(res["items"][3]["quantity"], "2 पाकीट")
            self.assertIsInstance(res["items"][3]["quantity"], str)
            self.assertEqual(res["items"][4]["quantity"], "अर्धा किलो")
            self.assertIsInstance(res["items"][4]["quantity"], str)


if __name__ == "__main__":
    unittest.main()

