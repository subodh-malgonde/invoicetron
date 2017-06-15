from accounts.models import Employee, Team
from accounts.utils import build_attachments_for_edited_invoice, send_message_to_user
from landing.models import UserInteractionState
from actions.models import LineItem, Invoice


def handle_slack_event(event):
    print(event)
    bot_user_id = "U5M3TV7K7"

    if "user" in event.keys():
        user_id = event['user']
        if user_id != bot_user_id:
            if 'type' in event.keys() and event['type'] == 'message':

                team = Team.objects.filter(slack_team_id = event['team']).first()

                employee = Employee.objects.filter(user__username=user_id).first()
                state = UserInteractionState.get_state_for_employee(employee)

                if state.state == UserInteractionState.CHILLING:
                    pass
                elif state.state == UserInteractionState.LINE_ITEM_DESCRIPTION_AWAITED:

                    line_item = LineItem.objects.filter(edited_details_awaited_from = employee).first()
                    line_item.description = event['text']
                    line_item.save()
                    state.state = UserInteractionState.CHILLING
                    state.save()

                    invoice = line_item.invoice
                    message = "Description has been changed"
                    attachments = build_attachments_for_edited_invoice(invoice)

                    send_message_to_user(message, employee, team, attachments)

                elif state.state == UserInteractionState.LINE_ITEM_AMOUNT_AWAITED:

                    line_item = LineItem.objects.filter(edited_details_awaited_from=employee).first()
                    line_item.amount = event['text']
                    line_item.save()
                    state.state = UserInteractionState.CHILLING
                    state.save()

                    invoice = line_item.invoice
                    message = "Amount has been changed"
                    attachments = build_attachments_for_edited_invoice(invoice)

                    send_message_to_user(message, employee, team, attachments)






        ## client.rtm_send_message(event['channel'], event['text'])





    # check if the UserInteractionState is chilling
    #
    # if LINE_ITEM_DESCRIPTION_AWAITED:
    #line_item