from django.utils import timezone
import requests
import stripe
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from weasyprint import HTML, CSS
from django.template.loader import render_to_string
from accounts.models import Team, StripeAccountDetails, Employee, Company, Customer
from accounts.utils import build_attachment_for_confirmed_invoice, send_message_to_user
from django.conf import settings

try:
    import StringIO
    StringIO = StringIO.StringIO
except Exception:
    from io import StringIO, BytesIO
from actions.models import Invoice, LineItem


@csrf_exempt
def index(request):
    client_id = settings.SLACK_CLIENT_ID
    return render(request, 'website/index.html', {'client_id': client_id})


@csrf_exempt
def slack_hook(request):
    if request.method == "POST":
        json_data = json.loads(request.POST['payload'])

        action_type, action_id = json_data["callback_id"].split(":")
        attachments = None
        if action_type == "invoice":
            response_message = 'Here is a link to your invoice <%s|click here> ' % request.build_absolute_uri(reverse('generate_pdf', args=[action_id]))

        elif action_type == "settings":
            response_message, attachments = Company.handle_team_settings(json_data)

        elif action_type == "invoice_confirmation":
            response_message, attachments = Invoice.handle_invoice_confirmation(action_id, json_data)

        elif action_type == "invoice_edition":
            response_message, attachments = LineItem.handle_lineitem_edition(action_id, json_data)

        elif action_type == "client_create":
            response_message, attachments = Customer.handle_client_create(action_id, json_data)

        elif action_type == "client_edit":
            response_message,attachments = Customer.handle_client_edit(action_id,json_data)

        elif action_type == "invoice_dropdown":
            response_message = Invoice.handle_new_invoice(json_data)

        elif action_type == "client_list":
            response_message, attachments = Customer.handle_client_list(action_id, json_data)

        elif action_type == "invoice_list":
            response_message, attachments = Invoice.handle_invoice_list(action_id, json_data)

        return JsonResponse({"text": response_message, "attachments": attachments})

    else:
        return HttpResponse("Ok")


@csrf_exempt
def generate_invoice(request, invoice_id):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        return HttpResponse("HTTP 404 Error: The invoice you requested does not exist", status=404)

    charge_status = None

    if request.method == "POST":
        if 'download' in request.POST:
            return pdf_generation(request, invoice)
        else:
            team = invoice.client.team
            employee = invoice.author
            line_item = LineItem.objects.filter(invoice=invoice).first()
            amount = str(line_item.amount)
            if '.' in amount:
                amount = amount.replace(".", "")
            if '$' in amount:
                amount = amount.replace("$", "")
            stripe_account = StripeAccountDetails.objects.filter(team=team).first()
            stripe.api_key = settings.STRIPE_CLIENT_SECRET_KEY
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
            invoice.stripe_charge_id = charge.id
            invoice.save()
            if charge['status'] == 'succeeded':
                invoice.payment_status = Invoice.PAID
                invoice.payment_date = timezone.now()
                invoice.save()
                attachments = build_attachment_for_confirmed_invoice(invoice)
                message = "Your invoice has been paid"
                send_message_to_user(message, employee, team, attachments)

                charge_status = 'successful'
            else:
                charge_status = 'unsuccessful'

    payment_status = invoice.get_payment_status_display()

    payment_date = invoice.payment_date
    if payment_date:
        payment_date = invoice.payment_date.date()

    stripe_pub_key = settings.STRIPE_PUBLIC_KEY

    if invoice.author.company.company_logo:
        logo_url = invoice.company_logo.url
    else:
        logo_url = settings.PLACEHOLDER_LOGO_URL

    stripe_status = False
    team = Team.objects.filter(slack_team_id=invoice.author.company.name).first()
    stripe_account = StripeAccountDetails.objects.filter(team=team).first()
    connect_to_stripe_message = ""
    if stripe_account:
        stripe_status = True
    else:
        connect_to_stripe_message = "Connect to stripe to access payments."


    context = {
        'invoice': invoice, 'payment_status': payment_status, 'stripe': stripe_status, 'payment_date': payment_date,
        'stripe_pub_key': stripe_pub_key, 'charge_status': charge_status, 'logo_url': logo_url,
        'connect_to_stripe_message': connect_to_stripe_message
    }

    return render(request, 'application/invoice.html', context)


def pdf_generation(request, invoice):
    payment_status = invoice.get_payment_status_display()

    payment_date = invoice.payment_date
    if payment_date:
        payment_date = invoice.payment_date.date()

    context = {'invoice': invoice, 'payment_status': payment_status, 'payment_date' : payment_date}
    html_template ='application/invoice.html'
    template_string = render_to_string(html_template, context)
    # static_css_file = settings.STATICFILES_DIRS
    # static_css_file = ''.join(static_css_file)

    pdf_file = HTML(string=template_string).write_pdf()##stylesheets=[CSS(static_css_file + '/b.css')]
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="Invoice.pdf"'
    return response


def stripe_oauth(request):
    code = request.GET['code']
    team_id = request.GET['state']
    data = {
        'client_secret': settings.STRIPE_CLIENT_SECRET_KEY,
        'grant_type': 'authorization_code',
        'client_id': settings.STRIPE_CONNECT_URL,
        'code': code
    }
    response = requests.post(settings.STRIPE_OAUTH_URL, params=data)
    team = Team.objects.get(id=team_id)
    employee = Employee.objects.get(user=team.owner.user)
    stripe_access_token = response.json().get('access_token')
    stripe_user_id = response.json().get('stripe_user_id')
    stripe_publish_key = response.json().get('stripe_publishable_key')

    # stripe_account = StripeAccountDetails.objects.filter(stripe_user_id=stripe_user_id).first()
    StripeAccountDetails.objects.create(team=team, stripe_access_token=stripe_access_token,
                                        stripe_user_id=stripe_user_id,
                                        stripe_publish_key=stripe_publish_key)
    send_message_to_user(message='Your stripe account was successfully connected.\n'
                                     'Type `create invoice` to start invoicing or client', employee=employee, team=team)
    return render(request, 'website/post_connecting_stripe.html')


def slack_oauth(request):

    if request.method == "GET":
        code = request.GET.get('code', None)

        if not code:
            return HttpResponse("Invalid request", status=403)

        params = {
            'code': code,
            'client_id': settings.SLACK_CLIENT_ID,
            'client_secret': settings.SLACK_CLIENT_SECRET
        }
        url = 'https://slack.com/api/oauth.access'
        json_response = requests.get(url, params)
        data = json.loads(json_response.text)
        employee, team = Employee.consume_slack_data(data)

        from accounts.models import onboard_team
        onboard_team(team)

        return render(request, 'website/adminbot_post_add_slack.html')
