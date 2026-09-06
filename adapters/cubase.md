# Cubase adapter notes

## 既存入口 (Entry points)

Cubase's scripting surface (Steinberg's Expression Map / Logical Editor /
scripting API) is limited compared to Reaper or Ableton, and no
MCP/OSC bridge is confirmed as a stable, maintained project as of this
writing — **未確認 (unconfirmed)**. In practice most control ends up
going through Computer Use, which raises the stakes of every rule below.

## このリポジトリが推奨する操作手段 (Recommended method)

- Use any scripting API only for reading project state where possible.
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
