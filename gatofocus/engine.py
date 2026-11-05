import json
import logging
import os
from pathlib import Path
import threading
import time
import numpy as np
import cv2
import psutil
from .capture import SteamCapture, DesktopCapture, NoFrame
from .vision import Detector, FocusTracker, gaze_angles
from .osc import EyeOutput

DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GatoFocusVR"
DEFAULTS = {"fps": 6, "confidence": .27, "focus_radius": 28., "smooth": .18, "hold": False, "source": "desktop"}


class Engine:
    def __init__(self, root):
        self.root = root
        DATA.mkdir(parents=True, exist_ok=True)
        self.config = DEFAULTS.copy()
        try:
            saved = json.loads((DATA / "settings.json").read_text())
            for key in DEFAULTS:
                if key in saved:
                    self.config[key] = saved[key]
            self.config["fps"] = max(3, min(15, int(self.config["fps"])))
            self.config["confidence"] = max(.12, min(.7, float(self.config["confidence"])))
            self.config["focus_radius"] = max(12, min(40, float(self.config["focus_radius"])))
            self.config["smooth"] = max(.08, min(.6, float(self.config["smooth"])))
            if self.config["source"] not in ("desktop", "steamvr"):
                self.config["source"] = "desktop"
        except (OSError, ValueError, TypeError):
            self.config = DEFAULTS.copy()
        self.lock = threading.Lock()
        self.quit = threading.Event()
        self.enabled = False
        self.reset_requested = False
        self.frame = None
        self.desired = None
        self.desired_time = 0.
        self.osc_ready = False
        self.vrchat_pid = 0
        self.status = {"state": "Pronto para iniciar", "detail": "Conecte o headset ao SteamVR.",
                       "people": 0, "target": None, "inference_ms": 0., "fps": 0., "packets": 0,
                       "pitch": 0., "yaw": 0., "cpu": 0., "ram_mb": 0., "osc": False,
                       "capture": False, "native_error": "", "generation": 0, "frames": 0}
        self.threads = [threading.Thread(target=self._vision, daemon=True, name="vision"),
                        threading.Thread(target=self._output, daemon=True, name="osc")]
        for thread in self.threads:
            thread.start()

    def update(self, **values):
        with self.lock:
            self.config.update(values)
            saved = dict(self.config)
        temp = DATA / "settings.tmp"
        temp.write_text(json.dumps(saved, indent=2), encoding="utf-8")
        temp.replace(DATA / "settings.json")

    def set_enabled(self, value):
        with self.lock:
            self.enabled = value
            self.desired = None
            self.reset_requested = True
            self.frame = None
            self.status.update(state="Iniciando…" if value else "Pausado", target=None, people=0,
                               capture=False, fps=0., boxes=[], detail="Preparando a captura." if value else "Captura e envio interrompidos. Clique em Iniciar para retomar.")

    def snapshot(self):
        with self.lock:
            return dict(self.status), self.frame, dict(self.config), self.enabled

    def _vision(self):
        capture = None
        try:
            cv2.setNumThreads(1)
            detector = Detector(Path(self.root) / "models/yolox_nano.onnx")
            capture_mode = None
            tracker = FocusTracker()
            while not self.quit.is_set():
                with self.lock:
                    config, enabled = dict(self.config), self.enabled
                    if self.reset_requested:
                        tracker.reset()
                        self.reset_requested = False
                if not enabled:
                    if capture and capture.opened:
                        capture.close()
                    self.quit.wait(.2)
                    continue
                started = time.monotonic()
                try:
                    if not self.vrchat_pid:
                        if capture and capture.opened:
                            capture.close()
                        tracker.reset()
                        with self.lock:
                            self.desired = None
                            self.frame = None
                            self.status.update(state="Aguardando VRChat", detail="Abra o jogo em Desktop (Non-VR)." if config["source"] == "desktop" else "Conecte o Quest e abra o jogo pelo SteamVR.",
                                               target=None, people=0, capture=False, fps=0.)
                        self.quit.wait(1.)
                        continue
                    if config["source"] == "steamvr" and not any(
                        (p.info["name"] or "").lower() == "vrcompositor.exe"
                        for p in psutil.process_iter(["name"])
                    ):
                        raise NoFrame("O SteamVR ainda não está recebendo imagem do headset.")
                    mode = (config["source"], config["fps"])
                    if mode != capture_mode:
                        if capture:
                            capture.close()
                        capture = SteamCapture(self.root) if mode[0] == "steamvr" else DesktopCapture(mode[1])
                        capture_mode = mode
                        tracker.reset()
                    frame, projection, rotation, scene_pid = capture.grab()
                    if np.percentile(frame[::8, ::8], 95) < 5:
                        raise NoFrame("O VRChat está enviando uma imagem preta. Aguarde o carregamento ou restaure a janela.")
                    if not self.vrchat_pid or scene_pid != self.vrchat_pid:
                        with self.lock:
                            self.desired = None
                            self.frame = frame
                            self.status.update(state="Aguardando VRChat em VR", detail="Abra o VRChat no modo SteamVR.",
                                               capture=True, target=None, people=0, scene_pid=scene_pid)
                        tracker.reset()
                        self.quit.wait(.5)
                        continue
                    before = time.perf_counter()
                    people = detector.detect(frame, config["confidence"])
                    elapsed = (time.perf_counter() - before) * 1000
                    tracker.radius, tracker.held = config["focus_radius"], config["hold"]
                    target = tracker.update(people, started, projection, rotation)
                    desired = gaze_angles(target.head, projection, rotation) if target else None
                    with self.lock:
                        if not self.enabled:
                            continue
                        self.desired, self.desired_time = desired, started
                        self.frame = frame
                        self.status["frames"] += 1
                        self.status.update(
                            state="Acompanhando uma pessoa" if target else "Procurando no centro",
                            detail="Mantenha outra pessoa no centro para trocar o foco." if target else "Olhe na direção de um avatar por um instante.",
                            capture=True, native_error="", people=len(people),
                            boxes=[p.box.tolist() for p in people], target=target.box.tolist() if target else None,
                            inference_ms=round(elapsed, 1), generation=tracker.generation,
                            projection=projection.tolist(), scene_pid=scene_pid,
                            fps=round(1 / max(1 / config["fps"], time.monotonic() - started), 1))
                except NoFrame as exc:
                    tracker.reset()
                    with self.lock:
                        self.desired = None
                        self.frame = None
                        self.status.update(state="Aguardando imagem do VRChat", capture=False, detail=str(exc),
                                           target=None, people=0, fps=0.)
                except Exception as exc:
                    if capture:
                        capture.close()
                    tracker.reset()
                    with self.lock:
                        self.frame = None
                        self.desired = None
                        self.status.update(state="Aguardando imagem do SteamVR" if config["source"] == "steamvr" else "Aguardando VRChat no PC", capture=False,
                                           detail="Conecte o headset e entre no VRChat em VR." if config["source"] == "steamvr" else "Abra o VRChat em Desktop (Non-VR).",
                                           native_error=str(exc), target=None, people=0, fps=0.)
                    self.quit.wait(3.)
                self.quit.wait(max(.001, 1 / config["fps"] - (time.monotonic() - started)))
        except Exception as exc:
            logging.exception("Vision stopped")
            with self.lock:
                self.desired = None
                self.status.update(state="Não foi possível iniciar", detail=str(exc), capture=False)
        finally:
            if capture is not None:
                capture.close()

    def _output(self):
        output = EyeOutput()
        process = psutil.Process()
        process.cpu_percent()
        current = np.zeros(2)
        last, checked = time.monotonic(), 0.
        try:
            while not self.quit.wait(1 / 30):
                now = time.monotonic()
                if now - checked > 1.:
                    try:
                        ids = {p.info["pid"] for p in psutil.process_iter(["pid", "name"])
                               if (p.info["name"] or "").lower() == "vrchat.exe"}
                        self.vrchat_pid = next(iter(ids), 0)
                        self.osc_ready = any(c.pid in ids and c.laddr.port == 9000
                                             for c in psutil.net_connections(kind="udp") if c.laddr)
                    except (psutil.Error, OSError):
                        self.osc_ready = False
                    with self.lock:
                        self.status.update(osc=self.osc_ready, cpu=round(process.cpu_percent() / (psutil.cpu_count() or 1), 1),
                                           ram_mb=round(process.memory_info().rss / 1024 ** 2), packets=output.sent, updated_at=time.time())
                        diagnostic = dict(self.status)
                    try:
                        (DATA / "status.json").write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
                    except OSError:
                        pass
                    checked = now
                with self.lock:
                    desired = None if self.desired is None else self.desired.copy()
                    valid = self.enabled and now - self.desired_time < .65 and self.osc_ready
                    smooth = self.config["smooth"]
                if desired is not None and valid:
                    current += (desired - current) * (1 - np.exp(-min(.1, now - last) / smooth))
                    output.send(current)
                    with self.lock:
                        self.status.update(pitch=round(float(current[0]), 1), yaw=round(float(current[1]), 1))
                else:
                    current *= .85
                last = now
        except Exception:
            logging.exception("OSC stopped")
        finally:
            output.close()

    def close(self):
        with self.lock:
            self.enabled = False
            self.desired = None
        self.quit.set()
        for thread in self.threads:
            thread.join(timeout=4)
