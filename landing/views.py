import requests
import stripe
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
import json
from weasyprint import HTML, CSS

from django.template.loader import render_to_string
from accounts.models import Team, StripeAccountDetails, Employee, Company
from accounts.utils import build_attachment_for_confirmed_invoice, send_message_to_user
from invoicetron import settings
from invoicetron.settings import STRIPE_CLIENT_SECRET_KEY, STRIPE_CONNECT_URL, STRIPE_OAUTH_URL

try:
    import StringIO
    StringIO = StringIO.StringIO
except Exception:
    from io import StringIO, BytesIO
from actions.models import Invoice, LineItem


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
            response_message = 'Click on this link to get your pdf  ' + request.build_absolute_uri(reverse('generate_pdf', args=[action_id]))

        elif action_type == "settings":
            response_message, attachments = Company.handle_team_settings(json_data)

        elif action_type == "invoice_confirmation":
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
            return pdf_generation(request, invoice)##render_to_pdf('application/invoice.html', {'invoice': invoice})
        else:
            team = invoice.client.team
            employee = Employee.objects.get(slack_username=invoice.author)
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

            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=token,
                stripe_account=stripe_account.stripe_user_id,
                description=line_item.description,
                receipt_email=email
            )
            invoice.stripe_charge_id=charge.id
            invoice.save()
            if charge['status'] == 'succeeded':
                invoice.payment_status = Invoice.PAID
                invoice.save()
                attachments = build_attachment_for_confirmed_invoice(invoice)
                message = "Your invoice has been paid"
                send_message_to_user(message, employee, team, attachments)
                return render(request, 'application/invoice.html',{'invoice': invoice})

def pdf_generation(request, invoice):
    context = {'invoice': invoice}
    html_template ='application/invoice.html'
    template_string = render_to_string(html_template, context)
    static_css_file = settings.STATICFILES_DIRS
    static_css_file = ''.join(static_css_file)

    pdf_file = HTML(string=template_string).write_pdf(stylesheets=[CSS(static_css_file + '/bootstrap.css')])
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="Invoice.pdf"'
    return response

def stripe_oauth(request):
    code = request.GET['code']
    team_id = request.GET['state']
    data = {
        'client_secret': STRIPE_CLIENT_SECRET_KEY,
        'grant_type': 'authorization_code',
        'client_id': STRIPE_CONNECT_URL,
        'code': code
    }
    response = requests.post(STRIPE_OAUTH_URL, params=data)

    team = Team.objects.get(id=team_id)
    employee = Employee.objects.get(user=team.owner.user)
    stripe_access_token = response.json().get('access_token')
    stripe_user_id = response.json().get('stripe_user_id')
    stripe_publish_key = response.json().get('stripe_publishable_key')
    stripe_account = StripeAccountDetails.objects.filter(stripe_user_id=stripe_user_id).first()
    if stripe_account is None:
        StripeAccountDetails.objects.create(team=team, stripe_access_token=stripe_access_token,
                                            stripe_user_id=stripe_user_id,
                                            stripe_publish_key=stripe_publish_key)
        send_message_to_user(message='Hurray.Your account has been connected', employee=employee, team=team)
        return render(request, 'application/after_connection.html', {'stripe_account': stripe_account})
    else:
        return render(request, 'application/after_connection.html', {'stripe_account': stripe_account})


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




        # def render_to_pdf(template_src, context_dict):
        #     template = get_template(template_src)
        #     context = Context(context_dict)
        #     html  = template.render(context)
        #     result = BytesIO()
        #     pdf = pisa.pisaDocument(StringIO(html.decode("utf-8")), result) ##"{0}".format(html)
        #     if not pdf.err:
        #
        #         return http.HttpResponse(result.getvalue(), content_type='application/pdf')
        #     return http.HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))

# {
#   "amount": 3000,
#   "amount_refunded": 0,
#   "application": "ca_As3LPNYpHh1uDPy8C8bn69DTWkIJ9ZTk",
#   "application_fee": null,
#   "balance_transaction": "txn_1AXn2JKOlckYU7UIvXXF2KSt",
#   "captured": true,
#   "created": 1498206062,
#   "currency": "usd",
#   "customer": null,
#   "description": "mobile cover",
#   "destination": null,
#   "dispute": null,
#   "failure_code": null,
#   "failure_message": null,
#   "fraud_details": {},
#   "id": "ch_1AXn2IKOlckYU7UI6B51YlHg",
#   "invoice": null,
#   "livemode": false,
#   "metadata": {
#     "invoice_id": "28"
#   },
#   "object": "charge",
#   "on_behalf_of": null,
#   "order": null,
#   "outcome": {
#     "network_status": "approved_by_network",
#     "reason": null,
#     "risk_level": "normal",
#     "seller_message": "Payment complete.",
#     "type": "authorized"
#   },
#   "paid": true,
#   "receipt_email": "f@amazon.com",
#   "receipt_number": null,
#   "refunded": false,
#   "refunds": {
#     "data": [],
#     "has_more": false,
#     "object": "list",
#     "total_count": 0,
#     "url": "/v1/charges/ch_1AXn2IKOlckYU7UI6B51YlHg/refunds"
#   },
#   "review": null,
#   "shipping": null,
#   "source": {
#     "address_city": null,
#     "address_country": null,
#     "address_line1": null,
#     "address_line1_check": null,
#     "address_line2": null,
#     "address_state": null,
#     "address_zip": null,
#     "address_zip_check": null,
#     "brand": "Visa",
#     "country": "US",
#     "customer": null,
#     "cvc_check": "pass",
#     "dynamic_last4": null,
#     "exp_month": 12,
#     "exp_year": 2021,
#     "fingerprint": "bUpoBOxJfqQXhqia",
#     "funding": "credit",
#     "id": "card_1AXn2IKOlckYU7UIcEs0YMQl",
#     "last4": "4242",
#     "metadata": {},
#     "name": "x@b.com",
#     "object": "card",
#     "tokenization_method": null
#   },
#   "source_transfer": null,
#   "statement_descriptor": null,
#   "status": "succeeded",
#   "transfer_group": null
# }
#
#
#
