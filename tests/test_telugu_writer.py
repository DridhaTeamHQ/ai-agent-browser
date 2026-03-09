import unittest

from core.intelligence.telugu import TeluguWriter


class TeluguWriterTests(unittest.TestCase):
    def setUp(self):
        self.writer = object.__new__(TeluguWriter)

    def test_fit_body_length_clips_to_band(self):
        body = (
            "ఈ కథనం మొదటి భాగం స్పష్టంగా పరిస్థితిని వివరిస్తోంది. "
            "రెండో వాక్యం తాజా పరిణామాలను వివరంగా చెబుతోంది. "
            "మూడో వాక్యం ప్రభావాన్ని మరింత విస్తరించి వివరిస్తోంది. "
            "నాలుగో వాక్యం అవసరానికి మించిన నేపథ్యాన్ని జోడిస్తోంది. "
            "ఐదో వాక్యం పొడవును అదుపు దాటేలా పెంచుతోంది."
        )
        fitted = self.writer._fit_body_length(body, min_chars=355, max_chars=365)
        self.assertLessEqual(len(fitted), 365)
        self.assertTrue(fitted.endswith((".", "!", "?", "।")) or len(fitted) <= 365)

    def test_fit_body_length_pads_near_target_short_body(self):
        body = "ఈ పరిణామం ప్రాంతీయ స్థాయిలో ఆందోళన పెంచుతోంది. అధికారులు పరిస్థితిని సమీక్షిస్తున్నారు."
        fitted = self.writer._fit_body_length(body, min_chars=345, max_chars=365)
        self.assertGreaterEqual(len(fitted), 345)
        self.assertLessEqual(len(fitted), 365)
        self.assertTrue(fitted.endswith((".", "!", "?", "।")))

    def test_fit_body_length_completes_mid_sentence_tail(self):
        body = (
            "AI వాడకం పెరగడంతో ఉద్యోగులపై మానసిక ఒత్తిడి పెరుగుతోందని అధ్యయనం చెబుతోంది. "
            "ఇది పనితీరు, ఏకాగ్రతపై ప్రభావం చూపుతోందని పరిశోధకులు అంటున్నారు. "
            "సంస్థలు సమతుల్య వినియోగంపై దృష్టి పెట్టాలని నిపుణులు"
        )
        fitted = self.writer._fit_body_length(body, min_chars=345, max_chars=365)
        self.assertGreaterEqual(len(fitted), 345)
        self.assertLessEqual(len(fitted), 365)
        self.assertTrue(fitted.endswith((".", "!", "?", "।")))
        self.assertNotIn("నిపుణులు\n", fitted)


if __name__ == "__main__":
    unittest.main()


