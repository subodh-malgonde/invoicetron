from django.contrib.auth.models import User

from accounts.models import Employee, Team, Customer, Company
from accounts.utils import build_attachments_for_edited_invoice, send_message_to_user, build_attachments_for_invoice, \
    build_attachment_for_confirmed_invoice, build_attachment_for_error, build_message_for_help, \
    build_attachment_for_listing_clients
from landing.models import UserInteractionState
from actions.models import LineItem, Invoice
import boto3
from slackclient import SlackClient
import json


def handle_slack_event(event):
    print(event)
    bot_user_id = "U5M3TV7K7"

    if 'type' in event.keys() and event['type'] == 'message':
        if 'subtype' in event.keys() and event['subtype'] == 'bot_message':
            pass
        else:
            if "user" in event.keys():
                username = event['user']
                if username != bot_user_id:

                    team = Team.objects.filter(slack_team_id=event['team']).first()
                    company = Company.objects.get(name=team.name)
                    client = SlackClient(team.slack_bot_access_token)
                    employee = Employee.objects.filter(user__username=username).first()


                    if not employee:
                        response = client.api_call('users.info', user=username)
                        if response['ok']:
                            user = User.objects.filter(username=username).first()
                            if not user:
                                user = User.objects.create(username=username)
                            employee = Employee.objects.create(user=user, company=company,
                                                    slack_username=response['user']['name'], slack_tz_label=response['user']['tz_label'],
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

                            if response['intentName'] == 'create_invoice':
                                if response['dialogState'] == 'ElicitSlot':
                                    if response['slots']['ClientName'] != 'None':
                                        amount = response['slots']['Amount']
                                        name_of_client = response['slots']['ClientName']
                                        invoice_client = Customer.objects.filter(name=name_of_client).first()
                                        if not invoice_client:
                                            message = "Client '{}' is not created. Lets create the client first".format(name_of_client)
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

                                if response['dialogState'] == 'Fulfilled':
                                    amount = response['slots']['Amount']
                                    name_of_client = response['slots']['ClientName']
                                    invoice_client = Customer.objects.filter(name=name_of_client).first()
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
                                        message = 'Enter the description for this invoice'
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message)
                                        create_invoice(invoice_client, employee, amount)

                            elif response['intentName'] == 'create_client':
                                if response['dialogState'] == 'ElicitSlot':
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=response['message'])
                                if response['dialogState'] == 'Fulfilled':
                                    response_email = response['slots']['ClientEmail']
                                    if "|" in response_email:
                                        response_email = response_email.split("|")[1]
                                    Customer.objects.create(name=response['slots']['ClientName'],
                                                            email_id=response_email,
                                                            team=team, created_by=employee)
                                    client.api_call('chat.postMessage', channel=event['channel'],
                                                    text=response['message'])
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

                                        invoice_client = Customer.objects.filter(name=client_name).first()

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
                                        list_invoices(employee, event, client, None, None)
                                    elif response['slots']['Paid'] is not None and response['slots']['Sent'] == None:
                                        payment_status = response['slots']['Paid']
                                        list_invoices(employee, event, client, payment_status, None)
                                    elif response['slots']['Paid'] == None and response['slots']['Sent'] is not None:
                                        sent_status = response['slots']['Sent']
                                        list_invoices(employee, event, client, None, sent_status)
                                    elif response['slots']['Paid'] is not None and response['slots']['Sent'] is not None:
                                        payment_status = response['slots']['Paid']
                                        sent_status = response['slots']['Sent']
                                        list_invoices(employee, event, client, payment_status, sent_status)

                            elif response['intentName'] == 'start':

                                message = build_message_for_help()
                                client.api_call('chat.postMessage', channel=event['channel'],
                                                text=message)

                            elif response['intentName'] == 'list_clients':
                                if response['dialogState'] == 'Fulfilled':
                                    list_clients(event, client, team)

                        else:
                            message = " :x: I am afraid I did not understand. Please type `help` to know more about me.\n" \
                                      "What are you looking for?"
                            attachments = build_attachment_for_error()
                            attachment_str = json.dumps(attachments)

                            client.api_call('chat.postMessage', channel=event['channel'],
                                            text=message, attachments=attachment_str)

                    elif state.state == UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED:

                        line_item = LineItem.objects.filter(edited_details_awaited_from=employee).order_by('-updated_at').first()

                        description = line_item.description

                        if description:
                            line_item.description = event['text']
                            line_item.edited_details_awaited_from = None
                            line_item.invoice.description = event['text']
                            line_item.save()
                            state.state = UserInteractionState.CHILLING
                            state.save()
                            invoice = line_item.invoice
                            invoice.description = event['text']
                            invoice.save()
                            message = "Description has been added"
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

                        line_item = LineItem.objects.filter(edited_details_awaited_from=employee).first()
                        line_item.amount = event['text']
                        line_item.edited_details_awaited_from = None

                        line_item.save()
                        state.state = UserInteractionState.CHILLING
                        state.save()

                        invoice = line_item.invoice
                        message = "Amount has been changed"
                        attachments = build_attachments_for_edited_invoice(invoice)

                        send_message_to_user(message, employee, team, attachments)


def create_invoice(invoice_client, employee, amount):
    invoice = Invoice.objects.create(client=invoice_client,author=employee)
    line_item = LineItem.objects.create(invoice=invoice, amount=amount)
    line_item.edited_details_awaited_from = employee
    line_item.save()

def list_invoices(employee, event, client, payment_status, sent_status):


    invoices = Invoice.objects.filter(author=employee)[:5]

    if payment_status is not None and sent_status is not None:
        invoices = invoices.filter(payment_status= payment_status, sent_status = sent_status)
    elif payment_status is not None:
        invoices = invoices.filter(payment_status= payment_status)
    elif sent_status is not None:
        invoices = invoices.filter(sent_status= sent_status)

    if not invoices:
        message = "There are no invoices of the given category"
        client.api_call('chat.postMessage', channel=event['channel'],
                        text=message)
    else:
        for invoice in invoices:
            attachments = build_attachment_for_confirmed_invoice(invoice)
            attachment_str = json.dumps(attachments)
            client.api_call('chat.postMessage', channel=event['channel'],
                            text="invoice", attachments=attachment_str)

def list_clients(event, client, team):

    customers = Customer.objects.filter(team=team)[:5]
    if not customers:
        message = "There are no clients in your team"
        client.api_call('chat.postMessage', channel=event['channel'],
                        text=message)
    else:
        for customer in customers:
            attachments = build_attachment_for_listing_clients(customer)
            attachment_str = json.dumps(attachments)
            client.api_call('chat.postMessage', channel=event['channel'],
                            text="Client #%d" % customer.id, attachments=attachment_str)










