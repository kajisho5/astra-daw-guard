# during.md

Purpose: the concrete, per-operation check an agent runs before *every*
individual action on the DAW session (not once per whole task — once
per action). This is where `policy_engine/` actually gets used, not
just referenced from `SKILL.md`.

## The procedure

For every operation you are about to perform:

1. Express it as an Action: `{"operation": "...", "target": "...", "attributes": {...}}`.
   See the table below for common cases, or `policy_engine/README.md`
   for the full operation catalog and every field's meaning.
2. Run it through the Policy Engine — this is the authoritative check,
   not `tools/deny_check.py`. **If your tool-calling code runs inside
   the same Python process that has this repo importable (this is the
   normal case for an agent driving MCP/OSC/`enforcement` tool calls),
   call it in-process:**

   ```python
   from policy_engine import evaluate
   decision = evaluate(action)
   ```

   This check runs once per operation, so its cost adds up over a whole
   session — an in-process call is a single function call (microseconds),
   while shelling out to the CLI below re-starts a Python interpreter
   every time (tens of milliseconds). Prefer in-process whenever you can.

   Only fall back to the CLI form when the caller genuinely cannot import
   this repo (e.g. checking from a shell script, or from a non-Python
   process):

   ```bash
   echo '<action json>' | python3 -m policy_engine.cli
   ```
3. Act on `decision`:
   - `ALLOW` → proceed.
   - `ASK` → stop and ask the user to confirm before proceeding. Do not
     treat silence or an unrelated reply as confirmation.
   - `DENY` → do not perform the action. Record the operation and the
     returned `reason` under "Denied actions" in `checklists/after.md`.

If your current environment cannot execute code against this repo (no
shell/Python access to it), fall back to reading `policy/deny.txt`
yourself, optionally sanity-checked with `tools/deny_check.py` — and
say so in your report's "Failures" line, since that fallback is a
heuristic, not the authoritative engine.

**This procedure is a recommendation you follow, not a technical
guarantee.** If your tool-calling code can import this repo, wrap the
actual tool function with `enforcement.enforce()` or `@enforcement.guarded`
(see `enforcement/README.md`) instead of just checking the decision and
proceeding by hand — that way a DENY means the tool function itself is
never invoked, not just a rule you're expected to have honored.

## Common operations → Action JSON

| You're about to... | Action |
|---|---|
| Read tempo / tracks / clips | `{"operation": "read.tempo"}` (or `read.tracks`, `read.clips`) |
| Save As, user asked this turn | `{"operation": "project.save", "attributes": {"mode": "save_as", "user_requested_this_turn": true}}` |
| Save As, not sure the user asked | `{"operation": "project.save", "attributes": {"mode": "save_as"}}` |
| Overwrite the open project | `{"operation": "project.save", "attributes": {"mode": "overwrite"}}` |
| Fetch a MIDI file the user named this turn | `{"operation": "midi.fetch", "attributes": {"host": "<host>", "user_approved_this_turn": true}}` |
| Write generated MIDI into a new track | `{"operation": "midi.write", "attributes": {"source": "generated", "track": "GEN-<name>"}}` |
| Create a new track for generated content | `{"operation": "track.create", "attributes": {"name": "GEN-<name>"}}` |
| Mix generated + imported material on one track | `{"operation": "track.mix_sources", "attributes": {"labeled": true}}` (or `false` if you have not labeled it) |
| Use Computer Use for some capability | `{"operation": "computer_use.invoke", "attributes": {"daw": "<daw>", "capability": "read.tempo"}}` |
| Move/resize/retile a DAW window | `{"operation": "daw.window_change", "attributes": {"action": "move"}}` |
| Install a plugin / accept a license dialog | `{"operation": "daw.plugin_install"}` |
| Send the project/stems/song elsewhere | `{"operation": "data.send_external", "attributes": {"is_model_api_in_use": false}}` |

Full operation catalog and the reasoning behind each rule:
`policy_engine/README.md`.

## Legacy self-check (kept for agents without code execution)

- 今から変えるオブジェクトは何か (What object am I about to change?)
- それは上書きか追加か (Is this an overwrite or an addition?)
- deny.txt に当たるか (Does this action match a rule in `policy/deny.txt`?
  Yes/No — use this only when you cannot run `policy_engine/`; it is a
  cross-check, not a substitute for the authoritative decision above.)
