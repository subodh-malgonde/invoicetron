from accounts.models import Employee, Team, Customer
from accounts.utils import build_attachments_for_edited_invoice, send_message_to_user, build_attachments_for_invoice, \
    build_attachment_for_confirmed_invoice
from landing.models import UserInteractionState
from actions.models import LineItem, Invoice
import boto3
from slackclient import SlackClient
import json


def handle_slack_event(event):
    print(event)
    bot_user_id = "U5M3TV7K7"

    if "user" in event.keys():
        username = event['user']
        if username != bot_user_id:
            user = Employee.objects.filter(user__username=username).first()
            if 'type' in event.keys() and event['type'] == 'message':

                team = Team.objects.filter(slack_team_id=event['team']).first()
                client = SlackClient(team.slack_bot_access_token)
                employee = Employee.objects.filter(user__username=username).first()
                state = UserInteractionState.get_state_for_employee(employee)

                if state.state == UserInteractionState.CHILLING:
                    inputstring = event['text']
                    client2 = boto3.client('lex-runtime')
                    response = client2.post_text(
                        botName='invoicetron',
                        botAlias='version',
                        userId=username,
                        inputText=inputstring
                    )
                    print(response)
                    if response['intentName'] == 'create_invoice':
                        if response['dialogState'] == 'ElicitSlot':
                            if response['slots']['ClientName'] != 'None':
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
                                create_invoice(invoice_client, user, amount, description='None')

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
                                create_invoice(invoice_client, employee, total_amount, description='None')

                    elif response['intentName'] == 'list_invoices':
                        if response['dialogState'] == 'Fulfilled':

                            invoice = Invoice.objects.filter(payment_status=Invoice.UNPAID, sent_status=Invoice.NOT_SENT)[:5]
                            for invoice in invoice:
                                print(invoice)
                                attachments = build_attachment_for_confirmed_invoice(invoice)
                                attachment_str = json.dumps(attachments)
                                client.api_call('chat.postMessage', channel=event['channel'],
                                                text="invoice", attachments=attachment_str)

                    else:
                        client.api_call('chat.postMessage', channel=event['channel'],
                                        text="NO intent match")




                elif state.state == UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED:

                    line_item = LineItem.objects.filter(edited_details_awaited_from=employee).order_by('-updated_at').first()
                    print(line_item)
                    desc = line_item.description  ##To check whether description is edited or entered first time

                    line_item.description = event['text']
                    line_item.edited_details_awaited_from = None
                    line_item.invoice.description = event['text']
                    line_item.save()
                    state.state = UserInteractionState.CHILLING
                    state.save()

                    invoice = line_item.invoice
                    if desc == 'None':
                        message = "Description has been added"
                        attachments = build_attachments_for_invoice(invoice)
                    else:
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


def create_invoice(invoice_client, user, amount, description):
    invoice = Invoice.objects.create(description=description, client=invoice_client,author=user)

    line_item = LineItem.objects.create(invoice=invoice, amount=amount,description=description)
    line_item.edited_details_awaited_from = user
    line_item.save()



{'message': 'Here is your list',
 'sessionAttributes': {'invoice': '{"Payment_status": null, "Sent_status": null}'},
 'slots': {'Paid': None, 'Sent': None},
 'ResponseMetadata': {'HTTPHeaders': {'x-amzn-requestid': 'c187c0c2-54e6-11e7-81e0-b55a4d4d55ab',
                                      'date': 'Mon, 19 Jun 2017 11:59:31 GMT',
                                      'connection': 'keep-alive',
                                      'content-length': '244',
                                      'content-type': 'application/json'},
                      'RequestId': 'c187c0c2-54e6-11e7-81e0-b55a4d4d55ab',
                      'RetryAttempts': 0,
                      'HTTPStatusCode': 200},
 'dialogState': 'Fulfilled',
 'intentName': 'list_invoices'}






