import pytest
from freezegun import freeze_time

import demistomock as demisto

integration_params = {
    'url': 'http://test.com',
    'credentials': {'identifier': 'test', 'password': 'pass'},
    'fetch_time': '3 days',
    'proxy': 'false',
    'unsecure': 'false',
}

sample_incidents = [{
    "id": "P-12345",
    "alertTime": 1664697641,
    "policy.name": "This is a test"
}, {
    "id": "P-678910",
    "alertTime": 1664697641,
    "policy.name": "This is a test"
}]

expected_incidents = [
    {
        'name': 'This is a test - P-12345',
        'occurred': '1970-01-20T06:24:57Z',
        'severity': 0,
        'rawJSON': '{"id": "P-12345", "alertTime": 1664697641, "policy.name": "This is a test"}'
    }, {
        'name': 'This is a test - P-678910',
        'occurred': '1970-01-20T06:24:57Z',
        'severity': 0,
        'rawJSON': '{"id": "P-678910", "alertTime": 1664697641, "policy.name": "This is a test"}'
    }]


@pytest.fixture(autouse=True)
def set_mocks(mocker):
    mocker.patch.object(demisto, 'params', return_value=integration_params)


@freeze_time("2021-07-10T16:34:14.758295 UTC+1")
def test_fetch_incidents_first_time_fetch(mocker):
    """
        Given
            - fetch incidents command
            - command args
        When
            - mock the integration parameters
        Then
            - Validate that the last_time is as the now time(not changed, not of the incident)
    """
    mocker.patch.object(demisto, 'command', return_value='fetch-incidents')
    from RedLock import fetch_incidents
    mocker.patch('RedLock.req', return_value=[])

    _, _, next_run = fetch_incidents()
    assert next_run == 1625938454758


@freeze_time("2021-07-10T16:34:14.758295 UTC+1")
def test_fetch_incidents_fetch_all_new(mocker):
    """
        Given
            - fetch incidents command
            - command args
            - No last run object, meaning first fetch
        When
            - mock the integration parameters
        Then
            - Validate that the last_time is as the now time(not changed, not of the incident)
            - Validate that the length of fetched_ids is 2 indicating they were collected
            - Validate that the incidents match what is expected
    """
    mocker.patch.object(demisto, 'command', return_value='fetch-incidents')
    from RedLock import fetch_incidents
    mocker.patch('RedLock.req', return_value=sample_incidents)

    incidents, fetched_ids, next_run = fetch_incidents()
    assert next_run == 1625938454758
    assert len(fetched_ids) == 2
    assert incidents == expected_incidents


@freeze_time("2021-07-10T16:34:14.758295 UTC+1")
def test_fetch_incidents_fetch_previously_fetched(mocker):
    """
        Given
            - fetch incidents command
            - command args
            - Mocked last run where the P-12345 incident was laready fetched
        When
            - mock the integration parameters
        Then
            - Validate that the last_time is as the now time(not changed, not of the incident)
            - Validate that the length of fetched_ids is 2 indicating the previous were not
              dropped and the new ones were added
            - Validate that only one incident was created
    """
    mock_last_run = {
        'fetched_ids': [{'P-12345': 123456789}],
        'time': 1625927654758
    }
    mocker.patch.object(demisto, 'command', return_value='fetch-incidents')
    mocker.patch.object(demisto, 'getLastRun', return_value=mock_last_run)
    from RedLock import fetch_incidents
    mocker.patch('RedLock.req', return_value=sample_incidents)

    incidents, fetched_ids, next_run = fetch_incidents()
    assert next_run == 1625927654758
    assert len(fetched_ids) == 2
    assert len(incidents) == 1


@freeze_time("2021-07-10T16:34:14.758295 UTC+1")
def test_expire_stored_ids_should_not_expire():
    """
        Given
            - a set of fetched IDs within the last hour
        When
            - cleaning expired IDs from the context
        Then
            - Validate that cleaned IDs returned contains the unexpired ID.
    """
    from RedLock import expire_stored_ids
    fetched_ids = [{'P-12345': 1625938454758}]

    cleaned_ids = expire_stored_ids(fetched_ids=fetched_ids)
    assert cleaned_ids == [{'P-12345': 1625938454758}]


@freeze_time("2022-07-10T16:34:14.758295 UTC+1")
def test_expire_stored_ids_should_expire():
    """
        Given
            - a set of fetched IDs from the last year
        When
            - cleaning expired IDs from the context
        Then
            - Validate that the ID is expired and an empty array is returned
    """
    from RedLock import expire_stored_ids
    fetched_ids = [{'P-12345': 1625927654758}]

    cleaned_ids = expire_stored_ids(fetched_ids=fetched_ids)
    assert cleaned_ids == []


