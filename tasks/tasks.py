import time

from celery.schedules import crontab

from core import tasks_app


@tasks_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    
    sender.add_periodic_task(
        crontab(minute = '*/2'),
        wait_return_true.s(3),
    )


@tasks_app.task
def wait_return_true(task_type):
    time.sleep(int(task_type) * 3)
    return True


