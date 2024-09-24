from unittest.mock import patch

from django.test import TestCase

from flags import models as flags

from .tasks import check_automated_flag
from . import models


class Test__Automation(TestCase):
    fixtures = ['flags', 'autoflags']

    def setUp(self):
        self.autoflag = models.AutoFlag.objects.get(tag = 'godstow')  # Enabled & Grey by default


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


    def test__changed(self):
        """A change is reported if the status has changed"""

        output = check_automated_flag('godstow')
        self.assertEqual(output, 'Change')

        self.autoflag.refresh_from_db()
        self.assertEqual(self.autoflag.status, flags.Status.Flags.GREEN)

