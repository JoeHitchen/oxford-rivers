from datetime import date

from django.test import TestCase

from .. import analysis


class Test__DateRange(TestCase):

    def test__standard_use(self):
        """The start date is inclusive and the end date is exclusive"""

        start_date = date.fromisoformat('2024-01-04')
        end_date = date.fromisoformat('2024-01-08')

        dates = analysis.get_date_range(start_date, end_date)
        self.assertEqual(len(dates), 4)
        self.assertIn(start_date, dates)
        self.assertNotIn(end_date, dates)

    def test__same_date(self):
        """The exclusive end date trumps the inclusive start date and the range is empty"""

        start_date = date.fromisoformat('2024-01-04')

        dates = analysis.get_date_range(start_date, start_date)
        self.assertEqual(len(dates), 0)

    def test__reversed(self):
        """Empty output if the end date is before the start date"""

        start_date = date.fromisoformat('2024-01-04')
        end_date = date.fromisoformat('2024-01-08')

        dates = analysis.get_date_range(end_date, start_date)
        self.assertEqual(len(dates), 0)

