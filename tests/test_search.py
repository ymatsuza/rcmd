from rcmd import search
from rcmd.models import Entry


def _entries():
    return [
        Entry(id="1", command="docker ps", description="list containers", tags=["docker"]),
        Entry(id="2", command="git log --oneline", description="compact log", tags=["git"]),
        Entry(id="3", command="docker compose up", description="start stack", tags=["docker", "dev"]),
    ]


def test_query_matches_command_and_description_case_insensitive():
    hits = search.filter_entries(_entries(), query="DOCKER")
    assert [e.id for e in hits] == ["1", "3"]
    hits = search.filter_entries(_entries(), query="compact")
    assert [e.id for e in hits] == ["2"]


def test_tags_and_filter():
    hits = search.filter_entries(_entries(), tags=["docker", "dev"])
    assert [e.id for e in hits] == ["3"]


def test_query_and_tags_combined():
    hits = search.filter_entries(_entries(), query="compose", tags=["docker"])
    assert [e.id for e in hits] == ["3"]


def test_empty_query_returns_all_in_order():
    hits = search.filter_entries(_entries())
    assert [e.id for e in hits] == ["1", "2", "3"]


def test_no_match_returns_empty():
    assert search.filter_entries(_entries(), query="zzz") == []
