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


def _wait_until(read, matches, *, attempts: int = 5, delay: float = 0.2):
    """Poll `read()` until it returns `matches` or `attempts` is
    exhausted, then return whatever `read()` last returned either way.

    AbletonOSC's write addresses send no reply (see module docstring),
    so a write's effect can only be observed by re-querying state --
    and that state may not be visible to a `get` query the instant
    after the `send()` returns. This is a documented, real timing
    assumption, unverified against real Ableton Live (see README.md).
    """
    value = read()
    for _ in range(attempts - 1):
        if value == matches:
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
        (num_tracks,) = _osc().query("/live/song/get/num_tracks")
        track_index = next(
            (i for i in range(num_tracks) if _track_property(i, "name") == track_name),
            None,
        )
        if track_index is None:
            raise ValueError(f"No track named {track_name!r} exists. Call create_track first.")
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
