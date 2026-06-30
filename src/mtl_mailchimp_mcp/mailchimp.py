"""Mailchimp Marketing API client — audiences, campaigns, content, test sends, reports.

Draft-and-test only by design: this client deliberately exposes no campaign
*send* or *schedule* call. Review the draft and send it from the Mailchimp UI.
"""

import os
import sys

import httpx

_TIMEOUT = 30


def _api_key() -> str:
    """Return the Mailchimp API key, or raise with a helpful message."""
    key = os.getenv("MAILCHIMP_API_KEY")
    if not key:
        print(
            "ERROR: MAILCHIMP_API_KEY must be set.\n"
            "Get it from: Mailchimp → Account → Extras → API keys",
            file=sys.stderr,
        )
        raise ValueError("MAILCHIMP_API_KEY is required")
    return key


def _data_center(key: str) -> str:
    """Mailchimp keys end in '-usXX'; that suffix selects the API data center."""
    if "-" not in key:
        raise ValueError(
            "MAILCHIMP_API_KEY is missing its data-center suffix (e.g. '-us19')"
        )
    return key.rsplit("-", 1)[1]


def _base_url() -> str:
    return f"https://{_data_center(_api_key())}.api.mailchimp.com/3.0"


def _request(
    method: str,
    endpoint: str,
    json: dict | None = None,
    params: dict | None = None,
) -> dict:
    """Make an authenticated request to the Mailchimp Marketing API."""
    resp = httpx.request(
        method,
        f"{_base_url()}{endpoint}",
        json=json,
        params=params,
        auth=("key", _api_key()),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return {}
    return resp.json()


# --- Audiences (lists) ---


def get_audiences(count: int = 25) -> dict:
    """List audiences (a.k.a. lists) with member counts."""
    return _request(
        "GET",
        "/lists",
        params={
            "count": count,
            "fields": "lists.id,lists.name,lists.stats.member_count,total_items",
        },
    )


# --- Campaigns ---


def get_campaigns(status: str | None = None, count: int = 20) -> dict:
    """List recent campaigns, newest first. Optionally filter by status."""
    params = {"count": count, "sort_field": "create_time", "sort_dir": "DESC"}
    if status:
        params["status"] = status
    return _request("GET", "/campaigns", params=params)


def get_campaign(campaign_id: str) -> dict:
    """Get a single campaign's settings, recipients, and status."""
    return _request("GET", f"/campaigns/{campaign_id}")


def get_campaign_content(campaign_id: str) -> dict:
    """Get a campaign's stored HTML/plain-text content."""
    return _request("GET", f"/campaigns/{campaign_id}/content")


def replicate_campaign(campaign_id: str) -> dict:
    """Copy an existing campaign into a new draft."""
    return _request("POST", f"/campaigns/{campaign_id}/actions/replicate")


def create_campaign(
    list_id: str,
    subject: str,
    title: str,
    from_name: str,
    reply_to: str,
    preview_text: str = "",
) -> dict:
    """Create a new regular (draft) campaign for an audience."""
    body = {
        "type": "regular",
        "recipients": {"list_id": list_id},
        "settings": {
            "subject_line": subject,
            "title": title,
            "from_name": from_name,
            "reply_to": reply_to,
            "preview_text": preview_text,
        },
    }
    return _request("POST", "/campaigns", json=body)


def set_campaign_content(campaign_id: str, html: str) -> dict:
    """Set a campaign's HTML content."""
    return _request("PUT", f"/campaigns/{campaign_id}/content", json={"html": html})


def update_campaign_settings(campaign_id: str, settings: dict) -> dict:
    """Patch a campaign's settings (subject, title, preview text, sender, ...)."""
    return _request("PATCH", f"/campaigns/{campaign_id}", json={"settings": settings})


def send_test(campaign_id: str, emails: list[str], send_type: str = "html") -> dict:
    """Send a test of the campaign to one or more seed addresses."""
    return _request(
        "POST",
        f"/campaigns/{campaign_id}/actions/test",
        json={"test_emails": emails, "send_type": send_type},
    )


# --- Reports ---


def get_report(campaign_id: str) -> dict:
    """Get the summary report (opens, clicks, bounces) for a sent campaign."""
    return _request("GET", f"/reports/{campaign_id}")
