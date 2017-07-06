import re

import django_rq
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from accounts.models import Employee, Team, Customer, Company
from accounts.utils import build_attachments_for_edited_invoice, send_message_to_user, build_attachments_for_invoice, \
    build_attachment_for_confirmed_invoice, build_attachment_for_error, build_message_for_help, \
    build_attachment_for_listing_clients, build_attachment_for_settings, \
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
            if 'subtype' in event.keys() and event['subtype'] == 'file_share':
                print(event)
                if state.state == UserInteractionState.COMPANY_LOGO_AWAITED:
                    company = Company.objects.filter(edited_details_awaited_from_for_company=employee).first()
                    upload_logo(event)
                    state.state = UserInteractionState.CHILLING
                    state.save()

                else:
                    pass

            else:

                new_message = event['text']
                wordlist = ['cancel', 'bye', 'quit', 'exit']
                if new_message in wordlist:
                    client.api_call('chat.postMessage', channel=event['channel'],
                                    text='OK')
                    state.state = UserInteractionState.CHILLING
                    state.save()

                else:

                    if state.state == UserInteractionState.CHILLING:
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

                                    owner = Team.objects.filter(owner=employee).first()
                                    if owner:
                                        company_name = company.company_name
                                        company_logo = company.company_logo

                                        if not company_name:
                                            company_name=None
                                        if not company_logo:
                                            company_logo=None

                                        message = ''
                                        attachments = build_attachment_for_settings(team, company_name=company_name,company_logo=company_logo)
                                        attachment_str = json.dumps(attachments)
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message, attachments=attachment_str)
                                    else:
                                        message = ' :x: You cannot manage settings because you are not the owner of the company.'
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message)

                            elif response['intentName'] == 'create_invoice':
                                if response['dialogState'] == 'ElicitSlot':

                                    if response['slots']['ClientName'] is not None and response['slots'][
                                        'Amount'] is not None:

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
                                    elif response['slots']['ClientName'] is not None and response['slots'][
                                        'Amount'] is None:

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
                                                inputText='create client {} '.format(name_of_client)
                                            )
                                            client.api_call('chat.postMessage', channel=event['channel'],
                                                            text=response2['message'])
                                        else:
                                            client.api_call('chat.postMessage', channel=event['channel'],
                                                            text=response['message'])


                                    elif response['slots']['ClientName'] is None and response['slots']['Amount'] is None:
                                        attachment = build_attachment_for_new_invoice(team)
                                        if attachment is None:
                                            message = 'Please create client first'
                                            attachment_str = None
                                        else:
                                            message = ''
                                            attachment_str = json.dumps(attachment)
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message, attachments=attachment_str)


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
                                        message = 'Great! Almost there. You are invoicing {} of $ {}. \n' \
                                                  'Now please enter the description.'.format(name_of_client, amount)
                                        client.api_call('chat.postMessage', channel=event['channel'],
                                                        text=message)
                                        create_invoice(invoice_client, employee, amount)

                            elif response['intentName'] == 'create_client':
                                if response['dialogState'] == 'ElicitSlot':
                                    if response['slots']['ClientName'] is not None and response[
                                        'slotToElicit'] == 'ClientEmail':
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
                                elif response['dialogState'] == 'Fulfilled':
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
                                        if response['sessionAttributes']['invoice']['ClientName'] == response['slots'][
                                            'ClientName']:
                                            session = json.loads(response['sessionAttributes']['invoice'])
                                            client_name = session['ClientName']
                                            total_amount = session['Amount']
                                            response2 = client2.post_text(
                                                botName='invoicetron',
                                                botAlias='version',
                                                userId=username,
                                                inputText='create invoice for {} of total {}'.format(client_name,
                                                                                                     total_amount)
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
                                                message = 'Great! Almost there. You are invoicing {} of $ {}. \n' \
                                                          'Now please enter the description.'.format(client_name,
                                                                                                     total_amount)
                                                client.api_call('chat.postMessage', channel=event['channel'],
                                                                text=message)
                                                create_invoice(invoice_client, employee, total_amount)
                                        else:
                                            pass
                                    else:
                                        pass

                            elif response['intentName'] == 'list_invoices':
                                if response['dialogState'] == 'Fulfilled':
                                    message = ''
                                    attachments = None
                                    if response['slots']['Paid'] == None and response['slots']['Sent'] == None:
                                        message, attachments = list_invoices(employee, team, page=1, payment_status=None,
                                                                             sent_status=None)
                                    elif response['slots']['Paid'] is not None and response['slots']['Sent'] == None:
                                        payment_status = response['slots']['Paid']
                                        message, attachments = list_invoices(employee, team, page=1,
                                                                             payment_status=payment_status,
                                                                             sent_status=None)
                                    elif response['slots']['Paid'] == None and response['slots']['Sent'] is not None:
                                        sent_status = response['slots']['Sent']
                                        message, attachments = list_invoices(employee, team, page=1, payment_status=None,
                                                                             sent_status=sent_status)
                                    elif response['slots']['Paid'] is not None and response['slots'][
                                        'Sent'] is not None:
                                        payment_status = response['slots']['Paid']
                                        sent_status = response['slots']['Sent']
                                        message, attachments = list_invoices(employee, team, page=1,
                                                                             payment_status=payment_status,
                                                                             sent_status=sent_status)

                                    send_message_to_user(message=message, employee=employee, team=team,
                                                         attachments=attachments)

                            elif response['intentName'] == 'start':
                                message = build_message_for_help()
                                client.api_call('chat.postMessage', channel=event['channel'],
                                                text=message)

                            elif response['intentName'] == 'list_clients':
                                if response['dialogState'] == 'Fulfilled':
                                    message, attachments = list_clients(employee, team, page=1)
                                    send_message_to_user(message=message, employee=employee, team=team,
                                                         attachments=attachments)

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

                        company_name = company.company_name

                        company_logo = company.company_logo
                        if not company_name:
                            company_name = None
                        if not company_logo:
                            company_logo = None
                        message = "Great!"
                        attachments = build_attachment_for_settings(team, company_name=company_name, company_logo=company_logo)
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

    return message,attachments

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

    return message, attachments

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

def upload_logo(event):

    if "url_private_download" not in event['file']:
        print("Ignoring as no downloadable file found")
        return

    else:
        file_details = event['file']
        team = Team.objects.filter(slack_team_id=event['team']).first()
        employee = Employee.objects.filter(user__username=event['user']).first()
        company = employee.company
        valid_file = False
        if file_details:
            # event_team = event['file']['url_private_download'].split('/files-pri/')[1].split('-')[0]
            if "url_private_download" not in file_details:
                message = "I am sorry I cannot read external files. Please drag and drop a file here."
                return send_message_to_user(message=message, employee=employee,team=team)

            if file_details['filetype'] in ('png', 'jpg', 'jpeg'):
                valid_file = True

            if valid_file:
                # return save_receipt_for_expense(expense, file_details['url_private_download'], team_bot)
                queue = django_rq.get_queue('high')
                queue.enqueue("landing.utils.save_logo", file_details['url_private_download'], team, company, employee)
                message = 'Your company logo is being saved. Please wait'
                send_message_to_user(message=message, employee=employee, team=team)
                print(valid_file)
            else:
                message = 'Please upload `png` `jpg` `jpeg` type of files only'
                send_message_to_user(message=message, employee=employee, team=team)


def save_logo(url, team, company, employee):

    from django.core.files.base import ContentFile
    import requests


    headers = {'Authorization': 'Bearer %s' % team.slack_bot_access_token}
    image_content = ContentFile(requests.get(url, headers=headers).content)
    company.company_logo.save(url.split("/")[-1], image_content)

    message = 'Your company logo is saved.'
    company.edited_details_awaited_from_for_company = None
    company.save()
    company_name = company.company_name
    company_logo = company.company_logo
    if not company_name:
        company_name = None
    if not company_logo:
        company_logo = None
    attachments = build_attachment_for_settings(team=team, company_name=company_name, company_logo=company_logo)
    send_message_to_user(message=message, employee=employee, team=team, attachments=attachments)




event = {'channel': 'D5WC1TV0V',
 'bot_id': None,
 'user_team': 'T5M4SAEBY',
 'subtype': 'file_share',
 'text': '<@U5WAKNTC4|shahtanmay69> uploaded a file: <https://attendancebot.slack.com/files/shahtanmay69/F644LQJH2/screenshot_from_2017-06-26_19-25-25.png|Screenshot from 2017-06-26 19-25-25.png>',
 'event_ts': '1499262368.799779',
 'ts': '1499262368.799779',
 'source_team': 'T5M4SAEBY',
 'username': 'shahtanmay69',
 'upload': True,
 'type': 'message',
 'user_profile': {'real_name': 'ironman',
                  'first_name': 'ironman',
                  'current_status': None,
                  'name': 'shahtanmay69',
                  'image_72': 'https://secure.gravatar.com/avatar/77ab8e21112019951896728e52e01ac1.jpg?s=72&d=https%3A%2F%2Fa.slack-edge.com%2F66f9%2Fimg%2Favatars%2Fava_0026-72.png',
                  'avatar_hash': 'g77ab8e21112'
                  },
 'file': {'thumb_160': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_160.png',
          'ims': [],
          'thumb_800': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_800.png',
          'thumb_960_w': 960,
          'thumb_1024_w': 1024,
          'mode': 'hosted',
          'thumb_720_h': 355,
          'user': 'U5WAKNTC4',
          'original_w': 1295, 'url_private': 'https://files.slack.com/files-pri/T5M4SAEBY-F644LQJH2/screenshot_from_2017-06-26_19-25-25.png', 'display_as_bot': False, 'thumb_480_h': 237, 'size': 141678, 'name': 'Screenshot from 2017-06-26 19-25-25.png', 'original_h': 639, 'thumb_480': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_480.png', 'thumb_360_w': 360, 'thumb_800_h': 395, 'thumb_1024_h': 505, 'permalink_public': 'https://slack-files.com/T5M4SAEBY-F644LQJH2-1593e7a978', 'editable': False, 'title': 'Screenshot from 2017-06-26 19-25-25.png', 'thumb_960': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_960.png', 'thumb_720': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_720.png', 'public_url_shared': False, 'url_private_download': 'https://files.slack.com/files-pri/T5M4SAEBY-F644LQJH2/download/screenshot_from_2017-06-26_19-25-25.png', 'thumb_80': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_80.png', 'timestamp': 1499262364, 'username': '', 'image_exif_rotation': 1, 'filetype': 'png', 'permalink': 'https://attendancebot.slack.com/files/shahtanmay69/F644LQJH2/screenshot_from_2017-06-26_19-25-25.png', 'is_public': False, 'thumb_360': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_360.png', 'is_external': False, 'mimetype': 'image/png', 'thumb_1024': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_1024.png', 'thumb_800_w': 800, 'channels': [], 'id': 'F644LQJH2', 'pretty_type': 'PNG', 'external_type': '', 'groups': [], 'thumb_720_w': 720, 'created': 1499262364, 'thumb_480_w': 480, 'thumb_360_h': 178, 'comments_count': 0, 'thumb_960_h': 474, 'thumb_64': 'https://files.slack.com/files-tmb/T5M4SAEBY-F644LQJH2-61931d842c/screenshot_from_2017-06-26_19-25-25_64.png'},
 'user': 'U5WAKNTC4',
 'team': 'T5M4SAEBY',
 'display_as_bot': False
 }