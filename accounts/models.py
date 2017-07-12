import django_rq
from django.db import models
from django.contrib.auth.models import User
from slackclient import SlackClient
from django.conf import settings


def logo_upload_location(company, filename):
    return "logos/%s-%s/%s" % (company.name, company.id, filename)


class Company(models.Model):
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    company_logo = models.ImageField(upload_to=logo_upload_location,max_length=250, blank=True, null=True)
    edited_details_awaited_from_for_company = models.ForeignKey('accounts.Employee', blank=True, null=True, related_name='company_name')

    def __str__(self):
        return self.name

    @classmethod
    def handle_team_settings(cls, json_data):
        from landing.models import UserInteractionState
        company = Company.objects.get(name=json_data['team']['id'])
        selected_value = json_data['actions'][0]['value']
        attachments = None

        if selected_value == "logo":
            employee = Employee.objects.filter(user__username= json_data['user']['id']).first()
            company_logo = company.company_logo
            print(company_logo)
            if company_logo:
                response_message = 'Please upload new logo.'
                state = UserInteractionState.get_state_for_employee(employee)
                state.state = UserInteractionState.COMPANY_LOGO_AWAITED
                state.save()
                company.edited_details_awaited_from_for_company = employee
                company.save()


            else:
                state = UserInteractionState.get_state_for_employee(employee)
                state.state = UserInteractionState.COMPANY_LOGO_AWAITED
                state.save()
                company.edited_details_awaited_from_for_company = employee
                company.save()
                response_message = 'You have not uploaded your company logo yet. \n' \
                                   'Drag/drop a file. Supported file formats are jpg/jpeg/png'


        elif selected_value == "name":

            username = json_data['user']['id']
            employee = Employee.objects.filter(user__username=username).first()
            from landing.models import UserInteractionState
            ui_state = UserInteractionState.get_state_for_employee(employee)
            ui_state.state = UserInteractionState.COMPANY_NAME_AWAITED
            ui_state.save()
            company.edited_details_awaited_from_for_company = employee
            company.save()
            response_message = 'Please enter your legal/company name. \n' \
                               'This name will be used to raise invoices'

        elif selected_value == "stripe_connect":

            from accounts.utils import build_payload_for_settings
            from django.conf import settings
            team = Team.objects.get(slack_team_id=json_data['team']['id'])
            stripe_account = StripeAccountDetails.objects.filter(team=team).first()
            if not stripe_account:
                response_message = 'Please <https://connect.stripe.com/oauth/authorize?response_type=code&client_id={}&scope=read_write&state={}|click here>' \
                                   ' to connect your stripe account with InvoiceTron ' .format(settings.STRIPE_CLIENT_ID, str(team.id))


            else:
                response_message = 'You already have stripe account connected with your team'
                m, attachments = build_payload_for_settings(team)

        return response_message, attachments

# for now we will treat a user's username to be the same as the user_id in slack
class Employee(models.Model):

    user = models.OneToOneField(User, related_name='employee')
    company = models.ForeignKey(Company)
    slack_username = models.CharField(max_length=100, null=True, blank=True)
    slack_tz_label = models.CharField(max_length=100, null=True, blank=True)
    slack_tz = models.CharField(max_length=100, null=True, blank=True)
    slack_image_url = models.CharField(max_length=256, null=True, blank=True)

    def __str__(self):
        if self.slack_username:
            return self.slack_username
        elif self.user.first_name:
            name = self.user.first_name
            if self.user.last_name:
                name += " %s" % self.user.last_name
            return name
        else:
            return self.user.username

    @classmethod
    def acquire_slack_user(self, team_id, user_id, intro=False, team_bot=None):
        # this method will be called when acquiring a new user
        pass

    @classmethod
    def consume_slack_data(self, data, user_data=False, state_user=None):

        company, created = Company.objects.get_or_create(name=data['team_id'])
        user, created = User.objects.get_or_create(username=data['user_id'])
        print(company)
        print(user)

        client = SlackClient(data['bot']['bot_access_token'])
        response = client.api_call('users.info', user=data['user_id'])


        employee, created = Employee.objects.get_or_create(user=user, company=company)

        employee.slack_username=response['user']['name']
        employee.slack_tz_label=response['user']['tz_label']
        employee.slack_tz=response['user']['tz']
        employee.save()


        team, created = Team.objects.get_or_create(name=data['team_name'], slack_team_id=data['team_id'],
                                          slack_bot_user_id=data['bot']['bot_user_id'],
                                          slack_bot_access_token=data['bot']['bot_access_token'],
                                          owner=employee)
        return employee,team


