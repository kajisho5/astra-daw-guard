"""MCP server exposing Ableton Live state via AbletonOSC, plus a small
set of write tools (Issue #44).

This is the "mcp" adapter referenced by ../../adapters/ableton.md and
../../SKILL.md (priority order: MCP > read-only > Computer Use).
`get_tempo`/`get_song_info`/`get_tracks` are read-only, as before.
`create_track`/`write_generated_midi` are new write tools -- both are
gated through `enforcement.enforce()` before they touch the Live set,
so the Policy Engine's ALLOW/ASK/DENY decision (see
../../policy_engine/rules.py) always runs first. There is no `save`
tool here: AbletonOSC has no OSC address for saving/exporting the Live
set at all (confirmed against its source), matching this repo's
existing precedent for a capability that genuinely doesn't exist (see
mcp-ardour/README.md's tempo-tool absence).

Requires Ableton Live to be running on the same machine, with AbletonOSC
(https://github.com/ideoforms/AbletonOSC) installed as a Remote Script
and selected as the Control Surface. See README.md in this directory.

OSC addresses used here are taken from AbletonOSC's source
(abletonosc/song.py, abletonosc/track.py, abletonosc/clip.py,
abletonosc/clip_slot.py) as of the version checked when this was
written — see README.md for the exact addresses and where they were
confirmed. They have not been exercised against a real Ableton Live
instance in this environment (see README.md's verification status).
None of AbletonOSC's write addresses send an OSC reply (confirmed
against its source), so the write tools below read back state
afterward to report what happened, rather than trusting a
confirmation that AbletonOSC never sends.
"""

from __future__ import annotations

import time

from mcp.server.mcpserver import MCPServer

from enforcement import enforce

from .osc_client import OSCQueryClient

mcp = MCPServer("astra-daw-guard-ableton-readonly")
_client: OSCQueryClient | None = None


class AbletonWriteUnconfirmed(RuntimeError):
    """A write's effect could not be confirmed by re-querying state.

    Raised instead of returning a result that looks successful but may
    not reflect what actually happened in Ableton Live -- see the
    write tools' docstrings and osc_client.py's `send()` for why
    AbletonOSC's write addresses give no way to know synchronously
    whether they took effect.
    """


def _osc() -> OSCQueryClient:
    global _client
    if _client is None:
        _client = OSCQueryClient()
    return _client


def _track_property(track_index: int, prop: str) -> object:
    """Query /live/track/get/<prop> for one track, stripping an echoed index.

    AbletonOSC's reply convention (confirmed for /live/track/get/name in
    its source) is to echo the track_index as the first reply argument,
    followed by the value. This strips that leading index if present, so
    callers just get the value.
    """
    reply = _osc().query(f"/live/track/get/{prop}", track_index)
    if len(reply) >= 2 and reply[0] == track_index:
        return reply[1]
    return reply[0] if reply else None


def _find_track_index(track_name: str) -> int:
    """Return the 0-based index of the track named `track_name`, or
    raise ValueError if no such track exists.
    """
    (num_tracks,) = _osc().query("/live/song/get/num_tracks")
    for i in range(num_tracks):
        if _track_property(i, "name") == track_name:
            return i
    raise ValueError(f"No track named {track_name!r} exists. Call create_track first.")


@mcp.tool()
def get_tempo() -> dict:
    """Return the Live set's current tempo (BPM). Read-only."""
    (bpm,) = _osc().query("/live/song/get/tempo")
    return {"bpm": bpm}


@mcp.tool()
def get_song_info() -> dict:
    """Return basic song/transport state: tempo, length, playhead, playing.

    Read-only. Ableton's OSC surface does not expose a project file name
    or path (unlike Reaper's), so those fields are not included here.
    """
    (bpm,) = _osc().query("/live/song/get/tempo")
    (song_length,) = _osc().query("/live/song/get/song_length")
    (current_time,) = _osc().query("/live/song/get/current_song_time")
    (is_playing,) = _osc().query("/live/song/get/is_playing")
    (num_tracks,) = _osc().query("/live/song/get/num_tracks")
    (num_scenes,) = _osc().query("/live/song/get/num_scenes")
    return {
        "bpm": bpm,
        "song_length_beats": song_length,
        "current_song_time_beats": current_time,
        "is_playing": bool(is_playing),
        "track_count": num_tracks,
        "scene_count": num_scenes,
    }


