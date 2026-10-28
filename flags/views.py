from datetime import timedelta
import logging

from django.db import DatabaseError
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.http import JsonResponse
from django.utils import timezone

from discharges import models as discharges
from jameson import models as jameson

from . import models, transits, analysis

logger = logging.getLogger(__name__)


class FlagNavMixin:
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'all_reaches': models.Reach.objects.all(),
            'flag_reaches': models.Reach.objects.filter(has_ourcs_flag = True).order_by('pk'),
        })
        return context


class Index(FlagNavMixin, TemplateView):
    
    template_name = 'flags/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['all_reaches'] = context['all_reaches'].prefetch_related('advisories')
        context['flag_reaches'] = context['flag_reaches'].prefetch_related('statuses')
        
        context['transits'] = transits.generate_transit_information(
            context['flag_reaches'],
            context['all_reaches'],
        )
        
        try:
            context['differentials'] = jameson.Differential.latest_by_reach()
        except DatabaseError:
            logger.exception('Unable to retrieve differentials from the Jameson database')
            context['differentials'] = []

        context['discharge_events'] = discharges.DischargeEvent.objects.recent_listing()
        context['discharges_out_of_date'] = discharges.Station.readings_out_of_date()

        return context


class FlagHistory(FlagNavMixin, DetailView):
    
    model = models.Reach
    queryset = models.Reach.objects.filter(has_ourcs_flag = True).prefetch_related('statuses')
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/flag_history.html'


class AdvisoryHistory(FlagNavMixin, DetailView):
    
    model = models.Reach
    queryset = models.Reach.objects.prefetch_related('advisories')
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'flags/advisory_history.html'


class Timelines(FlagNavMixin, TemplateView):
    
    template_name = 'flags/timelines.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        context['timeline_data'] = analysis.get_statuses_and_advisories_by_date(today)
        return context


def data_health_api(request):
    """Reports on the oldest flag status and advisory, and whether any outages are recorded."""
    
    def flag_health_ordering(flag_status):
        """Ordered by last seen, with future scope for outages."""
        return (True, flag_status.last_seen)
    
    def advisory_health_ordering(advisory):
        """Ordered by last seen, with trump for outages."""
        return (advisory.board != models.Advisory.Boards.OUT, advisory.last_seen)
    
    reaches = list(models.Reach.objects.all())
    
    current_flags = [reach.current_flag_status for reach in reaches if reach.has_ourcs_flag]
    current_flags.sort(key = flag_health_ordering)
    least_healthy_flag = current_flags[0]
    
    current_advisories = [reach.current_advisory for reach in reaches]
    current_advisories.sort(key = advisory_health_ordering)
    least_healthy_advisory = current_advisories[0]
    
    data_healthy = (
        current_flags[0].last_seen >= timezone.now() - timedelta(hours = 4)
        and least_healthy_advisory.board != models.Advisory.Boards.OUT
        and least_healthy_advisory.last_seen >= timezone.now() - timedelta(hours = 4)
    )
    
    return JsonResponse({
        'health': 'HEALTHY' if data_healthy else 'DATED',
        'oldestCurrentFlag': {
            'reach': least_healthy_flag.reach.tag,
            'status': least_healthy_flag.flag,
            'lastSeen': least_healthy_flag.last_seen,
        },
        'oldestCurrentAdvisory': {
            'reach': least_healthy_advisory.reach.tag,
            'advisory': least_healthy_advisory.board,
            'lastSeen': least_healthy_advisory.last_seen,
        },
    })

