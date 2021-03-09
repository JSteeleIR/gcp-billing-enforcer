import base64
import json
import os
import slack
from googleapiclient import discovery
from slack.errors import SlackApiError
from google.logging.type import log_severity_pb2 as log_severity

PROJECT_ID = os.getenv('GCP_PROJECT')
PROJECT_NAME = f'projects/{PROJECT_ID}'

_ALERT_THRESHOLD_MESSAGE = """Billing account "{billing_account}" has exceeded alert threshold for budget "{budget_name}."
Threshold: {threshold_percent:.2f}%, Current Cost: {cost_amount}, Budget: {budget_amount}
"""
_OVERBUDGET_MESSAGE = """Billing account "{billing_account}" has exceeded budget "{budget_name}"!
(Current Cost: {cost_amount}, Budget: {budget_amount})
Disabling Billing on non-exempted projects...
"""
_FORECASTED_ALERT_THRESHOLD_MESSAGE = """
Billing account "{billing_account}" is forecasted to hit {threshold_percent:.2f}% of budget "{budget_name}"
Current Accrued cost: {cost_amount}. Budget: {budget_amount}.
"""
_NO_THRESHOLD_MESSAGE = """'No budget alert threshold (real or forecasted) exceeded for budget "{budget_name}".
(Billing Account: "{billing_account}", Current cost: {cost_amount}, Budget: {budget_amount})
"""
_PROJECT_EXCLUDED_MESSAGE = """Project "{p}" is excluded from billing enforcement."""


def stop_billing(event, context):
    try:
        pubsub_data = base64.b64decode(event['data']).decode('utf-8')
        pubsub_json = json.loads(pubsub_data)
        billing_account = event['attributes']['billingAccountId']
        budget_name = pubsub_json['budgetDisplayName']
        cost_amount = pubsub_json['costAmount']
        budget_amount = pubsub_json['budgetAmount']
    except json.decoder.JSONDecodeError:
        _log_structured(f"Unable to decode message: {event}",
                        log_severity.ERROR)
        pass
    except KeyError:
        print(
            f"Unable to extract budget alert information from pubusb event:\n {event}",
            log_severity.ERROR)
        pass

    if "alertThresholdExceeded" in pubsub_json:
        threshold_percent = pubsub_json['alertThresholdExceeded'] * 100
        alert_message = _ALERT_THRESHOLD_MESSAGE.format(
            budget_name=budget_name,
            billing_account=billing_account,
            threshold_percent=threshold_percent,
            cost_amount=cost_amount,
            budget_amount=budget_amount)
        print(alert_message)

        if cost_amount < budget_amount:
            _log_and_send_to_slack(alert_message)

            return
        else:
            overbudget_message = _OVERBUDGET_MESSAGE.format(
                budget_name=budget_name,
                billing_account=billing_account,
                threshold_percent=threshold_percent,
                cost_amount=cost_amount,
                budget_amount=budget_amount)
            _log_and_send_to_slack(overbudget_message, log_severity.ALERT)
            disable_billing_account(billing_account)

    elif "forecastThresholdExceeded" in pubsub_json:
        threshold_percent = pubsub_json['forecastThresholdExceeded'] * 100
        forecasted_message = _FORECASTED_ALERT_THRESHOLD_MESSAGE.format(
            budget_name=budget_name,
            billing_account=billing_account,
            threshold_percent=threshold_percent,
            cost_amount=cost_amount,
            budget_amount=budget_amount)

        _log_and_send_to_slack(forecasted_message, log_severity.WARNING)
    else:
        _log_structured(
            _NO_THRESHOLD_MESSAGE.format(budget_name=budget_name,
                                         billing_account=billing_account,
                                         cost_amount=cost_amount,
                                         budget_amount=budget_amount))


def disable_billing_account(billing_account):
    excluded = os.getenv("ENFORCE_EXEMPT_PROJECTS").split(',')
    billing = discovery.build(
        'cloudbilling',
        'v1',
        cache_discovery=False,
    )

    try:
        projects = billing.billingAccounts().projects().list(
            name=f"billingAccounts/{billing_account}").execute()
        projectclient = billing.projects()
    except Exception as e:
        _log_and_send_to_slack(
            f'Error while obtaining projects for billing account "{billing_account}": {e}',
            log_severity.ERROR)
        pass

    for p in projects:
        if p in excluded:
            excluded_project_message = _PROJECT_EXCLUDED_MESSAGE.format(p=p)
            _log_and_send_to_slack(excluded_project_message,
                                   log_severity.WARNING)

            continue

        billing_enabled = __is_billing_enabled(p, projectclient)

        if billing_enabled:
            __disable_billing_for_project(p, projectclient)
        else:
            _log_and_send_to_slack(f'Billing already disabled for project {p}')


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
        _log_and_send_to_slack(
            f'Unable to determine if billing is enabled on project "{project_name}", assuming billing is enabled',
            log_severity.WARNING)

        return True


def __disable_billing_for_project(project_name, projectclient):
    """
    Disable billing for a project by removing its billing account
    @param {string} project_name Name of project disable billing on
    """
    body = {'billingAccountName': ''}  # Disable billing
    try:
        res = projectclient.updateBillingInfo(name=project_name,
                                              body=body).execute()
        print(f'Billing disabled: {json.dumps(res)}')
        _log_and_send_to_slack(
            f'Billing disabled on project "{project_name}".')
    except Exception as e:
        _log_and_send_to_slack(
            f'!!! FAILED to disable Billing on project "{project_name}"!!! Check that the billing enforcer has permssions!!! Error: {e}',
            log_severity.CRITICAL)


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


def _log_structured(message, severity=log_severity.NOTICE):
    # Build structured log messages as an object.
    global_log_fields = {}

    # TODO: Implment trace_headers/nested logging once the necessary fields are exposed.
    # https://github.com/GoogleCloudPlatform/functions-framework/issues/34

    # Add log correlation to nest all log messages.
    #trace_header = request.headers.get("X-Cloud-Trace-Context")

    #if trace_header and PROJECT_ID:
    #    trace = trace_header.split("/")
    #    global_log_fields[
    #        "logging.googleapis.com/trace"] = f"projects/{PROJECT_ID}/traces/{trace[0]}"

    # Complete a structured log entry.
    entry = dict(
        severity=log_severity.LogSeverity.Name(severity),
        message=message,
        # Log viewer accesses 'component' as jsonPayload.component'.  component="arbitrary-property",
        **global_log_fields,
    )
    print(entry)


def _log_and_send_to_slack(text, severity=log_severity.NOTICE):

    _log_structured(text, severity)
    # TODO: Convert to the slack 'blocks' API to be able to make formatting more attention-grabbing.

    token = os.getenv("SLACK_ACCESS_TOKEN")

    # If SLACK_ACCESS_TOKEN not present, disable notifying slack.

    if not token or token == "":
        return

    slack_client = slack.WebClient(token=token)

    try:
        slack_client.api_call('chat.postMessage',
                              json={
                                  'channel': os.getenv("SLACK_CHANNEL"),
                                  'text': text
                              })
    except SlackApiError as e:
        print('Error posting to Slack: {}'.format(e.response["error"]))


def notify_slack(data, context):
    _log_and_send_to_slack(_extract_pubsub_text(data, context))