@mcp.tool()
def get_tracks() -> list[dict]:
    """Return the track list with basic per-track state.

    Read-only. `index` is 0-based, matching Ableton's track order. Does
    not include return/master tracks (only regular tracks 0..num_tracks-1
    as exposed by /live/song/get/num_tracks).
    """
    (num_tracks,) = _osc().query("/live/song/get/num_tracks")
    tracks = []
    for i in range(num_tracks):
        tracks.append(
            {
                "index": i,
                "name": _track_property(i, "name"),
                "muted": bool(_track_property(i, "mute")),
                "soloed": bool(_track_property(i, "solo")),
                "armed": bool(_track_property(i, "arm")),
                "color": _track_property(i, "color"),
            }
        )
    return tracks


def _approx_equal(a: object, b: object, tol: float = 1e-4) -> bool:
    """Numeric-tolerant equality for confirming a float write landed.

    OSC transmits floats as 32-bit, so a value read back after being
    sent (e.g. a volume or tempo) may differ from the original Python
    float by float32 rounding even when the write worked correctly --
    exact `==` would be too strict. Falls back to `==` for non-numeric
    values (e.g. track names).
    """
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def _wait_until(read, matches, *, attempts: int = 5, delay: float = 0.2, is_close=None):
    """Poll `read()` until it returns `matches` (per `is_close`, default
    `==`) or `attempts` is exhausted, then return whatever `read()`
    last returned either way.

    AbletonOSC's write addresses send no reply (see module docstring),
    so a write's effect can only be observed by re-querying state --
    and that state may not be visible to a `get` query the instant
    after the `send()` returns. This is a documented, real timing
    assumption, unverified against real Ableton Live (see README.md).
    """
    check = is_close or (lambda a, b: a == b)
    value = read()
    for _ in range(attempts - 1):
        if check(value, matches):
            return value
        time.sleep(delay)
        value = read()
    return value


@mcp.tool()
def create_track(name: str, approved: bool = False) -> dict:
    """Create a new MIDI track named `name` at the end of the track list.

    Gated by the Policy Engine (see policy/allow.txt, rule
    CREATE_GEN_TRACK / CREATE_OTHER_TRACK): a name starting with
    `GEN-` is auto-ALLOWed; any other name requires `approved=True`
    after the user has explicitly confirmed *this* track creation in
    the current turn (ASK otherwise -- see enforcement/README.md).
    """
    action = {"operation": "track.create", "attributes": {"name": name}}

    def _do() -> dict:
        (before_count,) = _osc().query("/live/song/get/num_tracks")
        new_index = before_count
        _osc().send("/live/song/create_midi_track", -1)
        _osc().send("/live/track/set/name", new_index, name)
        actual_name = _wait_until(lambda: _track_property(new_index, "name"), matches=name)
        if actual_name != name:
            raise AbletonWriteUnconfirmed(
                f"Sent create_midi_track + set/name {name!r} at index {new_index}, but "
                f"re-reading the track name still returns {actual_name!r} after retrying. "
                "Either the track wasn't created/renamed, or Ableton Live is slower to "
                "apply the change than this tool's retry window -- check get_tracks() "
                "before assuming this failed outright."
            )
        return {"index": new_index, "name": actual_name}

    return enforce(action, _do, approved=approved)


