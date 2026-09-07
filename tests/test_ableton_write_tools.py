"""Regression tests for Issue #44's Ableton Live write tools
(mcp-ableton/ableton_mcp/server.py's create_track / write_generated_midi).

Like tests/test_reaper_write_tools.py, these test exactly one thing:
that every write tool is gated by the Policy Engine via
enforcement.enforce() before it sends anything to Ableton Live. `_osc`
is monkeypatched with a fake OSCQueryClient that records every
send()/query() call and simulates AbletonOSC's actual state-update
behavior (confirmed against AbletonOSC's own source: creating a track
or adding notes sends no OSC reply at all -- see osc_client.py's
`send()` docstring), since no live Ableton Live instance exists in
this environment.

ableton_mcp.server requires the `mcp` package and python-osc to
import; this module skips cleanly, not with an error, if either isn't
installed, matching tests/test_ardour_osc_client.py's precedent (this
repo's CI never installs mcp-*/'s own dependencies).
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mcp-ableton"))

try:
    from ableton_mcp import server as ableton_server  # noqa: E402

    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - environment-dependent
    _IMPORT_ERROR = exc

from enforcement.boundary import ApprovalRequired, ToolDenied  # noqa: E402


class _FakeAbletonOSC:
    """Simulates just enough of AbletonOSC's real behavior for these
    tests: track creation/naming and clip/note writes take effect
    immediately (no reply, per the real protocol) and are visible to a
    subsequent query() -- matching what a real (patient) re-query
    would eventually see. Pass `drop_rename=True` / `drop_notes=True` to
    simulate one specific write never taking effect (e.g. a lost UDP
    packet, or Live being slower than the tool's retry window) while
    the rest of the sequence still succeeds normally.
    """

    def __init__(self, track_names: list[str], drop_rename: bool = False, drop_notes: bool = False):
        self.track_names = list(track_names)
        self.clip_notes: dict[tuple[int, int], list] = {}
        self.sent: list[tuple] = []
        self.drop_rename = drop_rename
        self.drop_notes = drop_notes

    def query(self, address: str, *args):
        self.sent.append(("query", address, args))
        if address == "/live/song/get/num_tracks":
            return (len(self.track_names),)
        if address == "/live/track/get/name":
            (index,) = args
            return (index, self.track_names[index])
        if address == "/live/clip/get/notes":
            track_index, clip_index = args
            notes = self.clip_notes.get((track_index, clip_index), [])
            flattened = []
            for note in notes:
                flattened.extend(note)
            return (track_index, clip_index, *flattened)
        raise AssertionError(f"unexpected query: {address} {args}")

    def send(self, address: str, *args):
        self.sent.append(("send", address, args))
        if address == "/live/song/create_midi_track":
            self.track_names.append("")
        elif address == "/live/track/set/name":
            if self.drop_rename:
                return
            index, name = args
            self.track_names[index] = name
        elif address == "/live/clip_slot/create_clip":
            track_index, clip_index, _length = args
            self.clip_notes.setdefault((track_index, clip_index), [])
        elif address == "/live/clip/add/notes":
            if self.drop_notes:
                return
            track_index, clip_index, *note_args = args
            notes = self.clip_notes.setdefault((track_index, clip_index), [])
            for i in range(0, len(note_args), 5):
                notes.append(tuple(note_args[i : i + 5]))
        else:
            raise AssertionError(f"unexpected send: {address} {args}")


@unittest.skipIf(_IMPORT_ERROR is not None, f"ableton_mcp.server not importable: {_IMPORT_ERROR}")
class CreateTrackEnforcementTests(unittest.TestCase):
    def test_gen_prefixed_name_is_auto_allowed_and_creates_the_track(self):
        osc = _FakeAbletonOSC(track_names=["Drums"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.create_track("GEN-melody")
        self.assertEqual(result, {"index": 1, "name": "GEN-melody"})
        self.assertEqual(osc.track_names, ["Drums", "GEN-melody"])

    def test_non_gen_name_without_approval_is_blocked_and_sends_nothing(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ApprovalRequired):
                ableton_server.create_track("My Track")
        self.assertEqual(osc.sent, [])
        self.assertEqual(osc.track_names, [])

    def test_non_gen_name_with_approval_creates_the_track(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.create_track("My Track", approved=True)
        self.assertEqual(result, {"index": 0, "name": "My Track"})
        self.assertEqual(osc.track_names, ["My Track"])

    def test_unconfirmed_rename_raises_instead_of_reporting_success(self):
        osc = _FakeAbletonOSC(track_names=[], drop_rename=True)
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.create_track("GEN-melody")


@unittest.skipIf(_IMPORT_ERROR is not None, f"ableton_mcp.server not importable: {_IMPORT_ERROR}")
class WriteGeneratedMidiEnforcementTests(unittest.TestCase):
    def test_gen_track_is_allowed_and_notes_are_sent(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"])
        notes = [
            {"pitch": 60, "start_time": 0.0, "duration": 1.0},
            {"pitch": 62, "start_time": 1.0, "duration": 1.0, "velocity": 90, "mute": True},
        ]
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.write_generated_midi("GEN-melody", notes)
        self.assertEqual(result, {"track": "GEN-melody", "clip_index": 0, "notes_written": 2})
        sent_addresses = [call[1] for call in osc.sent if call[0] == "send"]
        self.assertIn("/live/clip_slot/create_clip", sent_addresses)
        self.assertIn("/live/clip/add/notes", sent_addresses)
        add_notes_call = next(call for call in osc.sent if call[1] == "/live/clip/add/notes")
        self.assertEqual(
            add_notes_call[2],
            (0, 0, 60, 0.0, 1.0, 100, False, 62, 1.0, 1.0, 90, True),
        )

    def test_non_gen_track_is_always_denied_even_with_approval(self):
        osc = _FakeAbletonOSC(track_names=["Vocals"])
        notes = [{"pitch": 60, "start_time": 0.0, "duration": 1.0}]
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ToolDenied):
                ableton_server.write_generated_midi("Vocals", notes, approved=True)
        self.assertEqual([c for c in osc.sent if c[0] == "send"], [])

    def test_missing_track_raises_after_being_allowed_through_the_gate(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ValueError):
                ableton_server.write_generated_midi("GEN-other", [{"pitch": 60, "start_time": 0, "duration": 1}])

    def test_unconfirmed_notes_raise_instead_of_reporting_success(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"], drop_notes=True)
        notes = [{"pitch": 60, "start_time": 0.0, "duration": 1.0}]
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.write_generated_midi("GEN-melody", notes)


if __name__ == "__main__":
    unittest.main()
