import unittest

from core.validator import ArticleValidator


class ValidatorCategoryTests(unittest.TestCase):
    def test_environment_category_is_valid(self):
        validator = ArticleValidator()
        result = validator.validate(
            english_title='Climate risks deepen across region',
            english_body='Officials say flood risks are rising as heavy rain continues across multiple districts.',
            telugu_title='వాతావరణ ముప్పులు పెరుగుతున్నాయి',
            telugu_body='భారీ వర్షాలు కొనసాగుతున్న నేపథ్యంలో పలుచోట్ల వరద ముప్పు పెరుగుతోందని అధికారులు చెబుతున్నారు.',
            category='Environment',
            image_path=None,
            hashtag='#environment',
            image_search_query='climate flood photo',
        )
        self.assertTrue(result.is_valid)


    def test_source_boilerplate_body_is_rejected(self):
        validator = ArticleValidator()
        result = validator.validate(
            english_title='LPG crisis deepens in India',
            english_body='LPG crisis in India. The Times of India. of India. Times of India.',
            telugu_title='ఎల్పీజీ సంక్షోభం ముదురుతోంది',
            telugu_body='ఇంధన సరఫరా ఒత్తిడి పెరుగుతున్న నేపథ్యంలో పరిస్థితిపై ఆందోళన వ్యక్తమవుతోంది.',
            category='National',
            image_path=None,
            hashtag='#national',
            image_search_query='lpg supply photo',
        )
        self.assertFalse(result.is_valid)
        self.assertIn('source boilerplate', result.error_message.lower())

    def test_titles_with_commas_are_rejected(self):
        validator = ArticleValidator()
        result = validator.validate(
            english_title='Market sinks, panic grows',
            english_body='Officials say selling pressure is deepening as global risks continue to rattle investors.',
            telugu_title='మార్కెట్ కూలింది, ఆందోళన పెరిగింది',
            telugu_body='ప్రపంచ ముప్పులు కొనసాగుతున్న వేళ అమ్మకాల ఒత్తిడి పెరుగుతోందని అధికారులు చెబుతున్నారు.',
            category='Environment',
            image_path=None,
            hashtag='#environment',
            image_search_query='market panic photo',
        )
        self.assertFalse(result.is_valid)
        self.assertIn('comma', result.error_message.lower())
if __name__ == '__main__':
    unittest.main()


