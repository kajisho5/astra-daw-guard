# astra-daw-guard — ROADMAP

このファイルは「最初から実行する構築手順」ではありません。**現在の
状態・完了済みのフェーズ・次にやることを記録する状況ドキュメント**
です（v0.1構築時は逆に「上から実行する手順書」でしたが、v0.1完成後は
この役割に変わっています）。

## 目的（変更なし）

GPT-6 Astra などのAIエージェントが DAW（Reaper / Ableton Live / Ardour /
その他）を操作するとき、次を防ぐ。

- ネットから MIDI / サンプルを無断取得する
- 生成物と既存素材を混ぜて出典を黙る
- プロジェクトを勝手に上書き保存する
- Computer Use でウィンドウやレイアウトを壊す

操作そのものは既存の MCP / OSC / Computer Use に任せる。このリポジトリは
**禁止事項・許可事項・機械的判定・検証報告** をエージェントに強制する層。

## 非目的（変更なし・今後も維持）

- 新しい DAW を作らない
- Ableton LiveAPI ブリッジや他DAWのAPIブリッジを再発明しない
- 自動作曲モデルを訓練しない
- Computer Use のスクリーンクリック自動化を実装しない
- 有料 MIDI 倉庫や著作権 MIDI のミラーを作らない
- **汎用Agent Guard製品への改名・汎用化はしない。DAW専用のまま進める**
- 新しいDAW/MCP/OSCアダプタを新規に追加しない（既存3アダプタの拡張とは別）

**更新（2026-09-07、Issue #44）**: 「書き込み可能なMCP/OSCアダプタを
作らない」という非目的は、リポジトリ所有者の明示的な合意によりReaper・
Ableton Live限定で解除された。`mcp-ardour`は引き続き読み取り専用（対象外）。
経緯は`CHANGELOG.md`・Issue #44参照。

## Current state（2026-09-07時点）

- `main` HEAD: `45e7280`（このPRのbase。マージ後さらに進む）
- テスト: 177件、全通過（`python3 -m unittest discover -s tests -p "test_*.py" -v`）
- GitHub Issues: #10, #12, #14, #16, #25, #26, #31, #34, #37, #38, #44 は
  全てCLOSED（重複なし確認済み）。OPENのIssueは #32
  （リモートfeatureブランチの削除 — この実行環境のgit権限制限
  （`HTTP 403`）でセッション側からは対応不可、ユーザーの手動削除待ち）
  と #46（本更新で実装、close予定）
- ガードレール本体（`SKILL.md` / `policy/`）は全DAW共通
- MCP: Reaper / Ableton Live / Ardour の3つ、いずれも実機未検証
  （擬似サーバーでのロジック検証のみ）
- **書き込み可能なMCPツールがReaper / Ableton Liveに存在する**
  （Issue #44, #46）: `create_track` / `write_generated_midi`（両DAW）、
  `save_project_as`（Reaperのみ）、`set_mixer_property` /
  `set_device_parameter` / `control_transport` / `set_tempo`
  （Abletonのみ）。全て`enforcement.enforce()`経由でPolicy Engineの
  判定を必ず通してから実行される。`mcp-ardour`は引き続き読み取り専用。
  Ableton側にSave/Export・Instrument Rackチェーン切り替えのツールは
  無い（AbletonOSCに対応するアドレスが無いことをソースコードで確認済み）
- Policy Engine（`policy_engine/`）と Enforcement Boundary
  （`enforcement/`）が実装済み。Enforcement Boundaryは今回初めて、
  モック化されたテストダブルではなく実際のDAW書き込み経路
  （fakeのreapy/OSCオブジェクト経由、実機未検証）に対して使われた。
  ただし実際のAstra Agent runtimeとの結線は無い（このリポジトリには
  実行中のAgentループが存在しないため）

## Completed（バージョン履歴の要約。詳細は CHANGELOG.md 参照）

