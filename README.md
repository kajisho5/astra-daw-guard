# astra-daw-guard

AIエージェント（GPT-6 Astra、Codex、Claude Code など）が DAW
（Ableton / Reaper / Cubase / FL Studio）を操作するときに従うべき
禁止事項・許可事項・作業後レポートのフォーマットをまとめたガードレール
リポジトリです。操作そのものは既存の MCP / OSC / Computer Use に任せ、
このリポジトリはその前後にかぶせる「やってよいこと・悪いこと」の層です。

## 防ぐこと

- ネットから MIDI / サンプルを無断取得すること
- 生成物と既存素材を混ぜて出典を黙ること
- プロジェクトを勝手に上書き保存すること
- Computer Use で DAW のウィンドウやレイアウトを壊すこと

## やらないこと

- 新しい DAW や LiveAPI ブリッジを作ること
- 自動作曲モデルを訓練すること
- Computer Use のスクリーンクリック自動化を実装すること

## Claude Code / Codex での使い方

このリポジトリを開いた状態で:

1. AGENTS.md と SKILL.md を読め
2. policy/deny.txt に当たる操作をするな
3. 作業後は checklists/after.md のフォーマットで報告しろ

## v0.1 の範囲

v0.1 はドキュメントのみです。コード・依存パッケージ・テストはありません。
`SKILL.md` と `policy/` `checklists/` `adapters/` `examples/` を読ませて
運用することを想定しています。

## 後続（v0.2 以降、未実装）

- Reaper 読み取り専用 MCP（トラック一覧、テンポ）
- ダウンロードしたファイルのライセンス記録用 `sources.json`
- Computer Use の前に deny を機械チェックする小さな CLI
- 日本語 / 英語の拒否メッセージ辞書
