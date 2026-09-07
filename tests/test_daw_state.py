"""Tests for policy_engine.daw_state (Issue #25).

The one property that matters here: attaching a DAWStateSnapshot to an
Action's attributes must never change what evaluate() returns, for any
operation -- this module is audit-context plumbing, not policy. Also
verifies enforcement.enforce()'s audit_log preserves an attached
snapshot unchanged (Issue #16 Step 5's guarantee extended to this new
attribute). Run from the repo root:

    python3 -m unittest tests.test_daw_state -v
"""

from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from enforcement import enforce  # noqa: E402
from policy_engine import evaluate  # noqa: E402
from policy_engine.daw_state import (  # noqa: E402
    attach_to_attributes,
    from_ableton,
    from_ardour,
    from_reaper,
)

_REAPER_SNAPSHOT_KWARGS = dict(
    tempo={"bpm": 120.0, "time_signature_numerator": 4},
    tracks=[{"index": 0, "name": "Drums", "muted": False, "soloed": False, "item_count": 3, "color_rgb": [0, 0, 0]}],
    project_info={"name": "song", "directory": "/x", "length_seconds": 30.0, "track_count": 1},
)

# A representative sample of operations, spanning ALLOW/ASK/DENY and
# fail-closed outcomes, to prove daw_state attachment is inert across
# the board -- not just for one lucky operation.
_REPRESENTATIVE_ACTIONS = [
    {"operation": "read.tempo"},
    {"operation": "track.create", "attributes": {"name": "GEN-bass"}},
    {"operation": "track.create", "attributes": {"name": "Vocals"}},  # ASK
    {"operation": "project.save", "attributes": {"mode": "overwrite"}},  # DENY
    {"operation": "totally.unknown"},  # fail-closed DENY
]


class SnapshotConstructionTests(unittest.TestCase):
    def test_from_reaper_populates_fields_from_the_three_reaper_tools(self):
        snap = from_reaper(**_REAPER_SNAPSHOT_KWARGS)
        self.assertEqual(snap.daw, "reaper")
        self.assertEqual(snap.tempo_bpm, 120.0)
        self.assertEqual(snap.track_count, 1)
        self.assertEqual(snap.tracks, _REAPER_SNAPSHOT_KWARGS["tracks"])
        self.assertIsNone(snap.transport)

    def test_from_reaper_falls_back_to_len_tracks_without_project_info(self):
        snap = from_reaper(tracks=[{"index": 0, "name": "A"}, {"index": 1, "name": "B"}])
        self.assertEqual(snap.track_count, 2)
        self.assertIsNone(snap.project)

    def test_from_ableton_populates_fields_from_song_info_and_tracks(self):
        snap = from_ableton(
            song_info={
                "bpm": 128.0,
                "song_length_beats": 64,
                "current_song_time_beats": 0,
                "is_playing": False,
                "track_count": 2,
                "scene_count": 1,
            }
        )
        self.assertEqual(snap.daw, "ableton")
        self.assertEqual(snap.tempo_bpm, 128.0)
        self.assertEqual(snap.track_count, 2)

    def test_from_ardour_never_sets_tempo_bpm(self):
        # Ardour's OSC surface has no tempo query -- see mcp-ardour's
        # own server.py docstring. This must stay None, never guessed.
        snap = from_ardour(
            tracks=[{"type": "audio_track", "name": "Bus"}],
            transport={"position_samples": 0, "speed": 0, "is_rolling": False},
        )
        self.assertEqual(snap.daw, "ardour")
        self.assertIsNone(snap.tempo_bpm)
        self.assertEqual(snap.track_count, 1)
        self.assertIsNotNone(snap.transport)

    def test_missing_inputs_leave_fields_none_rather_than_guessed(self):
        snap = from_reaper()
        self.assertIsNone(snap.tempo_bpm)
        self.assertIsNone(snap.track_count)
        self.assertIsNone(snap.tracks)
        self.assertIsNone(snap.project)


class AttachmentNeverChangesDecisionTests(unittest.TestCase):
    """The core guarantee this Issue exists to protect."""

    def test_attaching_daw_state_does_not_change_the_decision_for_any_representative_action(self):
        snapshot = from_reaper(**_REAPER_SNAPSHOT_KWARGS)
        for action in _REPRESENTATIVE_ACTIONS:
            with self.subTest(action=action):
                baseline = evaluate(action)
                attributes = action.get("attributes", {})
                augmented = {**action, "attributes": attach_to_attributes(attributes, snapshot)}
                with_state = evaluate(augmented)
                self.assertEqual(with_state.decision, baseline.decision)
                self.assertEqual(with_state.rule_id, baseline.rule_id)
                self.assertEqual(with_state.reason, baseline.reason)

    def test_attach_to_attributes_does_not_mutate_the_input_dict(self):
        original = {"name": "GEN-bass"}
        snapshot = from_reaper(**_REAPER_SNAPSHOT_KWARGS)
        attach_to_attributes(original, snapshot)
        self.assertEqual(original, {"name": "GEN-bass"})

    def test_attach_to_attributes_does_not_overwrite_existing_keys(self):
        snapshot = from_reaper(**_REAPER_SNAPSHOT_KWARGS)
        result = attach_to_attributes({"name": "GEN-bass"}, snapshot)
        self.assertEqual(result["name"], "GEN-bass")
        self.assertIn("daw_state", result)


class AuditLogPreservesDawStateTests(unittest.TestCase):
    """Issue #16 Step 5's audit guarantee extended to this new field:
    daw_state must survive into the audit_log entry unchanged, with
    zero code changes required in enforcement/ itself.
    """

    def test_audit_log_entry_contains_the_attached_snapshot_unchanged(self):
        snapshot = from_reaper(**_REAPER_SNAPSHOT_KWARGS)
        action = {
            "operation": "track.create",
            "attributes": attach_to_attributes({"name": "GEN-bass"}, snapshot),
        }
        log: list[dict] = []
        enforce(action, lambda: "created", audit_log=log)
        self.assertEqual(log[0]["attributes"]["daw_state"], snapshot.to_dict())


if __name__ == "__main__":
    unittest.main()
