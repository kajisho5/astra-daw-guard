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
- 書き込み可能なMCP/OSCアダプタを作らない（現状、`mcp-reaper` /
  `mcp-ableton` / `mcp-ardour` はすべて読み取り専用。この境界は意図的で、
  変更する場合は別途明確な合意が必要）

## Current state（2026-09-07時点）

- `main` HEAD: `b4dc98f`
- テスト: 97件、全通過（`python3 -m unittest tests.test_policy_engine
  tests.test_enforcement tests.test_cli tests.test_security_regression
  tests.test_audit_separation tests.test_decision_messages
  tests.test_benchmark -v`）
- GitHub Issues: #10, #12, #14, #16 は全てCLOSED（重複なし確認済み）。
  #25, #26 が新規OPEN（本ロードマップ更新時に作成、詳細は後述）
- ガードレール本体（`SKILL.md` / `policy/`）は全DAW共通
- 読み取り専用MCP: Reaper / Ableton Live / Ardour の3つのみ、いずれも
  実機未検証（擬似サーバーでのロジック検証のみ）
- **書き込み可能なMCP/OSCツールは1つも存在しない**（`mcp-reaper` /
  `mcp-ableton` / `mcp-ardour` の`@mcp.tool()`は全8関数とも読み取り専用）
- Policy Engine（`policy_engine/`）と Enforcement Boundary
  （`enforcement/`）が実装済み。ただし実際のAstra Agent runtimeとの
  結線は無い（このリポジトリには実行中のAgentループが存在しないため）

## Completed（バージョン履歴の要約。詳細は README.md 参照）

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

## Current phase — 次フェーズ再設計・監査（このコミット）

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

## Next phase — Issue #25, #26

- **Issue #25**: DAW状態スナップショットのスキーマ追加（Audit文脈用、
  判定ロジックは変更しない）
- **Issue #26**: `evaluate_plan()` — 複数Actionの事前一括チェック
  （dry-run、既存`evaluate()`の薄いラッパー、クロスAction推論はしない）

両Issueとも、実装前に必ず本文のNon-goalsを守ること。特にIssue #25は
「新しいpolicy判定ルールを追加しない」が最重要の制約。

## Definition of Done（次フェーズ）

- [ ] Issue #25の受け入れ基準を全て満たす
- [ ] Issue #26の受け入れ基準を全て満たす
- [ ] 既存テスト（97件）が無傷で通過し続ける
- [ ] `policy/deny.txt` / `policy/allow.txt` / 既存ルールのALLOW/ASK/DENY
      判定結果が一切変わらない
- [ ] `mcp-reaper` / `mcp-ableton` / `mcp-ardour` / `enforcement/boundary.py`
      への変更が無い（今回のスコープでは書き込み対象が無いため）
- [ ] README.md / ROADMAP.md が実装と同期している

## 非目的（このフェーズ限定）

- Risk Classificationのラベル追加（B、不採用）
- Enforcement Boundaryの強化（D、対象が無いため不採用）
- Post-execution Verification（E、Dに依存するため不採用）
- Provenanceの深い強化（F、書き込みアダプタが無いため不採用）
- 汎用Agent Guardへの改名・汎用化（恒久的な非目的）
- 新しいDAW/MCP/OSCアダプタの追加（恒久的な非目的）

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
