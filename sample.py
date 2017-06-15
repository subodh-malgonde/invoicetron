from accounts.utils import send_message_to_user, build_attachments_for_invoice
from accounts.models import Team, Employee
from actions.models import Invoice, LineItem
e = Employee.objects.first()
t = Team.objects.first()
i = Invoice.objects.first()
a = build_attachments_for_invoice(i)
send_message_to_user("hi", e, t, a)
