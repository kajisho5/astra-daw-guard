# Cubase adapter notes

## 既存入口 (Entry points)

Cubase's scripting surface is Steinberg's MIDI Remote API: JavaScript
scripts that run inside Cubase, designed for mapping hardware
controllers (MIDI CC in/out), not for querying project state. Two
community MCP bridges were found and reviewed (2026-09-07) —
[`hedidjs/cubase-mcp`](https://github.com/hedidjs/cubase-mcp) and
[`jehandy/cubase-mix-bot`](https://github.com/jehandy/cubase-mix-bot) —
and **neither can read track names, tempo, or other project metadata**.
Both are write-only (or feedback-limited to numeric fader/mute state) raw
MIDI CC bridges over a virtual MIDI port (macOS IAC Driver), and
`cubase-mix-bot`'s own README states plainly that "the MIDI Remote API is
primarily designed for control surfaces, not querying project metadata."

This is a platform limitation, not a missing library: as of this
writing there is **no way to build a read-only MCP for Cubase**
comparable to `mcp-reaper/` or `mcp-ableton/` without inventing a new
protocol from scratch (out of scope — see ROADMAP.md's non-goals). No
MCP/OSC bridge with real read capability is confirmed as of this writing
— **未確認 (unconfirmed)**. In practice all control (including reading
track/tempo state) ends up going through Computer Use, which raises the
stakes of every rule below.

## このリポジトリが推奨する操作手段 (Recommended method)

- There is currently no reliable way to read Cubase project state
  without Computer Use (see above). Keep reads as minimal and
  non-destructive as possible even so.
- Prefer manual user action over Computer Use for anything destructive.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Project window, MixConsole, or
  any docked panel.
- Do not touch Preferences, key commands, or plugin/license dialogs.
- Do not click through any "activate," "trial," or content-pack install
  prompt.

## 保存ダイアログの扱い

- Never trigger the default "Save" on the open project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename, and stop if a dialog asks about anything beyond the filename.
