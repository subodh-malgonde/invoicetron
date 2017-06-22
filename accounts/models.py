from django.db import models
from django.contrib.auth.models import User
from slackclient import SlackClient


class Company(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


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
    created_by = models.ForeignKey(Employee)

    def __str__(self):
        return self.name


class StripeAccountDetails(models.Model):

    team = models.ForeignKey(Team)
    stripe_user_id = models.CharField(max_length=100)
    stripe_publish_key = models.CharField(max_length=100)
    stripe_access_token = models.CharField(max_length=100)
