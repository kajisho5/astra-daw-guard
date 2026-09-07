# good-run.md

架空の良いログ例。ユーザー発言:

> 8小節のハウスのドラムを新規トラックに作って。保存しないで。

エージェントの行動:

- `checklists/before.md` を確認: 依頼は「作曲」、保存依頼なし、MCP/OSC あり
- MCP/OSC でプロジェクトのテンポ・トラック一覧を読み取り
- 新規トラック `GEN-drums` を作成する前に、`checklists/during.md` の手順で
  Policy Engine に通す:

  ```bash
  $ echo '{"operation": "track.create", "attributes": {"name": "GEN-drums"}}' | python3 -m policy_engine.cli
  {
    "decision": "ALLOW",
    "rule_id": "CREATE_GEN_TRACK",
    "reason": "New track created for generated content, correctly prefixed.",
    ...
  }
  ```

- ALLOWを確認してから `GEN-drums` トラックを作成し、8小節分のドラムMIDIを
  ゼロから生成して書き込み。書き込み前にも同様に確認:

  ```bash
  $ echo '{"operation": "midi.write", "attributes": {"source": "generated", "track": "GEN-drums"}}' | python3 -m policy_engine.cli
  {"decision": "ALLOW", "rule_id": "GENERATED_MIDI_INTO_GEN_TRACK", ...}
  ```

- 既存トラックには触れていない
- 保存操作は行っていない（ユーザーが依頼していないため、`project.save`は
  そもそも提案しない）
- Computer Use は使用していない

## 報告 (report)

```text
DAW: Ableton Live
Adapter used: mcp
Tracks changed: added GEN-drums
MIDI added:
  - track: GEN-drums
    source: generated
    url:
    license:
Saved: no
Computer Use used: no
Denied actions (what I refused): none
Failures: none
```

## 日本語要約

- GEN-drums トラックに8小節のハウスドラムを新規生成して追加した。
- 保存はしていない。既存素材の取得や拒否操作はなし。
