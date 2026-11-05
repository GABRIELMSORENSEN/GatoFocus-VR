"""Local YOLOX-Nano person detection and single-target temporal association."""
from dataclasses import dataclass, field
import math
import cv2
import numpy as np
import onnxruntime as ort


@dataclass
class Person:
    box: np.ndarray
    confidence: float = 1.0
    appearance: np.ndarray | None = None

    @property
    def head(self):
        x1, y1, x2, y2 = self.box
        return np.array([(x1 + x2) / 2, y1 + (y2 - y1) * .14])


class Detector:
    def __init__(self, path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        options.add_session_config_entry("session.inter_op.allow_spinning", "0")
        self.session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        grids, strides = [], []
        for stride in (8, 16, 32):
            yy, xx = np.mgrid[:416 // stride, :416 // stride]
            grids.append(np.stack((xx, yy), axis=-1).reshape(-1, 2))
            strides.append(np.full((xx.size, 1), stride))
        self.grid, self.strides = np.concatenate(grids), np.concatenate(strides)

    def detect(self, image, threshold=.27):
        # Official non-legacy YOLOX preprocessing: BGR, values 0..255, top-left letterbox.
        h, w = image.shape[:2]
        ratio = min(416 / h, 416 / w)
        canvas = np.full((416, 416, 3), 114, np.uint8)
        rw, rh = max(1, int(w * ratio)), max(1, int(h * ratio))
        canvas[:rh, :rw] = cv2.resize(image, (rw, rh))
        inp = np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32)
        raw = self.session.run(None, {self.session.get_inputs()[0].name: inp})[0][0]
        scores = raw[:, 4] * raw[:, 5]  # COCO class zero: person
        keep = scores >= threshold
        if not np.any(keep):
            return []
        xy = (raw[keep, :2] + self.grid[keep]) * self.strides[keep] / ratio
        wh = np.exp(np.clip(raw[keep, 2:4], -10, 10)) * self.strides[keep] / ratio
        boxes = np.column_stack((xy - wh / 2, wh))
        scores = scores[keep]
        indexes = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), threshold, .45)
        result = []
        for i in np.asarray(indexes).reshape(-1):
            x, y, bw, bh = boxes[i]
            box = np.array([max(0, x), max(0, y), min(w, x + bw), min(h, y + bh)])
            if box[3] - box[1] < 25 or box[2] - box[0] < 8:
                continue
            x1, y1, x2, y2 = box.astype(int)
            crop = image[y1:y2, x1:x2]
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [12, 8], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            result.append(Person(box / np.array([w, h, w, h]), float(scores[i]), hist))
        return result


def overlap(a, b):
    size = np.maximum(0, np.minimum(a[2:], b[2:]) - np.maximum(a[:2], b[:2]))
    inter = float(np.prod(size))
    return inter / max(1e-8, float(np.prod(a[2:] - a[:2]) + np.prod(b[2:] - b[:2])) - inter)


def gaze_angles(point, projection=(-1., 1., -1., 1.), rotation=None):
    left, right, top, bottom = projection
    x = left + float(point[0]) * (right - left)
    y = -(top + float(point[1]) * (bottom - top))
    ray = np.array([x, y, -1.])  # OpenVR forward is -Z.
    if rotation is not None:
        ray = np.asarray(rotation).reshape(3, 3) @ ray
    return np.array([math.degrees(math.atan2(-ray[1], math.hypot(ray[0], ray[2]))),
                     math.degrees(math.atan2(ray[0], -ray[2]))])


@dataclass
class FocusTracker:
    dwell: float = .65
    radius: float = 28.
    target: Person | None = None
    last_seen: float = 0.
    candidate: Person | None = None
    candidate_since: float = 0.
    generation: int = 0
    held: bool = False

    def reset(self):
        self.target = self.candidate = None
        self.last_seen = 0.

    def update(self, people, now, projection=(-1., 1., -1., 1.), rotation=None):
        def central(p):
            return float(np.linalg.norm(gaze_angles(p.head, projection, rotation)))

        matched = None
        if self.target is not None:
            ranked = []
            for p in people:
                iou = overlap(p.box, self.target.box)
                distance = float(np.linalg.norm(p.head - self.target.head))
                appearance = 1.
                if p.appearance is not None and self.target.appearance is not None:
                    appearance = 1 - cv2.compareHist(p.appearance, self.target.appearance, cv2.HISTCMP_BHATTACHARYYA)
                if (iou > .12 or distance < .13) and appearance > .25:
                    ranked.append((iou * .5 + appearance * .4 - distance * .7, p))
            if ranked:
                matched = max(ranked, key=lambda item: item[0])[1]
                self.target, self.last_seen = matched, now
            elif now - self.last_seen > .85:
                self.reset()

        candidates = [p for p in people if central(p) <= self.radius]
        best = min(candidates, key=central) if candidates else None
        if best is not None and best is not matched and not (self.held and self.target is not None):
            better = self.target is None or (matched is not None and central(best) + 6 < central(matched))
            if better:
                if self.candidate is None or overlap(best.box, self.candidate.box) < .20:
                    self.candidate, self.candidate_since = best, now
                else:
                    self.candidate = best
                if now - self.candidate_since >= self.dwell:
                    self.target, self.last_seen = best, now
                    self.candidate = None
                    self.generation += 1
            else:
                self.candidate = None
        else:
            self.candidate = None
        return self.target
