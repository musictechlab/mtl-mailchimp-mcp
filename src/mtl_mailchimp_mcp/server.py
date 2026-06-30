"""MCP server exposing Mailchimp tools for Claude Code.

Draft + test only: this server can list, copy, and create *draft* campaigns,
push HTML content, and send *test* emails to seed addresses. It deliberately
exposes no send/schedule tool — review the draft and send it from the
Mailchimp UI.
"""

import fnmatch
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from . import mailchimp

load_dotenv()

mcp = FastMCP(
    "mtl-mailchimp",
    instructions=(
        "Mailchimp campaigns for Claude Code. List audiences, copy an existing "
        "campaign (replicate) or create a new one, push HTML content, and send "
        "test emails. DRAFT + TEST ONLY: there is no send/schedule tool by "
        "design — review the draft and send it from the Mailchimp UI."
    ),
)

# Filename globs that must never be read as campaign content, even from inside
# the allowed root — the usual homes of credentials and private keys.
_SENSITIVE_GLOBS = (
    "*.pem",
    "*.key",
    "*.env",
    ".env",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".netrc",
    "credentials",
)
_DEFAULT_MAX_HTML_MB = 5


def _resolve_html_path(file_path: str) -> str:
    """Resolve and validate a local HTML file before sending it to Mailchimp.

    Guards against arbitrary local-file reads (e.g. a prompt-injected path):
    - Confine to an allowed root: MAILCHIMP_CONTENT_DIR if set, else the user's
      home directory. Symlinks are resolved first so they can't escape the root.
    - Must be a regular file (no directories or devices).
    - Reject any hidden path component (a part starting with "."), where secrets
      overwhelmingly live. Set MAILCHIMP_ALLOW_HIDDEN=1 to opt out.
    - Reject sensitive filename patterns (keys, certs, *.env).
    - Enforce a size cap (MAILCHIMP_MAX_HTML_MB, default 5 MB).
    """
    base = os.path.realpath(
        os.environ.get("MAILCHIMP_CONTENT_DIR") or os.path.expanduser("~")
    )
    resolved = os.path.realpath(file_path)
    if resolved != base and not resolved.startswith(base + os.sep):
        raise ValueError(f"file_path must be within {base}")
    if not os.path.isfile(resolved):
        raise ValueError(f"file_path is not a regular file: {resolved}")

    if os.environ.get("MAILCHIMP_ALLOW_HIDDEN") != "1":
        rel = os.path.relpath(resolved, base)
        for part in rel.split(os.sep):
            if part.startswith("."):
                raise ValueError(f"refusing to read hidden path component: {part}")

    name = os.path.basename(resolved)
    for glob in _SENSITIVE_GLOBS:
        if fnmatch.fnmatch(name, glob):
            raise ValueError(f"refusing to read sensitive file: {name}")

    max_mb = float(os.environ.get("MAILCHIMP_MAX_HTML_MB", _DEFAULT_MAX_HTML_MB))
    size_mb = os.path.getsize(resolved) / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(f"file is {size_mb:.1f} MB, over the {max_mb} MB cap")
    return resolved


def _campaign_line(c: dict) -> str:
    s = c.get("settings", {})
    recips = c.get("recipients", {})
    return (
        f"- **{s.get('title') or s.get('subject_line') or '(untitled)'}**  "
        f"`{c.get('id')}`\n"
        f"  status: {c.get('status', '?')} | subject: {s.get('subject_line', '')!r}"
        f" | audience: {recips.get('list_name', '—')}"
    )


@mcp.tool()
def mailchimp_list_audiences() -> str:
    """List Mailchimp audiences (lists) with their IDs and member counts."""
    data = mailchimp.get_audiences()
    lists = data.get("lists", [])
    if not lists:
        return "No audiences found."
    lines = [f"# Audiences ({len(lists)})\n"]
    for a in lists:
        members = a.get("stats", {}).get("member_count", "?")
        lines.append(f"- **{a.get('name')}**  `{a.get('id')}`  ({members} members)")
    return "\n".join(lines)


@mcp.tool()
def mailchimp_list_campaigns(status: str = "", count: int = 20) -> str:
    """List recent campaigns, newest first.

    Args:
        status: Optionally filter by status (save, paused, schedule, sending, sent).
        count: How many to return (default 20).
    """
    data = mailchimp.get_campaigns(status=status or None, count=count)
    campaigns = data.get("campaigns", [])
    if not campaigns:
        return "No campaigns found."
    header = f"# Campaigns ({len(campaigns)})"
    return header + "\n\n" + "\n".join(_campaign_line(c) for c in campaigns)


