"""Installed argv discovery avoids the legacy stack; all indexes load together."""

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "arguments",
    [
        ["api", "search", "sprint"],
        ["api", "describe", "getIssue"],
        ["help"],
        ["help", "api"],
        ["help", "paging"],
        ["--version"],
    ],
)
def test_discovery_does_not_import_legacy_or_http_stack(arguments):
    program = """
import runpy
import sys
from pathlib import Path

def reject_network(event, args):
    if event == 'socket.connect':
        raise AssertionError('discovery attempted a network connection')
sys.addaudithook(reject_network)
entry = Path(sys.executable).with_name('jira-as')
sys.argv = ['jira-as', *sys.argv[1:]]
try:
    runpy.run_path(str(entry), run_name='__main__')
except SystemExit as exc:
    assert exc.code in (None, 0), exc.code
for name in ('jira_as.jira_client', 'jira_as.config_manager', 'requests', 'assistant_skills_lib', 'jsonschema', 'as_engine.converters'):
    assert name not in sys.modules, name
"""
    result = subprocess.run(
        [sys.executable, "-c", program, *arguments],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_three_primary_indexes_fresh_process_load_budget():
    program = f"from as_engine.index import ProductIndexes; indexes=ProductIndexes({str(ROOT / 'src/jira_as/_generated')!r}); assert sum(len(index.operations) for _,index in indexes.primary())==797"
    samples = []
    for _ in range(5):
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-c", program], capture_output=True, text=True, timeout=5
        )
        samples.append((time.perf_counter() - start) * 1000)
        assert result.returncode == 0, result.stderr
    median = statistics.median(samples)
    print(
        f"three primary indexes median_ms={median:.3f}; samples_ms={json.dumps(samples)}"
    )
    assert median < 200, f"three-index fresh-process load regressed: {median:.3f} ms"


def test_all_legacy_export_names_resolve_and_cache_without_changing_exports():
    import jira_as

    assert len(jira_as.__all__) == len(set(jira_as.__all__))
    for name in jira_as.__all__:
        value = getattr(jira_as, name)
        assert getattr(jira_as, name) is value
    with pytest.raises(AttributeError):
        getattr(jira_as, "not_a_public_export")
