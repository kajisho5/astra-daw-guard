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

    _MIXER_PROPS = ("volume", "panning", "mute", "solo")

    def __init__(
        self,
        track_names: list[str],
        drop_rename: bool = False,
        drop_notes: bool = False,
        drop_mixer: bool = False,
        drop_device: bool = False,
        drop_transport: bool = False,
        drop_tempo: bool = False,
    ):
        self.track_names = list(track_names)
        self.clip_notes: dict[tuple[int, int], list] = {}
        self.mixer: dict[tuple[int, str], object] = {}
        self.device_params: dict[tuple[int, int, int], float] = {}
        self.is_playing = False
        self.tempo = 120.0
        self.sent: list[tuple] = []
        self.drop_rename = drop_rename
        self.drop_notes = drop_notes
        self.drop_mixer = drop_mixer
        self.drop_device = drop_device
        self.drop_transport = drop_transport
        self.drop_tempo = drop_tempo

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
        for prop in self._MIXER_PROPS:
            if address == f"/live/track/get/{prop}":
                (index,) = args
                return (index, self.mixer.get((index, prop)))
        if address == "/live/device/get/parameter/value":
            track_index, device_index, param_index = args
            return (track_index, device_index, param_index, self.device_params.get((track_index, device_index, param_index)))
        if address == "/live/song/get/is_playing":
            return (self.is_playing,)
        if address == "/live/song/get/tempo":
            return (self.tempo,)
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
        elif address in ("/live/track/set/volume", "/live/track/set/panning", "/live/track/set/mute", "/live/track/set/solo"):
            if self.drop_mixer:
                return
            prop = address.rsplit("/", 1)[-1]
            index, value = args
            self.mixer[(index, prop)] = value
        elif address == "/live/device/set/parameter/value":
            if self.drop_device:
                return
            track_index, device_index, param_index, value = args
            self.device_params[(track_index, device_index, param_index)] = value
        elif address in ("/live/song/start_playing", "/live/song/stop_playing"):
            if self.drop_transport:
                return
            self.is_playing = address.endswith("start_playing")
        elif address == "/live/song/set/tempo":
            if self.drop_tempo:
                return
            (value,) = args
            self.tempo = value
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


