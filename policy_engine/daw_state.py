"""DAW state snapshot for policy Action context (Issue #25).

**This module changes NO Decision.** No rule in `rules.py` reads
anything from a snapshot built here, and none may be added that does
without a corresponding line in `policy/deny.txt` or `policy/allow.txt`
to justify it (see this module's own non-goals below, and Issue #25).
This exists purely to give an Action a structured, non-ad-hoc place to
carry "what did the DAW look like right before this Action was
proposed" for audit/debugging purposes — `enforcement.enforce()`'s
`audit_log` (Issue #16 Step 5) already records `Decision.attributes`
verbatim, so anything attached this way is durably recorded with zero
further plumbing.

Every field here is derived from an existing MCP read tool's actual
return shape — never aspirational (same discipline as
`capabilities.CAPABILITY_MATRIX`). `policy_engine` still never calls an
MCP server itself: the caller collects state via `mcp-reaper` /
`mcp-ableton` / `mcp-ardour`'s own tools and passes the resulting dicts
into one of the `from_*` constructors below.

Non-goals:
- No new `policy/deny.txt` / `policy/allow.txt`-derived rules that read
  `daw_state` — nothing currently in those files depends on DAW state
- `policy_engine` gains no ability to query an MCP server itself
- No changes to `mcp-reaper` / `mcp-ableton` / `mcp-ardour`
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class DAWStateSnapshot:
    """A snapshot of what a DAW looked like at some point in time.

    Fields are a superset across the three DAWs this repo supports —
    any field a given DAW's MCP adapter cannot report is left `None`
    rather than guessed. See the `from_*` constructors for exactly
    which MCP tool populates which field.
    """

    daw: str
    tempo_bpm: Optional[float] = None
    track_count: Optional[int] = None
    tracks: Optional[list] = field(default=None)
    transport: Optional[dict] = None
    project: Optional[dict] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def from_reaper(
    *,
    tempo: Optional[dict] = None,
    tracks: Optional[list] = None,
    project_info: Optional[dict] = None,
) -> DAWStateSnapshot:
    """Build a snapshot from mcp-reaper's tool return values.

    - `tempo`: `mcp-reaper/reaper_mcp/server.py`'s `get_tempo()` ->
      `{"bpm": ..., "time_signature_numerator": ...}`
    - `tracks`: its `get_tracks()` -> list of per-track dicts
    - `project_info`: its `get_project_info()` ->
      `{"name", "directory", "length_seconds", "track_count"}`
    """
    if project_info is not None:
        track_count = project_info.get("track_count")
    elif tracks is not None:
        track_count = len(tracks)
    else:
        track_count = None
    return DAWStateSnapshot(
        daw="reaper",
        tempo_bpm=tempo.get("bpm") if tempo else None,
        track_count=track_count,
        tracks=tracks,
        project=project_info,
    )


def from_ableton(
    *,
    song_info: Optional[dict] = None,
    tracks: Optional[list] = None,
) -> DAWStateSnapshot:
    """Build a snapshot from mcp-ableton's tool return values.

    - `song_info`: `mcp-ableton/ableton_mcp/server.py`'s
      `get_song_info()` -> `{"bpm", "song_length_beats",
      "current_song_time_beats", "is_playing", "track_count",
      "scene_count"}`
    - `tracks`: its `get_tracks()` -> list of per-track dicts
    """
    if song_info is not None:
        track_count = song_info.get("track_count")
    elif tracks is not None:
        track_count = len(tracks)
    else:
        track_count = None
    return DAWStateSnapshot(
        daw="ableton",
        tempo_bpm=song_info.get("bpm") if song_info else None,
        track_count=track_count,
        tracks=tracks,
        project=song_info,
    )


def from_ardour(
    *,
    tracks: Optional[list] = None,
    transport: Optional[dict] = None,
) -> DAWStateSnapshot:
    """Build a snapshot from mcp-ardour's tool return values.

    - `tracks`: `mcp-ardour/ardour_mcp/server.py`'s `get_tracks()` ->
      list of strip dicts (tracks/buses/VCAs)
    - `transport`: its `get_transport()` -> `{"position_samples",
      "speed", "is_rolling"}`

    `tempo_bpm` is always `None` for Ardour: its OSC surface has no
    tempo/BPM query at all (see `mcp-ardour/ardour_mcp/server.py`'s
    module docstring) — fabricating one here would violate the same
    "don't claim things you haven't confirmed" rule that keeps
    `get_tempo()` out of `mcp-ardour` itself.
    """
    return DAWStateSnapshot(
        daw="ardour",
        tempo_bpm=None,
        track_count=len(tracks) if tracks is not None else None,
        tracks=tracks,
        transport=transport,
    )


def attach_to_attributes(attributes: dict, snapshot: DAWStateSnapshot) -> dict:
    """Return a copy of `attributes` with `snapshot` attached under the
    agreed `"daw_state"` key — the convention `evaluate()`/`enforce()`
    callers should follow (see `policy_engine/README.md`). Purely
    additive: never overwrites any other key, never mutates the input.
    """
    return {**attributes, "daw_state": snapshot.to_dict()}
