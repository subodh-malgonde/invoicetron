
import requests
import stripe
from django import template
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.template import loader

from django.views.decorators.csrf import csrf_exempt
import json
from django import http
from django.shortcuts import render_to_response
from django.template.loader import get_template
from django.template import Context
import xhtml2pdf.pisa as pisa

from accounts.models import Team, StripeAccountDetails, Employee
from accounts.utils import build_attachment_for_confirmed_invoice, send_message_to_user
from invoicetron import settings
from invoicetron.settings import STRIPE_CLIENT_SECRET_KEY, STRIPE_CONNECT_URL, STRIPE_OAUTH_URL

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
            response_message = request.build_absolute_uri(reverse('generate_pdf', args=[action_id]))

        else:
            if action_type == "invoice_confirmation":
                response_message, attachments = Invoice.handle_invoice_confirmation(action_id, json_data)

            elif action_type == "invoice_edition":
                response_message, attachments = LineItem.handle_lineitem_edition(action_id, json_data)

        return JsonResponse({"text": response_message, "attachments": attachments})

    else:
        return HttpResponse("Ok")

@csrf_exempt
def generate_invoice(request, invoice_id):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
        amount = invoice.get_amount()
    except Invoice.DoesNotExist:
        raise Http404("Invoice does not exist")

    if request.method == "GET":
       return render(request, 'application/invoice.html', {'invoice': invoice, 'amount': amount})
    else:
        if 'download' in request.POST:
            return render_to_pdf('application/invoice.html', {'invoice': invoice})
        else:
            team = invoice.client.team
            line_item = LineItem.objects.filter(invoice=invoice).first()
            amount = str(line_item.amount)
            if '.' in amount:
                amount = amount.replace(".", "")
            if '$' in amount:
                amount = amount.replace("$", "")
            stripe_account = StripeAccountDetails.objects.filter(team=team).first()
            stripe.api_key = STRIPE_CLIENT_SECRET_KEY
            token = request.POST['stripeToken']
            email = request.POST['stripeEmail']
            customer = stripe.Customer.create(
                email=email,
                description='demo'
            )
            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=token,
                stripe_account=stripe_account.stripe_user_id,
                description=line_item.description
            )

            invoice.payment_status = Invoice.PAID
            invoice.save()

            employee = Employee.objects.filter(slack_username=invoice.author).first()
            attachments = build_attachment_for_confirmed_invoice(invoice)
            message = "Your invoice has been paid"
            send_message_to_user(message, employee, team, attachments )

            return render(request, 'application/invoice.html')


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(StringIO("{0}".format(html) ), result)
    if not pdf.err:

        return http.HttpResponse(result.getvalue(), content_type='application/pdf')
    return http.HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))


def after_connecting(request):

    if request.method == "GET":
        code = request.GET['code']
        team_id = request.GET['state']
        data = {
            'client_secret': STRIPE_CLIENT_SECRET_KEY,
            'grant_type': 'authorization_code',
            'client_id': STRIPE_CONNECT_URL,
            'code': code
        }
        response = requests.post(STRIPE_OAUTH_URL, params=data)



        team = Team.objects.filter(id = team_id).first()
        stripe_access_token = response.json().get('access_token')
        stripe_user_id = response.json().get('stripe_user_id')
        stripe_publish_key = response.json().get('stripe_publishable_key')
        stripe_account = StripeAccountDetails.objects.filter(stripe_user_id=stripe_user_id).first()
        if stripe_account is None:
            StripeAccountDetails.objects.create(team=team, stripe_access_token=stripe_access_token, stripe_user_id=stripe_user_id,
                                            stripe_publish_key=stripe_publish_key)
            return render(request, 'application/after_connection.html', {'stripe_user_id': stripe_user_id})
        else:
            stripe_user_id='Your account is already connected'
            return render(request, 'application/after_connection.html', {'stripe_user_id': stripe_user_id})

    else:
        pass

@csrf_exempt
def stripe_event_hook(request):
  # Retrieve the request's body and parse it as JSON
    event_json = json.loads(request.body)

  # Do something with event_json
    return HttpResponse(status=200)


def index(request):
    client_id = settings.SLACK_CLIENT_ID
    return render(request, 'application/install.html', {'client_id': client_id})

def slack_oauth(request):

    if request.method == "GET":
        code = request.GET['code']

        params = {
            'code': code,
            'client_id': settings.SLACK_CLIENT_ID,
            'client_secret': settings.SLACK_CLIENT_SECRET
        }
        url = 'https://slack.com/api/oauth.access'
        json_response = requests.get(url, params)
        data = json.loads(json_response.text)
        employee,team = Employee.consume_slack_data(data)

        send_message_to_user(message="Hi. Welcome to Invoicetron", employee=employee, team=team)
        return render(request, 'application/after_installing.html')