def test_redlock_list_scans(mocker):
    """
        Given
            - The response from the API call of redlock-list-scans command.
        When
            - calling redlock-list-scans
        Then
            - Validate that the readable output and the context entry of the command is as expected

    """
    from RedLock import redlock_list_scans
    list_scans_response = {
        'data': [{
            'id': '111111111',
            'attributes': {
                'name': ['test name'],
                'type': ['test type'],
                'user': ['test user'],
                'scanTime': '2021-10-18T14:38:53.654174'
            }
        }]
    }
    expected_readable_output = '### Scans List:\n|ID|Name|Scan Time|Type|User|\n|---|---|---|---|---|\n| 111111111 |' \
                               ' test name | 2021-10-18T14:38:53.654174 | test type | test user |\n'
    expected_context_entry = {'Redlock.Scans(val.id == obj.id)': [{'id': '111111111',
                                                                   'name': ['test name'],
                                                                   'type': ['test type'],
                                                                   'user': ['test user'],
                                                                   'scanTime': '2021-10-18T14:38:53.654174'}]}
    mocker.patch('RedLock.req', return_value=list_scans_response)
    mocker.patch.object(demisto, 'results')
    redlock_list_scans()
    assert demisto.results.call_args[0][0].get('HumanReadable') == expected_readable_output
    assert demisto.results.call_args[0][0].get('EntryContext') == expected_context_entry


def test_redlock_get_scan_status(mocker):
    """
        Given
            - The response from the API call of redlock-get-scan-status command.
        When
            - calling redlock-get-scan-status
        Then
            - Validate that the readable output and the context entry of the command is as expected

    """
    from RedLock import redlock_get_scan_status
    get_status_response = {
        'data': {
            'id': '111111111',
            'attributes': {
                'status': 'test'
            }
        }
    }
    expected_readable_output = '### Scan Status:\n|ID|Status|\n|---|---|\n| 111111111 | test |\n'
    expected_context_entry = {'Redlock.Scans(val.id == obj.id)': {'id': '111111111',
                                                                  'status': 'test'}}
    mocker.patch('RedLock.req', return_value=get_status_response)
    mocker.patch.object(demisto, 'results')
    redlock_get_scan_status()
    assert demisto.results.call_args[0][0].get('HumanReadable') == expected_readable_output
    assert demisto.results.call_args[0][0].get('EntryContext') == expected_context_entry


def test_redlock_get_scan_results(mocker):
    """
        Given
            - The response from the API call of redlock-get-scan-result command.
        When
            - calling redlock-get-scan-result
        Then
            - Validate that the readable output and the context entry of the command is as expected

    """
    from RedLock import redlock_get_scan_results
    get_result_response = {
        'data': [{
            'id': '111111111',
            'attributes': {
                'name': 'test',
                'policyId': '2222',
                'desc': 'test',
                'severity': 'high'
            }}]
    }
    expected_readable_output = '### Scan Results:\n|Description|ID|Name|Policy ID|Severity|\n|---|---|---|---|---|\n|' \
                               ' test | 111111111 | test | 2222 | high |\n'
    expected_context_entry = {'Redlock.Scans(val.id == obj.id)': {'id': None,
                                                                  'results': [
                                                                      {'id': '111111111',
                                                                       'attributes': {'name': 'test',
                                                                                      'policyId': '2222',
                                                                                      'desc': 'test',
                                                                                      'severity': 'high'}}]}}
    mocker.patch('RedLock.req', return_value=get_result_response)
    mocker.patch.object(demisto, 'results')
    redlock_get_scan_results()
    assert demisto.results.call_args[0][0].get('HumanReadable') == expected_readable_output
    assert demisto.results.call_args[0][0].get('EntryContext') == expected_context_entry