@unittest.skipIf(_IMPORT_ERROR is not None, f"ableton_mcp.server not importable: {_IMPORT_ERROR}")
class SetMixerPropertyEnforcementTests(unittest.TestCase):
    def test_gen_track_is_allowed_and_volume_is_sent(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.set_mixer_property("GEN-melody", "volume", 0.7)
        self.assertEqual(result, {"track": "GEN-melody", "param": "volume", "value": 0.7})
        self.assertEqual(osc.mixer[(0, "volume")], 0.7)

    def test_mute_is_sent_as_int(self):
        osc = _FakeAbletonOSC(track_names=["GEN-drums"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.set_mixer_property("GEN-drums", "mute", True)
        self.assertEqual(result, {"track": "GEN-drums", "param": "mute", "value": 1})
        self.assertEqual(osc.mixer[(0, "mute")], 1)

    def test_non_gen_track_without_approval_is_blocked_and_sends_nothing(self):
        osc = _FakeAbletonOSC(track_names=["Vocals"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ApprovalRequired):
                ableton_server.set_mixer_property("Vocals", "volume", 0.5)
        self.assertEqual([c for c in osc.sent if c[0] == "send"], [])

    def test_non_gen_track_with_approval_sends_the_change(self):
        osc = _FakeAbletonOSC(track_names=["Vocals"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.set_mixer_property("Vocals", "pan", -0.3, approved=True)
        self.assertEqual(result, {"track": "Vocals", "param": "pan", "value": -0.3})

    def test_invalid_param_raises_before_touching_osc(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ValueError):
                ableton_server.set_mixer_property("GEN-melody", "reverb", 0.5)
        self.assertEqual(osc.sent, [])

    def test_unconfirmed_change_raises_instead_of_reporting_success(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"], drop_mixer=True)
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.set_mixer_property("GEN-melody", "volume", 0.7)

    def test_dropped_write_near_preexisting_value_is_not_falsely_confirmed(self):
        # CodeRabbit review finding on PR #47: a fixed 1e-4 tolerance
        # could confirm a genuinely dropped write as landed whenever the
        # pre-existing value already sat within that tolerance of the
        # requested one (e.g. existing 0.7, dropped request 0.70005).
        # float32-rounding the comparison instead still catches the drop.
        osc = _FakeAbletonOSC(track_names=["GEN-melody"], drop_mixer=True)
        osc.mixer[(0, "volume")] = 0.7
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.set_mixer_property("GEN-melody", "volume", 0.70005)

    def test_non_boolean_mute_value_is_rejected_before_touching_osc(self):
        # CodeRabbit review finding on PR #47: int(bool(0.5)) sends 1
        # over OSC while the recorded Action/audit data kept 0.5 --
        # reject non-boolean values instead of silently coercing them.
        osc = _FakeAbletonOSC(track_names=["GEN-melody"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ValueError):
                ableton_server.set_mixer_property("GEN-melody", "mute", 0.5)
        self.assertEqual(osc.sent, [])

    def test_mute_action_records_the_same_normalized_value_that_is_sent(self):
        osc = _FakeAbletonOSC(track_names=["GEN-melody"])
        captured: dict = {}
        real_enforce = ableton_server.enforce

        def spy_enforce(action, *args, **kwargs):
            captured["action"] = action
            return real_enforce(action, *args, **kwargs)

        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "enforce", side_effect=spy_enforce
        ):
            ableton_server.set_mixer_property("GEN-melody", "mute", True)
        self.assertEqual(captured["action"]["attributes"]["value"], 1)
        self.assertEqual(osc.mixer[(0, "mute")], 1)


@unittest.skipIf(_IMPORT_ERROR is not None, f"ableton_mcp.server not importable: {_IMPORT_ERROR}")
class SetDeviceParameterEnforcementTests(unittest.TestCase):
    def test_gen_track_is_allowed_and_value_is_sent(self):
        osc = _FakeAbletonOSC(track_names=["GEN-bass"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.set_device_parameter("GEN-bass", 0, 3, 0.42)
        self.assertEqual(result, {"track": "GEN-bass", "device_index": 0, "param_index": 3, "value": 0.42})
        self.assertEqual(osc.device_params[(0, 0, 3)], 0.42)

    def test_non_gen_track_without_approval_is_blocked_and_sends_nothing(self):
        osc = _FakeAbletonOSC(track_names=["Synth"])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ApprovalRequired):
                ableton_server.set_device_parameter("Synth", 0, 3, 0.42)
        self.assertEqual([c for c in osc.sent if c[0] == "send"], [])

    def test_action_records_device_index_for_audit_precision(self):
        # Issue #46 review finding: the Action used to omit device_index,
        # so an audit_log/approval couldn't distinguish which device on
        # a track was actually changed.
        osc = _FakeAbletonOSC(track_names=["GEN-bass"])
        captured: dict = {}
        real_enforce = ableton_server.enforce

        def spy_enforce(action, *args, **kwargs):
            captured["action"] = action
            return real_enforce(action, *args, **kwargs)

        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "enforce", side_effect=spy_enforce
        ):
            ableton_server.set_device_parameter("GEN-bass", 2, 3, 0.42)
        self.assertEqual(captured["action"]["attributes"]["device_index"], 2)

    def test_unconfirmed_change_raises_instead_of_reporting_success(self):
        osc = _FakeAbletonOSC(track_names=["GEN-bass"], drop_device=True)
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.set_device_parameter("GEN-bass", 0, 3, 0.42)


@unittest.skipIf(_IMPORT_ERROR is not None, f"ableton_mcp.server not importable: {_IMPORT_ERROR}")
class ControlTransportTests(unittest.TestCase):
    def test_play_is_always_allowed_with_no_approval_needed(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.control_transport("play")
        self.assertEqual(result, {"action": "play", "is_playing": True})
        self.assertIn(("send", "/live/song/start_playing", ()), osc.sent)

    def test_stop_is_always_allowed(self):
        osc = _FakeAbletonOSC(track_names=[])
        osc.is_playing = True
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.control_transport("stop")
        self.assertEqual(result, {"action": "stop", "is_playing": False})

    def test_invalid_action_raises_before_touching_osc(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ValueError):
                ableton_server.control_transport("rewind")
        self.assertEqual(osc.sent, [])

    def test_unconfirmed_transport_raises_instead_of_reporting_success(self):
        osc = _FakeAbletonOSC(track_names=[], drop_transport=True)
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.control_transport("play")


@unittest.skipIf(_IMPORT_ERROR is not None, f"ableton_mcp.server not importable: {_IMPORT_ERROR}")
class SetTempoEnforcementTests(unittest.TestCase):
    def test_user_requested_this_turn_is_allowed_and_sets_tempo(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.set_tempo(128.0, user_requested_this_turn=True)
        self.assertEqual(result, {"bpm": 128.0})
        self.assertEqual(osc.tempo, 128.0)

    def test_without_user_request_or_approval_is_blocked(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            with self.assertRaises(ApprovalRequired):
                ableton_server.set_tempo(128.0)
        self.assertEqual([c for c in osc.sent if c[0] == "send"], [])

    def test_approved_after_ask_sets_tempo(self):
        osc = _FakeAbletonOSC(track_names=[])
        with mock.patch.object(ableton_server, "_osc", return_value=osc):
            result = ableton_server.set_tempo(90.0, approved=True)
        self.assertEqual(result, {"bpm": 90.0})

    def test_unconfirmed_tempo_raises_instead_of_reporting_success(self):
        osc = _FakeAbletonOSC(track_names=[], drop_tempo=True)
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.set_tempo(128.0, user_requested_this_turn=True)

    def test_dropped_tempo_near_preexisting_value_is_not_falsely_confirmed(self):
        # Same float32-tolerance fix as SetMixerPropertyEnforcementTests's
        # equivalent test, applied to tempo (the exact scenario
        # CodeRabbit's review comment used: existing 120.0, dropped
        # request landing within the old fixed tolerance).
        osc = _FakeAbletonOSC(track_names=[], drop_tempo=True)
        osc.tempo = 120.0
        with mock.patch.object(ableton_server, "_osc", return_value=osc), mock.patch.object(
            ableton_server, "time"
        ):
            with self.assertRaises(ableton_server.AbletonWriteUnconfirmed):
                ableton_server.set_tempo(120.00005, user_requested_this_turn=True)


if __name__ == "__main__":
    unittest.main()
