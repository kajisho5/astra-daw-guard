# bad-run-autosave.md

## 何が悪いか (最初に結論)

エージェントが、ユーザーから保存の依頼を受けていないのに、あるいは
「保存して」の依頼を「上書き保存」と解釈し、開いていたプロジェクトファイルを
そのまま上書き保存した。既存プロジェクトが復旧不能な形で書き換わる
リスクがあり、`policy/deny.txt` に違反する。

## 架空の悪いログ（悪い例）

ユーザー発言:

> ドラムトラックだけ聞かせて。

エージェントの行動（悪い例）:

- 依頼にない保存を判断で実行し、開いているプロジェクトファイルを上書き保存した
- Saved 欄を確認せずに作業を終えた

## 違反したルール

- `Do not overwrite the open DAW project. Save As only, and only if the user asked.`

## Policy Engineに通していれば防げていた

保存を実行する前に `checklists/during.md` の手順で Policy Engine に
通していれば、この時点でDENYが返っていた:

```bash
$ echo '{"operation": "project.save", "attributes": {"mode": "overwrite"}}' | python3 -m policy_engine.cli
{
  "decision": "DENY",
  "rule_id": "PROJECT_OVERWRITE",
  "reason": "Overwriting the currently open project is never allowed, regardless of user request.",
  ...
}
```

`reason`にある通り、**ユーザーが保存を依頼していたとしても**
`mode: overwrite`である限りDENYになる（`policy/deny.txt`にオーバーライドの
例外は無いため）。正しくは`mode: "save_as"`にして
`user_requested_this_turn`を確認する。

## 正しい行動（Save As に変える）

- 保存の依頼が無ければ、そもそも保存しない
- ユーザーが明示的に保存を依頼した場合のみ、タイムスタンプ付きの新規
  ファイル名で "Save As" する

```text
Saved: no
```

または、保存依頼があった場合:

```text
Saved: saved-as project_2026-09-06_1830.als
```
