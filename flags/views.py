from django.shortcuts import render, redirect
from django.urls import reverse

from . import models


def index(request):
    reaches = models.Reach.objects.prefetch_related('advisories').all()
    context = {'reaches': reaches}
    return render(request, 'flags/index.html', context)

