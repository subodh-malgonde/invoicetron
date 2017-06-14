from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# Create your views here.

@csrf_exempt
def post_list(request):
    if request.method == "GET":
        response = {"status": "GET request"}
    else:
        print(request.body)
        data = request.body.decode('utf-8')
        response = json.loads(data)
    return JsonResponse(response)

