# Ableton Live adapter notes

## 既存入口 (Entry points)

This repository now ships its own read-only adapter: `../mcp-ableton/`.
It talks to [AbletonOSC](https://github.com/ideoforms/AbletonOSC) (a
third-party but well-documented, actively maintained Remote Script that
exposes Ableton's Live Object Model over OSC — install it separately per
its own README) and exposes only `get_tempo`, `get_song_info`, and
`get_tracks` — no write tools. Its OSC addresses were confirmed against
AbletonOSC's source, and its request/reply logic has been tested against
a simulated AbletonOSC server, but **not yet against a real Ableton Live
instance** — see `../mcp-ableton/README.md` for status.

Other community-made bridges exist too (e.g. projects styled like
"ableton-mcp-extension", or MCP servers built on top of AbletonOSC such
as `ableton-osc-mcp`). These are **community-made, third-party,
self-responsibility** — this guard does not vouch for any specific
package, and many of them include write operations (play, mute, etc.)
that go beyond what `../mcp-ableton/` or `policy/deny.txt` allow. No
official, Ableton-maintained network bridge is confirmed as of this
writing — **未確認 (unconfirmed)**.

Read this guard (`../SKILL.md`, `../policy/deny.txt`) before pointing any
bridge at a real project.

## このリポジトリが推奨する操作手段 (Recommended method)

- Prefer `../mcp-ableton/` for reading tempo/tracks/song info.
- Beyond that adapter's read-only scope, only use an existing,
  already-configured MCP/OSC bridge — never one that requires installing
  or approving something mid-task.
- New material goes into a new MIDI track prefixed `GEN-`, never into an
  existing track.

## Computer Use でやってはいけない UI

- Do not drag, resize, minimize, or retile the Live window or its panels.
- Do not touch Live's Preferences, license/activation dialogs, or Pack
  install prompts.
- Do not change the color of tracks/clips or the UI theme.

## 保存ダイアログの扱い

- Never trigger "Save" on the currently open Set.
- If the user asked to save, use "Save Live Set As" with a new,
  timestamped filename, and only that.