| バージョン | 内容 | 参照 |
|---|---|---|
| v0.1 | ドキュメントのみの骨格（SKILL.md / policy/ / checklists/ / adapters/ / examples/） | PR #1 |
| v0.2 | Reaper読み取り専用MCP、sources.json記録、deny_check.py、拒否メッセージ辞書 | PR #2, #3, #4 |
| v0.3 | Ableton Live読み取り専用MCP | PR #5 |
| v0.4 | Ardour読み取り専用MCP、全主要DAWの読み取り可否調査 | PR #6, #7 |
| — | CI（GitHub Actions）導入、MCPセットアップの手動負担削減 | PR #8, #9 |
| v0.5 | Policy Engine（`policy_engine/`、機械可読ALLOW/ASK/DENY、fail-closed） | Issue #10, PR #11 |
| v0.6 | Policy Engineを`checklists/during.md`の具体的な呼び出し手順に統合 | Issue #12, PR #13 |
| v0.7 | Enforcement Boundary（`enforcement/`、Tool実行そのものをゲート） | Issue #14, PR #15 |
| v0.8 | Runtime Efficiency & UX Optimization（in-process優先、Capability分離、output最小化、セキュリティ回帰テスト、Audit separation、Approval/Failure UX、ベンチマーク、ドキュメント整理） | Issue #16, PR #17-#24 |
| v0.9 | 次フェーズ監査、`evaluate_plan()`（計画の事前一括チェック）、`DAWStateSnapshot`（監査文脈用、判定ロジックは無変更） | Issue #25, #26, PR #27-#29 |
| v0.9.1 | 自己レビュー・品質改善(新機能なし): CI test-discovery自動化、`policy_engine`のfail-closed型安全性バグ3件の発見・修正、`CONTRIBUTING.md`新設、`tools/benchmark.py`のゼロ反復クラッシュ修正、`mcp-ardour`の`query_list()`タイムアウト予算修正、README/ROADMAP同期、READMEの英語化(看板)・`CHANGELOG.md`分離 | Issue #31, #34, #37, #38, PR #33, #35, #36, #39-#43 |
| v0.9.2 | Reaper / Ableton Liveへの書き込み可能MCPツール追加（`create_track` / `write_generated_midi` / [Reaperのみ]`save_project_as`）。「書き込みアダプタを作らない」非目的を明示的合意により解除。Enforcement Boundaryを実際のDAW書き込み経路（fake経由、実機未検証）に初めて接続 | Issue #44 |
| v0.9.3 | Ableton Liveのミキサー制御・デバイスパラメータ変更・トランスポート制御・テンポ変更を追加（`set_mixer_property` / `set_device_parameter` / `control_transport` / `set_tempo`）。`policy/allow.txt`に4行追加、対応する新オペレーション4つをPolicy Engineに追加。Instrument Rackのチェーン切り替えはAbletonOSCに対応アドレスが無いため実装せず | Issue #46 |

## 前回の監査フェーズ — 記録（2026-09-07実施）

ユーザー指示により、以下を実施：

1. リポジトリ全体の実監査（README / ROADMAP / AGENTS / SKILL /
   policy/ / policy_engine/ / enforcement/ / checklists/ / examples/ /
   adapters/ / mcp-reaper/ / mcp-ableton/ / mcp-ardour/ / tests/ /
   .github/workflows/、Git履歴、GitHub Issues）
2. ROADMAP.mdとREADME.mdの実装との乖離を洗い出し
3. 次フェーズ候補（A〜F）を実装可能性・DAW固有価値・既存設計との整合性で検証
4. 採用したものだけをIssue化、このROADMAP.mdを更新

### 検証した候補と判断

| 候補 | 判断 | 理由 |
|---|---|---|
| A. DAW State Awareness | **採用(縮小)** → Issue #25 | 既存の読み取り専用MCP（tempo/tracks/project_info/song_info/transport）から導出できる範囲でのみ、AuditログにDAW状態を残せる構造を追加。**新しいpolicy判定ルールは追加しない**（deny.txt/allow.txtに根拠が無いルールを作らない） |
| B. Risk Classification | **不採用** | ALLOW/ASK/DENYの3段階が既に判断の粒度として機能しており、ラベルだけ追加しても判定に影響しない「装飾」になる。判定を変える具体的な仕組みが無い限り採用しない |
| C. Plan / Dry Run | **採用** → Issue #26 | 既存の`evaluate()`を複数Actionにバッチ適用するだけの薄いラッパーで実装可能。新しいルール・状態管理は不要。既存アーキテクチャ（ステートレスな純粋関数）と完全に整合する |
| D. Enforcement Boundary hardening | **不採用（現時点）** | `enforcement/boundary.py`を監査した結果、ゲートすべき書き込み可能なTool呼び出し箇所がリポジトリ内に1つも存在しない（3つのMCPは全て読み取り専用・常にALLOW）。async関数も存在しないためasync対応の必要も無い。書き込み可能なアダプタが将来追加されない限り、強化すべき対象が無い |
| E. Post-execution Verification | **不採用（現時点）** | 技術的には既存の読み取りツールで実行前後のtrack_count等を比較できるが、このリポジトリのEnforcementがゲートする書き込み操作が存在しないため、何と何を比較するかが定義できない。DのEnforcement対象が無い限り前提が成立しない |
| F. Provenance strengthening | **不採用（現時点）** | `sources.json` / `tools/record_source.py`が既に`policy/allow.txt`の「取得後は出典を報告する」要求を満たしている。DAW内部での素材追跡の強化は書き込み可能なアダプタを要するため、今は対象が無い |

