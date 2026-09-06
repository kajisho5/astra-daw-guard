# Reaper adapter notes

## 既存入口 (Entry points)

Reaper ships with ReaScript (Lua/EEL2/Python), which can read and write
project state directly, and has a long-standing OSC implementation for
control surfaces.

This repository now ships its own read-only adapter: `../mcp-reaper/`
(v0.2). It wraps `python-reapy` and exposes only `get_tempo`,
`get_tracks`, and `get_project_info` — no write tools. Its logic has been
verified against a stubbed `reapy.Project`, but **not yet against a real
Reaper instance** — see `../mcp-reaper/README.md` for status. Any other
third-party Reaper MCP you find beyond this one should still be treated
as community-made and self-responsibility until verified.

## このリポジトリが推奨する操作手段 (Recommended method)

- Prefer `../mcp-reaper/` for reading tempo/tracks/project info.
- Beyond that adapter's read-only scope, restrict ReaScript/OSC use to:
  reading project state (items, devices) and adding new tracks/items. No
  deleting or overwriting existing items via script.
- New generated material goes into a new track prefixed `GEN-`.

## Computer Use でやってはいけない UI

- Do not move, resize, or dock/undock the Reaper main window or toolbars.
- Do not touch Preferences, action list edits, or plugin/pack install
  dialogs.

## 保存ダイアログの扱い

- Never overwrite the open `.rpp` project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
