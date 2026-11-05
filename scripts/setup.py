"""Download pinned public runtime/model dependencies and verify their SHA-256."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "assets/dependencies.json").read_text())
revision = manifest["openvr_revision"]
paths = {"models/yolox_nano.onnx": manifest["model_url"],
         "vendor/openvr/openvr.h": f"https://raw.githubusercontent.com/ValveSoftware/openvr/{revision}/headers/openvr.h",
         "vendor/openvr/openvr_api.dll": f"https://raw.githubusercontent.com/ValveSoftware/openvr/{revision}/bin/win64/openvr_api.dll",
         "vendor/openvr/openvr_api.lib": f"https://raw.githubusercontent.com/ValveSoftware/openvr/{revision}/lib/win64/openvr_api.lib"}
for relative, url in paths.items():
    dest = ROOT / relative
    expected = manifest["sha256"][relative]
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == expected:
        print("Verified:", relative)
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "GatoFocusVR-Setup/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError(f"Checksum mismatch: {relative}")
    temporary = dest.with_suffix(dest.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(dest)
    print("Installed:", relative)
