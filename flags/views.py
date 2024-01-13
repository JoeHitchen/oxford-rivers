from datetime import timedelta

from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.http import JsonResponse
from django.utils import timezone

from . import models, transits


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
        'healthy': 'HEALTHY' if data_healthy else 'UNHEALTHY',
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

