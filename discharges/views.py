from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from flags.views import FlagNavMixin

from . import models


class History(FlagNavMixin, ListView):

    template_name = 'discharges/history.html'
    paginate_by = 100

    def get_station(self):
        permit_number = self.request.GET.get('station')
        if permit_number:
            return get_object_or_404(models.Station, permit_number = permit_number)

    def get_queryset(self):
        events = models.DischargeEvent.objects.select_related('station')
        station = self.get_station()
        if station:
            events = events.filter(station = station)
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.get_station()
        context['readings_out_of_date'] = models.Station.readings_out_of_date()
        return context
