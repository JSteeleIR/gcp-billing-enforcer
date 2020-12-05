import base64
import json
import os
import slack
from googleapiclient import discovery
from slack.errors import SlackApiError

PROJECT_ID = os.getenv('GCP_PROJECT')
PROJECT_NAME = f'projects/{PROJECT_ID}'

def stop_billing(data, context):
    pubsub_data = base64.b64decode(data['data']).decode('utf-8')
    pubsub_json = json.loads(pubsub_data)
    billing_account = pubsub_json['billingAccountId']
    cost_amount = pubsub_json['costAmount']
    budget_amount = pubsub_json['budgetAmount']

    excluded = os.getnv("ENFORCE_EXEMPT_PROJECTS").split(',')
    if cost_amount <= budget_amount:
        print(f'No action necessary. (Current cost: {cost_amount}, Budget: {budget_amount})')
        _send_to_slack(f'Billing account "{billing_account}" has accrued a cost of {cost_amount}. Account has a budget of {budget_amount}.')
        return
    else:
        print(f'Account Overbudget. (Current cost: {cost_amount}, Budget: {budget_amount})')
        _send_to_slack(f'Billing account "{billing_account}" has exceeded budget! (Current Cost: {cost_amount}, Budget: {budget_amount})\n Disabling Billing on non-exempted projects...')


    if PROJECT_ID is None:
        print('No project specified with environment variable')
        return

    billing = discovery.build(
        'cloudbilling',
        'v1',
        cache_discovery=False,
    )

    projects = billing.billingAccounts().projects().list(name=billing_account).execute()
    projectclient = billing.projects()

    for p in projects:
        if p in excluded:
            print(f'Project {p} is excluded from enforcement!')
            _send_to_slack(f'Project "{p}" is excluded from billing enforcement.')
            continue

        billing_enabled = __is_billing_enabled(p, projectclient)

        if billing_enabled:
            __disable_billing_for_project(p, projectclient)
        else:
            print('Billing already disabled')


def __is_billing_enabled(project_name, projectclient):
    """
    Determine whether billing is enabled for a project
    @param {string} project_name Name of project to check if billing is enabled
    @return {bool} Whether project has billing enabled or not
    """
    try:
        res = projectclient.getBillingInfo(name=project_name).execute()
        return res['billingEnabled']
    except KeyError:
        # If billingEnabled isn't part of the return, billing is not enabled
        return False
    except Exception:
        print('Unable to determine if billing is enabled on specified project, assuming billing is enabled')
        return True


def __disable_billing_for_project(project_name, projectclient):
    """
    Disable billing for a project by removing its billing account
    @param {string} project_name Name of project disable billing on
    """
    body = {'billingAccountName': ''}  # Disable billing
    try:
        res = projectclient.updateBillingInfo(name=project_name, body=body).execute()
        print(f'Billing disabled: {json.dumps(res)}')
        _send_to_slack(f'Billing disabled on project "{project_name}".')
    except Exception:
        print('Failed to disable billing, possibly check permissions')
        _send_to_slack(f'!!! FAILED to disable Billing on project "{project_name}"!!!')

def _extract_pubsub_text(data, context):

    pubsub_message = data

    # For more information, see
    # https://cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications#notification_format
    try:
        notification_attr = json.dumps(pubsub_message['attributes'])
    except KeyError:
        notification_attr = "No attributes passed in"

    try:
        notification_data = base64.b64decode(data['data']).decode('utf-8')
    except KeyError:
        notification_data = "No data passed in"

    # This is just a quick dump of the budget data (or an empty string)
    # You can modify and format the message to meet your needs
    return f'{notification_attr}, {notification_data}'

def _send_to_slack(text):
    #TODO: Convert to the slack 'blocks' API to be able to make formatting more attention-grabbing.

    token = os.getenv("SLACK_ACCESS_TOKEN")

    # If SLACK_ACCESS_TOKEN not present, disable notifying slack.
    if not token or token == "":
        return

    slack_client = slack.WebClient(token=token)

    try:
        slack_client.api_call(
            'chat.postMessage',
            json={
                'channel': os.getenv("SLACK_CHANNEL"),
                'text'   : text
            }
        )
    except SlackApiError:
        print('Error posting to Slack')

def notify_slack(data, context):
    _send_to_slack(_extract_pubsub_text(data,context))