@mcp.tool()
def write_generated_midi(
    track_name: str, notes: list[dict], clip_index: int = 0, approved: bool = False
) -> dict:
    """Create a clip in an existing track named `track_name` and write
    generated MIDI `notes` into it.

    The track must already exist -- call `create_track` first. Gated
    by the Policy Engine (see policy/allow.txt, rule
    GENERATED_MIDI_INTO_GEN_TRACK): only ALLOWed automatically when
    `track_name` starts with `GEN-`; generated MIDI into any other
    track is always DENIED (GENERATED_MIDI_INTO_OTHER_TRACK), since
    policy/allow.txt only covers generated content written into a
    new GEN--prefixed track.

    Each entry in `notes` is a dict with keys `pitch` (0-127),
    `start_time`, `duration` (both in beats), and optionally
    `velocity` (0-127, default 100) and `mute` (default False).
    `clip_index` selects which clip slot in the track to use
    (default 0, the first).
    """
    action = {
        "operation": "midi.write",
        "attributes": {"source": "generated", "track": track_name},
    }

    def _do() -> dict:
        track_index = _find_track_index(track_name)
        length_beats = max((note["start_time"] + note["duration"] for note in notes), default=1.0)
        _osc().send("/live/clip_slot/create_clip", track_index, clip_index, length_beats)
        note_args: list = [track_index, clip_index]
        for note in notes:
            note_args.extend(
                [
                    note["pitch"],
                    note["start_time"],
                    note["duration"],
                    note.get("velocity", 100),
                    note.get("mute", False),
                ]
            )
        _osc().send("/live/clip/add/notes", *note_args)

        def _written_note_count() -> int:
            reply = _osc().query("/live/clip/get/notes", track_index, clip_index)
            # Reply is (track_index, clip_index, pitch, start, duration,
            # velocity, mute, pitch, ...) -- 5 values per note after the
            # leading pair (confirmed against AbletonOSC's clip_get_notes).
            return (len(reply) - 2) // 5

        written = _wait_until(_written_note_count, matches=len(notes))
        if written != len(notes):
            raise AbletonWriteUnconfirmed(
                f"Sent {len(notes)} note(s) to track {track_name!r} clip {clip_index}, "
                f"but re-reading the clip's notes still shows {written} after retrying. "
                "Either the write didn't fully take effect, or Ableton Live is slower to "
                "apply it than this tool's retry window -- check the clip in Live before "
                "assuming this failed outright."
            )
        return {"track": track_name, "clip_index": clip_index, "notes_written": written}

    return enforce(action, _do, approved=approved)


_MIXER_PARAM_ADDRESSES = {
    "volume": "/live/track/set/volume",
    "pan": "/live/track/set/panning",
    "mute": "/live/track/set/mute",
    "solo": "/live/track/set/solo",
}


@mcp.tool()
def set_mixer_property(track_name: str, param: str, value: float, approved: bool = False) -> dict:
    """Set a mixer property on an existing track: `param` must be one
    of "volume", "pan", "mute", "solo".

    Gated by the Policy Engine (see policy/allow.txt, rule
    MIXER_CHANGE_ON_GEN_TRACK / MIXER_CHANGE_ON_OTHER_TRACK): auto-ALLOWed
    only when `track_name` starts with `GEN-`; any other track requires
    `approved=True` after the user has explicitly confirmed this change
    in the current turn (ASK otherwise).

    Value ranges are whatever Ableton's `mixer_device.volume`/`panning`
    Parameter objects accept -- AbletonOSC's own source and Ableton's
    published Live Object Model reference do not state the exact
    numeric range or unity-gain value, so this has NOT been
    independently confirmed in this environment (community references
    describe 0.0-1.0 for volume with ~0.85 as unity gain, and -1.0-1.0
    for panning, but treat that as unverified until checked against
    real Ableton Live). `mute`/`solo` take 0/1 (sent as int(bool(value))).
    """
    if param not in _MIXER_PARAM_ADDRESSES:
        raise ValueError(f"param must be one of {sorted(_MIXER_PARAM_ADDRESSES)}, got {param!r}")

    action = {
        "operation": "track.mixer_change",
        "attributes": {"track": track_name, "param": param, "value": value},
    }

    def _do() -> dict:
        track_index = _find_track_index(track_name)
        wire_value = int(bool(value)) if param in ("mute", "solo") else value
        address = _MIXER_PARAM_ADDRESSES[param]
        _osc().send(address, track_index, wire_value)
        prop = address.rsplit("/", 1)[-1]  # e.g. "/live/track/set/panning" -> "panning"
        actual = _wait_until(
            lambda: _track_property(track_index, prop),
            matches=wire_value,
            is_close=_approx_equal,
        )
        if not _approx_equal(actual, wire_value):
            raise AbletonWriteUnconfirmed(
                f"Sent {param}={wire_value!r} to track {track_name!r}, but re-reading "
                f"it still shows {actual!r} after retrying. Either the write didn't "
                "take effect, or Ableton Live is slower to apply it than this tool's "
                "retry window -- check the track in Live before assuming this failed "
                "outright."
            )
        return {"track": track_name, "param": param, "value": actual}

    return enforce(action, _do, approved=approved)


