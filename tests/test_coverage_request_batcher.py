"""Issue aggregation through a real batcher and an in-memory HTTP seam."""

import asyncio
from threading import Lock

import pytest

from jira_as import BatchError, JiraError, batch_fetch_issues


class LocalClient:
    """Only the public GET boundary used by issue fetching; never sends HTTP."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.lock = Lock()

    def get(self, endpoint, params=None, **kwargs):
        with self.lock:
            self.calls.append((endpoint, params))
        response = self.responses[endpoint]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def batch_loop():
    # execute_sync uses the caller's current event loop. Own and close the test
    # loop, restoring any prior loop so other tests do not inherit a closed one.
    try:
        previous = asyncio.get_event_loop()
    except RuntimeError:
        previous = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()
        asyncio.set_event_loop(previous)


def test_empty_input_never_requests_an_issue(batch_loop):
    client = LocalClient({})
    assert batch_fetch_issues(client, []) == {}
    assert client.calls == []


def test_successful_requests_map_payloads_to_original_keys(batch_loop):
    first = {"key": "SBX-1", "fields": {"summary": "First"}}
    second = {"key": "SBX-2", "fields": {"summary": "Second"}}
    client = LocalClient(
        {"/rest/api/3/issue/SBX-1": first, "/rest/api/3/issue/SBX-2": second}
    )
    assert batch_fetch_issues(client, ["SBX-2", "SBX-1"]) == {
        "SBX-2": second,
        "SBX-1": first,
    }
    assert sorted(client.calls) == [
        ("/rest/api/3/issue/SBX-1", None),
        ("/rest/api/3/issue/SBX-2", None),
    ]


@pytest.mark.parametrize("all_fail", [False, True])
def test_failures_preserve_other_results_and_report_progress(batch_loop, all_fail):
    first = JiraError("first unavailable") if all_fail else {"key": "SBX-1"}
    client = LocalClient(
        {
            "/rest/api/3/issue/SBX-1": first,
            "/rest/api/3/issue/SBX-2": JiraError("second unavailable"),
        }
    )
    progress = []
    results = batch_fetch_issues(
        client,
        ["SBX-1", "SBX-2"],
        progress_callback=lambda completed, total: progress.append((completed, total)),
    )
    expected_first = {"error": "first unavailable"} if all_fail else {"key": "SBX-1"}
    assert results == {
        "SBX-1": expected_first,
        "SBX-2": {"error": "second unavailable"},
    }
    assert progress == [(1, 2), (2, 2)]
    assert len(client.calls) == 2


@pytest.mark.parametrize("payload", [None, {}, []])
def test_successful_empty_payload_is_not_reclassified_as_failure(batch_loop, payload):
    client = LocalClient({"/rest/api/3/issue/SBX-1": payload})
    assert batch_fetch_issues(client, ["SBX-1"]) == {"SBX-1": payload}


def test_batch_error_supports_jira_exception_handling():
    with pytest.raises(JiraError, match="Cannot fetch issues") as raised:
        raise BatchError("Cannot fetch issues", status_code=503)
    assert raised.value.status_code == 503
    assert raised.value.message == "Cannot fetch issues"
    assert str(BatchError()) == "Batch execution failed"