class Team(models.Model):
    name = models.CharField(db_index=True, max_length=200)
    slack_team_id = models.CharField(db_index=True, max_length=20, null=True, blank=True)
    slack_bot_user_id = models.CharField(max_length=20, null=True, blank=True)
    slack_bot_access_token = models.CharField(max_length=100, null=True, blank=True)
    active = models.BooleanField(default=True)
    owner = models.ForeignKey(Employee, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_slack_socket(self):
        sc = SlackClient(self.slack_bot_access_token)
        return sc


class Customer(models.Model):
    name = models.CharField(max_length=100)
    email_id = models.EmailField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    created_by = models.ForeignKey(Employee, related_name='created_customers')
    edited_details_awaited_from = models.ForeignKey(Employee, blank=True, null=True)


    def __str__(self):
        return self.name

    @classmethod
    def handle_client_create(cls,client_id, json_data):
        from accounts.utils import build_attachment_for_editing_client
        customer = Customer.objects.filter(id=client_id).first()
        selected_value = json_data['actions'][0]['value']
        username = json_data['user']['id']
        channel_id = json_data['channel']['id']
        attachments = None
        response_message = ''
        if selected_value == 'invoice':
            response_message = 'You are invoicing `%s` ' % customer.name
            queue = django_rq.get_queue('high')
            queue.enqueue('landing.utils.call_lex_for_creating_invoice', customer=customer, username=username, channel_id=channel_id, json_data=json_data)

        elif selected_value == 'edit':
            response_message = ''
            attachments = build_attachment_for_editing_client(customer)

        elif selected_value == 'add_more':
            response_message = 'Lets add a new client.'
            queue = django_rq.get_queue('high')
            queue.enqueue('landing.utils.call_lex_for_creating_client', username=username, json_data=json_data, channel_id=channel_id )

        elif selected_value == 'later':
            response_message = 'OK'

        return response_message, attachments

    @classmethod
    def handle_client_edit(cls,client_id,json_data):
        from landing.models import UserInteractionState
        from accounts.utils import build_attachment_for_listing_clients
        customer = Customer.objects.filter(id=client_id).first()
        selected_value = json_data['actions'][0]['value']
        attachments = None
        username = json_data['user']['id']
        if selected_value == 'edit_name':
            employee = Employee.objects.filter(user__username=username).first()
            ui_state = UserInteractionState.get_state_for_employee(employee)
            ui_state.state = UserInteractionState.CLIENT_NAME_AWAITED
            ui_state.save()
            customer.edited_details_awaited_from = employee
            customer.save()

            response_message = "Please enter the new name"

        elif selected_value == 'edit_email':
            employee = Employee.objects.filter(user__username=username).first()
            ui_state = UserInteractionState.get_state_for_employee(employee)
            ui_state.state = UserInteractionState.CLIENT_EMAIL_AWAITED
            ui_state.save()
            customer.edited_details_awaited_from = employee
            customer.save()

            response_message = "Please enter the new email"

        elif selected_value == 'finish_editing':
            response_message = "Your client has been edited."
            attachments = build_attachment_for_listing_clients(customer, add_more=False)

        return response_message,attachments

    @classmethod
    def handle_client_list(cls,page_number, json_data):
        from landing.utils import list_clients
        selected_value = json_data['actions'][0]['value']
        username = json_data['user']['id']
        channel_id = json_data['channel']['id']
        employee = Employee.objects.filter(user__username=username).first()
        team = Team.objects.filter(slack_team_id = json_data['team']['id']).first()
        attachments = None
        if selected_value == 'view_more':

            page_number = int(page_number)
            page_number += 1
            response_message, attachments = list_clients(employee, team, page_number)

        elif selected_value == 'add_new':
            response_message = 'Lets add a new client.'
            queue = django_rq.get_queue('high')
            queue.enqueue('landing.utils.call_lex_for_creating_client', username=username, json_data=json_data,
                          channel_id=channel_id)

        return response_message, attachments


class StripeAccountDetails(models.Model):

    team = models.ForeignKey(Team)
    stripe_user_id = models.CharField(max_length=100)
    stripe_publish_key = models.CharField(max_length=100)
    stripe_access_token = models.CharField(max_length=100)


def onboard_team(team):
    from landing.utils import send_message_to_user
    attachments = [
        {
            "title": "",
            "text": "This is how a sample invoice looks like",
            "image_url": settings.SAMPLE_INVOICE_URL,
            "color": "#F4B042"
        },
        {
            "title": "",
            "text": "Type `settings` to setup your team",
            "color": "good"
        }
    ]

    message = "Hi! Welcome to Invoicetron :wave:\n" \
              "I can help you create invoices and receive payments for them directly in your stripe account."

    send_message_to_user(message=message, employee=team.owner, team=team, attachments=attachments, unfurl_media=True)