@mcp.tool()
def set_device_parameter(
    track_name: str, device_index: int, param_index: int, value: float, approved: bool = False
) -> dict:
    """Set a device parameter's value on an existing track's device.

    Gated by the Policy Engine (see policy/allow.txt, rule
    DEVICE_PARAM_CHANGE_ON_GEN_TRACK / DEVICE_PARAM_CHANGE_ON_OTHER_TRACK):
    auto-ALLOWed only when `track_name` starts with `GEN-`; any other
    track requires `approved=True` after explicit user confirmation
    this turn.

    This tool does not enumerate devices/parameters itself -- use
    AbletonOSC's own `/live/device/get/parameters/name` (not wrapped
    here) to find `device_index`/`param_index` first. Value range
    depends entirely on the specific parameter (AbletonOSC exposes
    `/live/device/get/parameters/min`/`max` for this, also not wrapped
    here); passing an out-of-range value is Live's own behavior to
    reject or clamp, not something this tool validates.
    """
    action = {
        "operation": "device.param_change",
        "attributes": {
            "track": track_name,
            "device_index": device_index,
            "param_index": param_index,
            "value": value,
        },
    }

    def _do() -> dict:
        track_index = _find_track_index(track_name)
        _osc().send("/live/device/set/parameter/value", track_index, device_index, param_index, value)

        def _current_value():
            reply = _osc().query("/live/device/get/parameter/value", track_index, device_index, param_index)
            # Reply is (track_index, device_index, param_index, value) --
            # confirmed against AbletonOSC's device_get_parameter_value.
            return reply[-1] if reply else None

        actual = _wait_until(_current_value, matches=value, is_close=_approx_equal)
        if not _approx_equal(actual, value):
            raise AbletonWriteUnconfirmed(
                f"Sent param_index={param_index} value={value!r} to track {track_name!r} "
                f"device {device_index}, but re-reading it still shows {actual!r} after "
                "retrying. Either the write didn't take effect, or Ableton Live is "
                "slower to apply it than this tool's retry window -- check the device "
                "in Live before assuming this failed outright."
            )
        return {"track": track_name, "device_index": device_index, "param_index": param_index, "value": actual}

    return enforce(action, _do, approved=approved)


_TRANSPORT_ADDRESSES = {"play": "/live/song/start_playing", "stop": "/live/song/stop_playing"}


@mcp.tool()
def control_transport(action: str) -> dict:
    """Start or stop playback. `action` must be "play" or "stop".

    Always ALLOWed (see policy/allow.txt, rule TRANSPORT_CONTROL) --
    starting/stopping playback changes no project data.
    """
    if action not in _TRANSPORT_ADDRESSES:
        raise ValueError(f"action must be one of {sorted(_TRANSPORT_ADDRESSES)}, got {action!r}")

    policy_action = {"operation": "transport.control", "attributes": {"action": action}}

    def _do() -> dict:
        _osc().send(_TRANSPORT_ADDRESSES[action])
        expected_playing = action == "play"
        actual_playing = _wait_until(
            lambda: bool(_osc().query("/live/song/get/is_playing")[0]), matches=expected_playing
        )
        if actual_playing != expected_playing:
            raise AbletonWriteUnconfirmed(
                f"Sent {action!r}, but /live/song/get/is_playing still reports "
                f"{actual_playing!r} after retrying. Either the write didn't take "
                "effect, or Ableton Live is slower to apply it than this tool's retry "
                "window -- check the transport in Live before assuming this failed "
                "outright."
            )
        return {"action": action, "is_playing": actual_playing}

    return enforce(policy_action, _do)


@mcp.tool()
def set_tempo(bpm: float, user_requested_this_turn: bool = False, approved: bool = False) -> dict:
    """Change the project's tempo (BPM).

    Gated by the Policy Engine (see policy/allow.txt, rule
    TEMPO_CHANGE_APPROVED / TEMPO_CHANGE_UNCONFIRMED): auto-ALLOWed
    only when `user_requested_this_turn=True`; otherwise ASK, since a
    tempo change affects the timing of everything already in the set.
    """
    action = {
        "operation": "tempo.change",
        "attributes": {"bpm": bpm, "user_requested_this_turn": user_requested_this_turn},
    }

    def _do() -> dict:
        _osc().send("/live/song/set/tempo", bpm)
        actual_bpm = _wait_until(
            lambda: _osc().query("/live/song/get/tempo")[0], matches=bpm, is_close=_approx_equal
        )
        if not _approx_equal(actual_bpm, bpm):
            raise AbletonWriteUnconfirmed(
                f"Sent tempo={bpm!r}, but re-reading it still shows {actual_bpm!r} "
                "after retrying. Either the write didn't take effect, or Ableton Live "
                "is slower to apply it than this tool's retry window -- check the "
                "tempo in Live before assuming this failed outright."
            )
        return {"bpm": actual_bpm}

    return enforce(action, _do, approved=approved)


if __name__ == "__main__":
    mcp.run(transport="stdio")
