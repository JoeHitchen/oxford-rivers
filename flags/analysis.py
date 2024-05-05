from datetime import timedelta

EA_GREEN = 'Green'
EA_YELLOW = 'Yellow'
EA_RED = 'Red'
EA_OUTAGE = 'Outage'


def get_date_range(start_date, end_date):
    """Creates a list of dates inclusive of the start date but exclusive of the end date"""
    return [start_date + timedelta(day) for day in range(0, (end_date - start_date).days)]

