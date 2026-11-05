"""Explicitly saved local annotations. No automatic recording or uploads."""
import hashlib
import json
from pathlib import Path
import time
import cv2


def save_example(folder, image, boxes, source):
    if not boxes:
        raise ValueError("Marque pelo menos um avatar antes de salvar.")
    labels = []
    for x1, y1, x2, y2 in boxes:
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("Marcação fora da imagem.")
        labels.append(f"0 {(x1+x2)/2:.6f} {(y1+y2)/2:.6f} {x2-x1:.6f} {y2-y1:.6f}")
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Não foi possível preparar a imagem.")
    image_bytes = encoded.tobytes()
    key = hashlib.sha256(image_bytes).hexdigest()[:20]
    root = Path(folder)
    (root / "images").mkdir(parents=True, exist_ok=True)
    (root / "labels").mkdir(exist_ok=True)
    (root / "images" / f"{key}.png").write_bytes(image_bytes)
    (root / "labels" / f"{key}.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")
    (root / f"{key}.json").write_text(json.dumps({"source": source, "saved_at": time.time(),
                                                 "labels_reviewed": True, "class": "person", "training_applied": False}, indent=2), encoding="utf-8")
    return key
