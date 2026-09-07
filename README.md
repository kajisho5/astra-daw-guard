# astra-daw-guard

AIエージェント（GPT-6 Astra、Codex、Claude Code など）が DAW を
操作するときに従うべき禁止事項・許可事項・作業後レポートのフォーマット
をまとめた、**AI Agent向けDAW safety / policy layer**です。特定のDAWの
MCPコレクションではありません。特定のDAWにも限定していません。
操作そのものは既存の MCP / OSC / Computer Use に任せ、このリポジトリは
その前後にかぶせる「やってよいこと・悪いこと」の層です。

判定は2段構えです。`SKILL.md`をAgentに読ませて自然言語で守らせる層
（人間にも読める）と、`policy_engine/`という**機械可読なALLOW/ASK/DENY
判定エンジン**（構造化データのみを扱い、fail-closed）です。
`checklists/during.md`が操作ごとにこのエンジンを呼ぶ具体的な手順を、
`enforcement/`がTool実行そのものをこの判定でゲートする参照実装を
提供します。ただし、これは**Astra自身の実行中のAgent runtimeへの
実接続ではありません** — このリポジトリには実行中のAgentループが
存在しないため、呼び出し側（実際のAgent実行環境）がこれらをどう使う
かに委ねられています。「安全を保証する」ものではなく、「機械的に
判定・監査できる」層を提供するものです。

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

念のため、最低限守るべき禁止事項を`policy/deny.txt`の10行全てここにも
書いておきます（正本は `policy/deny.txt`。内容が食い違ったら
`policy/deny.txt` が優先）:

- ユーザーが今のターンで明示的に許可していない限り、ネットから
  `.mid` / `.midi` / `.kar` を取得しない
- BitMidi・MIDIWorld・Free MIDI など出所不明の MIDI 倉庫サイトからは
  取得しない
- 「パブリックドメイン」という表示だけでは信頼しない。ホストが
  `policy/license-allowlist.txt` に無ければ取得前に確認する
- 開いているプロジェクトファイルを上書き保存しない（保存する場合は
  必ず Save As、かつユーザーが保存を依頼した場合のみ）
- 生成したMIDIと外部から取り込んだ素材を、出典を書かずに同じトラックへ
  混ぜない
- DAW のウィンドウ位置・サイズを変更しない
- 表示倍率・配色テーマ・キー割り当てを変更しない
- プラグインのインストールやライセンスダイアログへの応答をしない
- プロジェクトファイル・ステム・未公開の楽曲を、このセッションで
  使っているモデルAPI以外へ送信しない
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
- [x] 実際のAgentの行動選択への組み込み — v0.6で対応（下記）

## v0.6（Policy Engineの行動ループ統合 — Issue [#12](https://github.com/kajisho5/astra-daw-guard/issues/12)）

Policy Engineが「あるだけで呼ばれない」状態を避けるため、Agentが実際に
呼び出す具体的な手順を`checklists/during.md`に落とし込んだ。

- [x] `checklists/during.md`を、操作ごとにPolicy Engineへ通す具体的な
      手順として書き直し。操作→Action JSONの対応表を追加（13ケース、
      すべて実行して記載通りの結果になることを確認済み）
- [x] `examples/good-run.md` / `bad-run-midi-fetch.md` /
      `bad-run-autosave.md` に、実際の`policy_engine.cli`呼び出しと
      その結果を追記。悪い例では「通していればDENYで防げていた」ことを
      実際の出力で示した
- [x] `policy_engine/`のロジック・テストは無変更（既存35テスト継続通過）
- [x] コード実行できない環境のAgent向けに、`policy/deny.txt`への
      フォールバック手順も明記（Policy Engineが使えない場合の代替）

## v0.7（Enforcement Boundary — Issue [#14](https://github.com/kajisho5/astra-daw-guard/issues/14)）

v0.6までは「Agentがpolicy_engineを呼ぶ手順」だった。これは文書上の
お願いであり、Agentがバイパスして直接Toolを呼ぶことを技術的には
防げない。`enforcement/`はこれに対応する、**Tool実行そのものを
Policy Engineの判定でゲートする**参照実装。詳細は`enforcement/README.md`。

- [x] `enforcement.enforce(action, tool, approved=False, audit_log=None)`
      — ALLOWで実行、ASKは未承認なら`ApprovalRequired`で実行させない、
      DENYは`approved`の値に関わらず常に`ToolDenied`で実行させない
- [x] `@enforcement.guarded`デコレータで既存Tool関数を宣言的に包める
- [x] テスト16件 — 「DENYされたToolは一度も呼ばれない」ことを
      `policy/deny.txt`の10パターン全てで検証、「`approved=True`でも
      DENYはオーバーライドされない」ことも明示的に検証。既存35テストと
      合わせて計51件、全て通過
