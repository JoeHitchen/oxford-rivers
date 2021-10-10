from django.core.management.base import BaseCommand

from ...tasks import wait_return_true


class Command(BaseCommand):
    
    def add_arguments(self, parser):
        parser.add_argument(
            'length',
            type = int,
            help = 'Length of task to trigger, in tens of seconds',
        )
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Running Management command')
        task = wait_return_true.delay(kwargs.get('length', 1))
        self.stdout.write('Started async task: {}'.format(task))

