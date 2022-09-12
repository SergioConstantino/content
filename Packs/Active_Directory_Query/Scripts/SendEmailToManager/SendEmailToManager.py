import textwrap
import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
from string import Template


def find_additional_incident_info(incident: dict) -> dict:
    additional_info = {}

    for label in incident['labels']:
        if label['type'] == 'Email/from':
            additional_info["employee_email"] = label['value'].lower()

    additional_info["incident_subject"] = demisto.gets(incident, 'name')
    additional_info["employee_request"] = incident.get('details')

    return additional_info


def find_additional_ad_info(email: str, manager_attribute: str) -> dict:
    additional_info = {}

    if not manager_attribute:
        manager_attribute = 'manager'

    response = demisto.executeCommand('ad-search', {'filter': r'(&(objectClass=user)(mail=' + email + '))',
                                               'attributes': 'displayname,' + manager_attribute})

    if isError(response[0]):
        demisto.results(response)
        sys.exit(0)

    additional_info["manager_dn"] = demisto.get(response[0]['Contents'][0], manager_attribute)
    additional_info["employee_name"] = demisto.get(response[0]['Contents'][0], 'displayname')

    if not additional_info["manager_dn"]:
        demisto.results('Unable to get manager email')
        sys.exit(0)

    filter_str = r'(&(objectClass=User)(distinguishedName=' + additional_info["manager_dn"] + '))'
    response = demisto.executeCommand('ad-search', {'filter': filter_str, 'attributes': 'displayname,mail'})

    if isError(response[0]):
        demisto.results(response)
        sys.exit(0)

    additional_info["manager_email"] = demisto.get(response[0]['Contents'][0], 'mail')
    additional_info["manager_name"] = demisto.get(response[0]['Contents'][0], 'displayname')

    return additional_info


def generate_mail_subject(incident_subject: str, allow_reply: bool = True) -> str:
    subject = incident_subject + ' - #' + demisto.investigation().get('id')

    if allow_reply:
        response = demisto.executeCommand('addEntitlement',
                                          {'persistent': demisto.get(demisto.args(), 'persistent'),
                                           'replyEntriesTag': demisto.get(demisto.args(), 'replyEntriesTag')})

        if isError(response[0]):
            demisto.results(response)
            sys.exit(0)

        entitlement = demisto.get(response[0], 'Contents')

        if not entitlement:
            demisto.results('Unable to get entitlement')
            sys.exit(0)

        subject += ' ' + entitlement

    return subject


def generate_mail_body(manager_name, employee_name, employee_request) -> str:
    body = """
    Hi $manager_name,
    We've received the following request below from $employee_name. \
    Please reply to this email with either "approve" or "deny".
    Cheers,
    Your friendly security team
    """

    actual_body = Template(body)

    return textwrap.dedent(actual_body.safe_substitute(manager_name=manager_name, employee_name=employee_name))\
        + '\n----------' + employee_request


def main():
    email = demisto.get(demisto.args(), 'email')
    manager_attribute = demisto.get(demisto.args(), 'manager')
    additional_info = find_additional_incident_info(demisto.incidents()[0])

    if not email:
        if additional_info.get("employee_email"):
            email = additional_info["employee_email"]

        else:
            demisto.results('Could not find employee email. Quiting.')

    additional_info.update(find_additional_ad_info(email=email, manager_attribute=manager_attribute))

    body = demisto.get(demisto.args(), 'body')
    employee_request = demisto.get(demisto.args(), 'request')

    if not employee_request:
        employee_request = additional_info.get("employee_request")

    if not body:
        body = generate_mail_body(
            manager_name=additional_info["manager_name"],
            employee_name=additional_info["employee_name"],
            employee_request=employee_request)

    demisto.results(
        demisto.executeCommand('send-mail', {
            'to': additional_info["manager_email"],
            'subject': generate_mail_subject(
                incident_subject=additional_info["incident_subject"],
                allow_reply=argToBoolean(demisto.get(demisto.args(), 'allowReply'))),
            'body': body
        }))


if __name__ in ('__builtin__', 'builtins', '__main__'):
    main()
