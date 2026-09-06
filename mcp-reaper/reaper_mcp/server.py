"""Read-only MCP server exposing Reaper project state via reapy.

This is the "mcp" adapter referenced by ../../adapters/reaper.md and
../../SKILL.md (priority order: MCP > read-only > Computer Use). It never
writes to the project: no track creation, no item editing, no save, no
tempo/track changes. That boundary matches ../../policy/deny.txt and
../../policy/allow.txt in the repository root.

Requires Reaper to be running on the same machine, with reapy configured
once beforehand (see README.md in this directory).
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

try:
    import reapy
except ImportError as exc:  # pragma: no cover - import-time guard
    raise SystemExit(
        "python-reapy is required. Install it with `pip install python-reapy` "
        "and run `python -c \"import reapy; reapy.configure_reaper()\"` once "
        "while Reaper is open, then restart Reaper. See README.md."
    ) from exc

mcp = MCPServer("astra-daw-guard-reaper-readonly")


def _project() -> "reapy.Project":
    try:
        return reapy.Project()
    except Exception as exc:
        raise RuntimeError(
            "Could not reach Reaper via reapy. Make sure Reaper is running "
            "on this machine and reapy has been configured (see README.md "
            "in mcp-reaper/)."
        ) from exc


@mcp.tool()
def get_tempo() -> dict:
    """Return the project's current tempo and time signature numerator.

    Read-only. Note: reapy only exposes the time signature numerator
    (called `bpi`, beats per interval/measure) at this API level, not the
    denominator, so the denominator is not reported here.
    """
    project = _project()
    return {
        "bpm": project.bpm,
        "time_signature_numerator": project.bpi,
    }


@mcp.tool()
def get_tracks() -> list[dict]:
    """Return the project's track list with basic per-track state.

    Read-only. Excludes the master track. `index` is 0-based, matching
    Reaper's track GUI order.
    """
    project = _project()
    return [
        {
            "index": track.index,
            "name": track.name,
            "muted": track.is_muted,
            "soloed": track.is_solo,
            "item_count": track.n_items,
            "color_rgb": list(track.color),
        }
        for track in project.tracks
    ]


@mcp.tool()
def get_project_info() -> dict:
    """Return basic project metadata: name, directory, length, track count.

    Read-only.
    """
    project = _project()
    return {
        "name": project.name,
        "directory": project.path,
        "length_seconds": project.length,
        "track_count": project.n_tracks,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
