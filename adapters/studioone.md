# Studio One adapter notes

## 既存入口 (Entry points)

Investigated 2026-09-07. PreSonus has not published a public scripting
or OSC API for Studio One: community discussion (KVR Audio, the
official Studio One forum, and PreSonus's own feedback/answers site)
confirms Studio One's internal scripting is for PreSonus staff only, not
documented for third parties, and that OSC support has been a
long-standing feature *request* rather than a shipped feature. The only
external-control path in practice is emulating a Mackie Control-class
surface (fader/transport feedback only, no track-name or tempo query),
or third-party MIDI/OSC translation tools aimed at physical control
surfaces, not project-state queries. No MCP/OSC bridge for Studio One is
confirmed as usable as of this writing — **未確認 (unconfirmed)**.

## このリポジトリが推奨する操作手段 (Recommended method)

- There is currently no reliable way to read Studio One project state
  without Computer Use.
- Prefer manual user action over Computer Use for anything destructive.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Arrange, Console (mixer), or
  Browser panels.
- Do not touch Preferences, Setup (audio/MIDI devices), or plugin/
  content-installer dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open Song.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
