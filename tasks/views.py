from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from celery.result import AsyncResult

from .tasks import wait_return_true


def index(request):
    return render(request, 'tasks/index.html')


@csrf_exempt
def task_start(request):
    if request.POST:
        task_type = request.POST.get('type')
        task = wait_return_true.delay(int(task_type))
        return JsonResponse({'task_id': task.id}, status = 202)


def task_status(request, task_id):
    task_result = AsyncResult(str(task_id))
    result = {
        'task_id': task_id,
        'task_status': task_result.status,
        'task_result': task_result.result,
    }
    return JsonResponse(result, status = 200)

