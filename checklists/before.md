# before.md

Purpose: questions an agent asks itself before touching a DAW session.
Answer each with Yes/No before acting.

- 使用中のDAWは何か。対応する `adapters/<name>.md` を読んだか
  (Which DAW is open? Have you read its `adapters/<name>.md`? Find the
  filename in `adapters/README.md` if unsure. Yes/No — if No, read it
  before anything else in this list)
- 開いているプロジェクト名は何か (What is the name of the open project?)
- ユーザーは保存を依頼したか (Did the user ask to save, this turn? Yes/No)
- 依頼は「作曲」か「既存曲の再現」か「編曲」か
  (Is the request: compose new / reproduce an existing song / arrange existing material?)
- MCP/OSC は使えるか (Is an MCP/OSC adapter available and configured?
  Yes/No — if No, do not ask the user to install or configure one; just
  proceed with Computer Use / manual read-only inspection instead)
- ネット取得の許可は今ターンの文章にあるか
  (Did the user explicitly approve a network fetch in this turn's message? Yes/No)

If the request is "reproduce an existing song by fetching it from the
internet," switch to composing a new part in a similar style instead.
Do not fetch an existing song's MIDI without explicit, in-turn approval
and a host on `policy/license-allowlist.txt`.

If you can already express your intended actions for this task as a
list of Action JSON (see `checklists/during.md`), you can optionally
check the whole plan up front instead of finding out step-by-step:

```python
from policy_engine import evaluate_plan, plan_is_clear, worst_decision
decisions = evaluate_plan([action1, action2, ...])
```

or `python3 -m policy_engine.cli --plan` with a JSON array on stdin.
This is a stateless batch of independent `evaluate()` calls — it does
not reason about dependencies between steps (see
`policy_engine/README.md`). You still run `checklists/during.md`'s
per-operation check before each actual action; this is a convenience
for surfacing an obvious DENY/ASK earlier, not a replacement for it.