- [x] 承認はAction単位（グローバルな承認状態を持たない）
- [x] 例外は`policy_engine.Decision`をそのまま保持（独自の曖昧な
      エラーに変換しない）

**正直な限界（誇張しない）**:

- **Astra自身のAgent runtimeへの実接続ではない。** このリポジトリには
  実行中のAgentループが存在しないため、「Astra runtime統合済み」とは
  書かない。これは「どんなPythonコードからでも使える参照実装」であり、
  将来実際のAgent実行環境がこのリポジトリをインポートして使うための
  土台
- 既存の`mcp-reaper` / `mcp-ableton` / `mcp-ardour`の読み取り専用ツールは
  **変更していない**。理由: 全ツールが`policy_engine`上常にALLOWになる
  ため、Enforcementを追加してもDENY/ASKパスが一度も発火せず実演に
  ならない。かつ実機未検証のコードに不要な変更を加えるリスクを避けた
- 実機DAWでの確認は対象外（従来通り）

## v0.8（ASTRA Runtime Efficiency & UX Optimization — Issue [#16](https://github.com/kajisho5/astra-daw-guard/issues/16)）

Policy Engine / Enforcement Boundaryの**安全性は一切弱めずに**、
Agent（Astra）が実際に使う際のトークン・レイテンシ・UXを最適化した。
Phase 0（現状の再調査）とPhase 1（実測）を先に行い、測定できる事実
（文字数・呼び出し回数・実測レイテンシ）と測定不能な事実（実際の
Astraのトークン数・再読込み挙動）を明確に分けた上で、承認された
範囲のみ順番に実装した。

- [x] 既存Policyの不整合確認（Step 0） — `track.mix_sources`の
      `UNLABELED_MIXED_SOURCES`/`LABELED_MIXED_SOURCES`を疑われた
      バグとして再検証。ソースコードと既存テストで「バグなし」と
      確認し、修正は行わなかった
- [x] CLI → in-process優先（Step 1, PR [#17](https://github.com/kajisho5/astra-daw-guard/pull/17)） — 実測で
      in-process `evaluate()` 数μs、CLI subprocess起動 数十ms
      （約1万倍）の差を確認。`checklists/during.md`の推奨手順を
      in-process優先に変更（CLIは非Python呼び出し元向けフォール
      バックとして存続）
- [x] Capability-unavailable vs Policy-DENY分離（Step 2, PR [#18](https://github.com/kajisho5/astra-daw-guard/pull/18)） —
      Ardourの`read.tempo`が`ALLOW`を返すが`mcp-ardour`に該当ツールが
      無いギャップを`Decision.capability_available`フィールドで分離。
      `decision`（ALLOW/ASK/DENY）自体は不変
- [x] Agent-visible output minimization（Step 3, PR [#19](https://github.com/kajisho5/astra-daw-guard/pull/19)） —
      `policy_engine.cli`のデフォルト出力を最小化（実測で約50%削減）。
      `--full`/`--pretty`で完全出力・整形出力に戻せる
- [x] セキュリティ回帰テスト（Step 4, PR [#20](https://github.com/kajisho5/astra-daw-guard/pull/20)） — Step 1-3が
      ALLOW/ASK/DENYの判定結果・ルール順を一切変えていないことを
      横断的に固定するテストを追加
- [x] Audit separation（Step 5, PR [#21](https://github.com/kajisho5/astra-daw-guard/pull/21)） — Agent向け表示の
      最小化が監査情報を一切失っていないことを明文化・regression testで固定
- [x] Approval UX + Failure UX（Step 6, PR [#22](https://github.com/kajisho5/astra-daw-guard/pull/22)） —
      `tools/decision_message.py`を新規追加。`policy_engine`の
      `rule_id`をキーに、ASK確認文言・DENY拒否文言を日英バイリンガル
      で提供（`tools/refusal_message.py`はDENY専用・別スラッグとして
      無変更のまま併存）
- [x] ベンチマーク（Step 7, PR [#23](https://github.com/kajisho5/astra-daw-guard/pull/23)） — `tools/benchmark.py`で
      Phase 1の実測値をいつでも再現できるようにした。数値は実行環境
      依存であり、Astra実機の本番性能ではないことを明記

**測定できたこと/できなかったことの区別（誇張しない）**:

- 測定できた: 各ドキュメントの文字数、CLI出力のバイト数、
  `evaluate()`/`enforce()`呼び出し回数、実測レイテンシ
  （`time.perf_counter()`、この環境・この1回の実行）
- 測定できなかった/測定不能: 実際のAstraのトークン消費量、実際の
  Agentがドキュメントを再読込みする頻度・挙動、本番環境でのCLI
  起動コスト — これらは本リポジトリにAstraの実行環境が無いため
  原理的に計測できず、一度も「測定済み」として扱っていない
- このフェーズも実機DAW・実際のAstra runtimeとの結線は対象外
  （v0.7までと同様）
