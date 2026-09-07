"""Read-only MCP server exposing Ardour session/track state via OSC.

This is the "mcp" adapter referenced by ../../adapters/ardour.md and
../../SKILL.md (priority order: MCP > read-only > Computer Use). It never
writes to the session: no track creation, no transport control, no mute/
solo toggling, no save. That boundary matches ../../policy/deny.txt and
../../policy/allow.txt in the repository root.

Requires Ardour to be running on the same machine with its built-in OSC
surface enabled (Preferences > Control Surfaces > Open Sound Control
(OSC), Port Mode = Auto). See README.md in this directory.

OSC addresses used here (/strip/list, /transport_frame,
/transport_speed) were confirmed against Ardour's OSC source
(libs/surfaces/osc/osc.cc) and manual ("Querying Ardour with OSC") as of
the version checked when this was written. Ardour's OSC surface does
NOT expose a tempo/BPM query (confirmed via an Ardour developer's reply
on the Ardour forum: "No such command, sorry" — there is no single
session-wide tempo to query in the general case, since tempo can vary
along the timeline) — so, unlike mcp-reaper/mcp-ableton, there is no
get_tempo() here. Fabricating one would violate this project's own
"don't claim things you haven't confirmed" rule. This has not been
exercised against a real Ardour instance in this environment — see
README.md for verification status.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .osc_client import ArdourOSCClient

mcp = MCPServer("astra-daw-guard-ardour-readonly")
_client: ArdourOSCClient | None = None

_STRIP_TYPES = {
    "AT": "audio_track",
    "MT": "midi_track",
    "B": "audio_bus",
    "MB": "midi_bus",
    "FB": "foldback_bus",
    "V": "vca",
}


def _osc() -> ArdourOSCClient:
    global _client
    if _client is None:
        _client = ArdourOSCClient()
    return _client


def _parse_strip(params: tuple) -> dict:
    """Parse one /strip/list reply tuple.

    Per Ardour's manual ("Querying Ardour with OSC"): type, name,
    n_inputs, n_outputs, muted, soloed, ssid, [rec_enabled]. Buses have
    no rec_enabled field ("A bus will not have a record enable and so a
    bus message will have one less parameter than a track.").
    """
    strip_type, name, n_in, n_out, muted, soloed, ssid = params[:7]
    rec_enabled = bool(params[7]) if len(params) > 7 else None
    return {
        "type": _STRIP_TYPES.get(strip_type, strip_type),
        "name": name,
        "index": ssid,
        "inputs": n_in,
        "outputs": n_out,
        "muted": bool(muted),
        "soloed": bool(soloed),
        "record_enabled": rec_enabled,
    }


@mcp.tool()
def get_tracks() -> list[dict]:
    """Return the strip list (tracks, buses, VCAs) with basic state.

    Read-only, via /strip/list. `index` (Ardour calls it "ssid") is
    1-based, matching Ardour's own numbering. Buses and VCAs have
    `record_enabled: null` since Ardour doesn't report that field for
    them.
    """
    replies = _osc().query_list("/strip/list", "end_route_list")
    return [_parse_strip(r) for r in replies]


@mcp.tool()
def get_transport() -> dict:
    """Return transport position and speed. Read-only.

    Note: Ardour's OSC surface has no tempo/BPM query — a session can
    have multiple tempos along its timeline, and no single "current
    tempo" address is exposed (confirmed on Ardour's own forum). This
    tool intentionally does not report a tempo field.
    """
    (position_samples,) = _osc().query("/transport_frame")
    (speed,) = _osc().query("/transport_speed")
    return {
        "position_samples": position_samples,
        "speed": speed,
        "is_rolling": speed != 0,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
