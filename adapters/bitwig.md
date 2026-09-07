# Bitwig Studio adapter notes

## 既存入口 (Entry points)

Bitwig's own Controller API (Java, runs inside Bitwig as a controller
extension) is control-surface-oriented, like Cubase's MIDI Remote API,
and is not designed for external processes to query project state
directly.

One well-known third-party project was found and reviewed (2026-09-07):
[`git-moss/DrivenByMoss`](https://github.com/git-moss/DrivenByMoss) — a
mature, actively-versioned (frequent dated releases) controller
extension supporting many hardware surfaces plus a generic **OSC**
interface. Per its own documentation
([Open Sound Control (OSC)](https://github.com/git-moss/DrivenByMoss-Documentation/blob/master/Generic-Tools-Protocols/Open-Sound-Control-(OSC).md)),
it exposes read addresses such as `/tempo/raw`, `/track/{1-8}/name`,
`/track/{1-8}/mute`, and `/track/{1-8}/solo`. This is
**community-made, third-party, self-responsibility** — this guard does
not vouch for it, has not built or verified a wrapper around it, and it
has architectural differences from `mcp-reaper`/`mcp-ableton`/`mcp-ardour`
worth knowing before relying on it:

- It is a **continuous feedback-push** protocol, not query/reply: once
  connected, Bitwig streams `/update` messages on its own schedule
  rather than answering a specific request. A consumer needs to keep a
  listener running and cache the latest values, not "ask and get one
  answer."
- Track addressing is a fixed **1–8 bank** (control-surface paging
  convention), not a single "give me all N tracks" call — reading a
  session with more than 8 tracks means paging through banks.
- OSC host/port are **not fixed defaults** — they're configured per
  install in Bitwig's Controller Preferences and must be set up by hand.

No other MCP/OSC bridge for Bitwig was confirmed as stable and
maintained as of this writing beyond the project named above —
**未確認 (unconfirmed)** for anything else.

## このリポジトリが推奨する操作手段 (Recommended method)

- If DrivenByMoss's OSC interface is already configured, only read its
  documented state-report addresses (tempo, track name, mute, solo).
  Never send it a write/control address unless the user explicitly asked
  for that specific action in this turn.
- Otherwise, prefer Computer Use only for reading visible state (track
  names in the Mixer/Arranger), and avoid any action this guard's
  `policy/deny.txt` would flag.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Arranger, Mixer, or Device panel
  layout.
- Do not touch Preferences, controller script settings, or plugin/
  content-pack install dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
