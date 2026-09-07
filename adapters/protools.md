# Pro Tools adapter notes

## 既存入口 (Entry points)

Investigated 2026-09-07: Pro Tools' external control surface protocol
is Avid's **EUCON**. EUCON is a proprietary protocol primarily meant for
Avid's own control surfaces (S1/S3/S4/S6) and licensed third-party
hardware manufacturers — its SDK is not a freely published, open,
community-usable API the way reapy, AbletonOSC, or Ardour's OSC are. No
public documentation of a way to read track names or tempo from an
external, unlicensed process was found. No MCP/OSC bridge for Pro Tools
is confirmed as usable without an Avid developer/partner relationship —
**未確認 (unconfirmed)**, and unlikely to become available without one.

## このリポジトリが推奨する操作手段 (Recommended method)

- There is currently no reliable way to read Pro Tools session state
  without Computer Use. Keep reads as minimal and non-destructive as
  possible even so.
- Prefer manual user action over Computer Use for anything destructive.
- Pro Tools sessions are frequently used in live/broadcast contexts —
  treat any UI interaction as higher-stakes than in a personal project.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Edit, Mix, or Transport windows.
- Do not touch Preferences, Peripherals (I/O routing), or plugin/
  authorization dialogs.
- Do not touch playback engine or hardware buffer settings.

## 保存ダイアログの扱い

- Never trigger "Save" on the open session.
- If the user asked to save, use "Save Copy In..." or "Save As" with a
  new, timestamped session name, and stop if a dialog asks about audio
  format/sample rate conversion beyond the filename.
