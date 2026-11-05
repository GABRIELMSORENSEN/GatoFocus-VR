"""Explicit offline check. Never connects to or sends commands to VRChat."""
import sys
import json
from pathlib import Path
import statistics
import time
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gatofocus.vision import Detector

image = cv2.imread(sys.argv[1])
if image is None:
    raise SystemExit("Provide an existing test image")
detector = Detector(ROOT / "models/yolox_nano.onnx")
timings = []
for index in range(20):
    before = time.perf_counter()
    people = detector.detect(image)
    timings.append((time.perf_counter() - before) * 1000)
    time.sleep(.1)
report = {"model_bytes": (ROOT / "models/yolox_nano.onnx").stat().st_size,
          "people": len(people), "median_ms": round(statistics.median(timings[3:]), 2),
          "p95_ms": round(sorted(timings[3:])[-2], 2), "provider": "CPUExecutionProvider", "threads": 2}
print(json.dumps(report, indent=2))
for p in people:
    h, w = image.shape[:2]
    x1,y1,x2,y2 = (p.box * [w,h,w,h]).astype(int)
    cv2.rectangle(image, (x1,y1), (x2,y2), (70,220,140), 3)
cv2.imwrite(str(ROOT / ".work/detector-result.jpg"), image)