@mcp.tool()
def mailchimp_get_campaign(campaign_id: str) -> str:
    """Get a campaign's settings, recipients, and status."""
    c = mailchimp.get_campaign(campaign_id)
    s = c.get("settings", {})
    r = c.get("recipients", {})
    return (
        f"# {s.get('title') or '(untitled)'}\n"
        f"ID: `{c.get('id')}`\n"
        f"Status: {c.get('status')}\n"
        f"Subject: {s.get('subject_line', '')!r}\n"
        f"Preview: {s.get('preview_text', '')!r}\n"
        f"From: {s.get('from_name', '')} <{s.get('reply_to', '')}>\n"
        f"Audience: {r.get('list_name', '—')} (`{r.get('list_id', '')}`)\n"
        f"Recipients: {r.get('recipient_count', '?')}\n"
        f"Web preview: {c.get('long_archive_url', 'N/A')}"
    )


@mcp.tool()
def mailchimp_get_content(campaign_id: str, max_chars: int = 2000) -> str:
    """Peek at a campaign's stored HTML content (truncated)."""
    content = mailchimp.get_campaign_content(campaign_id)
    html = content.get("html", "")
    if not html:
        return "This campaign has no HTML content yet."
    body = html[:max_chars]
    suffix = (
        "" if len(html) <= max_chars else f"\n… (+{len(html) - max_chars} more chars)"
    )
    return f"Content length: {len(html)} chars\n\n```html\n{body}{suffix}\n```"


@mcp.tool()
def mailchimp_replicate_campaign(campaign_id: str) -> str:
    """Copy an existing campaign into a new draft (the fastest way to reuse a newsletter)."""
    c = mailchimp.replicate_campaign(campaign_id)
    s = c.get("settings", {})
    return (
        f"Replicated into a new draft.\n"
        f"New campaign ID: `{c.get('id')}`\n"
        f"Title: {s.get('title') or '(untitled)'}\n"
        f"Status: {c.get('status')}\n\n"
        f"Next: update settings, push fresh content, then send a test."
    )


@mcp.tool()
def mailchimp_create_campaign(
    subject: str,
    title: str,
    list_id: str = "",
    from_name: str = "",
    reply_to: str = "",
    preview_text: str = "",
    segment_id: str = "",
) -> str:
    """Create a new draft campaign for an audience.

    Args:
        subject: Subject line.
        title: Internal campaign title (not shown to recipients).
        list_id: Audience ID. Defaults to MAILCHIMP_DEFAULT_LIST_ID.
        from_name: Sender name. Defaults to MAILCHIMP_FROM_NAME.
        reply_to: Reply-to address. Defaults to MAILCHIMP_REPLY_TO.
        preview_text: Inbox preview text.
        segment_id: Optional saved segment / tag ID to target instead of the
            whole audience (see mailchimp_list_segments).
    """
    list_id = list_id or os.getenv("MAILCHIMP_DEFAULT_LIST_ID", "")
    from_name = from_name or os.getenv("MAILCHIMP_FROM_NAME", "")
    reply_to = reply_to or os.getenv("MAILCHIMP_REPLY_TO", "")
    missing = [
        n
        for n, v in (
            ("list_id", list_id),
            ("from_name", from_name),
            ("reply_to", reply_to),
        )
        if not v
    ]
    if missing:
        return (
            f"Missing required value(s): {', '.join(missing)}. "
            "Pass them as arguments or set the matching MAILCHIMP_* env vars."
        )
    c = mailchimp.create_campaign(
        list_id=list_id,
        subject=subject,
        title=title,
        from_name=from_name,
        reply_to=reply_to,
        preview_text=preview_text,
        segment_id=int(segment_id) if segment_id else None,
    )
    target = f"segment `{segment_id}`" if segment_id else f"audience `{list_id}`"
    return (
        f"Created draft campaign **{title}**\n"
        f"ID: `{c.get('id')}`\n"
        f"Target: {target}\n\n"
        f"Next: mailchimp_set_content_from_file, then mailchimp_send_test."
    )


@mcp.tool()
def mailchimp_list_segments(list_id: str = "") -> str:
    """List an audience's segments and tags (with IDs and member counts)."""
    list_id = list_id or os.getenv("MAILCHIMP_DEFAULT_LIST_ID", "")
    if not list_id:
        return "Provide list_id or set MAILCHIMP_DEFAULT_LIST_ID."
    data = mailchimp.get_list_segments(list_id)
    segs = data.get("segments", [])
    if not segs:
        return "No segments or tags found."
    lines = [f"# Segments & tags ({len(segs)})\n"]
    for s in segs:
        lines.append(
            f"- [{s.get('type')}] **{s.get('name')}**  "
            f"id=`{s.get('id')}`  ({s.get('member_count')} members)"
        )
    return "\n".join(lines)


