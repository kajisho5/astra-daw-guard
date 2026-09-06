# FL Studio adapter notes

## 既存入口 (Entry points)

FL Studio has limited external scripting (MIDI scripting for controllers)
but no general-purpose project-control API. No MCP/OSC bridge is
confirmed as a stable, maintained project as of this writing —
**未確認 (unconfirmed)**. Most control goes through Computer Use.

## このリポジトリが推奨する操作手段 (Recommended method)

- Prefer generating a MIDI file and having the user import it manually
  over automating the Piano Roll via Computer Use.
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
