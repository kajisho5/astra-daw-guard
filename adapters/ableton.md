# Ableton Live adapter notes

## 既存入口 (Entry points)

Several community-made bridges exist that expose Ableton Live's LiveAPI
over MCP/OSC (names seen in the wild include projects styled like
"ableton-live-mcp" or "ableton-mcp-extension"). These are
**community-made, third-party, self-responsibility** — this guard does
not vouch for any specific package or endorse a URL, and none is
officially maintained by Ableton. Verify the exact repository and its
maintenance status yourself before installing anything. No official
Ableton-provided network bridge is confirmed as of this writing —
**未確認 (unconfirmed)**.

Read this guard (`../SKILL.md`, `../policy/deny.txt`) before pointing any
such bridge at a real project.

## このリポジトリが推奨する操作手段 (Recommended method)

- Prefer an existing, already-configured MCP/OSC bridge over Computer Use.
- Read-only calls (get tracks, get tempo, get devices) are lower risk than
  any bridge call that writes or deletes clips/tracks.
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
