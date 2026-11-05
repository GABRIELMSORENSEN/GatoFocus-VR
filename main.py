import argparse
import ctypes
import logging
import os
from pathlib import Path
import sys


def main():
    from gatofocus.engine import DATA
    DATA.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None:
        sys.stdout = open(DATA / "console.log", "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = sys.stdout
    logging.basicConfig(filename=DATA / "app.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    # Avoid duplicate OSC writers. Handle must remain alive for the process lifetime.
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel.CreateMutexW(None, False, "Local\\GatoFocusVR.Application")
    if ctypes.get_last_error() == 183:
        ctypes.windll.user32.MessageBoxW(None, "O GatoFocus VR já está aberto. Confira a barra de tarefas.", "GatoFocus VR", 0)
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
        from gatofocus.ui import App
        App(root, args.start).mainloop()
    except Exception:
        logging.exception("Application failed")
        ctypes.windll.user32.MessageBoxW(None, f"Não foi possível abrir. Consulte {DATA / 'app.log'}", "GatoFocus VR", 0x10)
    finally:
        if mutex:
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle(mutex)


if __name__ == "__main__":
    main()