@mcp.tool()
def mailchimp_set_language_from_tag(
    tag_segment_id: str,
    in_language: str = "pl",
    out_language: str = "en",
    list_id: str = "",
    confirm: bool = False,
) -> str:
    """Set each member's contact language based on a tag/segment.

    Members in the given tag get ``in_language``; everyone else gets
    ``out_language``. This writes to real contacts, so it is a DRY RUN unless
    ``confirm=true`` is passed.

    Args:
        tag_segment_id: The tag (static segment) that marks the in-language group.
        in_language: Language code for tagged members (default "pl").
        out_language: Language code for everyone else (default "en").
        list_id: Audience ID. Defaults to MAILCHIMP_DEFAULT_LIST_ID.
        confirm: Must be true to actually write changes.
    """
    list_id = list_id or os.getenv("MAILCHIMP_DEFAULT_LIST_ID", "")
    if not list_id:
        return "Provide list_id or set MAILCHIMP_DEFAULT_LIST_ID."

    seg = mailchimp.get_segment_members(list_id, tag_segment_id)
    in_emails = {m["email_address"].lower() for m in seg.get("members", [])}
    members = mailchimp.get_members(list_id).get("members", [])

    plan = []  # (subscriber_hash, email, target_language)
    for m in members:
        target = (
            in_language if m["email_address"].lower() in in_emails else out_language
        )
        if m.get("language") != target:
            plan.append((m["id"], m["email_address"], target))

    if not plan:
        return "All members already have the correct language. Nothing to do."

    n_in = sum(1 for _, _, t in plan if t == in_language)
    n_out = len(plan) - n_in
    summary = (
        f"{len(plan)} members to update: "
        f"{n_in} → {in_language}, {n_out} → {out_language} "
        f"(of {len(members)} total)."
    )
    if not confirm:
        return f"DRY RUN — {summary}\nRe-run with confirm=true to apply."

    done = 0
    for subscriber_hash, _email, target in plan:
        mailchimp.update_member_language(list_id, subscriber_hash, target)
        done += 1
    return f"Updated {done} members. {summary}"


@mcp.tool()
def mailchimp_set_content_from_file(campaign_id: str, html_path: str) -> str:
    """Push a local HTML file as a campaign's content.

    The path is confined to MAILCHIMP_CONTENT_DIR (or your home directory) and
    hidden/secret files are rejected. Images must use absolute URLs — Mailchimp
    does not rehost them.
    """
    resolved = _resolve_html_path(html_path)
    with open(resolved, encoding="utf-8") as fh:
        html = fh.read()
    mailchimp.set_campaign_content(campaign_id, html)
    return (
        f"Set content for `{campaign_id}` from {resolved}\n"
        f"({len(html)} chars). Send a test before sending the campaign."
    )


@mcp.tool()
def mailchimp_update_settings(
    campaign_id: str,
    subject: str = "",
    title: str = "",
    preview_text: str = "",
    from_name: str = "",
    reply_to: str = "",
) -> str:
    """Update a draft campaign's settings. Only the fields you pass are changed."""
    settings = {}
    if subject:
        settings["subject_line"] = subject
    if title:
        settings["title"] = title
    if preview_text:
        settings["preview_text"] = preview_text
    if from_name:
        settings["from_name"] = from_name
    if reply_to:
        settings["reply_to"] = reply_to
    if not settings:
        return "Nothing to update — pass at least one field."
    mailchimp.update_campaign_settings(campaign_id, settings)
    return f"Updated {', '.join(settings)} on `{campaign_id}`."


@mcp.tool()
def mailchimp_send_test(campaign_id: str, emails: str = "") -> str:
    """Send a test of the campaign to seed addresses.

    Args:
        campaign_id: Campaign to test.
        emails: Comma-separated addresses. Defaults to MAILCHIMP_TEST_EMAILS.
    """
    raw = emails or os.getenv("MAILCHIMP_TEST_EMAILS", "")
    addrs = [e.strip() for e in raw.split(",") if e.strip()]
    if not addrs:
        return (
            'No test addresses. Pass emails="a@x.com,b@y.com" '
            "or set MAILCHIMP_TEST_EMAILS."
        )
    mailchimp.send_test(campaign_id, addrs)
    return f"Sent a test of `{campaign_id}` to: {', '.join(addrs)}"


@mcp.tool()
def mailchimp_report(campaign_id: str) -> str:
    """Get the opens/clicks/bounces report for a sent campaign."""
    r = mailchimp.get_report(campaign_id)
    opens = r.get("opens", {})
    clicks = r.get("clicks", {})
    bounces = r.get("bounces", {})
    return (
        f"# Report — {r.get('campaign_title', campaign_id)}\n"
        f"Emails sent: {r.get('emails_sent', '?')}\n"
        f"Opens: {opens.get('opens_total', '?')} "
        f"(rate {opens.get('open_rate', 0):.1%})\n"
        f"Clicks: {clicks.get('clicks_total', '?')} "
        f"(rate {clicks.get('click_rate', 0):.1%})\n"
        f"Bounces: {sum(v for v in bounces.values() if isinstance(v, int))}\n"
        f"Unsubscribes: {r.get('unsubscribed', '?')}"
    )


if __name__ == "__main__":
    mcp.run()
