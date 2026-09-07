# astra-daw-guard

[![checks](https://github.com/kajisho5/astra-daw-guard/actions/workflows/checks.yml/badge.svg)](https://github.com/kajisho5/astra-daw-guard/actions/workflows/checks.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇯🇵 **日本語版: [README.ja.md](README.ja.md)**

A **DAW safety / policy layer for AI agents**: a set of prohibitions,
permissions, and a post-run report format that any AI agent (GPT-6
Astra, Codex, Claude Code, etc.) should follow while operating a DAW.
It is not a collection of MCP servers for one specific DAW, and it is
not limited to any single DAW. Actually operating the DAW is left to
whatever MCP / OSC / Computer Use tooling already exists — this
repository is the "what's allowed, what isn't" layer that sits around
that.

This is written for agents that can genuinely act on a real desktop —
including ones with live screen perception and direct mouse/keyboard
control (Computer Use), not just MCP/OSC calls. That is exactly why
`SKILL.md`'s priority order matters: prefer an MCP/OSC adapter whenever
one covers the action, and drop to Computer Use only when nothing else
can do it. Computer Use means re-capturing and re-reasoning over a
screenshot every turn — real, recurring token cost and latency, and far
more fragile than one structured call — so this ordering isn't
red tape, it is the cheaper and more reliable path whenever it's
available.

Enforcement is two-layered. `SKILL.md` is a natural-language layer an
agent reads and follows (also readable by humans), and `policy_engine/`
is a **machine-readable ALLOW/ASK/DENY decision engine** (structured
data only, fail-closed). `checklists/during.md` documents the concrete
procedure for calling this engine per operation, and `enforcement/`
provides a reference implementation that gates actual tool execution
behind this decision. This is **not a live connection into Astra's own
running Agent runtime** — this repository has no running Agent loop of
its own, so how the caller (the real Agent execution environment) uses
these pieces is up to it. This does not "guarantee safety" — it
provides a layer that can **decide and audit mechanically**.

## What it prevents

- Fetching MIDI / samples from the internet without permission
- Mixing generated material with existing material without disclosing sources
- Silently overwriting a project file
- Breaking a DAW's window or layout via Computer Use

## What it does not do

- Build a new DAW or LiveAPI bridge
- Train an auto-composition model
- Implement Computer Use screen-click automation

## Supported DAWs

The guardrail itself (`SKILL.md` / `policy/`) works identically across
every DAW. In addition, some DAWs ship with an MCP that can safely
fetch tempo and track lists. Reaper and Ableton Live also have write
tools — track creation, MIDI writing, mixer control (volume/pan/mute/
solo), device parameter changes, transport control, tempo changes, and
(Reaper only) Save As; Ardour's MCP remains read-only. Ableton Live has
no save/export tool and no Instrument Rack chain-switching tool,
because AbletonOSC (the bridge it goes through) has no OSC address for
either capability at all — confirmed against AbletonOSC's own source,
not assumed. Every write tool is gated through the Policy Engine and
Enforcement Boundary described above — see `mcp-reaper/README.md` /
`mcp-ableton/README.md` for exactly what each tool does and does not
do.

| DAW | MCP | Write tools | Transport | Verified against real hardware |
|---|---|---|---|---|
| Reaper | ✅ `mcp-reaper/` | ✅ create track / write MIDI / Save As | [reapy](https://github.com/RomeoDespres/reapy) (external Python wrapper) | Not verified (logic-only verification) |
| Ableton Live | ✅ `mcp-ableton/` | ✅ create track / write MIDI / mixer / device params / transport / tempo | [AbletonOSC](https://github.com/ideoforms/AbletonOSC) (Remote Script) | Not verified (verified against a fake server) |
| Ardour | ✅ `mcp-ardour/` | Read-only | Ardour's own built-in OSC surface | Not verified (verified against a fake server) |
| Bitwig Studio | Guardrail only (no MCP) | — | Reference: [DrivenByMoss](https://github.com/git-moss/DrivenByMoss)'s OSC support (community-made, use at your own risk) | Not investigated / not implemented (`adapters/bitwig.md`) |
| FL Studio | Guardrail only (no MCP) | — | Reference: [`flstudio-mcp`](https://github.com/rosasynthesiz/flstudio-mcp) (community-made, use at your own risk) | Not investigated / not implemented (`adapters/flstudio.md`) |
| Cubase | Guardrail only (no MCP) | — | — | Investigated: no readable surface due to platform constraints (`adapters/cubase.md`) |
| Pro Tools | Guardrail only (no MCP) | — | — | Investigated: EUCON is Avid-partner-only, not generally available (`adapters/protools.md`) |
| Logic Pro | Guardrail only (no MCP) | — | — | Investigated: no readable API/OSC exists (`adapters/logicpro.md`) |
| Studio One | Guardrail only (no MCP) | — | — | Investigated: no public API/OSC exists (`adapters/studioone.md`) |
| Cakewalk | Guardrail only (no MCP) | — | — | Investigated: no public API/OSC exists (`adapters/cakewalk.md`) |
| GarageBand | Guardrail only (no MCP) | — | — | No scripting capability exists at all (`adapters/garageband.md`) |

The guardrail itself works the same on every DAW. MCPs currently exist
for three DAWs — Reaper, Ableton Live, and Ardour — and none of the
three has been verified against real hardware (logic has been verified
against fake servers). Reaper's and Ableton Live's MCPs also have
write tools now (Issues #44, #46); Ardour's remains read-only. The remaining
DAWs were each investigated individually as of 2026-09-07, with the
results recorded in `adapters/*.md`. Nothing here is exaggerated:
where investigation found "this doesn't exist," that's stated plainly.

See `mcp-reaper/README.md` / `mcp-ableton/README.md` /
`mcp-ardour/README.md` / `adapters/*.md` for setup details on each
adapter. All three automate what can be automated via
`python3 install.py`, but changes on the DAW's own side (e.g. picking
a Control Surface in Ableton's Preferences) can't be done from outside
the app and remain manual. If you don't need any MCP setup, the
guardrail itself (`SKILL.md` / `policy/`) works on its own.

## Handing this to Astra or another external agent

If you just want to hand over this repository's URL and have an agent
follow it, give it an instruction like this (copy-paste ready):

```text
Read this GitHub repository and follow the rules written in it:
https://github.com/kajisho5/astra-daw-guard

In particular, make sure to:
1. Read AGENTS.md and SKILL.md
2. Never break a prohibition listed in policy/deny.txt
3. Report your work afterward in the format in checklists/after.md
```

In case the agent can't navigate the repository on its own, it's
worth also handing it direct links to the key files:

- The rules themselves: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/SKILL.md
- Top-priority prohibitions: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/policy/deny.txt
- Permissions: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/policy/allow.txt
- Report format: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/checklists/after.md

Just in case, here are all 10 minimum prohibitions from
`policy/deny.txt` reproduced here as well (the canonical source is
`policy/deny.txt`; if this ever disagrees with it, `policy/deny.txt`
wins):

- Do not fetch `.mid` / `.midi` / `.kar` files from the internet
  unless the user has explicitly approved it in the current turn
- Do not fetch from MIDI-dump sites of unknown provenance such as
  BitMidi, MIDIWorld, or Free MIDI
- Don't trust a "public domain" label alone — if the host isn't on
  `policy/license-allowlist.txt`, confirm before fetching
- Don't overwrite an open project file (if saving, always Save As,
  and only when the user asked for a save)
- Don't mix generated MIDI with externally-fetched material into the
  same track without disclosing the source
- Don't change the DAW window's position or size
- Don't change display scale, color theme, or key bindings
- Don't install plugins or respond to license dialogs
- Don't send project files, stems, or unreleased music to anything
  other than the model API used in this session
- Don't use Computer Use when the same operation can be done via
  MCP/OSC

See `policy/deny.txt` for the full text and `SKILL.md` for the
procedure.

## Using it with Claude Code / Codex

With this repository open:

1. Read AGENTS.md and SKILL.md
2. Don't perform an operation covered by policy/deny.txt
3. Report your work afterward in the format in checklists/after.md

## Current status

The latest version is `v0.9.3`. Both the Policy Engine
(`policy_engine/`) and the Enforcement Boundary (`enforcement/`) are
implemented, with all 182 tests passing. Reaper and Ableton Live now
have a set of Policy-Engine-gated write tools (Issues #44, #46); see
`CHANGELOG.md` for the full development history, and `ROADMAP.md` for
the current assessment and what's next.

Honest limitations (not exaggerated): none of the following exist
inside this repository — verification against real DAW hardware, or a
live connection into an actual Astra Agent runtime. See `ROADMAP.md`
for the reasoning and details.

## Contributing

If you want to work on this repository itself, read `CONTRIBUTING.md`
first. In particular, any PR touching `policy_engine/` or
`enforcement/` requires an independent review (e.g. the `code-review`
skill) before merging.

## License

[MIT License](LICENSE)
