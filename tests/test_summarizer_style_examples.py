import unittest

from core.intelligence.summarize import Summarizer


class SummarizerStyleExampleTests(unittest.TestCase):
    def setUp(self):
        self.summarizer = object.__new__(Summarizer)
        self.summarizer._training_examples = [
            {
                "category": "Technology",
                "style": "policy_regulation",
                "source_title": "UK peers demand AI halt to protect creative rights",
                "target_title": "UK Peers Push AI Curbs to Protect Creative Rights",
                "target_body": "The row is intensifying the debate over AI regulation and intellectual property.",
                "_style_tokens": frozenset({"uk", "peers", "demand", "ai", "halt", "creative", "rights", "regulation", "protect"}),
            },
            {
                "category": "Environment",
                "style": "restoration_conservation",
                "source_title": "Wildlife Trusts restore Norfolk land for ecology",
                "target_title": "Wildlife Trusts Turn Norfolk Land Into New Habitat",
                "target_body": "The project is aimed at boosting biodiversity and rebuilding damaged ecosystems.",
                "_style_tokens": frozenset({"wildlife", "trusts", "restore", "norfolk", "land", "ecology", "biodiversity", "habitat"}),
            },
            {
                "category": "Finance",
                "style": "market_move",
                "source_title": "Gold prices surge sharply in Hyderabad",
                "target_title": "Gold Jumps in Hyderabad as Global Market Swings Bite",
                "target_body": "Analysts say global market volatility is continuing to push domestic bullion prices higher.",
                "_style_tokens": frozenset({"gold", "prices", "surge", "hyderabad", "market", "global", "bullion"}),
            },
        ]

    def test_pick_style_examples_prefers_matching_topic(self):
        picks = self.summarizer._pick_style_examples(
            "UK peers demand AI halt to protect creative rights",
            "Lawmakers are debating whether AI firms can use copyrighted work without consent.",
            limit=2,
        )
        self.assertGreaterEqual(len(picks), 1)
        self.assertEqual(picks[0]["category"], "Technology")

    def test_build_dynamic_style_examples_formats_reference_block(self):
        block = self.summarizer._build_dynamic_style_examples(
            "Wildlife Trusts restore Norfolk land for ecology",
            "The project aims to boost biodiversity through habitat restoration.",
            limit=1,
        )
        self.assertIn("Closest reference examples", block)
        self.assertIn("Category=Environment", block)
        self.assertIn("Better title='Wildlife Trusts Turn Norfolk Land Into New Habitat'", block)

    def test_expand_body_uses_source_specific_context(self):
        body = "Netflix is opening a new office in Hyderabad as its second facility in India after Mumbai."
        source_title = "Netflix to open office in Hyderabad"
        source_body = (
            "Netflix is set to establish a new office in Hyderabad, marking its second facility in India after Mumbai. "
            "The 30,000 sq ft centre will be inaugurated on March 12 by CM Revanth Reddy. "
            "The hub will focus on animation, visual effects and digital content production. "
            "The move is expected to boost the AVGC sector while creating new job opportunities for skilled youth."
        )
        expanded = self.summarizer._expand_body(body, source_title, source_body, target_chars=330, max_chars=350)
        self.assertGreaterEqual(len(expanded), 320)
        self.assertLessEqual(len(expanded), 350)
        self.assertIn("30,000 sq ft centre", expanded)
        self.assertNotIn("follow-up decisions are being prepared", expanded)

    def test_has_title_hook_accepts_active_consequence_headline(self):
        self.assertTrue(self.summarizer._has_title_hook("Airstrikes Empty Beirut Suburbs as Crisis Deepens"))

    def test_boost_title_punch_removes_weak_explainer_phrase(self):
        boosted = self.summarizer._boost_title_punch(
            "Rupee hits all-time low: what it means",
            "Rupee hits all-time low as oil shock rattles markets",
        )
        self.assertNotIn("what it means", boosted.lower())
        self.assertLessEqual(len(boosted), 68)

    def test_fit_body_length_trims_to_target_band(self):
        source_title = "Gold prices surge sharply in Hyderabad"
        source_body = (
            "Gold prices rose sharply in Hyderabad on Saturday, with 24-carat gold jumping by Rs 2,510. "
            "The price of 22-carat gold also increased sharply. "
            "Silver remained around Rs 1.04 lakh per kg. "
            "Analysts say global volatility is influencing domestic bullion prices."
        )
        long_body = (
            "Gold prices rose sharply in Hyderabad on Saturday, with 24-carat rates seeing a major jump. "
            "The move also lifted 22-carat prices and kept silver elevated in local markets. "
            "Traders say global volatility is feeding directly into domestic bullion rates. "
            "The sharp move is now forcing buyers to reassess near-term purchases before the next session opens."
        )
        fitted = self.summarizer._fit_body_length(long_body, source_title, source_body, target_chars=330, min_chars=299, max_chars=350)
        self.assertGreaterEqual(len(fitted), 299)
        self.assertLessEqual(len(fitted), 350)

    def test_fit_body_length_avoids_dangling_tail(self):
        source_title = "Akhtar blasts India, claims cricket imbalance"
        source_body = (
            "Shoaib Akhtar sharply criticized India's T20 World Cup win and said the rivalry is intensifying. "
            "He argued that the gap between teams is widening and warned about long-term balance concerns. "
            "Analysts say the remarks are amplifying debate around competitiveness in major tournaments."
        )
        dangling = (
            "Shoaib Akhtar has sharply criticized India's overwhelming T20 World Cup win, accusing the team "
            "of creating an imbalance in cricket. The former Pakistan pacer compared India's dominance to a "
            "privileged child ruling local games. His remarks underscore the intense cricket rivalry between the "
            "nations. India's victory solidifies their status as a powerhouse in the"
        )
        fitted = self.summarizer._fit_body_length(dangling, source_title, source_body, target_chars=330, min_chars=299, max_chars=350)
        self.assertGreaterEqual(len(fitted), 299)
        self.assertLessEqual(len(fitted), 350)
        self.assertFalse(fitted.lower().endswith("in the."))
        self.assertTrue(fitted.endswith((".", "!", "?")))

    def test_has_dangling_tail_flags_short_subordinate_fragment(self):
        self.assertTrue(self.summarizer._has_dangling_tail("This development comes as the US."))

    def test_looks_broken_sentence_detects_abrupt_us_fragment(self):
        self.assertTrue(self.summarizer._looks_broken_sentence("This development comes as the US."))
        self.assertFalse(
            self.summarizer._looks_broken_sentence(
                "The arrival could signal a shift in US-Cuba relations."
            )
        )

    def test_looks_broken_sentence_detects_short_since_fragment(self):
        self.assertTrue(self.summarizer._looks_broken_sentence("Since the Iraq War."))

    def test_is_weak_ending_sentence_flags_big_picture_wrapup(self):
        self.assertTrue(
            self.summarizer._is_weak_ending_sentence(
                "The development could deepen broader tensions in the region.",
                title="Ireland faces scrutiny over US military use of Shannon",
            )
        )
        self.assertFalse(
            self.summarizer._is_weak_ending_sentence(
                "The airport's involvement in weapons transfers to Israel has sparked criticism.",
                title="Ireland faces scrutiny over US military use of Shannon",
            )
        )

    def test_fit_body_length_removes_dangling_conjunction_tail(self):
        source_title = "Gulf conflict spikes Indian airline costs: Fares rise"
        source_body = (
            "Indian airlines are facing a spike in insurance costs for flights to the Middle East due to ongoing Gulf conflicts. "
            "This increase is significantly affecting operational expenses, prompting airlines to consider raising ticket prices. "
            "The heightened costs are forcing carriers to reevaluate their strategies for Middle Eastern routes."
        )
        dangling = (
            "Indian airlines are facing a spike in insurance costs for flights to the Middle East due to ongoing Gulf conflicts. "
            "This increase is significantly affecting operational expenses, prompting airlines to consider raising ticket prices. "
            "The heightened costs are forcing carriers to reevaluate their strategies for Middle Eastern routes to sustain profitability and"
        )
        fitted = self.summarizer._fit_body_length(dangling, source_title, source_body, target_chars=330, min_chars=299, max_chars=350)
        self.assertGreaterEqual(len(fitted), 299)
        self.assertLessEqual(len(fitted), 350)
        self.assertFalse(fitted.lower().endswith("and."))
        self.assertTrue(fitted.endswith((".", "!", "?")))

    def test_fit_body_length_drops_generic_summary_tail(self):
        source_title = "Ireland faces scrutiny over US military use of Shannon"
        source_body = (
            "Shannon Airport in Ireland is under scrutiny for its role as a transit hub for the US military since the Iraq War. "
            "The airport's involvement in facilitating weapons transfers to Israel has sparked criticism."
        )
        body = (
            "Shannon Airport in Ireland is under scrutiny for its role as a transit hub for the US military since the Iraq War. "
            "The airport's involvement in facilitating weapons transfers to Israel has sparked criticism. "
            "The development could deepen broader tensions in the region."
        )
        fitted = self.summarizer._fit_body_length(body, source_title, source_body, target_chars=330, min_chars=260, max_chars=370)
        self.assertNotIn("broader tensions in the region", fitted)
        self.assertTrue(fitted.endswith((".", "!", "?")))

    def test_normalize_body_punctuation_strips_source_boilerplate(self):
        cleaned = self.summarizer._normalize_body_punctuation(
            "LPG crisis in India: State-wise impact of the Iran war and Strait of Hormuz disruption - The Times of India. of India. Times of India."
        )
        self.assertNotIn("Times of India", cleaned)
        self.assertNotIn("of India. of India", cleaned)

    def test_has_source_boilerplate_detects_publisher_leakage(self):
        self.assertTrue(
            self.summarizer._has_source_boilerplate(
                "LPG crisis in India. The Times of India. of India. Times of India."
            )
        )

    def test_clean_body_copy_uses_named_actor_and_drops_repetition(self):
        source_title = "Trump postpones strikes on Iranian power grid until April 6"
        source_body = (
            "Trump has postponed threatened strikes against Iran's power grid until April 6. "
            "The attacks were threatened as a means of pressuring Iran to reopen the Strait of Hormuz."
        )
        body = (
            "The U.S. president has postponed threatened strikes against Iran's power grid until April 6. "
            "The attacks were threatened as a means of pressuring Iran to reopen the Strait of Hormuz. "
            "The Strait of Hormuz is a vital waterway. "
            "The US president has threatened the attacks as a means of pressuring Iran to reopen Strait of Hormuz."
        )
        cleaned = self.summarizer._clean_body_copy(body, source_title, source_body)
        self.assertIn("Trump has postponed threatened strikes", cleaned)
        self.assertNotIn("vital waterway", cleaned.lower())
        self.assertNotIn("Trump Trump", cleaned)
        self.assertEqual(cleaned.lower().count("reopen the strait of hormuz"), 1)

    def test_clean_body_copy_removes_trump_name_collision_and_broken_fragment(self):
        source_title = "Former US President Donald Trump says he has no problem with tanker arrival"
        source_body = (
            "Former US President Donald Trump said he had no problem with the tanker's arrival. "
            "The move could signal a shift in US-Cuba relations."
        )
        body = (
            "A Russian oil tanker has entered Cuban waters shortly after former U.S. president Donald Trump stated he had no problem with its arrival. "
            "This development comes as the US. "
            "The situation may signal a shift in US-Cuba relations."
        )
        cleaned = self.summarizer._clean_body_copy(body, source_title, source_body)
        self.assertNotIn("former Trump Donald Trump", cleaned)
        self.assertNotIn("Trump Donald Trump", cleaned)
        self.assertIn("Donald Trump", cleaned)
        self.assertNotIn("comes as the US.", cleaned)

    def test_clean_body_copy_drops_overexplained_scrutiny_tail(self):
        source_title = "Ireland faces scrutiny over US military use of Shannon"
        source_body = (
            "Shannon Airport in Ireland is under scrutiny for its role as a transit hub for the US military since the Iraq War. "
            "The airport's involvement in facilitating weapons transfers to Israel has sparked criticism."
        )
        body = (
            "Shannon Airport in Ireland is under scrutiny for its role as a transit hub for the US military since the Iraq War. "
            "The airport's involvement in facilitating weapons transfers to Israel has sparked criticism. "
            "This scrutiny could impact Ireland's international relations and its stance on military neutrality. "
            "It is now under scrutiny again. Since the Iraq War."
        )
        cleaned = self.summarizer._clean_body_copy(body, source_title, source_body)
        self.assertNotIn("It is now under scrutiny again.", cleaned)
        self.assertNotIn("Since the Iraq War.", cleaned)
        self.assertNotIn("This scrutiny could impact", cleaned)

    def test_clean_body_copy_adds_first_mention_acronyms(self):
        source_title = "BCCI announces full schedule for IPL 2026 tournament"
        source_body = (
            "The Board of Control for Cricket in India (BCCI) has released the complete schedule for IPL 2026. "
            "This marks the 19th edition of the professional Twenty20 cricket league."
        )
        body = (
            "The Board of Control for Cricket in India has released the complete schedule for the 2026 Indian Premier League. "
            "This marks the 19th edition of the professional Twenty20 cricket league."
        )
        cleaned = self.summarizer._clean_body_copy(body, source_title, source_body)
        self.assertIn("Board of Control for Cricket in India (BCCI)", cleaned)
        self.assertIn("T20 cricket league", cleaned)

    def test_normalize_acronyms_removes_residual_period_in_us_phrase(self):
        normalized = self.summarizer._normalize_acronyms("U.S. Air Force E-11A")
        self.assertEqual(normalized, "US Air Force E-11A")

    def test_restore_designations_preserves_source_aircraft_identifier(self):
        restored = self.summarizer._restore_designations(
            "US Air Force E11A appears damaged",
            "Images circulating online appear to show damage to a U.S. Air Force E-11A",
            "",
        )
        self.assertIn("E-11A", restored)

    def test_enforce_cautious_body_framing_keeps_unverified_image_claims(self):
        source_title = "Images circulating online appear to show damage to a U.S. Air Force E-11A"
        source_body = (
            "Images circulating online appear to show significant damage to a U.S. Air Force E-11A. "
            "The images have not been independently verified."
        )
        body = "A US Air Force E-11A was badly damaged. The aircraft appears heavily hit."
        cleaned = self.summarizer._enforce_cautious_body_framing(body, source_title, source_body)
        self.assertIn("appear to show", cleaned.lower())
        self.assertIn("E-11A", cleaned)

    def test_passes_credibility_checks_flags_missing_caution(self):
        source_title = "Images circulating online appear to show damage to a U.S. Air Force E-11A"
        source_body = "The images have not been independently verified."
        self.assertFalse(
            self.summarizer._passes_credibility_checks(
                "Damage seen on US Air Force E-11A",
                "A US Air Force E-11A was damaged.",
                source_title,
                source_body,
            )
        )

    def test_passes_credibility_checks_flags_false_verification_language(self):
        source_title = "Images circulating online appear to show damage to a U.S. Air Force E-11A"
        source_body = "The images have not been independently verified and officials have not commented."
        self.assertFalse(
            self.summarizer._passes_credibility_checks(
                "Images appear to show damage to US E-11A",
                "Verified images show major damage and the investigation confirms the hit.",
                source_title,
                source_body,
            )
        )

    def test_enforce_cautious_title_prefers_exact_designation_over_generic_jet(self):
        source_title = "Images circulating online appear to show damage to a U.S. Air Force E-11A in Saudi Arabia"
        source_body = "The images have not been independently verified."
        title = self.summarizer._enforce_cautious_title(
            "Photos show damaged US jet at Saudi air base",
            source_title,
            source_body,
            68,
        )
        self.assertIn("E-11A", title)
        self.assertIn("appear to show", title.lower())
        self.assertNotIn("jet", title.lower())

    def test_title_too_close_to_source_detects_near_copy(self):
        self.assertTrue(
            self.summarizer._title_too_close_to_source(
                "Lebanon PM warns that Israeli actions threaten sovereignty",
                "Lebanon PM warns that Israeli actions threaten sovereignty",
            )
        )

    def test_smart_truncate_title_avoids_cutting_last_word(self):
        title = "Australia's new protest laws accused of targeting Palestine supporters"
        truncated = self.summarizer._smart_truncate_title(title, 62)
        self.assertLessEqual(len(truncated), 62)
        self.assertFalse(truncated.endswith("Palesti"))
        self.assertFalse(truncated.endswith("support"))

    def test_clean_title_copy_rewrites_actor_list_colons(self):
        cleaned = self.summarizer._clean_title_copy(
            "US: UK: EU Oppose UN Slavery Reparations Over Legal Fears",
            "US: UK: EU Oppose UN Slavery Reparations Over Legal Fears",
            "The US, UK, and EU member states are opposing UN-led efforts for slavery reparations.",
        )
        self.assertIn("US, UK, EU members", cleaned)
        self.assertIn("legal risk", cleaned.lower())

    def test_retitle_from_source_rewords_near_copy_headline(self):
        title = self.summarizer._retitle_from_source(
            "Lebanon PM warns that Israeli actions threaten sovereignty",
            (
                "Lebanon's prime minister has warned that Israeli actions and statements are a threat to Lebanese sovereignty. "
                "The statement follows Israel's decision to send additional troops into southern Lebanon."
            ),
            68,
        )
        self.assertNotEqual(
            title.lower(),
            "lebanon pm warns that israeli actions threaten sovereignty",
        )
        self.assertIn("sovereignty", title.lower())
        self.assertLessEqual(len(title), 68)


    def test_fallback_summary_builds_clean_source_led_copy(self):
        source_title = "Gold prices surge sharply in Hyderabad"
        source_body = (
            "Gold prices rose sharply in Hyderabad on Saturday, with 24-carat gold jumping by Rs 2,510. "
            "The price of 22-carat gold also increased sharply. "
            "Silver remained around Rs 1.04 lakh per kg. "
            "Analysts say global volatility is influencing domestic bullion prices."
        )
        result = self.summarizer._fallback_summary(
            source_title,
            source_body,
            min_title=36,
            max_title=62,
            target_body=330,
            min_body=299,
            max_body=350,
        )
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["title"]), 36)
        self.assertGreaterEqual(len(result["body"]), 299)
        self.assertLessEqual(len(result["body"]), 350)
        self.assertNotIn("Times of India", result["body"])
        self.assertTrue(result["body"].endswith((".", "!", "?")))

    def test_fallback_body_prefers_distinct_lead_context_and_consequence(self):
        source_title = "Netflix to open office in Hyderabad"
        source_body = (
            "Netflix is set to establish a new office in Hyderabad, marking its second facility in India after Mumbai. "
            "The 30,000 sq ft centre will be inaugurated on March 12 by CM Revanth Reddy. "
            "The hub will focus on animation, visual effects and digital content production. "
            "The move is expected to boost the AVGC sector while creating new job opportunities for skilled youth."
        )
        body = self.summarizer._fallback_body(
            source_title,
            source_body,
            target_chars=330,
            min_chars=299,
            max_chars=350,
        )
        self.assertIn("30,000 sq ft centre", body)
        self.assertIn("The hub will focus on animation", body)
        self.assertIn("job opportunities", body)
        self.assertNotIn("Netflix to open office in Hyderabad.", body)
        self.assertTrue(body.endswith((".", "!", "?")))

    def test_remove_title_commas_rewrites_separator(self):
        cleaned = self.summarizer._remove_title_commas("Akhtar blasts India, claims cricket imbalance")
        self.assertNotIn(",", cleaned)
        self.assertEqual(cleaned, "Akhtar blasts India: claims cricket imbalance")


if __name__ == "__main__":
    unittest.main()

