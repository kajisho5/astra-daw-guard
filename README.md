# astra-daw-guard

AIエージェント（GPT-6 Astra、Codex、Claude Code など）が DAW を
操作するときに従うべき禁止事項・許可事項・作業後レポートのフォーマット
をまとめた、**AI Agent向けDAW safety / policy layer**です。特定のDAWの
MCPコレクションではありません。特定のDAWにも限定していません。
操作そのものは既存の MCP / OSC / Computer Use に任せ、このリポジトリは
その前後にかぶせる「やってよいこと・悪いこと」の層です。

判定は2段構えです。`SKILL.md`をAgentに読ませて自然言語で守らせる層
（人間にも読める）と、`policy_engine/`という**機械可読なALLOW/ASK/DENY
判定エンジン**（構造化データのみを扱い、fail-closed）です。後者は
現時点ではロジック単体の検証に留まり、実際のAgentの行動選択に
組み込むかどうかは呼び出し側の実装次第です。「安全を保証する」もの
ではなく、「機械的に判定・監査できる」層を提供するものです。

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
| Ardour | ✅ `mcp-ardour/` | Ardour本体に内蔵のOSCサーフェス | 未確認（擬似サーバーで検証済み） |
| Bitwig Studio | ガードレールのみ（MCPなし） | 参考: [DrivenByMoss](https://github.com/git-moss/DrivenByMoss)のOSC機能（コミュニティ製・自己責任） | 未検証・未実装（`adapters/bitwig.md`） |
| FL Studio | ガードレールのみ（MCPなし） | 参考: [`flstudio-mcp`](https://github.com/rosasynthesiz/flstudio-mcp)（コミュニティ製・自己責任） | 未検証・未実装（`adapters/flstudio.md`） |
| Cubase | ガードレールのみ（MCPなし） | — | 調査済み: プラットフォーム側の制約で読み取り不可（`adapters/cubase.md`） |
| Pro Tools | ガードレールのみ（MCPなし） | — | 調査済み: EUCONはAvidパートナー限定で一般利用不可（`adapters/protools.md`） |
| Logic Pro | ガードレールのみ（MCPなし） | — | 調査済み: 読み取り可能なAPI/OSCなし（`adapters/logicpro.md`） |
| Studio One | ガードレールのみ（MCPなし） | — | 調査済み: 公開API/OSCなし（`adapters/studioone.md`） |
| Cakewalk | ガードレールのみ（MCPなし） | — | 調査済み: 公開API/OSCなし（`adapters/cakewalk.md`） |
| GarageBand | ガードレールのみ（MCPなし） | — | スクリプト機能自体が無い（`adapters/garageband.md`） |

ガードレール本体はどのDAWでも同じように使えます。読み取り専用MCPが
あるのは今のところ Reaper・Ableton Live・Ardour の3つで、いずれも実機
での疎通は未検証です（擬似サーバーでのロジック検証は実施済み）。他の
DAWは2026-09-07時点で個別に調査し、結果を`adapters/*.md`に記録して
います。誇張せず、調査済みで「無い」と分かったものは「無い」と明記して
います。

各アダプタの詳細・セットアップ手順は `mcp-reaper/README.md` /
`mcp-ableton/README.md` / `mcp-ardour/README.md` / `adapters/*.md` を
参照してください。3つとも `python3 install.py` で自動化できる部分は
自動化していますが、DAW側の設定変更（例: Ableton の Preferences で
Control Surface を選ぶ）は各アプリの外からは変更できないため手動です。
MCPのセットアップが不要な場合は、ガードレール本体（`SKILL.md` /
`policy/`）だけでも機能します。

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

## v0.4（進行中、全DAW調査）

「他のDAWにも対応してほしい」との要望で、Reaper/Ableton以外の主要DAW
（Ardour, Bitwig Studio, Cubase, FL Studio, Pro Tools, Logic Pro,
Studio One, Cakewalk, GarageBand）を2026-09-07に調査。

- [x] Ardour 読み取り専用 MCP（トラック/バス一覧、トランスポート） —
      `mcp-ardour/` に実装。Ardour本体内蔵のOSCサーフェス経由。
      テンポ取得APIはArdour自体に存在しないことを確認したため未実装
      （詳細は `mcp-ardour/README.md`）
- [x] Bitwig Studio, FL Studio — コミュニティ製ブリッジ
      （DrivenByMoss / flstudio-mcp）を確認。このリポジトリでは
      ラップ・実装せず、`adapters/*.md`に案内のみ記載
- [x] Cubase, Pro Tools, Logic Pro, Studio One, Cakewalk, GarageBand —
      いずれも読み取り可能な外部API/OSCが存在しないことを個別に調査・
      確認。各`adapters/*.md`に根拠を記載

## v0.5（Policy Engine — Issue [#10](https://github.com/kajisho5/astra-daw-guard/issues/10)）

「`tools/deny_check.py`はheuristicであり、authoritativeな強制ではない」
という課題への対応。`policy_engine/`を新設し、構造化された Action を
ALLOW / ASK / DENY で機械的に判定できるようにした。詳細は
`policy_engine/README.md`。

- [x] Action Schema（`operation` / `target` / `attributes`）を定義
- [x] ALLOW / ASK / DENY の3段階判定を実装、fail-closed（未知の操作・
      不正な構造は常にDENY）
- [x] 各ルールが`policy/deny.txt` / `policy/allow.txt`の該当行を直接
      参照し、テストで同期をチェック（乖離したらCIが落ちる）
- [x] Capability Model — `mcp-reaper` / `mcp-ableton` / `mcp-ardour`の
      実装済みツールから機械的に導出（Ardourはtempo取得ツールが無い
      ことを反映）。`computer_use.invoke`判定に使用
- [x] `tools/deny_check.py`は変更せず、heuristic警告ツールとして維持。
      READMEで役割を明確に分離
- [x] テスト35件（ALLOW/ASK/DENY各ケース、fail-closedケース、
      source同期チェック、capability整合性チェック）— 全て通過
- [ ] 実際のAgentの行動選択への組み込み — 今回の対象外。ロジック単体の
      提供に留まる
