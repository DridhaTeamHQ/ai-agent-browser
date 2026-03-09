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


if __name__ == '__main__':
    unittest.main()
