# before.md

Purpose: questions an agent asks itself before touching a DAW session.
Answer each with Yes/No before acting.

- 開いているプロジェクト名は何か (What is the name of the open project?)
- ユーザーは保存を依頼したか (Did the user ask to save, this turn? Yes/No)
- 依頼は「作曲」か「既存曲の再現」か「編曲」か
  (Is the request: compose new / reproduce an existing song / arrange existing material?)
- MCP/OSC は使えるか (Is an MCP/OSC adapter available and configured? Yes/No)
- ネット取得の許可は今ターンの文章にあるか
  (Did the user explicitly approve a network fetch in this turn's message? Yes/No)

If the request is "reproduce an existing song by fetching it from the
internet," switch to composing a new part in a similar style instead.
Do not fetch an existing song's MIDI without explicit, in-turn approval
and a host on `policy/license-allowlist.txt`.
