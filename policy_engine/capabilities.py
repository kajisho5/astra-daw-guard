"""Per-DAW MCP/OSC read capabilities, derived from what this repo's
mcp-*/ servers actually implement — never aspirational.

Whenever a mcp-*/*/server.py tool is added or removed, update
CAPABILITY_MATRIX to match by hand.
tests/test_policy_engine.py's CapabilityMatrixTests checks this stays in
sync by parsing the actual server.py files, so a drift here fails CI
instead of silently misleading `computer_use.invoke` decisions.

Only read capabilities are modeled: none of astra-daw-guard's MCP
servers implement any write tool, by design (see each mcp-*/README.md),
so there is nothing to model on the write side.
"""

from __future__ import annotations

# operation -> set of DAWs (lowercase) whose MCP adapter in this repo can
# do it. Source: mcp-reaper/reaper_mcp/server.py (get_tempo, get_tracks,
# get_project_info), mcp-ableton/ableton_mcp/server.py (get_tempo,
# get_song_info, get_tracks), mcp-ardour/ardour_mcp/server.py (get_tracks,
# get_transport — Ardour's OSC surface has no tempo query at all, see
# mcp-ardour/README.md).
CAPABILITY_MATRIX: dict[str, set[str]] = {
    "read.tempo": {"reaper", "ableton"},
    "read.tracks": {"reaper", "ableton", "ardour"},
    "read.project_info": {"reaper"},
    "read.song_info": {"ableton"},
    "read.transport": {"ardour"},
    "read.clips": set(),
}


def mcp_supports(daw: str, operation: str) -> bool:
    """Return True if this repo's MCP adapter for `daw` can do `operation`.

    An unknown DAW or unknown operation both return False: this function
    only ever claims a capability it can point at real code for.
    """
    return daw.lower() in CAPABILITY_MATRIX.get(operation, set())
