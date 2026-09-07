# enforcement/ — ASTRA Enforcement Boundary（参照実装）

`policy_engine/`（Issue [#10](https://github.com/kajisho5/astra-daw-guard/issues/10)）は
Action を受け取って ALLOW / ASK / DENY を返すだけで、何も実行しません。
`checklists/during.md`（Issue [#12](https://github.com/kajisho5/astra-daw-guard/issues/12)）は
Agent に「Policy Engineを呼んでから実行しろ」と**指示**しますが、
それはドキュメント上のお願いであり、技術的にバイパスを防ぐものでは
ありませんでした。

このディレクトリはIssue [#14](https://github.com/kajisho5/astra-daw-guard/issues/14)への
対応で、「Policy Engineを呼ぶよう頼む」ではなく「**Policy Engineを
通過しない限りTool関数そのものが呼ばれない**」構造を提供します。

## これは何か / 何ではないか（重要）

- **これは**: どんなPythonの「Tool呼び出しコード」からでも使える、
  汎用的な**参照実装**です。`enforce()`または`@guarded`で実際の
  Tool関数を包むと、DENYの場合そのTool関数は一度も呼ばれません
  （ハードコードされたテストで保証、下記参照）
- **これではない**: **Astra自身のAgent runtimeへの実接続**です。
  このリポジトリには実行中のAgentループが存在しないため、
  「Astra runtime統合済み」ではありません。将来Astra側の実行環境が
  このリポジトリをインポートして使う場合の土台として用意しています
- 既存の `mcp-reaper` / `mcp-ableton` / `mcp-ardour` の読み取り専用
  ツールは**変更していません**（v0.7時点）。理由: これらは全て
  `policy_engine`上常に`READ_ONLY`ルールでALLOWになるため、
  Enforcementを追加してもDENY/ASKの分岐が一度も発火せず、実演に
  ならないためです
- **追記（Issue [#44](https://github.com/kajisho5/astra-daw-guard/issues/44)）**:
  `mcp-reaper` / `mcp-ableton` に書き込みツール（トラック作成・
  MIDI書き込み・Save As）が追加され、これらは`enforcement.enforce()`
  経由でこのモジュールを実際に呼び出す初めてのケースになりました。
  上記の「DENY/ASKが一度も発火しない」という限界はこの2つのDAWの
  書き込みツールについては解消済みです（`mcp-ardour`は対象外のまま）。
  詳細は`mcp-reaper/README.md` / `mcp-ableton/README.md`参照

## Policy EngineとEnforcement Boundaryの役割分担

| | Policy Engine (`policy_engine/`) | Enforcement Boundary (`enforcement/`) |
|---|---|---|
| 入力 | Action | Action + 実際に呼び出すTool関数 |
| やること | ALLOW/ASK/DENYを判定するだけ | 判定結果を見て、Tool関数を実際に呼ぶかどうかを決める |
| Tool実行責任 | 持たない | 持つ（ここが唯一の実行ゲート） |

`checklists/during.md`はAgent向けの**推奨手順**、この`enforcement/`は
**技術的な強制**です。コード実行できるAgentは後者を、できないAgentは
前者にフォールバックしてください（`checklists/during.md`に明記済み）。

## API

### `enforce(action, tool, *, approved=False, audit_log=None)`

```python
from enforcement import enforce, ToolDenied, ApprovalRequired

def actually_save_as(filename):
    ...  # 実際にファイルを書き込むコード

action = {"operation": "project.save", "attributes": {"mode": "save_as"}}

try:
    enforce(action, lambda: actually_save_as("song_2026.als"))
except ApprovalRequired as e:
    # ユーザーに確認を取ってから：
    enforce(action, lambda: actually_save_as("song_2026.als"), approved=True)
except ToolDenied as e:
    print(e.decision.reason)  # 実行は一切されていない
```

- `ALLOW` → `tool()`を呼んで結果を返す
- `ASK` かつ `approved=False`(既定) → `ApprovalRequired`を送出。`tool`は呼ばれない
- `ASK` かつ `approved=True` → `tool()`を呼ぶ（そのAction固有の明示的承認後の実行）
- `DENY` → **`approved`の値に関わらず常に**`ToolDenied`を送出。`tool`は絶対に呼ばれない

### `@guarded(build_action)`

既存のTool関数を宣言的に包むデコレータ。

```python
from enforcement import guarded

@guarded(lambda name: {"operation": "track.create", "attributes": {"name": name}})
def create_track(name):
    ...  # Policy EngineがALLOWした場合のみ実行される

create_track("GEN-drums")          # ALLOW → 実行
create_track("Vocals")             # ASK → ApprovalRequired、未実行
create_track("Vocals", approved=True)  # 明示的承認後 → 実行
```

### 例外

- `ToolDenied` / `ApprovalRequired` はどちらも `EnforcementBlocked` を継承し、
  `.decision` に `policy_engine.Decision` をそのまま保持する
  （`{"decision", "rule_id", "reason", "operation", "target", "attributes"}`。
  独自の曖昧なエラーに変換していません）

## 承認（approval）の意味論（重要・セキュリティ上の注意）

- `approved=True` は**そのAction 1回の呼び出しに対してのみ**有効です。
  グローバルな「承認済み」状態は持ちません。別のActionを承認したことを
  流用して他のActionを実行することはできません（テストで保証）
- `approved=True` は**DENYを一切オーバーライドしません**。ASKをALLOW相当に
  進められるだけです（テストで保証: `test_deny_is_never_overridden_by_approved_true`）
- 「前にOKと言っていた」「たぶん大丈夫」からの推測でapprovedを立てては
  いけません。呼び出し側（Agent）が、そのAction を実際にユーザーへ提示し、
  明示的な確認を得たときにだけ`approved=True`を渡してください

## Audit Log（最小限のオプション機能）

`audit_log`にリストを渡すと、ブロックされた呼び出しも実行された呼び出しも
1エントリずつ追記されます（`decision`辞書 + `executed` + `timestamp`）。
これ自体が今回の実装の目的ではなく、あくまで補助機能です。

### Agent向け表示の最小化と、Audit Logの分離（Issue #16）

Issue #16でAgent向けの表示を最小化しました（`policy_engine.cli`の
デフォルト出力、`checklists/during.md`のin-process優先）。`enforce()`
の戻り値自体はもともと`tool()`の戻り値そのものであり、`decision`/
`rule_id`/`reason`等をAgentに逐一見せる作りではありません。

このAgent向け表示の最小化は、**監査に必要な情報を一切減らしていません**。
`audit_log`に渡したリストには、`decision`/`rule_id`/`reason`/
`operation`/`target`/`attributes`/`capability_available`の全フィールドが
`executed`/`timestamp`と共に毎回記録されます — Agentが実行時に読む
テキストを削っても、事後に何が起きたかを完全に再構成できることは
`tests/test_audit_separation.py`で固定しています。CLI経由で呼ぶ
非Python呼び出し元には`audit_log`が無いので、同等の完全な記録が
必要な場合は`policy_engine.cli --full`を使ってください
（`policy_engine/README.md`参照）。

## 動作確認

`tests/test_enforcement.py`（16テスト、全て成功）で以下を検証済みです。

- ALLOW → Tool実行、結果を返す
- ASK未承認 → Tool**未実行**、承認後に実行、実行は1回のみ
- 承認はActionごとにスコープされ、他のActionへ流用できない
- **DENY → Tool は一度も実行されない**（`policy/deny.txt`の10ルール全パターンで確認）
- **DENYは`approved=True`でもオーバーライドされない**
- fail-closed（未知operation・不正な構造）でもTool未実行、`approved=True`でも同様
- `@guarded`デコレータでも同じ保証が成り立つ
- Audit Logが両方のケース（ブロック/実行）を正しく記録する

Agent向け表示の最小化とAudit Logの分離自体は`tests/test_audit_separation.py`
（7テスト、全て成功）で検証しています。

実際のAstra runtimeとの結線・実機DAWでの確認は対象外です（上記
「これは何か/何ではないか」参照）。
