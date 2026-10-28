from core import tasks_app

from . import data


@tasks_app.task
def fetch_thames_water_discharges():
    stations = data.fetch_thames_water_discharges()
    return [station.name for station in stations]


@tasks_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    
    sender.add_periodic_task(15 * 60, fetch_thames_water_discharges.s())
