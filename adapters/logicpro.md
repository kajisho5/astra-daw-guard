# Logic Pro adapter notes

## 既存入口 (Entry points)

Investigated 2026-09-07. Logic Pro has three scripting-adjacent
surfaces, none of which give a clean read-only project-state API:

- **Scripter** (JavaScript MIDI FX): runs per-track inside a MIDI FX
  slot, sees only MIDI events and a `TimingInfo` object (current tempo
  *at the playhead*, meter) — it cannot list tracks or query the whole
  project, and installing one just to read tempo would itself be a
  project-modifying action.
- **AppleScript**: Logic Pro's AppleScript dictionary is historically
  very limited (no reliable track-list or tempo query).
- **OSCulator**: a paid, third-party macOS app that translates OSC
  messages into keystrokes/AppleScript aimed at Logic Pro — this is a
  keystroke-injection bridge, not a documented read API, and is
  **community/commercial, self-responsibility**.

No MCP/OSC bridge with a genuine read-only project-state query was
confirmed as of this writing — **未確認 (unconfirmed)**.

## このリポジトリが推奨する操作手段 (Recommended method)

- There is currently no reliable way to read Logic Pro project state
  without Computer Use.
- Do not install a Scripter MIDI FX instance solely to read tempo —
  adding it is itself a project change and needs the same approval as
  any other write action.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Tracks, Mixer, or Piano Roll
  windows.
- Do not touch Preferences, Audio/MIDI Setup, or plugin authorization/
  install dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
