"""Read-only MCP server exposing Ableton Live state via AbletonOSC.

This is the "mcp" adapter referenced by ../../adapters/ableton.md and
../../SKILL.md (priority order: MCP > read-only > Computer Use). It never
writes to the Live set: no track creation, no tempo changes, no mute/solo
toggling, no save. That boundary matches ../../policy/deny.txt and
../../policy/allow.txt in the repository root.

Requires Ableton Live to be running on the same machine, with AbletonOSC
(https://github.com/ideoforms/AbletonOSC) installed as a Remote Script
and selected as the Control Surface. See README.md in this directory.

OSC addresses used here are taken from AbletonOSC's source
(abletonosc/song.py, abletonosc/track.py) as of the version checked when
this was written — see README.md for the exact addresses and where they
were confirmed. They have not been exercised against a real Ableton Live
instance in this environment (see README.md's verification status).
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .osc_client import OSCQueryClient

mcp = MCPServer("astra-daw-guard-ableton-readonly")
_client: OSCQueryClient | None = None


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
