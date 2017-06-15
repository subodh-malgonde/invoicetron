from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from actions.models import Invoice, LineItem


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

@csrf_exempt
def slack_hook(request):
    if request.method == "POST":
        json_data = json.loads(request.POST['payload'])


        action_type, action_id = json_data["callback_id"].split(":")
        attachments = None
        if action_type == "invoice_confirmation":
            response_message, attachments = Invoice.handle_invoice_confirmation(action_id, json_data)

        elif action_type == "invoice_edition":
            response_message, attachments = LineItem.handle_lineitem_edition(action_id, json_data)


        return JsonResponse({"text": response_message, "attachments": attachments})
    else:
        return HttpResponse("Ok")


