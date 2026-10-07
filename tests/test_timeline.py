import unittest
from unittest.mock import patch, Mock

from followsinger.timeline import FollowClock
from followsinger.lyrics import LyricLine, active_index
import test_controls


def sample(position, at, **overrides):
    return dict(connected=True, timeline=True, identity="123", transport="direct",
                position=position, duration=10000, sample=at, playing=True, rate=1,
                canSeek=True, canPlay=True) | overrides


class TimelineTests(unittest.TestCase):
    def test_repeated_sample_does_not_undo_transition(self):
        clock = FollowClock()
        lines = [LyricLine(0, "a"), LyricLine(1000, "b"), LyricLine(1200, "c")]
        clock.update(sample(950, 100), 100)
        positions = [clock.position(100.0), clock.position(100.1)]
        clock.update(sample(950, 100.25), 100.25)
        positions.extend([clock.position(100.25), clock.position(100.35)])
        self.assertEqual([active_index(lines, p) for p in positions], [0, 1, 2, 2])
        self.assertEqual(positions, sorted(positions))

    def test_fast_lines_and_three_rates_never_rewind(self):
        lines = [LyricLine(i * 80, "Hi") for i in range(100)]
        for rate in (.5, 1, 1.5):
            clock = FollowClock()
            positions = []
            indices = []
            for tick in range(60):
                elapsed = tick * .05
                if tick % 5 == 0:
                    # Client updates its slider every 500ms; poll is every 250ms.
                    raw = int(elapsed / .5) * .5 * 1000 * rate
                    clock.update(sample(raw, 100 + elapsed, rate=rate), 100 + elapsed)
                positions.append(clock.position(100 + elapsed))
                indices.append(active_index(lines, positions[-1]))
            self.assertEqual(positions, sorted(positions), rate)
            self.assertEqual(indices, sorted(indices), rate)

    def test_corrections_and_stalls_are_bounded(self):
        clock = FollowClock()
        clock.update(sample(1000, 100), 100)
        self.assertEqual(clock.position(105), 2000)
        for i in range(1, 11):
            at = 100 + i
            clock.update(sample(1000 + i * 10, at), at)
            self.assertLessEqual(clock.position(at + .9), 1000 + i * 10 + 1000)

    def test_external_backward_seek_and_track_switch(self):
        clock = FollowClock()
        clock.update(sample(5000, 100), 100)
        clock.update(sample(4000, 100.25), 100.25)
        self.assertEqual(clock.position(100.25), 4000)
        clock.update(sample(0, 100.5, identity="next"), 100.5)
        self.assertEqual(clock.position(100.5), 0)

    def test_small_explicit_seek_waits_for_acknowledgement(self):
        clock = FollowClock()
        clock.update(sample(2000, 100), 100)
        clock.expect_seek(1970, 100.1)
        clock.update(sample(2000, 100.25), 100.25)
        self.assertEqual(clock.position(100.25), 2250)
        clock.update(sample(1970, 100.5), 100.5)
        self.assertEqual(clock.position(100.5), 1970)
        self.assertIsNone(clock.pending_seek)

    def test_pause_rate_disconnect_and_out_of_order(self):
        clock = FollowClock()
        clock.update(sample(1000, 100), 100)
        clock.update(sample(1100, 100.1, playing=False), 100.1)
        self.assertEqual(clock.position(101), 1100)
        clock.update(sample(1100, 101, rate=1.5), 101)
        self.assertEqual(clock.position(101.2), 1400)
        self.assertFalse(clock.update(sample(10, 100), 101.2))
        self.assertEqual(clock.position(101.2), 1400)
        clock.update({"connected": False, "sample": 102}, 102)
        self.assertEqual(clock.position(102), 0)

    def test_seek_ack_includes_playback_during_client_latency(self):
        clock = FollowClock()
        clock.update(sample(5000, 100, rate=1.5), 100)
        clock.expect_seek(1000, 100)
        clock.update(sample(1450, 100.3, rate=1.5), 100.3)
        self.assertIsNone(clock.pending_seek)
        self.assertEqual(clock.position(100.3), 1450)


class TimelineInterfaceTests(test_controls.ControlsTest):
    test_click_space_and_editor_space = None
    test_rate_modes_and_disconnect = None
    test_five_themes_persist = None

    def test_remote_boundary_scrolls_forward_once(self):
        self.w.cloud_clock.reset()
        self.w.list.scrollToItem = Mock()
        self.w._set_lines([LyricLine(0, "Hi"), LyricLine(1000, "Hello"), LyricLine(1400, "World")], "test")
        self.w.list.scrollToItem.reset_mock()
        sequence = []
        for now, stamped in [(100, 100), (100.1, 100), (100.25, 100.25), (100.35, 100.25)]:
            with patch("followsinger.window.time.monotonic", return_value=now):
                self.w._cloud_snapshot(sample(950, stamped))
                sequence.append(self.w.active)
        self.assertEqual(sequence, [0, 1, 1, 1])
        self.assertEqual(self.w.list.scrollToItem.call_count, 1)

    def test_click_previous_and_loop_can_rewind(self):
        self.w.cloud_clock.reset()
        self.w.track_identity = "123"
        self.w._set_lines([LyricLine(0, "Hi"), LyricLine(1000, "Hello"), LyricLine(3000, "World")], "test")
        with patch("followsinger.window.time.monotonic", return_value=100):
            self.w._cloud_snapshot(sample(2000, 100))
            self.w._jump_relative(-1)
            self.w.follower.send.assert_called_with("seek", 0, "123")
        with patch("followsinger.window.time.monotonic", return_value=100.25):
            self.w._cloud_snapshot(sample(0, 100.25))
            self.assertEqual(self.w.active, 0)
            self.w.loop.setChecked(True)
        with patch("followsinger.window.time.monotonic", return_value=101.25):
            self.w._cloud_snapshot(sample(1000, 101.25))
            self.w._tick()
            self.w.follower.send.assert_called_with("seek", 0, "123")
        with patch("followsinger.window.time.monotonic", return_value=101.5):
            self.w._cloud_snapshot(sample(0, 101.5))
            self.assertEqual(self.w.active, 0)
