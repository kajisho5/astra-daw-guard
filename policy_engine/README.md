# policy_engine/ — 機械可読な ALLOW / ASK / DENY 判定

これは astra-daw-guard の**唯一の authoritative な安全判定機構**です。
`SKILL.md`をAgentに読ませて自然言語で解釈させるだけでなく、
Agentが実行しようとしている操作を**構造化データ**として渡し、
機械的にALLOW/ASK/DENYを返します。

```
Agent → Action Proposal → Policy Engine → ALLOW/ASK/DENY → MCP/OSC/Computer Use → DAW
```

## `tools/deny_check.py` との違い(重要)

| | `tools/deny_check.py` | `policy_engine/` |
|---|---|---|
| 入力 | 自由記述の英語テキスト | 構造化 Action(JSON) |
| 判定方式 | キーワード重複のヒューリスティック | 明示的なルール(構造フィールドの比較のみ) |
| 位置づけ | **補助的な警告ツール**(誤検知・見逃しあり) | **唯一の authoritative な判定** |
| 保証 | なし(自己申告で「たぶん大丈夫」) | fail-closed(不明なら常にDENY) |

**`deny_check.py`がOKと言っても安全とは限りません。** 逆に
`policy_engine`がALLOWを返せば、それは`policy/deny.txt` /
`policy/allow.txt`の該当行に基づいた明示的な判定です。
`deny_check.py`は削除・格上げせず、このまま補助ツールとして残します。

## Action Schema

Policy Engineが受け取るのはこの形だけです。**自然言語は一切扱いません**。
自由記述からこのスキーマへの変換はAgent(呼び出し側)の責務です。

```json
{
  "operation": "project.save",
  "target": "current",
  "attributes": {"mode": "overwrite"}
}
```

- `operation`: `policy_engine.engine.KNOWN_OPERATIONS` にあるどれか
- `target`: 対象を表す文字列(省略可)
- `attributes`: 操作ごとに異なるフィールドを持つ辞書(省略可)

### 対応している operation 一覧

| operation | 由来 | 主な attributes |
|---|---|---|
| `read.tempo` / `read.tracks` / `read.clips` / `read.project_info` / `read.song_info` / `read.transport` | allow.txt: 読み取り | — |
| `midi.fetch` | deny.txt 1-3 / allow.txt: fetch | `host`, `user_approved_this_turn` |
| `midi.write` | allow.txt: GEN-トラック | `source`, `track` |
| `track.create` | allow.txt: GEN-トラック | `name` |
| `track.mix_sources` | deny.txt: 出典ラベル | `labeled` |
| `project.save` | deny.txt: 上書き禁止 / allow.txt: Save As | `mode` (`overwrite`\|`save_as`), `user_requested_this_turn` |
| `daw.window_change` | deny.txt: ウィンドウ操作禁止 | `action` |
| `daw.display_settings_change` | deny.txt: 表示設定変更禁止 | `setting` |
| `daw.plugin_install` / `daw.license_dialog_respond` | deny.txt: プラグイン/ライセンス禁止 | — |
| `data.send_external` | deny.txt: 外部送信禁止 | `destination`, `is_model_api_in_use` |
| `computer_use.invoke` | deny.txt: MCP優先 | `daw`, `capability` |

新しい operation を増やす場合は、必ず `policy/deny.txt` /
`policy/allow.txt` に対応する行があることを確認し、`rules.py` の
`source_text` にその行をそのまま書いてください。
`tests/test_policy_engine.py` の `SourceSyncTests` が、この対応が
崩れていないかを毎回チェックします。

## 判定結果(Decision)

```json
{
  "decision": "DENY",
  "rule_id": "PROJECT_OVERWRITE",
  "reason": "Overwriting the currently open project is never allowed, regardless of user request.",
  "operation": "project.save",
  "target": "current",
  "attributes": {"mode": "overwrite"},
  "capability_available": null
}
```

`rule_id`と`reason`があるので、「なぜその判定になったか」を常に
説明できます(監査可能性)。

## `capability_available` — Policy判定とCapabilityの分離(重要)

`capability_available`は`decision`(ALLOW/ASK/DENY)とは**別物**です。
`operation`が`read.`で始まり、`attributes.daw`が指定されている場合
だけ、`CAPABILITY_MATRIX`(下記)を見て`True`/`False`が入ります。
それ以外(read以外の操作、または`daw`未指定)は常に`null`(該当なし)。

- `read.tempo`はどのDAWに対しても**常にALLOW**です(ポリシー上、
  状態の読み取りを禁止する規則は存在しません)
- `capability_available: false`は「この操作がポリシーで禁止されている」
  という意味では**ありません**。「このリポジトリの該当DAW用MCP/OSC
  アダプタに、その読み取りを行うツールが実装されていない」という
  **技術的な制約**を表すだけです
