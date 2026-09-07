"""Regression tests for Issue #44's Reaper write tools
(mcp-reaper/reaper_mcp/server.py's create_track / write_generated_midi /
save_project_as).

These test exactly one thing: that every write tool is actually gated
by the Policy Engine via enforcement.enforce() -- a DENY or an
unapproved ASK must never let the underlying reapy call happen, and an
ALLOW (or an approved ASK) must let it happen. They do NOT exercise
real reapy/REAPER: `_project()` is monkeypatched with fake
Project/Track/Item/Take objects, since no live REAPER instance exists
in this environment (matching this repo's existing "verified against
a fake server, not real hardware" pattern for every other MCP tool).

reaper_mcp.server requires python-reapy and the `mcp` package to
import; this module skips cleanly, not with an error, if either isn't
installed, since this repo's CI never installs mcp-*/'s own
dependencies (see .github/workflows/checks.yml -- it only
byte-compiles mcp-*/ packages).
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mcp-reaper"))

try:
    from reaper_mcp import server as reaper_server  # noqa: E402

    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - environment-dependent
    _IMPORT_ERROR = exc

from enforcement.boundary import ApprovalRequired, ToolDenied  # noqa: E402


class _FakeTake:
    def __init__(self):
        self.notes: list[tuple] = []
        self.sorted = False

    def add_note(self, start, end, pitch, velocity=100, sort=True):
        self.notes.append((start, end, pitch, velocity, sort))

    def sort_events(self):
        self.sorted = True


class _FakeItem:
    def __init__(self):
        self.active_take = _FakeTake()


class _FakeTrack:
    def __init__(self, index: int, name: str):
        self.index = index
        self.name = name
        self.midi_items: list[_FakeItem] = []

    def add_midi_item(self, start=0, end=1):
        item = _FakeItem()
        self.midi_items.append(item)
        return item


class _FakeProject:
    def __init__(self, tracks=None):
        self.tracks: list[_FakeTrack] = list(tracks or [])
        self.id = "(ReaProject*)0xFAKE"

    @property
    def n_tracks(self):
        return len(self.tracks)

    def add_track(self, index=0, name=""):
        track = _FakeTrack(index, name)
        self.tracks.append(track)
        return track


@unittest.skipIf(_IMPORT_ERROR is not None, f"reaper_mcp.server not importable: {_IMPORT_ERROR}")
class CreateTrackEnforcementTests(unittest.TestCase):
    def test_gen_prefixed_name_is_auto_allowed_and_creates_the_track(self):
        project = _FakeProject()
        with mock.patch.object(reaper_server, "_project", return_value=project):
            result = reaper_server.create_track("GEN-melody")
        self.assertEqual(result, {"index": 0, "name": "GEN-melody"})
        self.assertEqual(project.n_tracks, 1)

    def test_non_gen_name_without_approval_is_blocked_and_creates_nothing(self):
        project = _FakeProject()
        with mock.patch.object(reaper_server, "_project", return_value=project):
            with self.assertRaises(ApprovalRequired):
                reaper_server.create_track("My Track")
        self.assertEqual(project.n_tracks, 0)

    def test_non_gen_name_with_approval_creates_the_track(self):
        project = _FakeProject()
        with mock.patch.object(reaper_server, "_project", return_value=project):
            result = reaper_server.create_track("My Track", approved=True)
        self.assertEqual(result, {"index": 0, "name": "My Track"})
        self.assertEqual(project.n_tracks, 1)


@unittest.skipIf(_IMPORT_ERROR is not None, f"reaper_mcp.server not importable: {_IMPORT_ERROR}")
class WriteGeneratedMidiEnforcementTests(unittest.TestCase):
    def test_gen_track_is_allowed_and_notes_are_written(self):
        track = _FakeTrack(0, "GEN-melody")
        project = _FakeProject(tracks=[track])
        notes = [{"start": 0.0, "end": 1.0, "pitch": 60}, {"start": 1.0, "end": 2.0, "pitch": 62}]
        with mock.patch.object(reaper_server, "_project", return_value=project):
            result = reaper_server.write_generated_midi("GEN-melody", notes)
        self.assertEqual(result, {"track": "GEN-melody", "notes_written": 2})
        self.assertEqual(len(track.midi_items), 1)
        self.assertEqual(track.midi_items[0].active_take.notes, [
            (0.0, 1.0, 60, 100, False),
            (1.0, 2.0, 62, 100, False),
        ])
        self.assertTrue(track.midi_items[0].active_take.sorted)

    def test_non_gen_track_is_always_denied_even_with_approval(self):
        track = _FakeTrack(0, "Vocals")
        project = _FakeProject(tracks=[track])
        notes = [{"start": 0.0, "end": 1.0, "pitch": 60}]
        with mock.patch.object(reaper_server, "_project", return_value=project):
            with self.assertRaises(ToolDenied):
                reaper_server.write_generated_midi("Vocals", notes, approved=True)
        self.assertEqual(track.midi_items, [])

    def test_missing_track_raises_after_being_allowed_through_the_gate(self):
        project = _FakeProject(tracks=[_FakeTrack(0, "GEN-melody")])
        with mock.patch.object(reaper_server, "_project", return_value=project):
            with self.assertRaises(ValueError):
                reaper_server.write_generated_midi("GEN-other", [{"start": 0, "end": 1, "pitch": 60}])


@unittest.skipIf(_IMPORT_ERROR is not None, f"reaper_mcp.server not importable: {_IMPORT_ERROR}")
class SaveProjectAsEnforcementTests(unittest.TestCase):
    def test_user_requested_this_turn_is_allowed_and_saves(self):
        project = _FakeProject()
        with mock.patch.object(reaper_server, "_project", return_value=project), mock.patch(
            "reapy.reascript_api.Main_SaveProjectEx", create=True
        ) as save_call:
            result = reaper_server.save_project_as("out.rpp", user_requested_this_turn=True)
        self.assertEqual(result, {"saved_to": "out.rpp"})
        save_call.assert_called_once_with(project.id, "out.rpp", 0)

    def test_without_user_request_or_approval_is_blocked(self):
        project = _FakeProject()
        with mock.patch.object(reaper_server, "_project", return_value=project), mock.patch(
            "reapy.reascript_api.Main_SaveProjectEx", create=True
        ) as save_call:
            with self.assertRaises(ApprovalRequired):
                reaper_server.save_project_as("out.rpp")
        save_call.assert_not_called()

    def test_approved_after_ask_saves(self):
        project = _FakeProject()
        with mock.patch.object(reaper_server, "_project", return_value=project), mock.patch(
            "reapy.reascript_api.Main_SaveProjectEx", create=True
        ) as save_call:
            result = reaper_server.save_project_as("out.rpp", approved=True)
        self.assertEqual(result, {"saved_to": "out.rpp"})
        save_call.assert_called_once_with(project.id, "out.rpp", 0)


if __name__ == "__main__":
    unittest.main()