def test_redlock_search_event(mocker):
    """
        Given
            - The response from the API call of redlock-search-event command.
        When
            - calling redlock_search_event
        Then
            - Validate that the readable output and the context entry of the command is as expected

    """
    from RedLock import redlock_search_event
    get_result_response = {
        "cloudType": "all",
        "id": "a0ca8eba-b4e0-4d35-bfda-36bb5276d255",
        "name": "",
        "description": "",
        "searchType": "audit_event",
        "saved": False,
        "timeRange": {
            "type": "relative",
            "value": {
                "unit": "hour",
                "amount": 1
            },
            "relativeTimeType": "BACKWARD"
        },
        "query": "event from cloud.audit_logs where ip EXISTS AND ip IN (35.180.1.1)",
        "data": {
            "totalRows": 11310,
            "items": [{
                "account": "712829893241",
                "regionId": 4,
                "eventTs": 1642497763000,
                "subject": "ejb-iam-cloudops",
                "type": "CREATE",
                "source": "s3.amazonaws.com",
                "name": "CreateBucket",
                "id": 2559773241,
                "ip": "35.180.1.1",
                "accessKeyUsed": False,
                "cityId": -4,
                "cityName": "Private",
                "stateId": -4,
                "stateName": "Private",
                "countryId": -4,
                "countryName": "Private",
                "cityLatitude": -1.0,
                "cityLongitude": -1.0,
                "success": False,
                "internal": False,
                "location": "Private",
                "accountName": "aws-emea-tac",
                "regionName": "AWS Oregon",
                "dynamicData": {}
            }]
        }
    }
    expected_context_entry = {
        'Redlock.Event(val.id == obj.id)': [{
            'account': '712829893241', 'regionId': 4, 'eventTs': 1642497763000,
            'subject': 'ejb-iam-cloudops', 'type': 'CREATE',
            'source': 's3.amazonaws.com', 'name': 'CreateBucket', 'id': 2559773241,
            'ip': '35.180.1.1', 'accessKeyUsed': False, 'cityId': -4,
            'cityName': 'Private', 'stateId': -4, 'stateName': 'Private',
            'countryId': -4, 'countryName': 'Private', 'cityLatitude': -1.0,
            'cityLongitude': -1.0, 'success': False, 'internal': False,
            'dynamicData': {}, 'location': 'Private', 'accountName': 'aws-emea-tac',
            'regionName': 'AWS Oregon'
        }]
    }
    mocker.patch('RedLock.req', return_value=get_result_response)
    mocker.patch.object(demisto, 'args', return_value={"query": "event from cloud.audit_logs where ip EXISTS AND ip "
                                                                "IN (35.180.1.1)"})
    mocker.patch.object(demisto, 'results')
    redlock_search_event()
    assert demisto.results.call_args[0][0].get('EntryContext') == expected_context_entry


def test_redlock_search_network(mocker):
    """
        Given
            - The response from the API call of redlock-search-network command.
        When
            - calling redlock_search_network
        Then
            - Validate that the readable output and the context entry of the command is as expected

    """
    from RedLock import redlock_search_network
    get_result_response = {
        "cloudType": "aws",
        "id": "62c2bd07-780d-4037-a6f6-d540b0bd5285",
        "name": "",
        "description": "",
        "searchType": "network",
        "saved": False,
        "timeRange": {
            "type": "relative",
            "value": {
                "unit": "day",
                "amount": 2
            },
            "relativeTimeType": "BACKWARD"
        },
        "query": "network from vpc.flow_record where bytes > 0",
        "data": {
            "nodes": [{
                "id": -1065892745,
                "name": "172.31.34.235",
                "ipAddr": "172.31.34.235",
                "grouped": False,
                "suspicious": False,
                "vulnerable": False,
                "metadata": {"keys": "values"}
            }],
            "connections": [
                {
                    "from": 994246246,
                    "to": 1418248367,
                    "label": "Postgres",
                    "suspicious": False,
                    "metadata": {"keys": "values"}
                }
            ]
        }
    }
    expected_context_entry = {
        'Redlock.Network.Node(val.id == obj.id)': [{
            'id': -1065892745, 'name': '172.31.34.235',
            'ipAddr': '172.31.34.235', 'grouped': False, 'suspicious': False,
            'vulnerable': False, 'metadata': {
                'keys': 'values'
            }
        }], 'Redlock.Network.Connection(val.id == obj.from)': [{
            'from': 994246246,
            'to': 1418248367,
            'label': 'Postgres',
            'suspicious': False,
            'metadata': {
                'keys': 'values'
            }
        }]
    }
    mocker.patch('RedLock.req', return_value=get_result_response)
    mocker.patch.object(demisto, 'args', return_value={"query": "event from cloud.audit_logs where ip EXISTS AND ip "
                                                                "IN (35.180.1.1)"})
    mocker.patch.object(demisto, 'results')
    redlock_search_network()
    assert demisto.results.call_args[0][0].get('EntryContext') == expected_context_entry
