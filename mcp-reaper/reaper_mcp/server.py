"""MCP server exposing Reaper project state via reapy, plus a small set
of write tools (Issue #44).

This is the "mcp" adapter referenced by ../../adapters/reaper.md and
../../SKILL.md (priority order: MCP > read-only > Computer Use).
`get_tempo`/`get_tracks`/`get_project_info` are read-only, as before.
`create_track`/`write_generated_midi`/`save_project_as` are new write
tools -- every one of them is gated through `enforcement.enforce()`
before it touches the project, so the Policy Engine's ALLOW/ASK/DENY
decision (see ../../policy_engine/rules.py) always runs first. None of
them can express the always-DENYed `project.save`/`mode=overwrite`
Action; only Save As is reachable. See README.md for what has and
hasn't been verified against real hardware.

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

from enforcement import enforce

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


@mcp.tool()
def create_track(name: str, approved: bool = False) -> dict:
    """Create a new track named `name` at the end of the track list.

    Gated by the Policy Engine (see policy/allow.txt, rule
    CREATE_GEN_TRACK / CREATE_OTHER_TRACK): a name starting with
    `GEN-` is auto-ALLOWed; any other name requires `approved=True`
    after the user has explicitly confirmed *this* track creation in
    the current turn (ASK otherwise -- see enforcement/README.md).
    """
    action = {"operation": "track.create", "attributes": {"name": name}}

    def _do() -> dict:
        project = _project()
        track = project.add_track(index=project.n_tracks, name=name)
        return {"index": track.index, "name": track.name}

    return enforce(action, _do, approved=approved)


@mcp.tool()
def write_generated_midi(track_name: str, notes: list[dict], approved: bool = False) -> dict:
    """Write generated MIDI `notes` into an existing track named `track_name`.

    The track must already exist -- call `create_track` first. Gated by
    the Policy Engine (see policy/allow.txt, rule
    GENERATED_MIDI_INTO_GEN_TRACK): only ALLOWed automatically when
    `track_name` starts with `GEN-`; generated MIDI into any other
    track is always DENIED (GENERATED_MIDI_INTO_OTHER_TRACK), since
    policy/allow.txt only covers generated content written into a
    new GEN--prefixed track.

    Each entry in `notes` is a dict with keys `start`, `end` (seconds),
    `pitch` (0-127), and optionally `velocity` (0-127, default 100).
    """
    action = {
        "operation": "midi.write",
        "attributes": {"source": "generated", "track": track_name},
    }

    def _do() -> dict:
        project = _project()
        track = next((t for t in project.tracks if t.name == track_name), None)
        if track is None:
            raise ValueError(f"No track named {track_name!r} exists. Call create_track first.")
        item_end = max((note["end"] for note in notes), default=1)
        item = track.add_midi_item(start=0, end=item_end)
        take = item.active_take
        for note in notes:
            take.add_note(
                note["start"],
                note["end"],
                note["pitch"],
                velocity=note.get("velocity", 100),
                sort=False,
            )
        take.sort_events()
        return {"track": track_name, "notes_written": len(notes)}

    return enforce(action, _do, approved=approved)


@mcp.tool()
def save_project_as(filename: str, user_requested_this_turn: bool = False, approved: bool = False) -> dict:
    """Save the current project to a NEW file path -- never overwrites
    the currently open project (policy/deny.txt: overwriting is always
    denied, and this tool has no way to even express that Action).

    Gated by the Policy Engine (see policy/allow.txt, rule
    SAVE_AS_APPROVED / SAVE_AS_UNCONFIRMED): auto-ALLOWed only when
    `user_requested_this_turn` is True; otherwise ASK.

    Uses REAPER's `Main_SaveProjectEx` (via reapy's raw
    `reascript_api`) rather than reapy's own `Project.save()` --
    `Project.save(force_save_as=True)` triggers REAPER's *interactive*
    Save As dialog (confirmed against reapy's source: it calls
    `Main_SaveProject`, not `Main_SaveProjectEx`), which would block
    waiting for a human at the DAW instead of saving headlessly to
    `filename`.
    """
    action = {
        "operation": "project.save",
        "attributes": {"mode": "save_as", "user_requested_this_turn": user_requested_this_turn},
    }

    def _do() -> dict:
        from reapy import reascript_api as RPR

        project = _project()
        RPR.Main_SaveProjectEx(project.id, filename, 0)
        return {"saved_to": filename}

    return enforce(action, _do, approved=approved)


if __name__ == "__main__":
    mcp.run(transport="stdio")
