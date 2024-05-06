from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from .. import models, analysis


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


class Test__GetStatusAndAdvisories(TestCase):
    fixtures = ['flags']

    @classmethod
    def setUpTestData(cls):
        cls.isis = models.Reach.objects.get(tag = models.Reach.Common.ISIS)
        cls.godstow = models.Reach.objects.get(tag = models.Reach.Common.GODS)
        cls.radley = models.Reach.objects.get(tag = models.Reach.Common.RAD)

        cls.morning = timezone.now().replace(hour = 10, minute = 15)
        cls.evening = timezone.now().replace(hour = 19, minute = 45)

    def setUp(self):
        analysis.get_statuses_and_advisories_by_date.cache_clear()

    def test__no_data(self):
        """The collation runs with an empty output if no data is set"""

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {})

    def test__flags__single_day(self):
        """Flag statuses only seen within the same day do not appear in the output"""

        self.isis.statuses.create(
            flag = models.Status.Flags.RED,
            set_at = timezone.now(),
            first_seen = self.morning,
            last_seen = self.evening,
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {})

    def test__flags__multi_day(self):
        """Flag statuses appear from the day after they start until the day they end"""

        self.isis.statuses.create(
            flag = models.Status.Flags.RED,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(4),
            last_seen = self.evening - timedelta(1),
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())

        self.assertEqual(all_data, {
            (timezone.now() - timedelta(3)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
            },
            (timezone.now() - timedelta(2)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
            },
            (timezone.now() - timedelta(1)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
            },
        })

    def test__flags__multi_flag(self):
        """Multiple reaches and multiple flag statuses for each each should be handled correctly"""

        self.godstow.statuses.create(
            flag = models.Status.Flags.GREEN,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(7),
            last_seen = self.evening - timedelta(5),
        )
        self.godstow.statuses.create(
            flag = models.Status.Flags.AMBER,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(5),
            last_seen = self.morning - timedelta(3),
        )
        self.isis.statuses.create(  # This should be ignored
            flag = models.Status.Flags.GREEN,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(4),
            last_seen = self.evening - timedelta(4),
        )
        self.isis.statuses.create(
            flag = models.Status.Flags.RED,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(4),
            last_seen = self.evening - timedelta(1),
        )
        self.isis.statuses.create(  # Moved last to check date order handling
            flag = models.Status.Flags.AMBER,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(8),
            last_seen = self.morning - timedelta(4),
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())

        self.assertEqual(all_data, {
            (timezone.now() - timedelta(7)).date(): {
                'statuses': {self.isis: models.Status.Flags.AMBER},
            },
            (timezone.now() - timedelta(6)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.GREEN,
                },
            },
            (timezone.now() - timedelta(5)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.GREEN,
                },
            },
            (timezone.now() - timedelta(4)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.AMBER,
                },
            },
            (timezone.now() - timedelta(3)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.RED,
                    self.godstow: models.Status.Flags.AMBER,
                },
            },
            (timezone.now() - timedelta(2)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
            },
            (timezone.now() - timedelta(1)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
            },
        })
        self.assertEqual(
            list(all_data.keys()),
            analysis.get_date_range((timezone.now() - timedelta(7)).date(), timezone.now().date()),
        )

    def test__advisories__single_day(self):
        """Advisories only seen within the same day do not appear in the output"""

        self.isis.advisories.create(
            board = models.Advisory.Boards.RED,
            first_seen = self.morning,
            last_seen = self.evening,
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {})

    def test__advisories__multi_day(self):
        """Advisories appear from the day after they start until the day they end"""

        self.isis.advisories.create(
            board = models.Advisory.Boards.RED,
            first_seen = self.morning - timedelta(6),
            last_seen = self.evening - timedelta(2),
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {
            (timezone.now() - timedelta(5)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.RED},
            },
            (timezone.now() - timedelta(4)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.RED},
            },
            (timezone.now() - timedelta(3)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.RED},
            },
            (timezone.now() - timedelta(2)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.RED},
            },
        })

    def test__advisories__multi_advisory(self):
        """Multiple reaches and multiple advisories for each each should be handled correctly"""

        self.isis.advisories.create(
            board = models.Advisory.Boards.RED,
            first_seen = self.morning - timedelta(6),
            last_seen = self.evening - timedelta(2),
        )
        self.radley.advisories.create(
            board = models.Advisory.Boards.DEC,
            first_seen = self.morning - timedelta(8),
            last_seen = self.evening - timedelta(5),
        )
        self.radley.advisories.create(
            board = models.Advisory.Boards.NONE,
            first_seen = self.morning - timedelta(5),
            last_seen = self.morning - timedelta(1),
        )
        self.radley.advisories.create(  # This should be ignored
            board = models.Advisory.Boards.NONE,
            first_seen = self.morning - timedelta(1),
            last_seen = self.evening - timedelta(1),
        )
        self.isis.advisories.create(  # Moved last to check date order handling
            board = models.Advisory.Boards.INC,
            first_seen = self.morning - timedelta(10),
            last_seen = self.morning - timedelta(6),
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {
            (timezone.now() - timedelta(9)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.INC},
            },
            (timezone.now() - timedelta(8)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.INC},
            },
            (timezone.now() - timedelta(7)).date(): {
                'advisories': {
                    self.isis: models.Advisory.Boards.INC,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(6)).date(): {
                'advisories': {
                    self.isis: models.Advisory.Boards.INC,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(5)).date(): {
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(4)).date(): {
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(3)).date(): {
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(2)).date(): {
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(1)).date(): {
                'advisories': {self.radley: models.Advisory.Boards.NONE},
            },
        })

        self.assertEqual(
            list(all_data.keys()),
            analysis.get_date_range((timezone.now() - timedelta(9)).date(), timezone.now().date()),
        )

    def test__both__flags_first(self):
        """The overall combined ordering should not be affected by which type starts first"""

        self.godstow.statuses.create(
            flag = models.Status.Flags.GREEN,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(7),
            last_seen = self.evening - timedelta(5),
        )
        self.godstow.statuses.create(
            flag = models.Status.Flags.AMBER,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(5),
            last_seen = self.morning - timedelta(3),
        )
        self.isis.statuses.create(  # This should be ignored
            flag = models.Status.Flags.GREEN,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(4),
            last_seen = self.evening - timedelta(4),
        )
        self.isis.statuses.create(
            flag = models.Status.Flags.RED,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(4),
            last_seen = self.evening - timedelta(1),
        )
        self.isis.statuses.create(  # Moved last to check date order handling
            flag = models.Status.Flags.AMBER,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(10),
            last_seen = self.morning - timedelta(4),
        )
        self.isis.advisories.create(
            board = models.Advisory.Boards.RED,
            first_seen = self.morning - timedelta(6),
            last_seen = self.evening - timedelta(2),
        )
        self.radley.advisories.create(
            board = models.Advisory.Boards.DEC,
            first_seen = self.morning - timedelta(8),
            last_seen = self.evening - timedelta(5),
        )
        self.radley.advisories.create(
            board = models.Advisory.Boards.NONE,
            first_seen = self.morning - timedelta(5),
            last_seen = self.morning - timedelta(1),
        )
        self.radley.advisories.create(  # This should be ignored
            board = models.Advisory.Boards.NONE,
            first_seen = self.morning - timedelta(1),
            last_seen = self.evening - timedelta(1),
        )
        self.isis.advisories.create(  # Moved last to check date order handling
            board = models.Advisory.Boards.INC,
            first_seen = self.morning - timedelta(8),
            last_seen = self.morning - timedelta(6),
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {
            (timezone.now() - timedelta(9)).date(): {
                'statuses': {self.isis: models.Status.Flags.AMBER},
            },
            (timezone.now() - timedelta(8)).date(): {
                'statuses': {self.isis: models.Status.Flags.AMBER},
            },
            (timezone.now() - timedelta(7)).date(): {
                'statuses': {self.isis: models.Status.Flags.AMBER},
                'advisories': {
                    self.isis: models.Advisory.Boards.INC,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(6)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.GREEN,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.INC,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(5)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.GREEN,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(4)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.AMBER,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(3)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.RED,
                    self.godstow: models.Status.Flags.AMBER,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(2)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(1)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
                'advisories': {self.radley: models.Advisory.Boards.NONE},
            },
        })

        self.assertEqual(
            list(all_data.keys()),
            analysis.get_date_range((timezone.now() - timedelta(9)).date(), timezone.now().date()),
        )

    def test__both__advisories_start_first(self):
        """The overall combined ordering should not be affected by which type starts first"""

        self.godstow.statuses.create(
            flag = models.Status.Flags.GREEN,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(7),
            last_seen = self.evening - timedelta(5),
        )
        self.godstow.statuses.create(
            flag = models.Status.Flags.AMBER,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(5),
            last_seen = self.morning - timedelta(3),
        )
        self.isis.statuses.create(  # This should be ignored
            flag = models.Status.Flags.GREEN,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(4),
            last_seen = self.evening - timedelta(4),
        )
        self.isis.statuses.create(
            flag = models.Status.Flags.RED,
            set_at = timezone.now(),
            first_seen = self.evening - timedelta(4),
            last_seen = self.evening - timedelta(1),
        )
        self.isis.statuses.create(  # Moved last to check date order handling
            flag = models.Status.Flags.AMBER,
            set_at = timezone.now(),
            first_seen = self.morning - timedelta(8),
            last_seen = self.morning - timedelta(4),
        )
        self.isis.advisories.create(
            board = models.Advisory.Boards.RED,
            first_seen = self.morning - timedelta(6),
            last_seen = self.evening - timedelta(2),
        )
        self.radley.advisories.create(
            board = models.Advisory.Boards.DEC,
            first_seen = self.morning - timedelta(8),
            last_seen = self.evening - timedelta(5),
        )
        self.radley.advisories.create(
            board = models.Advisory.Boards.NONE,
            first_seen = self.morning - timedelta(5),
            last_seen = self.morning - timedelta(1),
        )
        self.radley.advisories.create(  # This should be ignored
            board = models.Advisory.Boards.NONE,
            first_seen = self.morning - timedelta(1),
            last_seen = self.evening - timedelta(1),
        )
        self.isis.advisories.create(  # Moved last to check date order handling
            board = models.Advisory.Boards.INC,
            first_seen = self.morning - timedelta(10),
            last_seen = self.morning - timedelta(6),
        )

        all_data = analysis.get_statuses_and_advisories_by_date(timezone.now().date())
        self.assertEqual(all_data, {
            (timezone.now() - timedelta(9)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.INC},
            },
            (timezone.now() - timedelta(8)).date(): {
                'advisories': {self.isis: models.Advisory.Boards.INC},
            },
            (timezone.now() - timedelta(7)).date(): {
                'statuses': {self.isis: models.Status.Flags.AMBER},
                'advisories': {
                    self.isis: models.Advisory.Boards.INC,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(6)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.GREEN,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.INC,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(5)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.GREEN,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.DEC,
                },
            },
            (timezone.now() - timedelta(4)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.AMBER,
                    self.godstow: models.Status.Flags.AMBER,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(3)).date(): {
                'statuses': {
                    self.isis: models.Status.Flags.RED,
                    self.godstow: models.Status.Flags.AMBER,
                },
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(2)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
                'advisories': {
                    self.isis: models.Advisory.Boards.RED,
                    self.radley: models.Advisory.Boards.NONE,
                },
            },
            (timezone.now() - timedelta(1)).date(): {
                'statuses': {self.isis: models.Status.Flags.RED},
                'advisories': {self.radley: models.Advisory.Boards.NONE},
            },
        })

        self.assertEqual(
            list(all_data.keys()),
            analysis.get_date_range((timezone.now() - timedelta(9)).date(), timezone.now().date()),
        )

