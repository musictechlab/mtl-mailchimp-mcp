# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-30

### Added
- `mailchimp_list_segments` — list an audience's segments and tags.
- `segment_id` argument on `mailchimp_create_campaign` — target a saved
  segment / tag instead of the whole audience.
- `mailchimp_set_language_from_tag` — set each member's contact language from a
  tag (dry-run by default; `confirm=true` to apply).

## [0.1.0] - 2026-06-30

### Added
- Initial MCP server for Mailchimp (draft + test only).
- Tools: `mailchimp_list_audiences`, `mailchimp_list_campaigns`,
  `mailchimp_get_campaign`, `mailchimp_get_content`,
  `mailchimp_replicate_campaign`, `mailchimp_create_campaign`,
  `mailchimp_set_content_from_file`, `mailchimp_update_settings`,
  `mailchimp_send_test`, `mailchimp_report`.
- Path guard on `mailchimp_set_content_from_file` (confined root, hidden/secret
  file rejection, size cap).
- No send/schedule capability by design.
