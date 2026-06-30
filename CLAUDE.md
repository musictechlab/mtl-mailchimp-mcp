# CLAUDE.md

Project context for Claude Code.

## What this is

An MCP server that wraps the **Mailchimp Marketing API** so campaigns can be
copied, created, filled with HTML, and test-sent from Claude Code.

## Tech stack

- Python 3.10+, **Poetry**
- `mcp[cli]` (FastMCP), `httpx`, `python-dotenv`
- `ruff` (lint + format), `pytest`

## Layout

- `src/mtl_mailchimp_mcp/mailchimp.py` — thin httpx client over the Marketing API
- `src/mtl_mailchimp_mcp/server.py` — FastMCP tools (`@mcp.tool()`), returning human-readable strings
- `src/mtl_mailchimp_mcp/__main__.py` — `python -m mtl_mailchimp_mcp`

## Run / test

```bash
poetry install
poetry run ruff check . && poetry run ruff format --check .
poetry run pytest
poetry run python -m mtl_mailchimp_mcp   # start the server
```

## Hard rules

- **Draft + test only.** Never add a tool that sends or schedules a campaign to
  a real audience. Sending stays a human action in the Mailchimp UI.
- The API key comes from `MAILCHIMP_API_KEY` in `.env` (never commit `.env`,
  never log the key).
- `mailchimp_set_content_from_file` must keep its path guard (confined root,
  no hidden/secret files, size cap).
- Mailchimp does not rehost images — HTML content must use absolute image URLs.
