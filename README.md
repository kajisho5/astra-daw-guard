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

## 対応DAW

ガードレール本体（`SKILL.md` / `policy/`）は全DAW共通で使えます。加えて、
一部のDAWには「読み取り専用MCP」を同梱しており、テンポやトラック一覧を
安全に取得できます（書き込み系の操作は一切実装していません）。

| DAW | 読み取り専用MCP | 経由するもの | 実機での動作確認 |
|---|---|---|---|
| Reaper | ✅ `mcp-reaper/` | [reapy](https://github.com/RomeoDespres/reapy)（外部Pythonラッパー） | 未確認（ロジック検証のみ） |
| Ableton Live | ✅ `mcp-ableton/` | [AbletonOSC](https://github.com/ideoforms/AbletonOSC)（Remote Script） | 未確認（擬似サーバーで検証済み） |
| Cubase | ガードレールのみ（MCPなし） | — | 調査済み: プラットフォーム側の制約で読み取り不可（`adapters/cubase.md`） |
| FL Studio | ガードレールのみ（MCPなし） | 参考: [`flstudio-mcp`](https://github.com/rosasynthesiz/flstudio-mcp)（コミュニティ製・自己責任） | 未検証・未実装（`adapters/flstudio.md`） |

Cubase・FL Studioにはこのリポジトリ独自の読み取り専用MCPはまだありません。
2026-09-07時点で調査したところ、Cubaseは既存のMIDI Remote APIブリッジが
すべて書き込み専用で、トラック名やテンポの読み取りができない（プラット
フォーム側の制約）ことを確認しました。FL Studioにはコミュニティ製の
`flstudio-mcp`（beta）が読み取り専用リソースを持っていますが、この
リポジトリではラップ・検証していません。詳細は各`adapters/*.md`を参照
してください。操作はガードレール（`SKILL.md`の優先順位に従い、可能な
限り既存のMCP/OSC、無ければComputer Use）に委ねます。

各アダプタの詳細・セットアップ手順は `mcp-reaper/README.md` /
`mcp-ableton/README.md` / `adapters/*.md` を参照してください。

## Astra など外部エージェントへの渡し方

このリポジトリの URL を渡すだけで使わせたい場合、次のように指示してください
（そのままコピー可）:

```text
このGitHubリポジトリを読んで、書かれたルールに従って作業してください:
https://github.com/kajisho5/astra-daw-guard

特に以下は必ず守ってください:
1. AGENTS.md と SKILL.md を読む
2. policy/deny.txt にある禁止事項を破らない
3. 作業後は checklists/after.md のフォーマットで報告する
```

エージェントがリポジトリ内を自分でたどれない場合に備えて、主要ファイルの
直リンクも渡しておくと確実です。

- ルール本体: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/SKILL.md
- 最優先の禁止事項: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/policy/deny.txt
- 許可事項: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/policy/allow.txt
- 報告フォーマット: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/checklists/after.md

念のため、最低限守るべき禁止事項をここにも書いておきます
（正本は `policy/deny.txt`。内容が食い違ったら `policy/deny.txt` が優先）:

- ユーザーが今のターンで明示的に許可していない限り、ネットから
  `.mid` / `.midi` / `.kar` を取得しない
- BitMidi・MIDIWorld・Free MIDI など出所不明の MIDI 倉庫サイトからは
  取得しない
- 開いているプロジェクトファイルを上書き保存しない（保存する場合は
  必ず Save As、かつユーザーが保存を依頼した場合のみ）
- 生成したMIDIと外部から取り込んだ素材を、出典を書かずに同じトラックへ
  混ぜない
- DAW のウィンドウ位置・サイズ・配色・キー割り当てを変更しない
- プラグインのインストールやライセンスダイアログへの応答をしない
- MCP/OSC で同じ操作ができるなら Computer Use を使わない

全文は `policy/deny.txt`、実行手順は `SKILL.md` を参照してください。

## Claude Code / Codex での使い方

このリポジトリを開いた状態で:

1. AGENTS.md と SKILL.md を読め
2. policy/deny.txt に当たる操作をするな
3. 作業後は checklists/after.md のフォーマットで報告しろ

## v0.1 の範囲

v0.1 はドキュメントのみです。コード・依存パッケージ・テストはありません。
`SKILL.md` と `policy/` `checklists/` `adapters/` `examples/` を読ませて
運用することを想定しています。

## v0.2（進行中）

- [x] Reaper 読み取り専用 MCP（トラック一覧、テンポ） — `mcp-reaper/`
      に実装。ロジックはスタブ検証済みだが、実機の Reaper では未検証
      （詳細は `mcp-reaper/README.md`）
- [x] ダウンロードしたファイルのライセンス記録用 `sources.json` —
      `sources/`（スキーマ・例）と `tools/record_source.py`（記録用CLI）
      に実装・動作確認済み
- [x] Computer Use の前に deny を機械チェックする小さな CLI —
      `tools/deny_check.py`。標準ライブラリのみ、動作確認済み
      （キーワード一致のヒューリスティックであり保証ではない）
- [x] 日本語 / 英語の拒否メッセージ辞書 — `tools/refusal_messages.json`
      + `tools/refusal_message.py`。`policy/deny.txt` の10ルールと
      1対1対応していることを確認済み

## v0.3（進行中、ROADMAP.md には無い追加項目）

- [x] Ableton Live 読み取り専用 MCP（テンポ、トラック一覧） —
      `mcp-ableton/` に実装。[AbletonOSC](https://github.com/ideoforms/AbletonOSC)
      経由。OSCアドレスは一次ソースで確認済み、往復ロジックは
      擬似AbletonOSCサーバーで検証済みだが、実機の Ableton Live では
      未検証（詳細は `mcp-ableton/README.md`）
