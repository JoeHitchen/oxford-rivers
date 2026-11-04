from django.views.generic import ListView

from flags.views import FlagNavMixin

from . import models


class History(FlagNavMixin, ListView):

    template_name = 'discharges/history.html'
    paginate_by = 50

    def get_queryset(self):
        return models.DischargeEvent.objects.select_related('station')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['discharge_summary'] = models.Station.summary()
        context['pagination'] = {
            'page_obj': context['page_obj'],
            'paginator': context['paginator'],
        }
        return context
