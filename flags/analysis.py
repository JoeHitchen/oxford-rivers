from datetime import timedelta
from functools import cache

from . import models


EA_GREEN = 'Green'
EA_YELLOW = 'Yellow'
EA_RED = 'Red'
EA_OUTAGE = 'Outage'


def get_date_range(start_date, end_date):
    """Creates a list of dates inclusive of the start date but exclusive of the end date"""
    return [start_date + timedelta(day) for day in range(0, (end_date - start_date).days)]


def get_statuses_by_date():
    """Creates a date-indexed dictionary of all OURCs flag statuses in the dataset."""

    statuses_by_date = {}
    for reach in models.Reach.objects.all():
        for status in reach.statuses.all():

            status_dates = get_date_range(
                status.first_seen.date() + timedelta(1),
                status.last_seen.date() + timedelta(1),
            )

            for date in status_dates:
                try:
                    statuses_by_date[date][status.reach] = status.flag
                except KeyError:
                    statuses_by_date[date] = {status.reach: status.flag}

    return dict(sorted(statuses_by_date.items()))


def get_advisories_by_date():
    """Creates a date-indexed dictionary of all advisories in the dataset."""

    advisories_by_date = {}
    for reach in models.Reach.objects.all():
        for advisory in reach.advisories.all():

            advisory_dates = get_date_range(
                advisory.first_seen.date() + timedelta(1),
                advisory.last_seen.date() + timedelta(1),
            )

            for date in advisory_dates:
                try:
                    advisories_by_date[date][advisory.reach] = advisory.board
                except KeyError:
                    advisories_by_date[date] = {advisory.reach: advisory.board}

    return dict(sorted(advisories_by_date.items()))


@cache
def get_statuses_and_advisories_by_date():
    """Creates a date-indexed dictionary of all flag statuses and advisories in the dataset."""

    all_data = {}

    for date, statuses in get_statuses_by_date().items():
        all_data[date] = {'statuses': statuses}
    
    for date, advisories in get_advisories_by_date().items():
        if date in all_data:
            all_data[date]['advisories'] = advisories
        else:
            all_data[date] = {'advisories': advisories}

    return dict(sorted(all_data.items()))