B/D/E/Fは「今回不採用」であり「永久に不要」ではない。D/E/Fは特に、
書き込み可能なMCP/OSCアダプタが将来追加された場合に再検討する（ただし
非目的の通り、そのようなアダプタを積極的に作る計画は無い）。

**2026-09-07追記**: この「将来」はIssue #44でReaper/Ableton Liveに
限り実現した。D/E/Fの自動採用は意味しない（後述「非目的(恒久)」参照）。

## v0.9の実装結果

- **Issue #25**(DAW state snapshot)・**Issue #26**(`evaluate_plan()`)
  ともに実装完了・PR #28, #29でマージ済み・クローズ済み
- `policy_engine/rules.py`のルール・順序、`policy/deny.txt` /
  `policy/allow.txt`、`mcp-reaper` / `mcp-ableton` / `mcp-ardour`、
  `enforcement/boundary.py`は今回も一切変更していない(各PRで
  `git diff`により確認済み)
- テスト97→127件、全通過

## Definition of Done(v0.9・達成済み)

- [x] Issue #25の受け入れ基準を全て満たす
- [x] Issue #26の受け入れ基準を全て満たす
- [x] 既存テスト(97件)が無傷で通過し続ける(+30件追加、計127件)
- [x] `policy/deny.txt` / `policy/allow.txt` / 既存ルールのALLOW/ASK/DENY
      判定結果が一切変わらない
- [x] `mcp-reaper` / `mcp-ableton` / `mcp-ardour` / `enforcement/boundary.py`
      への変更が無い
- [x] README.md / ROADMAP.md が実装と同期している(このコミットで更新)

## v0.9.2の実装結果（Issue #44、書き込みMCPツール）

- **Issue #44**: `mcp-reaper`に`create_track` / `write_generated_midi` /
  `save_project_as`、`mcp-ableton`に`create_track` / `write_generated_midi`
  を追加。実装済み・PR番号は`CHANGELOG.md`参照
- 全ての書き込みツールは`enforcement.enforce()`経由でしか実行できず、
  DENY/未承認ASKの場合はreapy/AbletonOSCの呼び出しコードが一切実行
  されないことを、fakeのProject/Track/Item/Take（Reaper）・fakeの
  OSCクライアント（Ableton）を使ったテストで検証済み
  （`tests/test_reaper_write_tools.py`・`tests/test_ableton_write_tools.py`）
- `policy_engine/rules.py`のルール・順序、`policy/deny.txt` /
  `policy/allow.txt`は無変更（`track.create` / `midi.write` /
  `project.save`のルールは既存のものをそのまま使用）
- `mcp-ardour`は無変更（対象外）
- `save_project_as`はreapyの`Project.save(force_save_as=True)`ではなく
  生の`reascript_api.Main_SaveProjectEx`を使用。前者はREAPERの
  インタラクティブなSave Asダイアログを開くため無人実行できないことを
  reapyのソースコードで確認した上での判断（`mcp-reaper/README.md`参照）
- `mcp-ableton`側の書き込みは全てAbletonOSCの応答無しアドレスであることを
  ソースコードで確認済み。書き込み直後の状態確認は再クエリのポーリング
  （`_wait_until`）に依存しており、これは実機未検証（`mcp-ableton/README.md`参照）
- テスト135→152件、全通過

## v0.9.3の実装結果（Issue #46、ミキサー・デバイス・トランスポート・テンポ）

- **Issue #46**: `mcp-ableton`に`set_mixer_property` /
  `set_device_parameter` / `control_transport` / `set_tempo`を追加。
  `policy/allow.txt`に4行、`policy_engine/rules.py`に対応する
  ルール4オペレーション分を追加（`track.mixer_change` /
  `device.param_change` / `transport.control` / `tempo.change`）。
  既存の`track.create`/`midi.write`と同じ「GEN-トラック＝サンドボックス」
  の設計を踏襲
