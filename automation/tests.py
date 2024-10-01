from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from flags import models as flags

from .tasks import check_automated_flag
from . import models


class Test__Automation(TestCase):
    fixtures = ['flags', 'autoflags']

    def setUp(self):
        self.autoflag = models.AutoFlag.objects.get(tag = 'godstow')  # Enabled & Grey by default
        self.autoflag.statuses.create(
            flag = flags.Status.Flags.RED,
            set_at = timezone.now() - timedelta(1),
        )


    def test__disabled(self):
        """No action is performed if the autoflag is disabled"""

        self.autoflag.enabled = False
        self.autoflag.save()

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'Disabled')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREY)
    

    @patch('automation.tasks.get_current_flag')
    def test__no_change(self, lookup_mock):
        """No change is reported if the status is unchanged"""

        lookup_mock.return_value = flags.Status.Flags.GREY

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'No Change')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREY)


    def test__ourcs_matches(self):
        """No change is reported if the new flag matches the OURCs flag"""

        self.autoflag.statuses.create(flag = flags.Status.Flags.GREEN, set_at = timezone.now())

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'No Notification')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)


    def test__ourcs_differs(self):
        """A change is reported if the status has changed"""

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'Notification')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)

