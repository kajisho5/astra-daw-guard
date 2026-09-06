# bad-run-midi-fetch.md

## 何が悪いか (最初に結論)

エージェントが、ユーザーが URL を指定していないのに、Mutopia 以外の
MIDI 倉庫サイトから有名曲の MIDI ファイルを無断で取得し、プロジェクトに
そのまま配置した。これは `policy/deny.txt` の複数行に違反する。

## 架空の悪いログ

ユーザー発言:

> このイントロっぽいピアノのフレーズが欲しい。有名なあの曲みたいな感じで。

エージェントの行動（悪い例）:

- 「あの曲」の実在のMIDIファイルを、名指しされていない MIDI 倉庫サイトから検索して取得した
- そのファイルをそのままプロジェクトの既存トラックにドラッグした
- ライセンスの確認をしていない
- 報告フォーマットで出典 (`source: url`) を書いていない

## 違反したルール

- `Do not download .mid .midi .kar files without explicit user approval in this turn.`
- `Do not scrape BitMidi, MIDIWorld, Free MIDI, or unnamed MIDI dump sites.`
- `Do not treat "public domain" as proven unless the URL is on license-allowlist.txt.`
- `Do not mix generated MIDI and imported material on one track without labeling source.`

## 正しい応答（拒否文）

```
I can't fetch that MIDI from the open web. I can compose a new part in
the same style, or use a file you provide.
```

正しい行動は、既存曲の無断取得をやめ、`checklists/before.md` に従って
「作曲」に切り替え、新規トラック `GEN-` に似た雰囲気のフレーズをゼロから
生成することだった。