- Instrument Rackのチェーン切り替えはユーザーからの要望に含まれていたが、
  AbletonOSCに対応するOSCアドレスが1つも無いことをソースコードで確認し、
  実装しなかった（無いものを実装したふりをしない、という一貫した方針）
- `policy_engine/rules.py`の既存ルール・`policy/deny.txt`・`mcp-reaper`・
  `mcp-ardour`・`enforcement/boundary.py`は無変更
- テスト152件→182件、全通過（マージ前レビュー計5件の指摘のうち全て修正、詳細は`CHANGELOG.md`のv0.9.3参照）

## Next phase

機能面で採用済み・未着手のIssueは無い（Issue #46は本更新で実装済み、
close予定）。OPENのIssueは#32（リモートブランチ削除、環境のgit権限制限
でセッション側からは対応不可）のみで、これはユーザーの手動対応待ち。
次に何をやるかは、このリポジトリを再監査するか、ユーザーからの新しい
要望を起点に決める。候補としては、上記「非目的(恒久)」に記載の通り
D/E/Fの再評価（Reaper/Ableton Liveに書き込みアダプタができたことで
前提が変わった）がある。「候補を思いつきで実装する」ことはしない —
上記の監査と同じ規律(実装可能性・DAW固有価値・既存設計との整合性の検証、
不要なものは不採用と明記)を毎回通すこと。エンジニアリング作業の進め方（ブランチ
運用、PR粒度、squash-merge時のcommit message、`policy_engine/` /
`enforcement/`変更時の独立レビュー必須化など）は`CONTRIBUTING.md`に
分離して記録している。

## 非目的(恒久)

- Risk Classificationのラベル追加(B、不採用 — 判定に影響しないラベルのみになるため)
- 汎用Agent Guardへの改名・汎用化
- 新しいDAW/MCP/OSCアダプタの追加（既存3アダプタの拡張とは別）

**Issue #44により前提が一部変わったもの（未再評価・未決定）**: D
(Enforcement Boundary hardening) / E (Post-execution Verification) /
F (Provenance strengthening) は「ゲートすべき書き込み可能なアダプタが
1つも無い」ことを理由に不採用としていたが、Reaper / Ableton Liveには
今や書き込みツールが存在する（Ardourは対象外のまま）。これはD/E/Fを
自動的に採用する理由にはならない — 改めて実装可能性・DAW固有価値・
既存設計との整合性を検証してから判断すべきであり、今回のIssue #44では
その再評価を行っていない。次に手を付けるなら、この3つを最初に検討する。

## History — 旧ROADMAP.md（v0.1構築手順書）の対応表

一部のREADME（`mcp-reaper/README.md`・`tools/README.md`・
`sources/README.md`等）が「ROADMAP.md フェーズ7」「v0.2 項目1〜4」
という旧ROADMAP.mdの見出しを史実として引用している。旧ROADMAP.mdは
v0.1完成までの構築手順書（フェーズ0〜7）だったため、それらの引用を
解決できるよう対応関係だけ簡潔に残す（全文は`git log`で
`cf35d84`〜`919162c`時点のROADMAP.mdを参照すれば復元できる）。

| 旧見出し | 内容 | 現在の対応 |
|---|---|---|
| フェーズ0 | 骨格ファイル一式 | v0.1（Completed表） |
| フェーズ1 | policy/deny.txt・allow.txt | v0.1（Completed表） |
| フェーズ2 | SKILL.md | v0.1（Completed表） |
| フェーズ3 | checklists/ | v0.1（Completed表） |
| フェーズ4 | adapters/ | v0.1（Completed表） |
| フェーズ5 | examples/ | v0.1（Completed表） |
| フェーズ6 | README.md | v0.1（Completed表） |
| フェーズ7・v0.2項目1 | Reaper読み取り専用MCP | v0.2（`mcp-reaper/`） |
| フェーズ7・v0.2項目2 | sources.json記録 | v0.2（`sources/`, `tools/record_source.py`） |
| フェーズ7・v0.2項目3 | deny機械チェックCLI | v0.2（`tools/deny_check.py`） |
| フェーズ7・v0.2項目4 | 拒否メッセージ辞書 | v0.2（`tools/refusal_message.py`） |
