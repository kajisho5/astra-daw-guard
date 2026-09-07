# Cakewalk (by BandLab) adapter notes

## 既存入口 (Entry points)

Investigated 2026-09-07. Cakewalk has an internal CAL/CAL-like scripting
history and an Advanced Control Surface (ACS) plugin system for physical
controllers, but no public, documented external API or OSC support was
found — Cakewalk's own user forum shows OSC support as a long-standing,
unimplemented feature request. No MCP/OSC bridge for Cakewalk is
confirmed as usable as of this writing — **未確認 (unconfirmed)**.

## このリポジトリが推奨する操作手段 (Recommended method)

- There is currently no reliable way to read Cakewalk project state
  without Computer Use.
- Prefer manual user action over Computer Use for anything destructive.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Track view, Console view, or
  Piano Roll windows.
- Do not touch Preferences, MIDI/audio device setup, or plugin/pack
  install dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
