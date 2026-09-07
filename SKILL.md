# astra-daw-guard SKILL

Purpose: guardrails for any agent (Astra, Codex, Claude Code, etc.) that
operates a DAW (Ableton Live, Reaper, Ardour, Bitwig, Cubase, FL Studio,
Pro Tools, Logic Pro, Studio One, Cakewalk, GarageBand, or any other) on
a user's machine. This document is self-contained — an agent that reads
only this file can operate safely.

Rule text is in English so it is read consistently by different agents.
Japanese notes are added where useful for the human operator.

## 1. いつ使うか (When to use this)

Use this skill whenever an agent is about to:

- Read or change state in a running DAW (tracks, clips, MIDI, tempo)
- Fetch a MIDI file, sample, or preset from the internet for use in a DAW project
- Save, save-as, or export a DAW project
- Use Computer Use (screen/mouse/keyboard control) to interact with a DAW window

## 2. 使わないとき (When NOT to use this)

- The task has nothing to do with a DAW or its project files
- The agent is only discussing music theory, mixing advice, or reading
  documentation with no live DAW session involved
- The agent is writing standalone audio-processing code unrelated to an
  open DAW project

## 3. 優先順位 (Priority order)

Always prefer, in this order:

1. An existing MCP or OSC adapter already configured for the DAW
2. Read-only inspection (tempo, tracks, clips, devices) with no adapter
   write action
3. Computer Use — only when no MCP/OSC adapter can perform the same
   action, and never for actions listed in `policy/deny.txt`

Never use Computer Use to do something an MCP/OSC adapter could already do.
**Why this order, not just "policy for policy's sake":** Computer Use
means capturing a screenshot and reasoning over pixels every turn — for
a multimodal agent with real desktop/screen control (e.g. Astra-style
agents), that is real, recurring token cost and added latency per
action, on top of being far more fragile (a moved window, a different
zoom level, or a redrawn UI breaks it) than a single structured MCP/OSC
call. Preferring MCP/OSC whenever it covers the action is not just
safer, it is cheaper and more reliable every single time it's
available.

**If no MCP/OSC adapter is already configured and running, treat it as
unavailable and drop straight to Computer Use (or manual read-only
inspection) for this task — do not stop the task to walk the user
through installing or configuring one.** This repo's `mcp-*/install.py`
scripts and adapter setup steps are opt-in tools the user can run on
their own time, never a blocker you impose mid-task. Only mention that
an MCP adapter exists if the user asks how to get faster/more reliable
reads, or if the task is impossible without one (e.g. reading state a
GUI genuinely cannot expose) — and even then, offer it as an option
rather than a requirement.

## 4. 禁止 (Deny)

Full list: `policy/deny.txt`. Summary (the file is authoritative):

- No fetching `.mid` / `.midi` / `.kar` files without explicit user
  approval given in the current turn
- No scraping BitMidi, MIDIWorld, Free MIDI, or unnamed MIDI dump sites —
  ever, regardless of approval
- No treating "public domain" as proven unless the source host is on
  `policy/license-allowlist.txt`
- No overwriting the currently open project file — Save As only, and only
  if the user asked to save
- No mixing generated MIDI and imported/fetched material on one track
  without labeling the source of each part
- No moving, minimizing, or retiling DAW windows
- No changing display zoom, color theme, or key bindings
- No installing plugins, importing content packs, or accepting license
  dialogs on the user's behalf
- No sending the user's project file, stems, or unpublished songs to any
  remote endpoint other than the model API already in use for this session
- No using Computer Use when an MCP/OSC adapter can do the same action

**ネットから MIDI を無断で取得することは禁止。** これは本スキルの最重要ルール。

## 5. 許可 (Allow)

Full list: `policy/allow.txt`. Summary:

- Read current project state: tempo, time signature, track list, clip
  names, devices
