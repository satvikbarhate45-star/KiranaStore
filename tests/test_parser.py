import unittest
from app.services.regex_parser import (
    extract_tokens_from_line,
    normalize_unit_and_quantity,
    normalize_text
)

class TestRegexParser(unittest.TestCase):
    def test_concatenated_marathi_input(self):
        # साखर२किलो -> name: साखर, qty: 2, unit: किलो
        res = extract_tokens_from_line("साखर२किलो")
        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "साखर")
        self.assertEqual(res["qty"], 2.0)
        norm_qty, unit = normalize_unit_and_quantity(res["qty"], res["unit_str"])
        self.assertEqual(norm_qty, 2.0)
        self.assertEqual(unit, "kg")

    def test_concatenated_latin_input(self):
        # shengdanatel2L -> name: shengdanatel, qty: 2, unit: L
        res = extract_tokens_from_line("shengdanatel2L")
        self.assertIsNotNone(res)
        self.assertEqual(res["qty"], 2.0)
        norm_qty, unit = normalize_unit_and_quantity(res["qty"], res["unit_str"])
        self.assertEqual(unit, "L")

    def test_gram_to_kg_normalization(self):
        # तांदूळ५००ग्रॅम -> 0.5 kg
        res = extract_tokens_from_line("तांदूळ५००ग्रॅम")
        self.assertIsNotNone(res)
        norm_qty, unit = normalize_unit_and_quantity(res["qty"], res["unit_str"])
        self.assertEqual(norm_qty, 0.5)
        self.assertEqual(unit, "kg")

    def test_fraction_words(self):
        res = extract_tokens_from_line("साखर अर्धा किलो")
        self.assertIsNotNone(res)
        self.assertEqual(res["qty"], 0.5)

        res2 = extract_tokens_from_line("हळद पाव किलो")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["qty"], 0.25)

    def test_budget_price_to_quantity_intent(self):
        # "mitha 10rupees" should NEVER be 10 kg! Must evaluate to 1 packet with target_price 10
        res = extract_tokens_from_line("mitha 10rupees")
        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "mitha")
        self.assertEqual(res["qty"], 1.0)
        self.assertEqual(res["unit_str"], "पाकीट")
        self.assertEqual(res["target_price"], 10.0)

        # "20 rs kothimbir" -> bunch (पेंढी), qty: 1.0, target_price 20.0
        res_kothimbir = extract_tokens_from_line("20 rs kothimbir")
        self.assertIsNotNone(res_kothimbir)
        self.assertEqual(res_kothimbir["name"], "kothimbir")
        self.assertEqual(res_kothimbir["qty"], 1.0)
        self.assertEqual(res_kothimbir["unit_str"], "पेंढी")
        self.assertEqual(res_kothimbir["target_price"], 20.0)

        # "10 रुपयांचे मीठ"
        res_mr = extract_tokens_from_line("10 रुपयांचे मीठ")
        self.assertIsNotNone(res_mr)
        self.assertEqual(res_mr["name"], "मीठ")
        self.assertEqual(res_mr["qty"], 1.0)
        self.assertEqual(res_mr["target_price"], 10.0)

    def test_unit_preservation_grams_and_liters(self):
        # 100 gm should maintain entered unit gm and entered qty 100
        from app.services.regex_parser import parse_quantity_and_units
        u_info_100gm = parse_quantity_and_units(100, "gm")
        self.assertEqual(u_info_100gm["qty"], 100)
        self.assertEqual(u_info_100gm["unit"], "gm")
        self.assertEqual(u_info_100gm["display_qty"], 100)
        self.assertEqual(u_info_100gm["display_unit"], "ग्रॅम")
        self.assertAlmostEqual(u_info_100gm["quantity_norm"], 0.1, places=3)
        self.assertEqual(u_info_100gm["canonical_unit"], "kg")

        # 250 gm
        u_info_250gm = parse_quantity_and_units(250, "gm")
        self.assertEqual(u_info_250gm["qty"], 250)
        self.assertEqual(u_info_250gm["unit"], "gm")
        self.assertAlmostEqual(u_info_250gm["quantity_norm"], 0.25, places=3)

        # 2 L
        u_info_2L = parse_quantity_and_units(2, "L")
        self.assertEqual(u_info_2L["qty"], 2)
        self.assertEqual(u_info_2L["unit"], "L")
        self.assertEqual(u_info_2L["display_unit"], "लिटर")
        self.assertEqual(u_info_2L["quantity_norm"], 2.0)

    def test_generic_catch_all(self):
        # Line lacking standard markers must preserve raw text, default qty: 1, unit: 'नग'
        res = extract_tokens_from_line("अनोखी किराणा वस्तू")
        self.assertEqual(res["name"], "अनोखी किराणा वस्तू")
        self.assertEqual(res["qty"], 1.0)
        self.assertEqual(res["unit_str"], "नग")
        self.assertIsNone(res["target_price"])

    def test_zero_drop_validation_enforcement(self):
        from app.services.gemini_service import validate_ai_response
        raw_lines = [
            "साखर 2 kg",
            "mitha 10rupees",
            "जिरे 100 gm",
            "अनोखी वस्तू"
        ]
        # Simulate AI omitting 2 lines
        partial_ai_items = [
            {"line_index": 0, "name": "साखर", "qty": 2.0, "unit": "kg", "confidence": 0.98},
            {"line_index": 2, "name": "जिरे", "qty": 100, "unit": "gm", "confidence": 0.95}
        ]
        validated, fails = validate_ai_response(raw_lines, [[], [], [], []], partial_ai_items)
        # MUST yield exactly len(raw_lines) == 4 items
        self.assertEqual(len(validated), 4)
        self.assertEqual(validated[0]["name"], "साखर")
        self.assertEqual(validated[1]["target_price"], 10.0)
        self.assertEqual(validated[2]["unit"], "gm")
        self.assertEqual(validated[2]["qty"], 100)
        self.assertEqual(validated[3]["name"], "अनोखी वस्तू")
        self.assertEqual(validated[3]["unit"], "pcs")

    def test_strict_commodity_separation_godtel_vs_shengdana_oil(self):
        # 1. "गोडतेल" / "godtel" must map strictly to "गोडतेल", NEVER "शेंगदाणा तेल"
        res_godtel = extract_tokens_from_line("गोडतेल 2 L")
        self.assertEqual(res_godtel["name"], "गोडतेल")
        self.assertEqual(res_godtel["qty"], 2.0)
        self.assertEqual(res_godtel["unit_str"], "L")

        res_godtel_latin = extract_tokens_from_line("godtel 2 ltr")
        self.assertEqual(res_godtel_latin["name"], "गोडतेल")
        self.assertEqual(res_godtel_latin["qty"], 2.0)

        # 2. "शेंगदाणा तेल" requires both peanut and oil
        res_sheng_oil = extract_tokens_from_line("shengdana tel 2 L")
        self.assertEqual(res_sheng_oil["name"], "शेंगदाणा तेल")
        self.assertEqual(res_sheng_oil["qty"], 2.0)

        # 3. Raw peanuts without oil MUST NOT become oil
        res_peanuts = extract_tokens_from_line("शेंगदाणा 1 kg")
        self.assertNotIn("तेल", res_peanuts["name"])

    def test_dynamic_brand_extraction_in_brackets(self):
        # Brand extraction: <वस्तूचे नाव> [<ब्रँड नाव>]
        # "नंबर १ साबण" -> साबण [नंबर १]
        res_no1 = extract_tokens_from_line("नंबर १ साबण 4 pcs")
        self.assertEqual(res_no1["name"], "साबण [नंबर १]")
        self.assertEqual(res_no1["qty"], 4.0)

        # "संतूर साबण" -> साबण [संतूर]
        res_santoor = extract_tokens_from_line("संतूर साबण ४ नग")
        self.assertEqual(res_santoor["name"], "साबण [संतूर]")
        self.assertEqual(res_santoor["qty"], 4.0)

        # "फॉर्च्यून गोडतेल" -> गोडतेल [फॉर्च्यून]
        res_fortune = extract_tokens_from_line("फॉर्च्यून गोडतेल 2 L")
        self.assertEqual(res_fortune["name"], "गोडतेल [फॉर्च्यून]")
        self.assertEqual(res_fortune["qty"], 2.0)

        # "विलास अगरबत्ती 50 रुपये" -> अगरबत्ती [विलास], qty: 1, unit: पाकीट, target_price: 50.0
        res_vilas = extract_tokens_from_line("विलास अगरबत्ती 50 रुपये")
        self.assertEqual(res_vilas["name"], "अगरबत्ती [विलास]")
        self.assertEqual(res_vilas["qty"], 1.0)
        self.assertEqual(res_vilas["unit_str"], "पाकीट")
        self.assertEqual(res_vilas["target_price"], 50.0)

        # No brand specified: no brackets!
        res_plain_godtel = extract_tokens_from_line("गोडतेल 2 किलो")
        self.assertEqual(res_plain_godtel["name"], "गोडतेल")
        self.assertNotIn("[", res_plain_godtel["name"])

        res_plain_sugar = extract_tokens_from_line("साखर 2 किलो")
        self.assertEqual(res_plain_sugar["name"], "साखर")
        self.assertNotIn("[", res_plain_sugar["name"])

    def test_intelligent_pre_splitting_multi_delimiters(self):
        from app.services.gemini_service import split_raw_grocery_text
        raw_text = (
            "साखर २ किलो, शेंगदाणा तेल १ लिटर; चहा पावडर २५० ग्रॅम आणि पोहे अर्धा किलो "
            "तसेच १.५ किलो तांदूळ\n1. अगरबत्ती [विलास] ५० रुपये\n- साबण २ नग"
        )
        items = split_raw_grocery_text(raw_text)
        self.assertEqual(len(items), 7)
        self.assertEqual(items[0], "साखर २ किलो")
        self.assertEqual(items[1], "शेंगदाणा तेल १ लिटर")
        self.assertEqual(items[2], "चहा पावडर २५० ग्रॅम")
        self.assertEqual(items[3], "पोहे अर्धा किलो")
        self.assertEqual(items[4], "१.५ किलो तांदूळ")
        self.assertEqual(items[5], "अगरबत्ती [विलास] ५० रुपये")
        self.assertEqual(items[6], "साबण २ नग")

    def test_large_scale_chunking_engine_zero_loss(self):
        from unittest.mock import patch
        from app.services.gemini_service import call_gemini_api_chunked
        
        # Generate 65 items (exceeding chunk_size of 25: chunks of 25, 25, 15)
        raw_lines = [f"वस्तू {i} - {i+1} किलो" for i in range(65)]
        candidates = [[] for _ in range(65)]
        
        # 1. Test successful chunked upstream execution with Gemini mock
        def mock_gemini_call(chunk_lines, chunk_cands):
            return [
                {
                    "line_index": idx,
                    "name": f"वस्तू {idx}",
                    "qty": idx + 1.0,
                    "unit": "kg",
                    "confidence": 0.98,
                    "original_raw": chunk_lines[idx]
                }
                for idx in range(len(chunk_lines))
            ]

        with patch('app.services.gemini_service.call_gemini_api', side_effect=mock_gemini_call):
            result = call_gemini_api_chunked(raw_lines, candidates, db=None, chunk_size=25)
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 65)
            self.assertEqual(result[0]["line_index"], 0)
            self.assertEqual(result[24]["line_index"], 24)
            self.assertEqual(result[25]["line_index"], 25)
            self.assertEqual(result[64]["line_index"], 64)

        # 2. Test chunk failure fallback to local remediation
        with patch('app.services.gemini_service.call_gemini_api', return_value=None):
            result_fallback = call_gemini_api_chunked(raw_lines, candidates, db=None, chunk_size=25)
            self.assertIsNotNone(result_fallback)
            self.assertEqual(len(result_fallback), 65)
            self.assertEqual(result_fallback[0]["line_index"], 0)
            self.assertEqual(result_fallback[64]["line_index"], 64)

    def test_deduplication_repeated_wheat_flour_and_identical_items(self):
        from app.services.regex_parser import deduplicate_parsed_items
        
        # 1. Repeated "गव्हाचे पीठ" on separate lines (accidental repetition)
        repeated_flour = [
            {"line_index": 0, "name": "गव्हाचे पीठ", "qty": 1.0, "unit": "kg", "original_raw": "गव्हाचे पीठ"},
            {"line_index": 1, "name": "गव्हाचे पीठ", "qty": 1.0, "unit": "kg", "original_raw": "गव्हाचे पीठ"}
        ]
        deduped, notifs = deduplicate_parsed_items(repeated_flour, merge_duplicates=False, return_notifications=True)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(len(notifs), 1)
        self.assertIn("गव्हाचे पीठ", notifs[0])

        # 2. Repeated lines with synonymous Devanagari spellings (कणिक vs गव्हाचे पीठ)
        synonyms = [
            {"line_index": 0, "name": "गव्हाचे पीठ", "qty": 5.0, "unit": "kg", "original_raw": "गव्हाचे पीठ 5 kg"},
            {"line_index": 1, "name": "कणिक", "qty": 5.0, "unit": "kg", "original_raw": "कणिक 5 kg"}
        ]
        deduped_syn, notifs_syn = deduplicate_parsed_items(synonyms, merge_duplicates=False, return_notifications=True)
        self.assertEqual(len(deduped_syn), 1)

        # 3. Deliberately distinct entries preserved when quantities differ
        deliberate_diff = [
            {"line_index": 0, "name": "साखर", "qty": 2.0, "unit": "kg", "original_raw": "साखर 2 kg"},
            {"line_index": 1, "name": "साखर", "qty": 5.0, "unit": "kg", "original_raw": "साखर 5 kg"}
        ]
        deduped_delib = deduplicate_parsed_items(deliberate_diff, merge_duplicates=False)
        self.assertEqual(len(deduped_delib), 2)

        # 4. Merging distinct entries when merge_duplicates=True
        merged_delib, notifs_merge = deduplicate_parsed_items(deliberate_diff, merge_duplicates=True, return_notifications=True)
        self.assertEqual(len(merged_delib), 1)
        self.assertEqual(merged_delib[0]["qty"], 7.0)

    def test_classification_clean_vs_complex(self):
        from app.services.regex_parser import classify_item_complexity
        
        # Clean & Confident
        is_complex, reason = classify_item_complexity("साखर 2 किलो")
        self.assertFalse(is_complex)
        self.assertEqual(reason, "clean_confident")

        is_complex2, _ = classify_item_complexity("तांदूळ 5 kg")
        self.assertFalse(is_complex2)

        is_complex3, _ = classify_item_complexity("रवा 1 किलो")
        self.assertFalse(is_complex3)

        # Ambiguous / Complex
        is_complex_curr, reason_curr = classify_item_complexity("अगरबत्ती 50 रुपये")
        self.assertTrue(is_complex_curr)
        self.assertEqual(reason_curr, "currency_notation")

        is_complex_brand, reason_brand = classify_item_complexity("नंबर १ साबण 4 नग")
        self.assertTrue(is_complex_brand)
        self.assertEqual(reason_brand, "unbracketed_brand_marker")

        # Cached brand eliminates complexity
        cache = {"नंबर १ साबण": "साबण [नंबर १]"}
        is_complex_cached, reason_cached = classify_item_complexity("नंबर १ साबण 4 नग", brand_cache=cache)
        self.assertFalse(is_complex_cached)
        self.assertEqual(reason_cached, "cached_brand_commodity")

    def test_biscuit_currency_and_brand_cases(self):
        # Currency/Budget strings: "10 rs बिस्कीट", "अगरबत्ती 50 रुपये"
        res_biscuit = extract_tokens_from_line("10 rs बिस्कीट")
        self.assertIsNotNone(res_biscuit)
        self.assertEqual(res_biscuit["name"], "बिस्कीट")
        self.assertEqual(res_biscuit["qty"], 1.0)
        self.assertEqual(res_biscuit["unit_str"], "पाकीट")
        self.assertEqual(res_biscuit["target_price"], 10.0)

        res_vilas = extract_tokens_from_line("विलास अगरबत्ती")
        self.assertEqual(res_vilas["name"], "अगरबत्ती [विलास]")

        res_santoor = extract_tokens_from_line("संतूर साबण")
        self.assertEqual(res_santoor["name"], "साबण [संतूर]")

    def test_zero_kyc_apmc_mandi_rates_loading(self):
        from app.services.gov_price_service import load_local_apmc_rates
        rates = load_local_apmc_rates()
        self.assertIn("साखर", rates)
        self.assertIn("गोडतेल", rates)
        self.assertIn("शेंगदाणा तेल", rates)
        self.assertIn("तूर डाळ", rates)
        self.assertIn("तांदूळ", rates)
        self.assertIn("गव्हाचे पीठ", rates)
        self.assertIn("रवा", rates)
        self.assertIn("मूग डाळ", rates)
        self.assertIn("कांदा", rates)
        self.assertIn("बटाटा", rates)
        self.assertGreater(rates["साखर"]["modal_price"], 30.0)
        self.assertGreater(rates["गोडतेल"]["modal_price"], 100.0)
        self.assertGreater(rates["शेंगदाणा तेल"]["modal_price"], 150.0)

if __name__ == "__main__":
    unittest.main()
