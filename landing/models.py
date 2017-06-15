from django.db import models
from accounts.models import Employee


# Create your models here.
class UserInteractionState(models.Model):
    CHILLING = 'chilling'
    LINE_ITEM_DESCRIPTION_AWAITED = "line_item_description_awaited"
    LINE_ITEM_AMOUNT_AWAITED = "line_item_amount_awaited"

    STATE_CHOICES = (
        (CHILLING, "Chilling"),
        (LINE_ITEM_DESCRIPTION_AWAITED, "Line item description awaited"),
        (LINE_ITEM_AMOUNT_AWAITED, "Line item amount awaited")
    )

    state = models.CharField(max_length=50, default=CHILLING, choices=STATE_CHOICES)
    employee = models.OneToOneField(Employee, related_name="ui_state")

    @classmethod
    def get_state_for_employee(cls, employee):
        if hasattr(employee, "ui_state"):
            return employee.ui_state
        else:
            return UserInteractionState.objects.create(employee=employee)
