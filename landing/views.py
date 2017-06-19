

from django import template
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.template import loader

from django.views.decorators.csrf import csrf_exempt
import json
from django import http
from django.shortcuts import render_to_response
from django.template.loader import get_template
from django.template import Context
import xhtml2pdf.pisa as pisa
try:
    import StringIO
    StringIO = StringIO.StringIO
except Exception:
    from io import StringIO, BytesIO
import cgi


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

        if action_type == "invoice":
            return render(request, 'application/post_list.html')

        else:
            if action_type == "invoice_confirmation":
                response_message, attachments = Invoice.handle_invoice_confirmation(action_id, json_data)

            elif action_type == "invoice_edition":
                response_message, attachments = LineItem.handle_lineitem_edition(action_id, json_data)

            return JsonResponse({"text": response_message, "attachments": attachments})


    else:
        return HttpResponse("Ok")


def generate_invoice(request, invoice_id):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
        amount = invoice.get_amount()
    except Invoice.DoesNotExist:
        raise Http404("Invoice does not exist")

    if request.method == "GET":
       return render(request, 'application/post_list.html', {'invoice': invoice, 'amount': amount})
    else:
        return render_to_pdf('application/post_list.html', {'invoice': invoice})





def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(StringIO( "{0}".format(html) ), result)
    if not pdf.err:

        return http.HttpResponse(result.getvalue(), content_type='application/pdf')
    return http.HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))