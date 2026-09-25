"""Offline connection configuration checks for the pinned MCP adapter."""

import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "manager" / "mcp.py"
spec = importlib.util.spec_from_file_location("candidate_mcp_config", SOURCE)
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)


def configured(tmp_path, monkeypatch, servers):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")
    monkeypatch.setattr(mcp, "CONFIG_FILE_PATH", str(path))
    return mcp.mcp_client_config()


def test_legacy_stdio_and_sse_do_not_leak_env_to_url_or_process(tmp_path, monkeypatch):
    monkeypatch.delenv("CHILD_ONLY", raising=False)
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "local": {
                "command": "python",
                "args": ["server.py"],
                "env": {"CHILD_ONLY": "fixture"},
            },
            "remote": {"url": "https://example.org/sse"},
        },
    )
    assert result["local"] == {
        "transport": "stdio",
        "command": "python",
        "args": ["server.py"],
        "env": {"CHILD_ONLY": "fixture"},
    }
    assert result["remote"] == {"transport": "sse", "url": "https://example.org/sse"}
    assert "CHILD_ONLY" not in mcp.os.environ


def test_legacy_remote_env_requires_explicit_migration(tmp_path, monkeypatch, caplog):
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "old": {
                "url": "https://example.org/sse",
                "env": {"KEY": "synthetic-secret"},
            },
        },
    )
    assert result == {}
    assert "must use headers, not env" in caplog.text
    assert "synthetic-secret" not in caplog.text


def test_streamable_http_bearer_and_independent_header_bindings(tmp_path, monkeypatch):
    monkeypatch.setenv("SERVER_A", "synthetic-A")
    monkeypatch.setenv("SERVER_B", "synthetic-B")
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "a": {
                "url": "https://example.org/mcp",
                "transport": "streamable_http",
                "bearerTokenEnv": "SERVER_A",
                "headers": {"X-Trace": "fixed"},
            },
            "b": {
                "url": "https://example.net/sse",
                "transport": "sse",
                "headers": {
                    "Authorization": "Bearer ${SERVER_B}",
                    "X-Token": "${SERVER_A}",
                },
            },
        },
    )
    assert result["a"]["headers"] == {
        "X-Trace": "fixed",
        "Authorization": "Bearer synthetic-A",
    }
    assert result["b"]["headers"] == {
        "Authorization": "Bearer synthetic-B",
        "X-Token": "synthetic-A",
    }
    assert result["a"]["url"] == "https://example.org/mcp"
    assert result["b"]["url"] == "https://example.net/sse"


@pytest.mark.parametrize(
    "broken",
    [
        {"bearerTokenEnv": "MISSING"},
        {"headers": {"Authorization": "Bearer ${MISSING}"}},
        {"headers": {"Authorization": "Bearer ${BAD-NAME}"}},
        {"headers": {"Authorization": "Bearer fixed", "authorization": "Bearer other"}},
        {"bearerTokenEnv": "PRESENT", "headers": {"authorization": "Bearer fixed"}},
        {"headers": {"X-Trace": "line\r\nInjected: true"}},
        {"headers": {"X-Trace": "bad\x00value"}},
        {"headers": {"X\u200bTrace": "fixed"}},
    ],
)
def test_invalid_or_partial_header_binding_skips_only_that_server(
    tmp_path, monkeypatch, caplog, broken
):
    monkeypatch.setenv("PRESENT", "synthetic-secret")
    monkeypatch.delenv("MISSING", raising=False)
    servers = {
        "bad": {
            "url": "https://example.org/mcp",
            "transport": "streamable_http",
            **broken,
        },
        "good": {"url": "https://example.net/sse"},
    }
    result = configured(tmp_path, monkeypatch, servers)
    assert set(result) == {"good"}
    assert "synthetic-secret" not in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/mcp?key=synthetic-secret",
        "https://example.org/mcp?access_token=synthetic-secret",
        "https://example.org/mcp?x-api-key=synthetic-secret",
        "https://example.org/mcp?client_secret=synthetic-secret",
        "https://example.org/mcp?authToken=synthetic-secret",
        "https://example.org/mcp?refresh_token=synthetic-secret",
        "https://example.org/mcp?mode=read",
        "https://example.org/mcp#fragment",
        "https://u:synthetic-secret@example.org/mcp",
        "https://example.org/${SECRET}",
    ],
)
def test_credential_url_is_rejected_without_logging_value(
    tmp_path, monkeypatch, caplog, url
):
    result = configured(tmp_path, monkeypatch, {"bad": {"url": url}})
    assert result == {}
    assert "synthetic-secret" not in caplog.text


def test_http_credential_header_requires_loopback_or_https(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN", "synthetic-secret")
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "remote": {"url": "http://example.org/mcp", "bearerTokenEnv": "TOKEN"},
            "loopback": {
                "url": "http://127.0.0.1:8888/mcp",
                "transport": "streamable_http",
                "bearerTokenEnv": "TOKEN",
            },
        },
    )
    assert set(result) == {"loopback"}


def test_empty_env_is_not_silently_sent_as_authorization(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPTY", "")
    result = configured(
        tmp_path,
        monkeypatch,
        {"remote": {"url": "https://example.org/mcp", "bearerTokenEnv": "EMPTY"}},
    )
    assert result == {}


def test_control_character_in_bearer_env_is_rejected(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("TOKEN", "synthetic\x01secret")
    result = configured(
        tmp_path,
        monkeypatch,
        {"remote": {"url": "https://example.org/mcp", "bearerTokenEnv": "TOKEN"}},
    )
    assert result == {}
    assert "synthetic" not in caplog.text


@pytest.mark.parametrize("seconds", [0, -1, 0.5, 86400, 1e308, 10**400, "30", True])
def test_streamable_http_rejects_timeout_values_incompatible_with_pinned_sdk(
    tmp_path, monkeypatch, seconds
):
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "remote": {
                "url": "https://example.org/mcp",
                "transport": "streamable_http",
                "timeout": seconds,
            },
            "good": {"url": "https://example.net/sse"},
        },
    )
    assert set(result) == {"good"}


def test_streamable_timeout_is_timedelta_and_sse_timeout_is_float(
    tmp_path, monkeypatch
):
    from datetime import timedelta

    result = configured(
        tmp_path,
        monkeypatch,
        {
            "new": {
                "url": "https://example.org/mcp",
                "transport": "streamable_http",
                "timeout": 30,
                "sse_read_timeout": 300,
            },
            "old": {
                "url": "https://example.org/sse",
                "transport": "sse",
                "timeout": 0.5,
                "sse_read_timeout": 300,
            },
        },
    )
    assert result["new"]["timeout"] == timedelta(seconds=30)
    assert result["new"]["sse_read_timeout"] == timedelta(seconds=300)
    assert result["old"]["timeout"] == 0.5
    assert result["old"]["sse_read_timeout"] == 300.0


@pytest.mark.parametrize("seconds", [1e308, 10**400])
def test_extreme_sse_timeout_skips_only_bad_server(tmp_path, monkeypatch, seconds):
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "bad": {"url": "https://example.org/sse", "timeout": seconds},
            "good": {"url": "https://example.net/sse"},
        },
    )
    assert set(result) == {"good"}


def test_invalid_session_options_skip_only_bad_server(tmp_path, monkeypatch):
    result = configured(
        tmp_path,
        monkeypatch,
        {
            "bad": {
                "url": "https://example.org/mcp",
                "transport": "streamable_http",
                "session_kwargs": "unexpected",
            },
            "good": {"url": "https://example.net/sse"},
        },
    )
    assert set(result) == {"good"}