- Generate new MIDI from scratch when the user asked to compose
- Write generated MIDI only into a new track prefixed `GEN-`
- Save As to a new, timestamped filename, only if the user asked to save
- Use MCP/OSC/ReaScript if already configured for this session
- Fetch a file only if the user named the exact URL in this turn AND the
  host appears in `policy/license-allowlist.txt`
- Report sources after every run using the format in `checklists/after.md`

## 6. 実行プロトコル (Execution protocol: before → during → after)

- **Before**: identify which DAW is open, look it up in
  `adapters/README.md`, and read that DAW's `adapters/<name>.md` —
  **before** doing anything DAW-specific. It tells you what read path
  (if any) exists for that DAW and what Computer Use must never touch
  there. Then run through `checklists/before.md`. If the request is
  "fetch and reproduce an existing song from the internet," switch to
  composing a new part instead — do not fetch the existing song's MIDI
  without approval.
- **During**: for every individual operation, run through
  `checklists/during.md`. If an action matches `policy/deny.txt`, do not
  perform it — record it under "Denied actions" instead. **If
  `policy_engine/` is available, prefer it over your own natural-language
  reading of `policy/deny.txt`**: express the operation as an Action
  (see `policy_engine/README.md`) and check `evaluate(action).decision`
  — ALLOW means proceed, ASK means confirm with the user first, DENY
  means do not perform it (record it under "Denied actions"). This is
  authoritative, not a heuristic. If you can call code, prefer
  `enforcement.enforce()`/`@guarded` (`enforcement/README.md`) so a
  DENY blocks the tool call itself, not just your own judgment call.
  If `policy_engine/` isn't available,
  fall back to reading `policy/deny.txt` yourself, optionally sanity-
  checked with `tools/deny_check.py` (a non-authoritative keyword
  heuristic — see its own docstring for why it's not a substitute for
  `policy_engine/`). If you fetched a file, record it with
  `tools/record_source.py` (see `sources/README.md`). For consistent,
  bilingual wording for an ASK confirmation or a DENY refusal, look up
  `decision.rule_id` in `tools/decision_message.py` (`--list` shows the
  covered ids; falls back to `decision.reason` if not yet cataloged).
- **After**: fill out the report in `checklists/after.md` using the format
  in Section 7 below, every time, even if nothing was changed.

## 7. 報告フォーマット (Report format — copy this)

```text
DAW:
Adapter used: mcp | osc | computer-use | none
Tracks changed:
MIDI added:
  - track:
    source: generated | user-provided | url
    url:
    license:
Saved: no | saved-as <filename>
Computer Use used: yes/no
Denied actions (what I refused):
Failures:
```

## 8. DAW別の注意 (Per-DAW notes — details in adapters/)

This repo ships its own MCP for three DAWs; for everything else, read
the matching `adapters/*.md` before touching that DAW — most have no
safe read path beyond Computer Use, and each file says exactly what
was checked and when.

- **Reaper** ✅ `mcp-reaper/` (via reapy) — read tools plus gated write
  tools (`create_track`, `write_generated_midi`, `save_project_as`) —
  `adapters/reaper.md`
- **Ableton Live** ✅ `mcp-ableton/` (via AbletonOSC) — read tools plus
  gated write tools (`create_track`, `write_generated_midi`) —
  `adapters/ableton.md`
- **Ardour** ✅ `mcp-ardour/` (via Ardour's built-in OSC) — read-only —
  `adapters/ardour.md`

Every write tool above still goes through the Policy Engine
(`policy_engine/`) via `enforcement.enforce()` — calling one is not a
way around any rule in this file or in `policy/deny.txt`.
- **Bitwig Studio**, **FL Studio**: a community bridge exists (see the
  adapter file) but this repo hasn't wrapped or verified it — use only
  its read-only surface if you rely on it — `adapters/bitwig.md`,
  `adapters/flstudio.md`
- **Cubase**, **Pro Tools**, **Logic Pro**, **Studio One**, **Cakewalk**,
  **GarageBand**: no safe read path beyond Computer Use was found as of
  this writing — see the matching `adapters/*.md` for what was checked
