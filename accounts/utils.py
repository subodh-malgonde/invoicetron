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
            "short": True
        },
        {
            "title": "Amount",
            "value": "$" + str(line_item.amount.amount),
            "short": True
        },
        {
            "title": "Description",
            "value": line_item.description,
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

def build_attachment_for_listing_clients(customer, add_more):
    attachment = {"title": "" , "text": "", "color": "good"}

    attachment["callback_id"] = "client_create:%d" % customer.id

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
    if add_more == True:
        actions = [
            {
                "name": "create_client",
                "text": "Invoice",
                "value": "invoice",
                "type": "button",
                "style": "primary"
            },
            {
                "name": "create_client",
                "text": "Edit",
                "value": "edit",
                "type": "button",
            },
            {
                "name": "create_client",
                "text": "Add More",
                "value": "add_more",
                "type": "button"
            }
        ]

    else:
        actions = [
            {
                "name": "create_client",
                "text": "Invoice",
                "value": "invoice",
                "type": "button",
                "style": "primary"
            },
            {
                "name": "create_client",
                "text": "Edit",
                "value": "edit",
                "type": "button",
            }
        ]



    attachment["fields"] = fields
    attachment["actions"] = actions


    return [attachment]

def build_attachment_for_editing_client(customer):
    attachment = {"title": "", "text": "", "color": "good"}

    attachment["callback_id"] = "client_edit:%d" % customer.id

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
    actions = [
        {
            "name": "edit_client",
            "text": "Edit Name",
            "value": "edit_name",
            "type": "button"
        },
        {
            "name": "edit_client",
            "text": "Edit Email",
            "value": "edit_email",
            "type": "button",
        },
        {
            "name": "edit_client",
            "text": "Finish Editing",
            "value": "finish_editing",
            "type": "button"
        }
    ]

    attachment["fields"] = fields
    attachment["actions"] = actions

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
    message = "Hi :wave: I am InvoiceTron. I can help you invoice your clients. \n" \
              "Type `create invoice` to create and send invoices\n" \
              "Type `create client` to create a new client \n" \
              "Type `invoices` to view your invoices and  `clients` to view your clients \n" \
              "Type `settings` to manage your account \n"

    return message

def build_attachment_for_settings(team, company_name, company_logo):
    company = Company.objects.get(name=team.slack_team_id)
    attachment = {"title": "", "text": ""}

    attachment["callback_id"] = "settings:%d" % team.id

    if company_name is False and company_logo is False:
        fields = [
            {
                "title": "You have not entered your company details",
                "value": "",
                "short": True
            }
        ]
    else:

        fields = [
            {
                "title": "Legal Name",
                "value": company.company_name,
                "short": True
            }
        # },
        # {
        #     "title": "Company Logo",
        #     "value": "logo",
        #     "short": True
        # }
    ]
    attachment["fields"] = fields

    if company_name is True and company_logo is True:

        actions = [
            {
                "name": "settings",
                "text": "Edit logo",
                "value": "logo",
                "type": "button"
            },
            {
                "name": "settings",
                "text": "Edit Legal Name",
                "value": "name",
                "type": "button"
            },

            {
                "name": "settings",
                "text": "Connect Stripe",
                "value": "stripe_connect",
                "type": "button"
            }
        ]

    elif company_name is True and company_logo is False:
        actions = [
            {
                "name": "settings",
                "text": "Add logo",
                "value": "logo",
                "type": "button"
            },
            {
                "name": "settings",
                "text": "Edit Legal Name",
                "value": "name",
                "type": "button"
            },

            {
                "name": "settings",
                "text": "Connect Stripe",
                "value": "stripe_connect",
                "type": "button"
            }
        ]

    elif company_name is False and company_logo is True:
        actions = [
            {
                "name": "settings",
                "text": "Edit logo",
                "value": "logo",
                "type": "button"
            },
            {
                "name": "settings",
                "text": "Add Legal Name",
                "value": "name",
                "type": "button"
            },

            {
                "name": "settings",
                "text": "Connect Stripe",
                "value": "stripe_connect",
                "type": "button"
            }
        ]

    else:
        actions = [
            {
                "name": "settings",
                "text": "Add logo",
                "value": "logo",
                "type": "button"
            },
            {
                "name": "settings",
                "text": "Add Legal Name",
                "value": "name",
                "type": "button"
            },

            {
                "name": "settings",
                "text": "Connect Stripe",
                "value": "stripe_connect",
                "type": "button"
            }
        ]



    attachment["actions"] = actions



    return [attachment]

def build_attachment_for_no_clients():
    attachment = {"title": "", "text": "", "color": "good"}

    attachment["callback_id"] = "client_create:0"

    actions = [
        {
            "name": "create_client",
            "text": "Yes",
            "value": "add_more",
            "type": "button",
            "style": "primary"
        },
        {
            "name": "create_client",
            "text": "May be Later",
            "value": "later",
            "type": "button",
        }
    ]

    attachment['actions'] = actions

    return [attachment]

def build_attachment_for_new_invoice():
    attachment = {"title": 'Please select a client from list below', "text": "", "color": "good"}

    attachment["callback_id"] = "invoice_dropdown: "

    actions = [
        {
            "name": "Customer name",
            "text": "Choose a customer",
            "type": "select",
            "options": [{"text": customer.name, "value": str(customer.id)} for customer in Customer.objects.all()]
        }
    ]

    attachment['actions'] = actions

    return [attachment]

def build_attachment_for_pagination_for_invoices(view_more,page):
    attachment = {"title": "", "text": "", "color": "good"}

    attachment["callback_id"] = "invoice_list:%d" % int(page)
    if view_more == True:

        actions = [
            {
                "name": "page",
                "text": "View More",
                "value": "view_more",
                "type": "button"
            },
            {
                "name": "page",
                "text": "Add New",
                "value": "add_new",
                "type": "button"
            }
        ]

    else:
        actions = [
            {
                "name": "page",
                "text": "Add New",
                "value": "add_new",
                "type": "button"
            }
        ]

    attachment['actions'] = actions
    return [attachment]

def build_attachment_for_pagination_for_clients(view_more, page):

    attachment = {"title": "", "text": "", "color": "good"}

    attachment["callback_id"] = "client_list:%d" % int(page)
    if view_more == True:

        actions = [
            {
                "name": "page",
                "text": "View More",
                "value": "view_more",
                "type": "button"
            },
            {
                "name": "page",
                "text": "Add New",
                "value": "add_new",
                "type": "button"
            }
        ]

    else:
        actions = [
            {
                "name": "page",
                "text": "Add New",
                "value": "add_new",
                "type": "button"
            }
        ]


    attachment['actions'] = actions
    return [attachment]
