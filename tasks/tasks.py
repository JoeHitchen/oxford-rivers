import time

from celery import shared_task


@shared_task
def wait_return_true(task_type):
    time.sleep(int(task_type) * 3)
    return True


