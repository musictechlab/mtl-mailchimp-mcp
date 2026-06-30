# mtl-mailchimp-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/musictechlab/mtl-mailchimp-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/musictechlab/mtl-mailchimp-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![Built by MusicTech Lab](https://musictechlab.io/oss/build-by-musictechlab.io.svg)](https://musictechlab.io)

[Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server for [Mailchimp](https://mailchimp.com/).

Copy or create newsletter campaigns, push HTML content, and send test emails — all from Claude Code or any MCP-compatible client.

> **Draft + test only.** This server can list, copy, and create *draft* campaigns and send *test* emails to seed addresses. It deliberately exposes **no send/schedule tool** — you review the draft and hit *Send* in the Mailchimp UI. No accidental blasts from the CLI.

## Tools

| Tool | Description |
|------|-------------|
| `mailchimp_list_audiences` | List audiences (lists) with member counts |
| `mailchimp_list_campaigns` | List recent campaigns, newest first |
| `mailchimp_get_campaign` | Get a campaign's settings, recipients, status |
| `mailchimp_get_content` | Peek at a campaign's stored HTML (truncated) |
| `mailchimp_replicate_campaign` | Copy an existing campaign into a new draft |
| `mailchimp_create_campaign` | Create a new draft campaign for an audience |
| `mailchimp_set_content_from_file` | Push a local HTML file as the campaign content |
| `mailchimp_update_settings` | Update subject, title, preview text, sender |
| `mailchimp_send_test` | Send a test to seed addresses |
| `mailchimp_report` | Opens/clicks/bounces for a sent campaign |

## Setup

### 1. Get a Mailchimp API key

Mailchimp → **Account → Extras → API keys**. The key ends in a data-center suffix like `-us19`, which the server uses to find the right API host.

### 2. Configure

```bash
cp .env.example .env
# edit .env and paste your MAILCHIMP_API_KEY
poetry install
```

### 3. Register with Claude Code

```json
{
  "mcpServers": {
    "mtl-mailchimp": {
      "command": "poetry",
      "args": ["run", "python", "-m", "mtl_mailchimp_mcp"],
      "cwd": "/absolute/path/to/mtl-mailchimp-mcp"
    }
  }
}
```

## Typical flow: reuse last month's newsletter

1. `mailchimp_list_campaigns` — find the previous issue
2. `mailchimp_replicate_campaign <id>` — fresh draft
3. `mailchimp_set_content_from_file <new_id> /path/to/newsletter.html` — push new HTML
4. `mailchimp_update_settings <new_id> subject="..." preview_text="..."`
5. `mailchimp_send_test <new_id>` — check your inbox
6. Review in Mailchimp and **send from the UI**

> **Note on images:** Mailchimp does not rehost images. Use **absolute URLs** in your HTML (e.g. `https://yourdomain.com/img/...`) so they render in the inbox.

## Security

- Your API key lives only in `.env` (git-ignored) and is never logged.
- `mailchimp_set_content_from_file` is confined to `MAILCHIMP_CONTENT_DIR` (or your home directory) and refuses hidden paths and secret files (keys, certs, `*.env`).
- No send/schedule capability — see [SECURITY.md](SECURITY.md).

## Development

```bash
poetry install
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest
```

---

Built by [MusicTech Lab](https://musictechlab.io).
