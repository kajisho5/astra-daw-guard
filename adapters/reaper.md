# Reaper adapter notes

## 既存入口 (Entry points)

Reaper ships with ReaScript (Lua/EEL2/Python), which can read and write
project state directly, and has a long-standing OSC implementation for
control surfaces.

This repository now ships its own adapter: `../mcp-reaper/` (v0.2 read
tools, Issue #44 write tools). It wraps `python-reapy` and exposes
`get_tempo`, `get_tracks`, `get_project_info` (read-only), plus
`create_track`, `write_generated_midi`, and `save_project_as` (write
tools, gated by the Policy Engine — see `../mcp-reaper/README.md` for
exactly what each does). Its logic has been verified against stubbed
reapy objects, but **not yet against a real Reaper instance** — see
`../mcp-reaper/README.md` for status. Any other third-party Reaper MCP
you find beyond this one should still be treated as community-made and
self-responsibility until verified.

## このリポジトリが推奨する操作手段 (Recommended method)

- Prefer `../mcp-reaper/` for reading tempo/tracks/project info, and for
  creating a `GEN-` track or writing generated MIDI into one
  (`create_track`/`write_generated_midi` — both go through the Policy
  Engine, so calling them is not a way around this file's rules).
- Beyond that adapter's scope, restrict ReaScript/OSC use to: reading
  project state (items, devices). No deleting or overwriting existing
  items via script.
- New generated material goes into a new track prefixed `GEN-`.

## Computer Use でやってはいけない UI

- Do not move, resize, or dock/undock the Reaper main window or toolbars.
- Do not touch Preferences, action list edits, or plugin/pack install
  dialogs.

## 保存ダイアログの扱い

- Never overwrite the open `.rpp` project.
- If the user asked to save, prefer `../mcp-reaper/`'s `save_project_as`
  tool with a new, timestamped filename — it can only ever express Save
  As, never overwrite, and the Policy Engine still requires
  `user_requested_this_turn=True` (or approval) before it runs.
