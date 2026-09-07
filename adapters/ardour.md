# Ardour adapter notes

## 既存入口 (Entry points)

This repository ships its own read-only adapter: `../mcp-ardour/`. It
uses Ardour's own **built-in** OSC surface (no third-party plugin or
Remote Script needed — enable it in Preferences > Control Surfaces >
Open Sound Control (OSC)) and exposes only `get_tracks` and
`get_transport` — no write tools. Its OSC addresses were confirmed
against Ardour's manual and source, and its logic has been tested
against a simulated Ardour OSC responder, but **not yet against a real
Ardour instance** — see `../mcp-ardour/README.md` for status.

Ardour's OSC surface does not expose a tempo query at all (confirmed on
Ardour's own forum by a core developer) — this is a platform limitation,
not something this adapter is missing.

## このリポジトリが推奨する操作手段 (Recommended method)

- Prefer `../mcp-ardour/` for reading tracks/buses/transport state.
- Ardour also has a Lua scripting console (`Window > Scripting`) capable
  of far more than OSC, including reads this adapter doesn't cover. Only
  use it for read operations; do not run a Lua script that writes to the
  session without the user's explicit, in-turn request.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Editor, Mixer, or Recorder
  windows/panes.
- Do not touch Preferences, keybindings, or plugin-scan dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open session.
- If the user asked to save, use "Save As" with a new, timestamped
  session name.
