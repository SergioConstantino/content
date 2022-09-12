from SendEmailToManager import *


def test_find_additional_incident_info():
    example_incident_data = {
        "details": "employee_request",
        "name": "incident_subject",
        "labels": [
            {
                "type": "Email/from",
                "value": "employee_email"
            },
        ],
    }

    additional_info = find_additional_incident_info(example_incident_data)

    for item in ("employee_email", "incident_subject", "employee_request"):
        assert item == additional_info[item]


def test_find_additional_ad_info(mocker):
    pass  # TODO


def test_generate_mail_subject(mocker):
    example_entitlement = [{
        "Type": 1,
        "Contents": "3193a6d6-ec03-4237-8d98-b77d94785fcd",
    }]
    mocker.patch.object(demisto, 'executeCommand', return_value=example_entitlement)

    assert generate_mail_subject("test_subject", allow_reply=False) == \
           "test_subject - #1"

    assert generate_mail_subject("test_subject", allow_reply=True) == \
           "test_subject - #1 3193a6d6-ec03-4237-8d98-b77d94785fcd"


def test_generate_mail_body():
    returned_body = generate_mail_body(
        manager_name="test_manager",
        employee_name="test_employee",
        employee_request="test_employee_request")

    for item in ("test_manager", "test_employee", "test_employee_request"):
        assert item in returned_body
