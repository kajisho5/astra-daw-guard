# Reaper adapter notes

## 既存入口 (Entry points)

Reaper ships with ReaScript (Lua/EEL2/Python), which can read and write
project state directly, and has a long-standing OSC implementation for
control surfaces. A dedicated MCP server for Reaper is not confirmed to
exist as a stable, maintained project as of this writing — **未確認
(unconfirmed)**. Treat any third-party Reaper MCP you find as
community-made and self-responsibility until verified.

## このリポジトリが推奨する操作手段 (Recommended method)

- Until a vetted MCP exists, restrict ReaScript/OSC use to: reading
  project state (tracks, tempo, time signature, items) and adding new
  tracks/items. No deleting or overwriting existing items via script.
- New generated material goes into a new track prefixed `GEN-`.

## Computer Use でやってはいけない UI

- Do not move, resize, or dock/undock the Reaper main window or toolbars.
- Do not touch Preferences, action list edits, or plugin/pack install
  dialogs.

## 保存ダイアログの扱い

- Never overwrite the open `.rpp` project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
