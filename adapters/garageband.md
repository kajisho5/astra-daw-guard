# GarageBand adapter notes

## 既存入口 (Entry points)

GarageBand is Apple's consumer-tier DAW and shares Logic Pro's engine
but ships with essentially no scripting, AppleScript dictionary, or
external control surface support. No MCP/OSC bridge for GarageBand is
confirmed or expected — **未確認 (unconfirmed)**. Everything goes
through Computer Use.

## このリポジトリが推奨する操作手段 (Recommended method)

- There is no read path other than Computer Use. Keep reads minimal.
- Given GarageBand's consumer audience, be extra conservative — many
  users of this app are not comfortable troubleshooting a broken project
  or reversing an unwanted change.

## Computer Use でやってはいけない UI

- Do not move, resize, or rearrange the Tracks or Piano Roll windows.
- Do not touch Preferences, Loop Browser installs, or plugin/lesson
  content download dialogs.

## 保存ダイアログの扱い

- Never trigger "Save" on the open project.
- If the user asked to save, use "Save As" with a new, timestamped
  filename.
