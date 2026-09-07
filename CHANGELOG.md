# Changelog

このリポジトリの開発の経緯・各バージョンで実装した内容の詳細記録です。
「これは何か」「今すぐ使うには」を知りたいだけなら `README.md` を、
現在の状態・今後の方針を知りたいなら `ROADMAP.md` を見てください。

バージョン番号は `v0.1`〜のように、機能追加のまとまりごとに振っています
(厳密なSemVerではありません — 詳細は各エントリを参照)。

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

## v0.9（次フェーズ再設計・監査 — ROADMAP.md参照）

`ROADMAP.md`がv0.1構築時の手順書のまま放置され、Policy Engine
（v0.5）・Enforcement Boundary（v0.7）・v0.8の内容を反映していなかった
ため、リポジトリ全体を実際に再監査し、状況ドキュメントとして書き直した。
その上で次フェーズの候補6つ（DAW State Awareness / Risk Classification
/ Plan・Dry Run / Enforcement Boundary hardening / Post-execution
Verification / Provenance strengthening）を実装可能性・DAW固有価値・
既存設計との整合性で検証し、採用したものだけを実装した。

- [x] ROADMAP.md全面改訂（状況ドキュメント化）、AGENTS.mdの古い記述修正
- [x] `evaluate_plan()` / `plan_is_clear()` / `worst_decision()`
      （Issue [#26](https://github.com/kajisho5/astra-daw-guard/issues/26)、
      PR [#28](https://github.com/kajisho5/astra-daw-guard/pull/28)） —
      複数Actionからなる計画を実行前にまとめて事前チェックできる、
      既存`evaluate()`のステートレスな薄いラッパー。CLIに`--plan`
      モードも追加。Action間の依存関係は一切推論しない
- [x] `DAWStateSnapshot`（Issue [#25](https://github.com/kajisho5/astra-daw-guard/issues/25)、
      PR [#29](https://github.com/kajisho5/astra-daw-guard/pull/29)） —
      Actionが提案された時点のDAW状態を`attributes["daw_state"]`に
      構造化して残すヘルパー。`from_reaper()`/`from_ableton()`/
      `from_ardour()`は各MCPの実際のツール戻り値の形からそのまま構築
      （希望的観測なし）。**Policy判定は一切変更しない** — 新しい
      `policy/deny.txt`/`allow.txt`由来のルールは追加していない
- [x] 不採用と判断したもの: Risk Classification（判定に影響しない
      ラベルのみになるため）、Enforcement Boundary hardening /
      Post-execution Verification / Provenance強化（いずれも、
      ゲート・比較・追跡すべき書き込み可能なMCP/OSCアダプタが
      リポジトリ内に1つも存在しないため対象が無い — 理由は
      `ROADMAP.md`参照）

`policy_engine/rules.py`のルール・順序、`policy/deny.txt` /
`policy/allow.txt`、`mcp-reaper` / `mcp-ableton` / `mcp-ardour`、
`enforcement/boundary.py`は今回も一切変更していない。テストは
97件→127件（全通過）。実機DAW・実際のAstra runtimeとの結線は今回も
対象外。

## v0.9.1（自己レビュー・品質改善、新機能なし）

v0.9完了後、自分自身の作業を10点満点で採点し、見つかった課題点を
Issue化して解決する作業を実施。新しいpolicy判定機能の追加ではなく、
既存コードの品質・信頼性の改善のみ。

- [x] CI/README保守性（Issue [#31](https://github.com/kajisho5/astra-daw-guard/issues/31)、
      PR [#33](https://github.com/kajisho5/astra-daw-guard/pull/33)） —
      テストファイルを追加するたびに`.github/workflows/checks.yml`と
      `policy_engine/README.md`の同じ箇所を手で書き換えていたことが
      複数回のマージコンフリクトの原因だったため、CIを
      `unittest discover`による自動検出に変更、READMEのテスト一覧を
      追記だけで済む箇条書きに変更
- [x] `policy_engine`のfail-closed型安全性バグ3件（Issue [#34](https://github.com/kajisho5/astra-daw-guard/issues/34)、
      PR [#35](https://github.com/kajisho5/astra-daw-guard/pull/35)） —
      自分で書いたテストではなく、独立した`code-review`スキルによる
      実際のレビューで発見。`evaluate()`が`None`/文字列/リストなど
      Action以外のトップレベル入力でクラッシュする、`host`/`daw`属性が
      非文字列だとクラッシュする、`capability`属性がリストだと
      unhashableでクラッシュする、の3件全てを自分の手でも再現した上で
      修正。いずれも「例外を投げず必ずDENYで閉じる」という
      `evaluate()`自身のドキュメント上の約束に反する実バグだった
- [x] `CONTRIBUTING.md`新設(PR [#36](https://github.com/kajisho5/astra-daw-guard/pull/36)） —
      このセッション自身が繰り返したブランチ管理ミス・PR粒度による
      マージコンフリクト・squash-merge時のcommit message書式崩れ、
      といった実際に起きた問題を根拠に、エンジニアリング作業の進め方
      をAGENTS.md/ROADMAP.mdとは別ファイルとして記録
- [x] `tools/benchmark.py`のゼロ反復クラッシュ、`mcp-ardour`の
      `query_list()`タイムアウト予算未実施（Issue [#37](https://github.com/kajisho5/astra-daw-guard/issues/37),
      [#38](https://github.com/kajisho5/astra-daw-guard/issues/38)、
      PR [#39](https://github.com/kajisho5/astra-daw-guard/pull/39)） —
      同じく独立レビューで発見、両方とも修正前コードで実際に
      再現してから修正。`policy_engine/` / `enforcement/`は無関係
      （読み取り専用MCPの信頼性・開発ツールの入力検証の改善のみ）
- [x] `README.md` / `ROADMAP.md`の乖離修正（PR [#40](https://github.com/kajisho5/astra-daw-guard/pull/40)）、
      `mcp-ardour/README.md`へのテスト記録追記・文言精度修正
      （PR [#41](https://github.com/kajisho5/astra-daw-guard/pull/41),
      [#42](https://github.com/kajisho5/astra-daw-guard/pull/42)）
- [x] 開発ログをこの`CHANGELOG.md`として`README.md`から分離。
      README本体は初見の人向けの概要に絞った

テストは127件→135件（全通過）。`policy_engine/rules.py`のルール・
順序、`policy/deny.txt` / `policy/allow.txt`、
`mcp-reaper` / `mcp-ableton`、`enforcement/boundary.py`は無変更
（`mcp-ardour/ardour_mcp/osc_client.py`のみ、上記の意図的な変更）。

## v0.9.2（Reaper / Ableton Liveへの書き込み可能MCPツール — Issue [#44](https://github.com/kajisho5/astra-daw-guard/issues/44)）

`ROADMAP.md`の非目的「書き込み可能なMCP/OSCアダプタを作らない」を、
リポジトリ所有者の明示的な合意によりReaper・Ableton Live限定で解除。
`mcp-ardour`は対象外（引き続き読み取り専用）。

- [x] `mcp-reaper`に3つの書き込みツールを追加:
      `create_track(name, approved=False)`（`GEN-`prefixなら自動ALLOW、
      それ以外はASK）、`write_generated_midi(track_name, notes, approved=False)`
      （`GEN-`prefixの既存トラックのみALLOW、それ以外は常にDENY）、
      `save_project_as(filename, user_requested_this_turn=False, approved=False)`
      （`user_requested_this_turn=True`なら自動ALLOW、それ以外はASK。
      上書き保存は表現する手段自体が無い）。判定ロジックは
      `policy_engine/rules.py`に既存のものをそのまま使用（新ルール追加なし）
- [x] `save_project_as`はreapy自身の`Project.save(force_save_as=True)`
      ではなく生の`reascript_api.Main_SaveProjectEx`を使用 —
      前者はREAPERのインタラクティブなSave Asダイアログを開いてしまい
      無人実行できないことをreapyのソースコードで確認した上での判断
- [x] `mcp-ableton`に2つの書き込みツールを追加:
      `create_track` / `write_generated_midi`（Reaperと同じ判定基準）。
      保存ツールは無し — AbletonOSCにSave用OSCアドレスが1つも
      存在しないことをソースコード全体の確認で判断（`mcp-ardour`に
      テンポ取得ツールが無いのと同じ「無いものは無いと書く」判断）
- [x] AbletonOSCの書き込み系ハンドラ（`_call_method` /
      `clip_add_notes`）が**OSC応答を一切返さない**ことをソースコードで
      確認。そのため`osc_client.py`に応答を待たない片方向送信`send()`を
      新設し、書き込み結果は`get`系クエリで読み直して確認する設計にした
- [x] 全ての書き込みツールが`enforcement.enforce()`を経由し、DENY/未承認
      ASKの場合はreapy/AbletonOSCの呼び出しが一切実行されないことを、
      fakeのProject/Track/Item/Take（Reaper）・fakeのOSCクライアント
      （Ableton）を使ったテストで検証（`tests/test_reaper_write_tools.py`、
      `tests/test_ableton_write_tools.py`）。この検証の過程で、
      `create_track`の戻り値バグ（`_wait_until`が述語のbool値をそのまま
      返し、実際の名前を返していなかった）を自分のテストで発見・修正した
- [x] マージ前の独立レビュー（`code-review`スキル、CONTRIBUTING.md準拠）
      でさらに2件の実バグを発見・修正: (1) `create_track`が確認に
      失敗しても間違った名前を「成功」として返していた、(2)
      `write_generated_midi`は`create_track`と違い書き込み後の確認を
      一切していなかった。両方とも成功したかのような誤った結果を返す
      のではなく`AbletonWriteUnconfirmed`例外を投げるよう修正し、
      再現するテストを追加した。レビューが指摘した3件目（Reaperの
      `save_project_as`の`project.id`の使い方）はreapy自身の
      `Project.save()`実装と同じパターンであることを確認済みで、
      実バグではないと判断した
- [x] Enforcement Boundary（`enforcement/`）が実際のDAW書き込み経路
      （fake経由、実機未検証）に接続されたのはこれが初めて。
      それまでは全てのMCPツールが読み取り専用で常にALLOWだったため、
      DENY/ASKの分岐が一度も実戦投入されたことが無かった

`policy_engine/rules.py`のルール・順序、`policy/deny.txt` /
`policy/allow.txt`、`mcp-ardour`、`enforcement/boundary.py`は無変更。
テストは135件→152件（全通過）。実機DAW・実際のAstra runtimeとの結線は
今回も対象外 — 書き込みツールの実機での動作は未検証のまま。

## v0.9.3（Ableton Liveのミキサー・デバイス・トランスポート・テンポ制御 — Issue [#46](https://github.com/kajisho5/astra-daw-guard/issues/46)）

ユーザーから「Reaper/Ableton書き込みだけでなく、ミキサー・デバイス
パラメータ・Instrument Rack・トランスポート・テンポまで含めた
Ableton Live全体の制御をしたい」との要望。Policy Engineでゲートする
方針で合意の上、`policy/allow.txt`に新しいルールを4行追加してから実装した。

- [x] `policy/allow.txt`に4行追加:
      「GEN-トラックのミキサー設定変更は無確認可」
      「GEN-トラックのデバイスパラメータ変更は無確認可」
      「再生/停止はいつでも可」
      「ユーザーがこのターンで依頼したテンポ変更は無確認可」。
      既存のtrack.create/midi.writeと同じ「GEN-トラック＝エージェント
      自身のサンドボックス」という設計思想を踏襲
- [x] `policy_engine/rules.py`に新オペレーション4つのルールを追加:
      `track.mixer_change`（GEN-トラックはALLOW、他はASK）、
      `device.param_change`（同様）、`transport.control`（常にALLOW —
      データを一切変更しないため）、`tempo.change`
      （`user_requested_this_turn=True`ならALLOW、それ以外はASK —
      プロジェクト全体のタイミングに影響するため）
- [x] `mcp-ableton`に4つの書き込みツールを追加: `set_mixer_property` /
      `set_device_parameter` / `control_transport` / `set_tempo`。
      全て`enforcement.enforce()`経由
- [x] **Instrument Rackのチェーン切り替えは実装しなかった** —
      ユーザーからの要望に含まれていたが、AbletonOSCの
      `abletonosc/device.py`を全体確認した結果、チェーン切り替え用の
      OSCアドレスが1つも存在しないことを確認。無いものを実装したふりは
      しない、というこのリポジトリの一貫した方針に従い、保存ツール
      同様「対象外」として明記した
- [x] volume/panningの数値レンジ（0.0-1.0で0.85が0dB相当、等）は
      Ableton公式のLive Object Modelドキュメントでも確認できず、
      「未確認」として明記した（誇張しない）
- [x] 書き込み系OSCアドレス（`set/volume`・`set/panning`・`set/mute`・
      `set/solo`・`/live/device/set/parameter/value`・
      `start_playing`/`stop_playing`・`set/tempo`）が全て応答を返さない
      ことをAbletonOSCのソースコードで確認済み。書き込み後は対応する
      `get`系アドレスで読み直して確認し、確認できなければ
      `AbletonWriteUnconfirmed`を投げる（Issue #44と同じ設計）
- [x] `tests/test_ableton_write_tools.py`に4つの新テストクラスを追加
      （enforcement gatingの検証、fakeのOSCオブジェクト使用）
- [x] マージ前の独立レビューでさらに2件発見・修正: (1)
      `device.param_change`のActionが`device_index`を含んでおらず、
      監査ログ上で「同じトラックのどのデバイスを変更したか」を
      区別できなかった問題(実際の判定結果は変わらないが、監査精度の
      欠陥)。属性に追加し、再現テストも追加した。(2)
      `_MIXER_PARAM_ADDRESSES`と`_MIXER_PARAM_PROPERTY_NAMES`が
      実質重複した辞書だった（保守性の問題、将来の追加時に片方だけ
      更新し忘れるリスク）。アドレス文字列からプロパティ名を導出する
      形に統合した
- [x] PR #47（CodeRabbit）のレビューでさらに3件発見・修正: (1)
      **認可バイパス（CWE-863）**: `TEMPO_CHANGE_APPROVED`ルールの
      predicateが`user_requested_this_turn`を真偽値チェックではなく
      truthinessで判定していたため、文字列`"false"`（Pythonでは
      truthy）や整数`1`を渡すと実際にはユーザー確認が無くてもテンポ変更が
      自動ALLOWされてしまう欠陥があった。`is True`の厳密比較に修正し、
      `"false"`/`1`のどちらもASKに落ちることを回帰テストで確認。(2)
      `set_mixer_property`の`mute`/`solo`が`int(bool(value))`で送信値を
      丸めていたのに、Policy Engineに記録するAction/監査ログ側は
      丸める前の生の値（例: `0.5`）を保持していたため、実際に送信した
      値と監査記録が食い違う欠陥があった。`mute`/`solo`はブール値または
      `0`/`1`のみを受け付け、それ以外は`ValueError`で拒否した上で、
      Action構築前に正規化するよう修正。(3) 書き込み確認の許容誤差が
      固定`tol=1e-4`だったため、既存値がその範囲内にたまたま近い
      場合、実際には失敗した書き込み（ドロップ）を「確認できた」と
      誤判定する余地があった（例: 既存120.0、送信ドロップ後の
      120.00005も一致とみなされてしまう）。OSCが実際に伝送する
      float32表現に両者を丸めてから比較する方式に変更し、この
      誤判定が起きないことを回帰テストで確認

`policy_engine/rules.py`の既存ルール・`policy/deny.txt`・`mcp-reaper`・
`mcp-ardour`・`enforcement/boundary.py`は無変更。テストは152件→182件
（全通過）。実機Ableton Liveでの動作は今回も未検証のまま。
