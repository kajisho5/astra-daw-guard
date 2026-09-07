"""Policy rules for astra-daw-guard's Policy Engine.

Each Rule is a pure predicate over a structured Action — no keyword
matching, no regex over free text, no natural-language interpretation.
Rules are checked in the order they appear in RULES; the first one whose
predicate matches wins. Turning natural language into an Action is the
calling agent's job (see schema.py); this module never sees free text.

Every rule that enforces a policy/deny.txt or policy/allow.txt line
carries that exact line as `source_text`. tests/test_policy_engine.py's
SourceSyncTests checks these stay byte-for-byte in sync with the policy
files and that every deny.txt line is covered by at least one rule —
that is what stops this module from silently drifting away from the
human-readable policy it's supposed to enforce.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .capabilities import mcp_supports
from .schema import Action

ALLOW = "ALLOW"
ASK = "ASK"
DENY = "DENY"


@dataclass(frozen=True)
class Decision:
    decision: str
    rule_id: str
    reason: str
    operation: str
    target: str
    attributes: dict[str, Any]
    # Whether this repo's MCP/OSC adapter actually implements this read
    # for the DAW named in attributes["daw"] (see capabilities.py).
    # None means "not applicable / not checked" (non-read operation, or
    # no "daw" attribute given) — it is never a substitute for
    # `decision`. This is deliberately separate from ALLOW/ASK/DENY:
    # policy never forbids reading state, so a read.* Action is ALLOW
    # regardless of whether a given DAW's adapter can actually do it.
    # capability_available=False means "this specific MCP tool doesn't
    # exist for this DAW" (a capability gap the caller must fall back
    # from, per SKILL.md's priority order) — it does NOT mean "denied by
    # policy". Conflating the two would make an agent treat a missing
    # MCP tool as a policy violation, or a policy DENY as something a
    # different tool might route around.
    capability_available: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "operation": self.operation,
            "target": self.target,
            "attributes": self.attributes,
            "capability_available": self.capability_available,
        }


@dataclass(frozen=True)
class Rule:
    rule_id: str
    decision: str
    reason: str
    predicate: Callable[[Action], bool]
    source_text: Optional[str] = None

    def evaluate(self, action: Action) -> Optional[Decision]:
        if self.predicate(action):
            return Decision(
                decision=self.decision,
                rule_id=self.rule_id,
                reason=self.reason,
                operation=action.operation,
                target=action.target,
                attributes=action.attributes,
            )
        return None


# Known MIDI dump sites named explicitly in policy/deny.txt, plus one
# other well-known one (freemidi.org) covered by "or unnamed MIDI dump
# sites" — this list can grow, but it is not exhaustive by design: a
# caller proposing a fetch from a site NOT on this list still has to
# clear MIDI_FETCH_NOT_ALLOWLISTED / MIDI_FETCH_ALLOWED below, so an
# unlisted dump site cannot slip through as ALLOW.
_DUMP_SITE_HOSTS = {"bitmidi.com", "midiworld.com", "freemidi.org"}

# Mirrors policy/license-allowlist.txt's non-comment, non-file:// hosts.
_LICENSE_ALLOWLIST_HOSTS = {"mutopiaproject.org", "freesound.org"}


def _host_is_dump_site(host: object) -> bool:
    # `host` comes straight from an Action's attributes (see schema.py),
    # so it can be any JSON type, not just a string -- e.g. an Action
    # with `{"host": 123}`. str() coercion keeps this a normal (if
    # non-matching) comparison instead of an AttributeError, matching
    # this engine's fail-closed promise (evaluate() must never raise).
    host = str(host or "").lower()
    return any(host == h or host.endswith("." + h) for h in _DUMP_SITE_HOSTS)


def _host_on_license_allowlist(host: object) -> bool:
    host = str(host or "").lower()
    if host == "file":
        return True
    return any(host == h or host.endswith("." + h) for h in _LICENSE_ALLOWLIST_HOSTS)


RULES: list[Rule] = [
    # ------------------------------------------------------------------
    # midi.fetch — policy/deny.txt lines 1-3, policy/allow.txt line 6
    # ------------------------------------------------------------------
    Rule(
        rule_id="MIDI_DUMP_SITE",
        decision=DENY,
        reason=(
            "Host is a known MIDI dump site (BitMidi/MIDIWorld/FreeMIDI-"
            "style); never allowed, regardless of approval."
        ),
        source_text="Do not scrape BitMidi, MIDIWorld, Free MIDI, or unnamed MIDI dump sites.",
        predicate=lambda a: a.operation == "midi.fetch" and _host_is_dump_site(a.attr("host", "")),
    ),
    Rule(
        rule_id="MIDI_FETCH_NO_APPROVAL",
        decision=DENY,
        reason="MIDI/sample fetch without explicit user approval in this turn.",
        source_text="Do not download .mid .midi .kar files without explicit user approval in this turn.",
        predicate=lambda a: a.operation == "midi.fetch" and not a.attr("user_approved_this_turn", False),
    ),
    Rule(
        rule_id="MIDI_FETCH_NOT_ALLOWLISTED",
        decision=ASK,
        reason=(
            "Host is not on policy/license-allowlist.txt; confirm the "
            "license/source before fetching."
        ),
        source_text='Do not treat "public domain" as proven unless the URL is on license-allowlist.txt.',
        predicate=lambda a: (
            a.operation == "midi.fetch"
            and a.attr("user_approved_this_turn", False)
            and not _host_on_license_allowlist(a.attr("host", ""))
        ),
    ),
    Rule(
        rule_id="MIDI_FETCH_ALLOWED",
        decision=ALLOW,
        reason="User approved this turn and host is on policy/license-allowlist.txt.",
        source_text="Fetch a file only when: user named the URL in this turn AND the host is on license-allowlist.txt.",
        predicate=lambda a: (
            a.operation == "midi.fetch"
            and a.attr("user_approved_this_turn", False)
            and _host_on_license_allowlist(a.attr("host", ""))
        ),
    ),
    # ------------------------------------------------------------------
    # project.save — policy/deny.txt line 4, policy/allow.txt line 4
    # ------------------------------------------------------------------
    Rule(
        rule_id="PROJECT_OVERWRITE",
        decision=DENY,
        reason="Overwriting the currently open project is never allowed, regardless of user request.",
        source_text="Do not overwrite the open DAW project. Save As only, and only if the user asked.",
        predicate=lambda a: a.operation == "project.save" and a.attr("mode") == "overwrite",
    ),
    Rule(
        rule_id="SAVE_AS_APPROVED",
        decision=ALLOW,
        reason="Save As to a new filename, explicitly requested by the user this turn.",
        source_text="Save As to a new filename that includes a timestamp if the user asked to save.",
        predicate=lambda a: (
            a.operation == "project.save"
            and a.attr("mode") == "save_as"
            and a.attr("user_requested_this_turn", False)
        ),
    ),
    Rule(
        rule_id="SAVE_AS_UNCONFIRMED",
        decision=ASK,
        reason=(
            "Save As was proposed without a recorded user request this "
            "turn; confirm before writing a new file."
        ),
        source_text="Save As to a new filename that includes a timestamp if the user asked to save.",
        predicate=lambda a: a.operation == "project.save" and a.attr("mode") == "save_as",
    ),
    # ------------------------------------------------------------------
    # track.mix_sources — policy/deny.txt line 5
    # ------------------------------------------------------------------
    Rule(
        rule_id="UNLABELED_MIXED_SOURCES",
        decision=DENY,
        reason="Generated and imported material combined on one track without labeling the source of each part.",
        source_text="Do not mix generated MIDI and imported material on one track without labeling source.",
        predicate=lambda a: a.operation == "track.mix_sources" and not a.attr("labeled", False),
    ),
    Rule(
        rule_id="LABELED_MIXED_SOURCES",
        decision=ALLOW,
        reason="Sources are labeled.",
        predicate=lambda a: a.operation == "track.mix_sources" and a.attr("labeled", False),
    ),
    # ------------------------------------------------------------------
    # daw.window_change / daw.display_settings_change — deny.txt 6-7
    # ------------------------------------------------------------------
    Rule(
        rule_id="WINDOW_MANIPULATION",
        decision=DENY,
        reason="Moving, minimizing, or retiling DAW windows is never allowed.",
        source_text="Do not minimize, move, or retile DAW windows.",
        predicate=lambda a: a.operation == "daw.window_change",
    ),
    Rule(
        rule_id="DISPLAY_SETTINGS_CHANGE",
        decision=DENY,
        reason="Changing display zoom, color theme, or key bindings is never allowed.",
        source_text="Do not change display zoom, color theme, or key bindings.",
        predicate=lambda a: a.operation == "daw.display_settings_change",
    ),
    # ------------------------------------------------------------------
    # daw.plugin_install / daw.license_dialog_respond — deny.txt line 8
    # ------------------------------------------------------------------
    Rule(
        rule_id="PLUGIN_OR_LICENSE_DIALOG",
        decision=DENY,
        reason="Installing plugins/content packs or responding to license dialogs is never allowed.",
        source_text="Do not install plugins, pack content, or accept license dialogs.",
        predicate=lambda a: a.operation in ("daw.plugin_install", "daw.license_dialog_respond"),
    ),
    # ------------------------------------------------------------------
    # data.send_external — deny.txt line 9
    # ------------------------------------------------------------------
    Rule(
        rule_id="SEND_UNPUBLISHED_EXTERNALLY",
        decision=DENY,
        reason=(
            "Sending the project/stems/unpublished songs anywhere other "
            "than the model API already in use is never allowed."
        ),
        source_text=(
            "Do not send the user's project file, stems, or unpublished "
            "songs to a remote URL except the model API already in use."
        ),
        predicate=lambda a: a.operation == "data.send_external" and not a.attr("is_model_api_in_use", False),
    ),
    Rule(
        rule_id="SEND_TO_MODEL_API",
        decision=ALLOW,
        reason="Destination is the model API already in use for this session.",
        predicate=lambda a: a.operation == "data.send_external" and a.attr("is_model_api_in_use", False),
    ),
    # ------------------------------------------------------------------
    # computer_use.invoke — deny.txt line 10, capability-aware
    # ------------------------------------------------------------------
    Rule(
        rule_id="COMPUTER_USE_WHEN_MCP_AVAILABLE",
        decision=DENY,
        reason="An MCP/OSC adapter can already perform this operation for this DAW; Computer Use is not allowed.",
        source_text="Do not run Computer Use if an MCP/OSC adapter is available for the same action.",
        predicate=lambda a: (
            a.operation == "computer_use.invoke"
            and mcp_supports(a.attr("daw", ""), a.attr("capability", ""))
        ),
    ),
    Rule(
        rule_id="COMPUTER_USE_NO_MCP",
        decision=ALLOW,
        reason="No MCP/OSC adapter covers this capability for this DAW; Computer Use is the documented last resort.",
        predicate=lambda a: (
            a.operation == "computer_use.invoke"
            and not mcp_supports(a.attr("daw", ""), a.attr("capability", ""))
        ),
    ),
    # ------------------------------------------------------------------
    # read.* — always safe, policy/allow.txt line 1
    # ------------------------------------------------------------------
    Rule(
        rule_id="READ_ONLY",
        decision=ALLOW,
        reason="Read-only inspection carries no side effects.",
        source_text="Read the current set: tempo, time signature, track list, clip names, devices.",
        predicate=lambda a: a.operation.startswith("read."),
    ),
    # ------------------------------------------------------------------
    # midi.write / track.create — policy/allow.txt lines 2-3
    # ------------------------------------------------------------------
    Rule(
        rule_id="GENERATED_MIDI_INTO_GEN_TRACK",
        decision=ALLOW,
        reason="Generated MIDI written into a new GEN--prefixed track.",
        source_text="Write MIDI only into a new track named with prefix GEN-.",
        predicate=lambda a: (
            a.operation == "midi.write"
            and a.attr("source") == "generated"
            and str(a.attr("track", "")).startswith("GEN-")
        ),
    ),
    Rule(
        rule_id="GENERATED_MIDI_INTO_OTHER_TRACK",
        decision=DENY,
        reason="Generated MIDI must go into a new GEN--prefixed track, not an existing/other one.",
        source_text="Write MIDI only into a new track named with prefix GEN-.",
        predicate=lambda a: a.operation == "midi.write" and a.attr("source") == "generated",
    ),
    Rule(
        rule_id="CREATE_GEN_TRACK",
        decision=ALLOW,
        reason="New track created for generated content, correctly prefixed.",
        source_text="Write MIDI only into a new track named with prefix GEN-.",
        predicate=lambda a: a.operation == "track.create" and str(a.attr("name", "")).startswith("GEN-"),
    ),
    Rule(
        rule_id="CREATE_OTHER_TRACK",
        decision=ASK,
        reason="Track creation unrelated to generated content is not covered by policy/allow.txt; confirm.",
        predicate=lambda a: a.operation == "track.create",
    ),
    # ------------------------------------------------------------------
    # track.mixer_change / device.param_change — policy/allow.txt (Issue #46)
    # ------------------------------------------------------------------
    Rule(
        rule_id="MIXER_CHANGE_ON_GEN_TRACK",
        decision=ALLOW,
        reason="Mixer change on a track this agent created for generated content.",
        source_text="Change mixer settings (volume, pan, mute, or solo) on a track named with prefix GEN- without asking again.",
        predicate=lambda a: a.operation == "track.mixer_change" and str(a.attr("track", "")).startswith("GEN-"),
    ),
    Rule(
        rule_id="MIXER_CHANGE_ON_OTHER_TRACK",
        decision=ASK,
        reason="Mixer change on a track not created by this agent is not covered by policy/allow.txt; confirm.",
        predicate=lambda a: a.operation == "track.mixer_change",
    ),
    Rule(
        rule_id="DEVICE_PARAM_CHANGE_ON_GEN_TRACK",
        decision=ALLOW,
        reason="Device parameter change on a track this agent created for generated content.",
        source_text="Change device parameters on a track named with prefix GEN- without asking again.",
        predicate=lambda a: a.operation == "device.param_change" and str(a.attr("track", "")).startswith("GEN-"),
    ),
    Rule(
        rule_id="DEVICE_PARAM_CHANGE_ON_OTHER_TRACK",
        decision=ASK,
        reason="Device parameter change on a track not created by this agent is not covered by policy/allow.txt; confirm.",
        predicate=lambda a: a.operation == "device.param_change",
    ),
    # ------------------------------------------------------------------
    # transport.control — policy/allow.txt (Issue #46)
    # ------------------------------------------------------------------
    Rule(
        rule_id="TRANSPORT_CONTROL",
        decision=ALLOW,
        reason="Starting/stopping playback changes no project data.",
        source_text="Start or stop playback at any time.",
        predicate=lambda a: a.operation == "transport.control",
    ),
    # ------------------------------------------------------------------
    # tempo.change — policy/allow.txt (Issue #46)
    # ------------------------------------------------------------------
    Rule(
        rule_id="TEMPO_CHANGE_APPROVED",
        decision=ALLOW,
        reason="Tempo change explicitly requested by the user this turn.",
        source_text="Change tempo (BPM) if the user asked in this turn.",
        predicate=lambda a: a.operation == "tempo.change" and a.attr("user_requested_this_turn", False),
    ),
    Rule(
        rule_id="TEMPO_CHANGE_UNCONFIRMED",
        decision=ASK,
        reason=(
            "Tempo change was proposed without a recorded user request this turn; "
            "confirm before changing project-wide timing."
        ),
        source_text="Change tempo (BPM) if the user asked in this turn.",
        predicate=lambda a: a.operation == "tempo.change",
    ),
]
