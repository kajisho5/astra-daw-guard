# FL Studio adapter notes

## 既存入口 (Entry points)

FL Studio has limited external scripting (a Python-based MIDI Controller
Scripting API, meant for hardware controllers) but no first-party
general-purpose project-control API.

One community project was found and reviewed (2026-09-07):
[`rosasynthesiz/flstudio-mcp`](https://github.com/rosasynthesiz/flstudio-mcp)
bridges an external MCP server to FL Studio via virtual MIDI ports
(loopMIDI on Windows / IAC Driver on macOS) plus a controller script
installed inside FL Studio. It documents **6 read-only MCP resources**
(project state, mixer configuration, transport status, channel list,
pattern names, current system status) alongside ~60 write/control tools
(mixing, routing, note editing). This is **community-made, third-party,
self-responsibility** — not audited or maintained by this repository,
v1.0.0/beta at review time, Windows/macOS only, and setup is nontrivial
(a background daemon, virtual MIDI ports, and a one-time "arm" step
inside FL Studio for the write path).

No other MCP/OSC bridge for FL Studio was confirmed as stable and
maintained as of this writing — **未確認 (unconfirmed)** for anything
beyond the project named above.

## このリポジトリが推奨する操作手段 (Recommended method)

- If `flstudio-mcp` (or an equivalent bridge) is already configured, use
  only its documented **read-only resources** (project state, mixer
  config, transport status, channel list, pattern names) for read
  operations. Do not use its write/control tools unless the user has
  explicitly asked for the specific action in this turn — this repo has
  not verified that tool's write path stays within `policy/deny.txt`.
- Otherwise, prefer generating a MIDI file and having the user import it
  manually over automating the Piano Roll via Computer Use.
- Direct Piano Roll clicking via Computer Use is unreliable — coordinates
  drift with zoom level and window size, and misclicks can edit existing
  notes silently.

## Computer Use でやってはいけない UI

- Do not move, resize, or retile the Playlist, Piano Roll, or Mixer
  windows.
- Do not touch plugin manager, pack install, or activation dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open `.flp` project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
