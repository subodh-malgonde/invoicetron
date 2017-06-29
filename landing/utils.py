import re
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from accounts.models import Employee, Team, Customer, Company
from accounts.utils import build_attachments_for_edited_invoice, send_message_to_user, build_attachments_for_invoice, \
    build_attachment_for_confirmed_invoice, build_attachment_for_error, build_message_for_help, \
    build_attachment_for_listing_clients, build_attachment_for_settings, build_attachment_for_edited_settings, \
    build_attachment_for_editing_client, build_attachment_for_new_invoice, build_attachment_for_no_clients, \
    build_attachment_for_pagination_for_invoices, \
    build_attachment_for_pagination_for_clients
from landing.models import UserInteractionState
from actions.models import LineItem, Invoice
import boto3
from slackclient import SlackClient
import json


def handle_slack_events(events):
    for event in events:
        handle_slack_event(event)

def handle_slack_event(event):
    if 'type' in event.keys() and event['type'] == 'message':
        if 'subtype' in event.keys() and event['subtype'] == 'file_share':
            message = 'Uploading your company logo. Please wait'
            upload_logo()
            pass

        else:

            if "user" in event.keys():
                username = event['user']
                team = Team.objects.filter(slack_team_id=event['team']).first()
                company = Company.objects.get(name=team.slack_team_id)
                client = SlackClient(team.slack_bot_access_token)
                employee = Employee.objects.filter(user__username=username).first()

                if not employee:
                    response = client.api_call('users.info', user=username)
                    if response['ok']:
                        user = User.objects.filter(username=username).first()
                        if not user:
                            user = User.objects.create(username=username)
                        employee = Employee.objects.create(user=user, company=company,
                                                           slack_username=response['user']['name'],
                                                           slack_tz_label=response['user']['tz_label'],
                                                           slack_tz=response['user']['tz'])

                state = UserInteractionState.get_state_for_employee(employee)

                if state.state == UserInteractionState.CHILLING:
                    new_message = event['text']
                    if '$' in new_message:
                        new_message = new_message.replace("$", "")
                    inputstring = new_message
                    client2 = boto3.client('lex-runtime')
                    response = client2.post_text(
                        botName='invoicetron',
                        botAlias='version',
                        userId=username,
                        inputText=inputstring
                    )
                    print(response)
                    if "intentName" in response:

                        if response['intentName'] == 'settings':
                            if response['dialogState'] == 'Fulfilled':
                                company_name = company.company_name
                                company_logo = company.company_logo
                                if company_name is None and company_logo is None:
                                    message = 'You have not set your company details'
                                    attachments = build_attachment_for_edited_settings(team)
                                    attachment_str = json.dumps(attachments)
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=message, attachments=attachment_str)
                                else:
                                    message = ''
                                    attachments = build_attachment_for_settings(team)
                                    attachment_str = json.dumps(attachments)
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=message, attachments=attachment_str)

                        elif response['intentName'] == 'create_invoice':
                            if response['dialogState'] == 'ElicitSlot':

                                if response['slots']['ClientName'] is not None:

                                    amount = response['slots']['Amount']
                                    name_of_client = response['slots']['ClientName']
                                    invoice_client = Customer.objects.filter(name__icontains=name_of_client).first()
                                    if not invoice_client:
                                        message = "Client '{}' is not created. Lets create the client first".format(
                                            name_of_client)
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message)
                                        response2 = client2.post_text(
                                            botName='invoicetron',
                                            botAlias='version',
                                            userId=username,
                                            inputText='create {} of {}'.format(name_of_client, amount)
                                        )
                                        if response2['dialogState'] == 'ElicitSlot':
                                            client.api_call('chat.postMessage', channel=event['channel'],
                                                            text=response2['message'])
                                    else:
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=response['message'])
                                elif response['slots']['ClientName'] is None and response['slots']['Amount'] is None:
                                    attachment = build_attachment_for_new_invoice()
                                    attachment_str = json.dumps(attachment)
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text='',attachments = attachment_str)


                                else:
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=response['message'])

                            elif response['dialogState'] == 'Fulfilled':
                                amount = response['slots']['Amount']
                                name_of_client = response['slots']['ClientName']
                                invoice_client = Customer.objects.filter(name__icontains=name_of_client).first()
                                if not invoice_client:
                                    message = "The client name you entered is not created.Lets create the client first"
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=message)
                                    response2 = client2.post_text(
                                        botName='invoicetron',
                                        botAlias='version',
                                        userId=username,
                                        inputText='create {} of {}'.format(name_of_client, amount)
                                    )
                                    if response2['dialogState'] == 'ElicitSlot':
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=response2['message'])
                                else:
                                    state.state = UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED
                                    state.save()
                                    message = 'Great! Almost there. Please type description.'
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=message)
                                    create_invoice(invoice_client, employee, amount)

                        elif response['intentName'] == 'create_client':
                            if response['dialogState'] == 'ElicitSlot':
                                if response['slots']['ClientName'] is not None and response['slotToElicit'] == 'ClientEmail':
                                    name_of_client = response['slots']['ClientName']
                                    customer = Customer.objects.filter(name__icontains=name_of_client).first()
                                    if not customer:
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=response['message'])
                                    else:
                                        message = 'Client name you entered is already created.'

                                        attachment = build_attachment_for_listing_clients(customer, add_more=True)
                                        attachment_str = json.dumps(attachment)
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message, attachments=attachment_str)
                                else:
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=response['message'])
                            if response['dialogState'] == 'Fulfilled':
                                response_email = response['slots']['ClientEmail']
                                if "|" in response_email:
                                    response_email = response_email.split("|")[1]
                                customer = Customer.objects.create(name=response['slots']['ClientName'],
                                                        email_id=response_email,
                                                        team=team, created_by=employee)
                                attachment = build_attachment_for_listing_clients(customer, add_more=True)
                                attachment_str = json.dumps(attachment)
                                client.api_call('chat.postMessage', channel=event['channel'],
                                                text=response['message'], attachments=attachment_str)
                                if 'invoice' in response['sessionAttributes'].keys():
                                    session = json.loads(response['sessionAttributes']['invoice'])
                                    client_name = session['ClientName']
                                    total_amount = session['Amount']
                                    response2 = client2.post_text(
                                        botName='invoicetron',
                                        botAlias='version',
                                        userId=username,
                                        inputText='create invoice for {} of total {}'.format(client_name, total_amount)
                                    )

                                    invoice_client = Customer.objects.filter(name__icontains=client_name).first()

                                    if response2['dialogState'] == 'ElicitSlot':
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=response2['message'])

                                    elif response2['dialogState'] == 'Fulfilled':
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=response2['message'])
                                        state.state = UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED
                                        state.save()
                                        message = 'Enter the description for this invoice'
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message)
                                        create_invoice(invoice_client, employee, total_amount)
                                else:
                                    pass

                        elif response['intentName'] == 'list_invoices':
                            if response['dialogState'] == 'Fulfilled':

                                if response['slots']['Paid'] == None and response['slots']['Sent'] == None:
                                    list_invoices(employee, team,page=1, payment_status=None, sent_status=None)
                                elif response['slots']['Paid'] is not None and response['slots']['Sent'] == None:
                                    payment_status = response['slots']['Paid']
                                    list_invoices(employee, team,page=1, payment_status=payment_status, sent_status=None)
                                elif response['slots']['Paid'] == None and response['slots']['Sent'] is not None:
                                    sent_status = response['slots']['Sent']
                                    list_invoices(employee, team, page=1, payment_status=None, sent_status=sent_status)
                                elif response['slots']['Paid'] is not None and response['slots']['Sent'] is not None:
                                    payment_status = response['slots']['Paid']
                                    sent_status = response['slots']['Sent']
                                    list_invoices(employee, team,page=1, payment_status=payment_status, sent_status=sent_status)

                        elif response['intentName'] == 'start':
                            message = build_message_for_help()
                            client.api_call('chat.postMessage', channel=event['channel'],
                                            text=message)

                        elif response['intentName'] == 'list_clients':
                            if response['dialogState'] == 'Fulfilled':
                                list_clients(employee, team, page=1)

                    else:
                        message = " :x: I am afraid I did not understand. Please type `help` to know more about me.\n" \
                                  "What are you looking for?"
                        attachments = build_attachment_for_error()
                        attachment_str = json.dumps(attachments)

                        client.api_call('chat.postMessage', channel=event['channel'],
                                        text=message, attachments=attachment_str)

                elif state.state == UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED:

                    line_item = LineItem.objects.filter(edited_details_awaited_from=employee).order_by(
                        '-updated_at').first()

                    description = line_item.description

                    if description is None:
                        line_item.description = event['text']
                        line_item.edited_details_awaited_from = None
                        line_item.invoice.description = event['text']
                        line_item.save()
                        state.state = UserInteractionState.CHILLING
                        state.save()
                        invoice = line_item.invoice
                        invoice.description = event['text']
                        invoice.save()
                        message = "Awesome! You have successfully created your invoice."
                        attachments = build_attachments_for_invoice(invoice)
                    else:
                        line_item.description = event['text']
                        line_item.edited_details_awaited_from = None
                        line_item.invoice.description = event['text']
                        line_item.save()
                        state.state = UserInteractionState.CHILLING
                        state.save()
                        invoice = line_item.invoice
                        invoice.description = event['text']
                        invoice.save()
                        message = "Description has been edited"
                        attachments = build_attachments_for_edited_invoice(invoice)

                    send_message_to_user(message, employee, team, attachments)

                elif state.state == UserInteractionState.LINE_ITEM_AMOUNT_AWAITED:
                    new_message = event['text']
                    if '$' in new_message:
                        new_message = new_message.replace("$", "")
                    if not re.match('^[0-9]+$', new_message):
                        message = "Enter the correct amount"
                        send_message_to_user(message, employee, team)
                    else:
                        line_item = LineItem.objects.filter(edited_details_awaited_from=employee).first()
                        line_item.amount = new_message
                        line_item.edited_details_awaited_from = None

                        line_item.save()
                        state.state = UserInteractionState.CHILLING
                        state.save()

                        invoice = line_item.invoice
                        message = "Amount has been changed"
                        attachments = build_attachments_for_edited_invoice(invoice)

                        send_message_to_user(message, employee, team, attachments)

                elif state.state == UserInteractionState.COMPANY_NAME_AWAITED:

                    new_message = event['text']
                    company = Company.objects.filter(edited_details_awaited_from_for_company=employee).first()
                    print(company)
                    company.company_name = new_message
                    company.edited_details_awaited_from_for_company = None
                    company.save()

                    state.state = UserInteractionState.CHILLING
                    state.save()

                    message = "Great!"
                    attachments = build_attachment_for_edited_settings(team)
                    send_message_to_user(message, employee, team, attachments)

                elif state.state == UserInteractionState.CLIENT_NAME_AWAITED:
                    new_message = event['text']
                    customer = Customer.objects.filter(edited_details_awaited_from=employee).first()
                    print(customer)
                    customer.name = new_message
                    customer.edited_details_awaited_from = None
                    customer.save()

                    state.state = UserInteractionState.CHILLING
                    state.save()

                    message = ''
                    attachments = build_attachment_for_editing_client(customer)
                    send_message_to_user(message, employee, team, attachments)

                elif state.state == UserInteractionState.CLIENT_EMAIL_AWAITED:
                    new_message = event['text']
                    customer = Customer.objects.filter(edited_details_awaited_from=employee).first()

                    customer.email_id = new_message
                    customer.edited_details_awaited_from = None
                    customer.save()

                    state.state = UserInteractionState.CHILLING
                    state.save()

                    message = ''
                    attachments = build_attachment_for_editing_client(customer)
                    send_message_to_user(message, employee, team, attachments)

