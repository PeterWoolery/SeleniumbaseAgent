# tests/test_proxy.py
import pytest
from src.mcp_server.proxy import resolve_proxy


def test_per_call_proxy_returned():
    result = resolve_proxy(per_call="http://proxy:8080")
    assert result == "http://proxy:8080"


def test_no_proxy_by_default(monkeypatch):
    monkeypatch.delenv("ALWAYS_PROXY", raising=False)
    monkeypatch.delenv("SELENIUM_PROXY", raising=False)
    assert resolve_proxy() is None


def test_always_proxy_uses_env(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "true")
    monkeypatch.setenv("SELENIUM_PROXY", "http://env-proxy:3128")
    assert resolve_proxy() == "http://env-proxy:3128"


def test_always_proxy_missing_url_returns_none(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "true")
    monkeypatch.delenv("SELENIUM_PROXY", raising=False)
    assert resolve_proxy() is None


def test_per_call_overrides_always_proxy(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "true")
    monkeypatch.setenv("SELENIUM_PROXY", "http://env-proxy:3128")
    assert resolve_proxy(per_call="http://override:9090") == "http://override:9090"


def test_always_proxy_case_insensitive(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "True")
    monkeypatch.setenv("SELENIUM_PROXY", "http://env-proxy:3128")
    assert resolve_proxy() == "http://env-proxy:3128"
