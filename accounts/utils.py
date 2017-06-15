import json
from accounts.models import Customer


def open_dm_channel(sc, user_id):
    open_channel = sc.api_call('im.open', user=user_id)
    if open_channel['ok']:
        return open_channel['channel']['id']
    else:
        print('Error opening DM channel')
        return None


def send_message_to_user(message, employee, team, attachments=None, channel_id=None):
    attachment_str = ''
    if attachments:
        attachment_str = json.dumps(attachments)

    client = team.get_slack_socket()

    if not channel_id:
        channel_id = open_dm_channel(client, employee.user.username)

    client.api_call('chat.postMessage', channel=channel_id, text=message, attachments=attachment_str)


def build_attachments_for_invoice(invoice):
    attachment = {"title": "Invoice #%d" % invoice.id, "text": "", "color": "good"}

    attachment["callback_id"] = "invoice_confirmation:%d" % invoice.id

    line_item = invoice.line_items.first()

    actions = [
        {
            "name": "final_invoice",
            "text": "Confirm",
            "value": "confirm",
            "type": "button",
            "style": "primary"
        },
        {
            "name": "final_invoice",
            "text": "Edit",
            "value": "edit",
            "type": "button",
            "style": "primary"
        },
        {
            "name": "final_invoice",
            "text": "Cancel",
            "value": "cancel",
            "type": "button",
            "style": "primary"
        }
    ]

    attachment["actions"] = actions

    fields = [
        {
            "title": "Invoice",
            "value": invoice.client.name,
            "short": False
        },
        {
            "title": "Payment Status",
            "value": invoice.payment_status,
            "short": True
        },
        {
            "title": "Sent Status",
            "value": invoice.sent_status,
            "short": True
        },
        {
            "title": "Description",
            "value": line_item.description,
            "short": False
        },
        {
            "title": "Amount",
            "value": "$" + str(line_item.amount.amount),
            "short": True
        }

    ]

    attachment["fields"] = fields

    return [attachment]


def build_attachments_for_edited_invoice(invoice):
    edited_attachment = {"title": "Invoice id #%d" % invoice.id, "text": "", "color": "good"}

    edited_attachment["callback_id"] = "invoice_edition:%d" % invoice.id

    line_item = invoice.line_items.first()

    actions = [
        {
            "name": "Customer name",
            "text": "Choose a customer",
            "type": "select",
            "options": [{"text": customer.name, "value": str(customer.id)} for customer in Customer.objects.all()],
            "selected_options": [
                {
                    "text": invoice.client.name,
                    "value": str(invoice.client.id)
                }
            ]
        },

        {
            "name": "Edit",
            "text": "Change Description",
            "value": "change_description",
            "type": "button",
            "style": ""
        },
        {
            "name": "Edit",
            "text": "Change Amount",
            "value": "change_amount",
            "type": "button",
            "style": ""
        },
        {
            "name": "Edit",
            "text": "Finish Editing",
            "value": "finish_editing",
            "type": "button",
            "style": ""
        }

    ]

    edited_attachment["actions"] = actions

    fields = [
        {
            "title": "Amount",
            "value": "$" + str(line_item.amount.amount),
            "short": True
        },
        {
            "title": "Description",
            "value": line_item.description,
            "short": False
        }
    ]

    edited_attachment["fields"] = fields
    return [edited_attachment]


def build_attachment_for_finished_editing(invoice):

    attachment = {"title": "Invoice #%d" % invoice.id, "text": "", "color": "good"}

    attachment["callback_id"] = "invoice_confirmation:%d" % invoice.id

    line_item = invoice.line_items.first()

    fields = [
        {
            "title": "Invoice",
            "value": invoice.client.name,
            "short": False
        },
        {
            "title": "Payment Status",
            "value": invoice.payment_status,
            "short": True
        },
        {
            "title": "Sent Status",
            "value": invoice.sent_status,
            "short": True
        },
        {
            "title": "Description",
            "value": line_item.description,
            "short": False
        },
        {
            "title": "Amount",
            "value": "$" + str(line_item.amount.amount),
            "short": True
        }

    ]

    attachment["fields"] = fields

    return [attachment]