def create_invoice(invoice_client, employee, amount):
    invoice = Invoice.objects.create(client=invoice_client,author=employee)
    line_item = LineItem.objects.create(invoice=invoice, amount=amount)
    line_item.edited_details_awaited_from = employee
    line_item.save()

def list_invoices(employee, team, page, payment_status, sent_status):


    invoices = Invoice.objects.filter(author=employee).order_by('-created_at').all()
    # team = Team.objects.filter(slack_team_id=event['team']).first()

    if payment_status is not None and sent_status is not None:
        invoices = Invoice.objects.filter(author=employee,payment_status= payment_status, sent_status = sent_status).order_by('-created_at').all()
    elif payment_status is not None:
        invoices = Invoice.objects.filter(author=employee,payment_status= payment_status).order_by('-created_at').all()
    elif sent_status is not None:
        invoices = Invoice.objects.filter(author=employee,sent_status= sent_status).order_by('-created_at').all()
    attachments = []

    view_more = False

    if invoices.count() > 5:
        paginator = Paginator(invoices, 5)
        page_obj = paginator.page(page)
        invoices = page_obj.object_list
        view_more = page_obj.has_next()




    if not invoices:
        message = "There are no invoices of the given category"
    else:
        message = 'Your invoices'
        for invoice in invoices:
            attachment = build_attachment_for_confirmed_invoice(invoice)
            attachments.extend(attachment)

        pagination = build_attachment_for_pagination_for_invoices(view_more=view_more, page=page)
        attachments.extend(pagination)


    send_message_to_user(message=message,employee=employee, team=team,attachments=attachments)

