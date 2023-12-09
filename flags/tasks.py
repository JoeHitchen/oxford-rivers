from celery.schedules import crontab

from core import tasks_app

from . import models
from . import data


@tasks_app.task
def fetch_ourcs_flag(reach_tag):
    reach = models.Reach.objects.get(tag = reach_tag.lower())
    flag = data.fetch_ourcs_flag(reach)
    return flag.label


@tasks_app.task
def scrape_ea_boards():
    boards = data.scrape_ea_boards()
    return {reach.tag.capitalize(): flag.label for reach, flag in boards.items()}


@tasks_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    
    sender.add_periodic_task(
        crontab(minute = '*/5'),
        scrape_ea_boards.s(),
    )
    
    ourcs_reaches = models.Reach.objects.filter(has_ourcs_flag = True).order_by('pk')
    for reach in ourcs_reaches:
        sender.add_periodic_task(
            crontab(minute = '*/2'),
            fetch_ourcs_flag.s(reach.tag.capitalize()),
        )


