from django.db import models
from djmoney.models.fields import MoneyField

class Action(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Invoice(models.Model):
    description = models.CharField(max_length=500, blank=True, null=True)
    client = models.ForeignKey('accounts.models.Client', on_delete=models.CASCADE)  ##client name from Client model
    author = models.ForeignKey('accounts.models.Employee', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.client)

    def __str1__(self):
        return self.created_by


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)  ##id of invoice from Invoice model
    amount = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')
    description = models.CharField(max_length=200)

    def __str__(self):
        return "%s-%s-%s"% (str(self.invoice), self.description, self.amount)