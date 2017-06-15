from django.db import models
from djmoney.models.fields import MoneyField

from accounts.models import Employee, Customer
from landing.models import UserInteractionState
from accounts.utils import build_attachments_for_invoice, build_attachments_for_edited_invoice, \
    build_attachment_for_finished_editing


class Action(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Invoice(models.Model):
    PAID = 'paid'
    UNPAID = 'unpaid'

    PAYMENT_STATUS_CHOICES = (
        (PAID, "Paid"),
        (UNPAID, "Not Paid")
    )

    SENT = 'sent'
    NOT_SENT = 'not_sent'

    SENT_STATUS_CHOICES = (
        (SENT, "Sent"),
        (NOT_SENT, "Not Sent")
    )

    description = models.CharField(max_length=500, blank=True, null=True)
    client = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE)  ##client name from Client model
    author = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE)
    payment_status = models.CharField(max_length=10, default=UNPAID, choices=PAYMENT_STATUS_CHOICES)
    sent_status = models.CharField(max_length=10, default=NOT_SENT, choices=SENT_STATUS_CHOICES)

    def __str__(self):
        return "%s - %s - %s" % (str(self.client), self.description, str(self.get_amount()))

    def get_amount(self):
        line_item = self.line_items.first()
        if line_item:
            return line_item.amount
        else:
            return None

    @classmethod
    def handle_invoice_confirmation(cls, invoice_id, json_data):
        invoice = Invoice.objects.filter(id=invoice_id).first()
        selected_value = json_data['actions'][0]['value']
        attachments = None
        if selected_value == "edit":
            from accounts.utils import build_attachments_for_edited_invoice
            attachments = build_attachments_for_edited_invoice(invoice)
            response_message = "Todo: handle edition of invoice"
        elif selected_value == "confirm":
            response_message = "Todo: handle confirmation of invoice"
        elif selected_value == "cancel":
            response_message = "Your invoice has been deleted"

        return response_message, attachments



class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")  ##id of invoice from Invoice model
    amount = MoneyField(max_digits=10, decimal_places=2, default_currency='USD')
    description = models.CharField(max_length=200)
    edited_details_awaited_from = models.ForeignKey('accounts.Employee', blank=True, null=True)

    def __str__(self):
        return "%s-%s-%s"% (str(self.invoice), self.description, self.amount)

    @classmethod
    def handle_lineitem_edition(cls,line_item_id, json_data):

        line_item = LineItem.objects.filter(id=line_item_id).first()
        attachments = None

        if "selected_options" in json_data["actions"][0].keys():

            client_id = json_data["actions"][0]["selected_options"][0]["value"]

            response_message = "You have selected %s customer " % client_id

            # client = Customer.objects.filter(id =client_id).first()
            # line_item.invoice.client = client
            # line_item.save()

            line_item.invoice.client_id = int(client_id)
            line_item.invoice.save()

            invoice = Invoice.objects.filter(id=line_item_id).first()
            attachments = build_attachments_for_edited_invoice(invoice)

        else:
            selected_value = json_data['actions'][0]['value']

            if selected_value == "change_description":
                # todo: set the user interaction state to description awaited
                username = json_data['user']['id']
                employee = Employee.objects.filter(user__username=username).first()
                ui_state = UserInteractionState.get_state_for_employee(employee)
                ui_state.state = UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED
                ui_state.save()
                line_item.edited_details_awaited_from = employee
                line_item.save()
                response_message = "Please type the new description for this invoice"

            elif selected_value == "change_amount":
                username = json_data['user']['id']
                employee = Employee.objects.filter(user__username=username).first()
                ui_state = UserInteractionState.get_state_for_employee(employee)
                ui_state.state = UserInteractionState.LINE_ITEM_AMOUNT_AWAITED
                ui_state.save()
                line_item.edited_details_awaited_from = employee
                line_item.save()

                response_message = "Please type the new amount for this invoice"

            elif selected_value == "finish_editing":
                response_message = "Your invoice has been edited."
                invoice = Invoice.objects.filter(id = line_item_id).first()
                attachments = build_attachment_for_finished_editing(invoice)


        return response_message, attachments