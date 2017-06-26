import json
from accounts.models import Customer, Company


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
        },
        {
            "name": "final_invoice",
            "text": "Cancel",
            "value": "cancel",
            "type": "button",
            "style": "danger"
        }
    ]

    attachment["actions"] = actions

    fields = [
        {
            "title": "Client",
            "value": invoice.client.name,
            "short": False
        },
        {
            "title": "Payment Status",
            "value": invoice.get_payment_status_display(),
            "short": True
        },
        {
            "title": "Sent Status",
            "value": invoice.get_sent_status_display(),
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
            "style": "primary"
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

def build_attachment_for_confirmed_invoice(invoice):
    attachment = {"title": "Invoice #%d" % invoice.id, "text": "", "color": "good"}

    attachment["callback_id"] = "invoice:%d" % invoice.id

    line_item = invoice.line_items.first()

    actions = [
        {
            "name": "get_pdf",
            "text": "Get Link",
            "value": "get_pdf",
            "type": "button",
            "style": "primary"
        }
    ]

    attachment["actions"] = actions


    fields = [
        {
            "title": "Client",
            "value": invoice.client.name,
            "short": False
        },
        {
            "title": "Payment Status",
            "value": invoice.get_payment_status_display(),
            "short": True
        },
        {
            "title": "Delivery Status",
            "value": invoice.get_sent_status_display(),
            "short": True
        },
        {
            "title": "Description",
            "value": line_item.description,
            "short": True
        },
        {
            "title": "Amount",
            "value": "$" + str(line_item.amount.amount),
            "short": True
        }

    ]

    attachment["fields"] = fields

    return [attachment]

def build_attachment_for_listing_clients(customer):
    attachment = {"title": "" , "text": "", "color": "good"}

    fields = [
        {
            "title": "Client Name",
            "value": customer.name,
            "short": True
        },
        {
            "title": "Email id",
            "value": customer.email_id,
            "short": True
        }
    ]
    attachment["fields"] = fields

    return [attachment]

def build_attachment_for_error():
    attachment = {"title": "", "text": ""}

    fields = [
        {
            "title": "Trying to create a invoice?",
            "value": "Type `create invoice` ",
            "short": True
        },
        {
            "title": "Trying to create a client?",
            "value": "Type `create client` ",
            "short": True
        },
        {
            "title": "Want to view all your invoices?",
            "value": "Type `list invoices` ",
            "short": True
        },
        {
            "title": "You can also view your invoices category wise",
            "value": "Type something like `list paid/sent invoices` ",
            "short": True
        }
    ]

    attachment["fields"] = fields

    return [attachment]

def build_message_for_help():
    message = ":wave: \n" \
              "Type `create invoice` for creating invoice\n" \
              "Type `create client` to create client\n" \
              "Type `list` for viewing all your invoices\n" \
              "Type `list paid invoices` for viewing invoices categorywise\n" \
              "You can also type words like `paid` `unpaid` `sent` `unsent` for viewing invoices\n" \
              "Type `connect with stripe` in order to connect your stripe account"

    return message

def build_attachment_for_connecting_stripe(team):

    attachment = {"title": "Connect with stripe",
                  "title_link": "https://connect.stripe.com/oauth/authorize?response_type=code&client_id=ca_As3LPNYpHh1uDPy8C8bn69DTWkIJ9ZTk&scope=read_write&state=" + str(team.id),
                  "text": ""
                  }

    return [attachment]

def build_attachment_for_settings(team):
    company = Company.objects.get(name=team.slack_team_id)
    attachment = {"title": "", "text": ""}

    attachment["callback_id"] = "settings:%d" % team.id

    actions = [
        {
            "name": "settings",
            "text": "Logo",
            "value": "logo",
            "type": "button",
            "style": "primary"
        },
        {
            "name": "settings",
            "text":"Add Company Name" if company is None else "Edit Company Name" ,
            "value": "name",
            "type": "button",
            "style": "primary"
        },

        {
            "name": "settings",
            "text": "Connect Stripe",
            "value": "stripe_connect",
            "type": "button",
            "style": "primary"
        }
    ]

    attachment["actions"] = actions

    fields = [
        {
            "title": "Company Name",
            "value": company.company_name,
            "short": True
        }
    ]

    attachment["fields"] = fields

    return [attachment]