def list_clients(employee, team, page):

    customers = Customer.objects.filter(team=team).all()
    attachments = []

    view_more = False

    if customers.count() > 5:
        paginator = Paginator(customers, 5)
        page_obj = paginator.page(page)
        customers = page_obj.object_list
        view_more = page_obj.has_next()

    if not customers:
        message = "I have no clients for you yet. Lets add one"
        attachments = build_attachment_for_no_clients()

    else:
        message = 'Your clients'
        for customer in customers:
            attachment = build_attachment_for_listing_clients(customer, add_more=False)
            attachments.extend(attachment)

        pagination = build_attachment_for_pagination_for_clients(view_more=view_more, page=page)
        attachments.extend(pagination)

    send_message_to_user(message=message, employee=employee, team=team, attachments=attachments)

def call_lex_for_creating_invoice(username, channel_id, json_data, customer=None):
    client2 = boto3.client('lex-runtime')
    if customer:
        inputstring = "create invoice for %s " % customer.name
    else:
        inputstring = "create invoice"
    response = client2.post_text(
        botName='invoicetron',
        botAlias='version',
        userId=username,
        inputText=inputstring
    )
    employee = Employee.objects.filter(user__username=username).first()
    team = Team.objects.filter(slack_team_id=json_data['team']['id']).first()

    send_message_to_user(message=response['message'],employee=employee, team=team,channel_id=channel_id)

def call_lex_for_creating_client(username, json_data, channel_id):
    client2 = boto3.client('lex-runtime')
    inputstring = "create client"
    response = client2.post_text(
        botName='invoicetron',
        botAlias='version',
        userId=username,
        inputText=inputstring
    )
    employee = Employee.objects.filter(user__username=username).first()
    team = Team.objects.filter(slack_team_id=json_data['team']['id']).first()

    send_message_to_user(message=response['message'], employee=employee, team=team, channel_id=channel_id)

def upload_logo():
    pass
