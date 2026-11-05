import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "scripts/setup.py")], check=True, cwd=ROOT)
subprocess.run([str(ROOT / "scripts/build_native.cmd")], check=True, cwd=ROOT)
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
                "--name", "GatoFocusVR", "--icon", "assets/gatofocus.ico",
                "--add-data", "models;models", "--add-data", "assets;assets",
                "--add-binary", "runtime/gatofocus_capture.dll;runtime",
                "--add-binary", "runtime/openvr_api.dll;runtime",
                "--collect-all", "customtkinter", "--collect-all", "onnxruntime",
                "--collect-all", "windows_capture",
                "--copy-metadata", "numpy", "--copy-metadata", "onnxruntime",
                "--copy-metadata", "opencv-python", "--copy-metadata", "windows-capture",
                "--copy-metadata", "customtkinter", "--copy-metadata", "Pillow",
                "--copy-metadata", "psutil", "main.py"], check=True, cwd=ROOT)
folder = ROOT / "dist/GatoFocusVR"
for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
    shutil.copy2(ROOT / name, folder / name)
shutil.copytree(ROOT / "docs", folder / "docs", dirs_exist_ok=True)
shutil.copytree(ROOT / "vendor/openvr", folder / "licenses/openvr", dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("*.lib", "*.dll", "*.h"))
(folder / "Iniciar GatoFocus.cmd").write_text('@echo off\nstart "" "%~dp0GatoFocusVR.exe" --start\n')
release = ROOT / "release"
release.mkdir(exist_ok=True)
archive = Path(shutil.make_archive(str(release / "GatoFocusVR-0.1.0-Windows-x64"), "zip", ROOT / "dist", "GatoFocusVR"))
(release / "SHA256SUMS.txt").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n")
print(archive)
