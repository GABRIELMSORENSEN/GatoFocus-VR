import math
import socket
import struct
import unittest
import tempfile
from pathlib import Path
import numpy as np
from gatofocus.vision import Person, FocusTracker, gaze_angles
from gatofocus.osc import EyeOutput, osc_packet
from gatofocus.examples import save_example


def person(x=.5, y=.5, width=.22, height=.6):
    return Person(np.array([x-width/2, y-height*.14, x+width/2, y+height*.86]))


class FocusTests(unittest.TestCase):
    def test_waits_before_locking(self):
        tracker = FocusTracker()
        self.assertIsNone(tracker.update([person()], 0))
        self.assertIsNone(tracker.update([person()], .4))
        self.assertIsNotNone(tracker.update([person()], .7))
        self.assertEqual(tracker.generation, 1)

    def test_tracks_only_one_and_does_not_jump(self):
        tracker = FocusTracker()
        tracker.update([person(), person(.7)], 0)
        tracker.update([person(), person(.7)], .7)
        for i in range(10):
            target = tracker.update([person(.51 + i*.003), person(.7)], .8+i*.1)
            self.assertLess(target.head[0], .56)
        self.assertEqual(tracker.generation, 1)

    def test_switch_requires_new_central_focus_dwell(self):
        tracker = FocusTracker()
        tracker.update([person(.65)], 0)
        tracker.update([person(.65)], .7)
        tracker.update([person(.65), person(.48)], .8)
        self.assertGreater(tracker.update([person(.65), person(.48)], 1.1).head[0], .6)
        self.assertLess(tracker.update([person(.65), person(.48)], 1.5).head[0], .5)
        self.assertEqual(tracker.generation, 2)

    def test_hold_keeps_target(self):
        tracker = FocusTracker(held=True)
        tracker.update([person(.65)], 0)
        tracker.update([person(.65)], .7)
        tracker.update([person(.65), person(.5)], 1)
        self.assertGreater(tracker.update([person(.65), person(.5)], 3).head[0], .6)

    def test_lost_target_expires(self):
        tracker = FocusTracker()
        tracker.update([person()], 0)
        tracker.update([person()], .7)
        self.assertIsNotNone(tracker.update([], 1))
        self.assertIsNone(tracker.update([], 1.6))

    def test_outside_focus_is_not_acquired(self):
        tracker = FocusTracker(radius=12)
        self.assertIsNone(tracker.update([person(.9)], 0))
        self.assertIsNone(tracker.update([person(.9)], 2))

    def test_coordinates(self):
        np.testing.assert_allclose(gaze_angles((.5, .5)), [0, 0], atol=1e-8)
        self.assertLess(gaze_angles((.5, .25))[0], 0)
        self.assertGreater(gaze_angles((.75, .5))[1], 0)
        np.testing.assert_allclose(gaze_angles((.5, .5), (-.8, 1.2, -1., 1.)), [0, math.degrees(math.atan(.2))])

    def test_occlusion_does_not_immediately_change_identity(self):
        tracker = FocusTracker()
        tracker.update([person(.35)], 0)
        tracker.update([person(.35)], .7)
        result = tracker.update([person(.65)], .8)
        self.assertLess(result.head[0], .5)


class OscTests(unittest.TestCase):
    def test_real_udp_encoding_and_limits(self):
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1)
        output = EyeOutput(receiver.getsockname()[1])
        try:
            output.send((-60, 80))
            packet, _ = receiver.recvfrom(1024)
            self.assertTrue(packet.startswith(b"/tracking/eye/CenterPitchYaw\0"))
            self.assertEqual(packet[32:36], b",ff\0")
            self.assertEqual(struct.unpack(">ff", packet[-8:]), (-25., 35.))
        finally:
            output.close()
            receiver.close()

    def test_no_nan(self):
        with self.assertRaises(ValueError):
            osc_packet(float("nan"), 0)


class ExampleTests(unittest.TestCase):
    def test_exported_labels_match_normalized_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = save_example(tmp, np.zeros((90, 160, 3), np.uint8), [[.1,.2,.5,.8]], "desktop")
            self.assertTrue((Path(tmp)/"images"/f"{key}.png").is_file())
            self.assertEqual((Path(tmp)/"labels"/f"{key}.txt").read_text(), "0 0.300000 0.500000 0.400000 0.600000\n")

    def test_refuses_invalid_or_empty_annotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            for boxes in ([], [[.8,.1,.2,.9]], [[-1,0,1,1]]):
                with self.assertRaises(ValueError):
                    save_example(tmp, np.zeros((10,10,3), np.uint8), boxes, "desktop")


if __name__ == "__main__":
    unittest.main()