- 具体例: `evaluate({"operation": "read.tempo", "attributes": {"daw": "ardour"}})`
  は`decision: "ALLOW"`のまま、`capability_available: false`になります
  (ArdourのOSCサーフェス自体にテンポ取得コマンドが無いため —
  `mcp-ardour/README.md`参照)。この場合、Agentは「DENYされた」と
  誤解して読み取りを諦めるのではなく、`SKILL.md`の優先順位に従って
  別の手段(Computer Useなど)にフォールバックしてください
- `capability_available: false`をDENYと混同して扱ってはいけません。
  逆に、DENYされた操作を`capability_available`で回避できると考えるのも
  誤りです — 別軸の情報です

`tests/test_policy_engine.py`の`CapabilityAvailabilityTests`が、
`CAPABILITY_MATRIX`とこのフィールドの整合性を検証します。

## Fail-closed(最重要の設計原則)

- 未登録の `operation` → 常に `DENY`(`rule_id: UNKNOWN_OPERATION`)
- 構造として不正な Action(operationが無い、辞書でない等） → 常に
  `DENY`(`rule_id: INVALID_ACTION_SCHEMA`）
- 既知の operation だが、どのルールにも一致しなかった場合 → 常に
  `DENY`(`rule_id: NO_MATCHING_RULE`）

「判定できなかったから実行していい」という設計は**しません**。
不明な場合は常に安全側(DENY)に倒します。

## Capability Model

`policy_engine/capabilities.py` の `CAPABILITY_MATRIX` は、このリポジトリの
`mcp-reaper` / `mcp-ableton` / `mcp-ardour` が**実際に実装しているツール**
から手動で導出しています(希望的観測ではありません)。

- Reaper: `read.tempo` / `read.tracks` / `read.project_info`
- Ableton: `read.tempo` / `read.tracks` / `read.song_info`
- Ardour: `read.tracks` / `read.transport`(**`read.tempo`は無し** —
  ArdourのOSCサーフェス自体にテンポ取得コマンドが無いため。
  `mcp-ardour/README.md`参照）

`computer_use.invoke` はこの表を参照し、「同じ操作がMCP/OSCで可能なら
Computer UseはDENY」を機械的に判定します。したがってArdourで
`read.tempo`をComputer Use経由で行うのは(MCPに手段が無いため)ALLOWに
なります — これは意図的な挙動です。

`tests/test_policy_engine.py`の`CapabilityMatrixTests`が、この表が
実際の`mcp-*/*/server.py`のツール定義と一致しているかをASTで検証します。

## 計画の事前一括チェック(`evaluate_plan` — Issue #26)

1操作ずつではなく、複数Actionからなる計画をまとめて事前チェックできます。

```python
from policy_engine import evaluate_plan, plan_is_clear, worst_decision

plan = [
    {"operation": "read.tempo"},
    {"operation": "track.create", "attributes": {"name": "GEN-bass"}},
    {"operation": "midi.write", "attributes": {"source": "generated", "track": "GEN-bass"}},
]
decisions = evaluate_plan(plan)
if not plan_is_clear(decisions):
    print(worst_decision(decisions))  # "ASK" or "DENY"
```

CLIでも同様に`--plan`でJSON配列を渡せます:

```bash
echo '[{"operation": "read.tempo"}, {"operation": "project.save", "attributes": {"mode": "overwrite"}}]' \
    | python3 -m policy_engine.cli --plan
# 1行ずつDecisionを出力。終了コードは計画全体の最悪値
# (DENYが1つでもあれば2、無ければASKの有無で1、全ALLOWなら0)
```

**これは`evaluate()`を順番に呼ぶだけの薄いラッパーです。** Action同士の
依存関係(「step 2はstep 1がALLOWされて初めて意味を持つ」等)は一切
推論しません。各Actionは`evaluate()`を単体で呼んだときと完全に同じ
結果になります(状態を共有しない、ステートレスな一括処理)。

## DAW State Snapshot(監査文脈用、判定には影響しない — Issue #25)

`policy_engine/daw_state.py`は、Actionが提案された時点でDAWが
どういう状態だったかを、`attributes["daw_state"]`という決まった場所に
構造化して残すためのヘルパーです。**これはPolicy判定を一切変えません**
— `rules.py`のどのルールも`daw_state`を読みません。

```python
from policy_engine import evaluate
from policy_engine.daw_state import from_reaper, attach_to_attributes

# tempo/tracks/project_infoは、mcp-reaperの各ツールを呼んで得た
# 実際の戻り値をそのまま渡す(policy_engineがMCPを直接呼ぶことはない)
snapshot = from_reaper(tempo=tempo_result, tracks=tracks_result, project_info=project_info_result)

action = {"operation": "track.create", "attributes": {"name": "GEN-bass"}}
action["attributes"] = attach_to_attributes(action["attributes"], snapshot)

decision = evaluate(action)  # snapshotを付けても判定結果は変わらない
```

- `from_reaper()` / `from_ableton()` / `from_ardour()`: 各DAWの実際の
  MCPツールの戻り値の形からそのまま構築する(希望的観測でフィールドを
  埋めない。`from_ardour()`の`tempo_bpm`は常に`None` — Ardourの
  OSCサーフェスにテンポ取得コマンドが無いため)
- `attach_to_attributes(attributes, snapshot)`: `attributes`のコピーに
  `daw_state`キーで追加するだけ(既存キーは上書きしない、入力もmutateしない)
- `enforcement.enforce(..., audit_log=log)`の監査ログは、`Decision.attributes`
  をそのまま記録するため(Issue #16 Step 5)、この`daw_state`も追加の
  実装なしでそのまま監査ログに残ります

`tests/test_daw_state.py`が、`daw_state`を付けても付けなくても
ALLOW/ASK/DENY・fail-closedのどの判定結果も変わらないことを、
複数の代表的なoperationで固定しています。

## 使い方

### Pythonから

```python
from policy_engine import evaluate

decision = evaluate({"operation": "project.save", "attributes": {"mode": "overwrite"}})
print(decision.decision)   # "DENY"
print(decision.rule_id)    # "PROJECT_OVERWRITE"
```

### CLIから

Pythonから直接importできない呼び出し元(シェルスクリプト等)向けの
フォールバックです。`during.md`の通り、importできる場合は上の
Pythonの方を優先してください。

```bash
echo '{"operation": "read.tempo"}' | python3 -m policy_engine.cli
# {"decision": "ALLOW", "rule_id": "READ_ONLY", "reason": "..."}
# 終了コード 0

python3 -m policy_engine.cli '{"operation": "project.save", "attributes": {"mode": "overwrite"}}'
# {"decision": "DENY", "rule_id": "PROJECT_OVERWRITE", "reason": "..."}
# 終了コード 2
```

デフォルト出力は`decision`/`rule_id`/`reason`(該当する場合のみ
`capability_available`)に絞った最小限のJSONです(1行、コンパクト)。
Agentが操作ごとに毎回読むテキストなので、判断に不要な入力の
エコーバック(`operation`/`target`/`attributes`)は含めません。

- `--full`: 完全な`Decision`(`operation`/`target`/`attributes`含む)を出力。監査・デバッグ用
- `--pretty`: インデント付きで出力(人間が読む場合)

終了コード: `ALLOW`=0, `ASK`=1, `DENY`=2(`--full`/`--pretty`の有無に関わらず不変)。

## やらないこと(Non-goals)

- 自然言語の意味解釈をこのモジュール自体に持ち込むこと
  (Action Schemaへの正規化は呼び出し側の責務)
- `deny_check.py`を置き換えること(役割が違う。両方残す)
- 実機DAWでの動作保証(Policy Engineはロジックのみ。DAW側の実際の
  操作結果を保証するものではありません)

## 動作確認

`tests/test_policy_engine.py`(40テスト)で以下を検証済みです。
CLI自体(デフォルト出力の最小化・`--full`/`--pretty`/`--plan`・終了
コード)は`tests/test_cli.py`(15テスト)で別途検証しています。Issue #16の
Token/UX最適化(Step 1-3)がALLOW/ASK/DENYの判定結果やルールの並び順を
変えていないことは`tests/test_security_regression.py`(12テスト)で
横断的に固定しています。`evaluate_plan`/`plan_is_clear`/
`worst_decision`(Issue #26)は`tests/test_evaluate_plan.py`
(14テスト)で検証しています。`daw_state`(Issue #25)が判定結果を
変えないことは`tests/test_daw_state.py`(9テスト)で固定しています。

- `policy/deny.txt`の10ルールそれぞれに対応するDENYケース
- `policy/allow.txt`の許可ケース(ALLOW)
- Save As未確認・非allowlistホストへの承認済みfetch等のASKケース
- 未知operation・不正なAction構造のfail-closed(DENY)動作
- ルールの`source_text`が`policy/deny.txt`/`policy/allow.txt`の実際の
  行と一致していること、deny.txtの全行がいずれかのルールでカバー
  されていること
- `CAPABILITY_MATRIX`が`mcp-*/*/server.py`の実装と一致していること
- `capability_available`が`decision`を変えないこと(read.\*は`daw`の
  値に関わらず常にALLOW)、かつ`CAPABILITY_MATRIX`と一致すること
  (Ardourの`read.tempo`が`ALLOW`かつ`capability_available: false`
  になる、という確認済みのギャップを固定するregression testを含む)

実機DAWでの検証は対象外です(`mcp-reaper`/`mcp-ableton`/`mcp-ardour`
自体の動作確認状況は各READMEを参照してください)。
