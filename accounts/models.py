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
        # this method will be called during the oauth process
        pass


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
        return self.team

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