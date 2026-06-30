"""Smoke tests — no network. httpx is monkeypatched."""

import os

import pytest

from mtl_mailchimp_mcp import mailchimp, server


def test_data_center_parsing():
    assert mailchimp._data_center("abc123-us19") == "us19"
    with pytest.raises(ValueError):
        mailchimp._data_center("no-suffix-key".replace("-", ""))


def test_base_url(monkeypatch):
    monkeypatch.setenv("MAILCHIMP_API_KEY", "abc123-us7")
    assert mailchimp._base_url() == "https://us7.api.mailchimp.com/3.0"


def test_request_mocked(monkeypatch):
    monkeypatch.setenv("MAILCHIMP_API_KEY", "abc123-us1")
    captured = {}

    class FakeResp:
        status_code = 200
        content = b"{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "lists": [{"id": "L1", "name": "Main", "stats": {"member_count": 3}}]
            }

    def fake_request(method, url, **kwargs):
        captured["url"] = url
        captured["auth"] = kwargs.get("auth")
        return FakeResp()

    monkeypatch.setattr(mailchimp.httpx, "request", fake_request)
    data = mailchimp.get_audiences()
    assert captured["url"].startswith("https://us1.api.mailchimp.com/3.0/lists")
    assert captured["auth"] == ("key", "abc123-us1")
    assert data["lists"][0]["id"] == "L1"


def test_set_content_path_guard_rejects_hidden(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILCHIMP_CONTENT_DIR", str(tmp_path))
    monkeypatch.delenv("MAILCHIMP_ALLOW_HIDDEN", raising=False)
    hidden = tmp_path / ".secrets.html"
    hidden.write_text("<p>nope</p>")
    with pytest.raises(ValueError):
        server._resolve_html_path(str(hidden))


def test_set_content_path_guard_rejects_outside_root(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILCHIMP_CONTENT_DIR", str(tmp_path / "allowed"))
    os.makedirs(tmp_path / "allowed")
    outside = tmp_path / "outside.html"
    outside.write_text("<p>nope</p>")
    with pytest.raises(ValueError):
        server._resolve_html_path(str(outside))


def test_set_content_path_guard_accepts_normal(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILCHIMP_CONTENT_DIR", str(tmp_path))
    ok = tmp_path / "newsletter.html"
    ok.write_text("<h1>hi</h1>")
    assert server._resolve_html_path(str(ok)) == str(ok)
