import math
from pathlib import Path
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw
from .theme import COLORS as C, FONT, MONO
from .engine import Engine


class App(ctk.CTk):
    def __init__(self, root, autostart=False):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title("GatoFocus VR")
        self.iconbitmap(str(Path(root) / "assets/gatofocus.ico"))
        self.geometry("850x850")
        self.minsize(800, 810)
        self.configure(fg_color=C["background"])
        self.engine = Engine(root)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        ctk.CTkLabel(header, text="◉  GatoFocus", font=(FONT, 28, "bold"), text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(header, text="VR  /  OLHAR POR ESTIMATIVA", font=(MONO, 11), text_color=C["muted"]).pack(side="right")
        self.state_label = ctk.CTkLabel(self, text="Preparando…", font=(FONT, 23, "bold"), text_color=C["primary"], anchor="w")
        self.state_label.grid(row=1, column=0, padx=28, pady=(0, 10), sticky="ew")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, padx=28, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, minsize=250)
        body.grid_rowconfigure(0, weight=1)
        preview = ctk.CTkFrame(body, fg_color=C["surface"], corner_radius=18)
        preview.grid(row=0, column=0, padx=(0, 18), sticky="nsew")
        self.preview = ctk.CTkLabel(preview, text="", fg_color=C["surface"])
        self.preview.pack(expand=True, fill="both", padx=12, pady=12)
        self.preview_var = tk.BooleanVar(value=True)
        self.preview_switch = ctk.CTkSwitch(preview, text="Mostrar prévia", variable=self.preview_var,
                                          font=(FONT, 12), progress_color=C["primary"], text_color=C["muted"])
        self.preview_switch.pack(pady=(0, 14))
        side = ctk.CTkFrame(body, fg_color="transparent", width=250)
        side.grid(row=0, column=1, sticky="nsew")
        source = ctk.CTkOptionMenu(side, values=["PC · Janela do VRChat", "Quest · SteamVR"], font=(FONT, 13),
                                  fg_color=C["raised"], button_color=C["border"], text_color=C["text"],
                                  command=lambda v: self.engine.update(source="desktop" if v.startswith("PC") else "steamvr"))
        source.set("PC · Janela do VRChat" if self.engine.config["source"] == "desktop" else "Quest · SteamVR")
        source.pack(fill="x", pady=(0, 12))
        self.toggle = ctk.CTkButton(side, text="Iniciar rastreamento", height=48, font=(FONT, 15, "bold"),
                                   fg_color=C["primary"], hover_color="#B4D3FF", text_color=C["background"], command=self.toggle_run)
        self.toggle.pack(fill="x", pady=(0, 16))
        self.detail = ctk.CTkLabel(side, text="", wraplength=238, justify="left", anchor="w", font=(FONT, 14), text_color=C["muted"])
        self.detail.pack(fill="x", pady=(0, 14))
        self.osc_label = ctk.CTkLabel(side, text="OSC: verificando…", font=(FONT, 13), text_color=C["warning"], anchor="w")
        self.osc_label.pack(fill="x")
        self.metrics = ctk.CTkLabel(side, text="", justify="left", anchor="w", font=(MONO, 12), text_color=C["muted"])
        self.metrics.pack(fill="x", pady=(14, 18))
        self.hold_var = tk.BooleanVar(value=self.engine.config["hold"])
        ctk.CTkSwitch(side, text="Evitar troca de pessoa", variable=self.hold_var, font=(FONT, 13),
                      progress_color=C["primary"], command=lambda: self.engine.update(hold=self.hold_var.get())).pack(anchor="w")
        ctk.CTkButton(side, text="Escolher novamente", height=36, fg_color=C["raised"], hover_color=C["border"],
                      text_color=C["text"], command=self.reset_focus).pack(fill="x", pady=(12, 0))
        self.example_button = ctk.CTkButton(side, text="Salvar exemplo de avatar", height=36, fg_color=C["raised"],
                                           hover_color=C["border"], command=self.example)
        self.example_button.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(side, text="Minimizar mantém o rastreamento.\nFechar encerra o aplicativo.", font=(FONT, 12),
                     text_color=C["muted"], justify="left").pack(anchor="w", pady=(16, 0))
        controls = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=16)
        controls.grid(row=3, column=0, padx=28, pady=(18, 12), sticky="ew")
        for col in range(3):
            controls.grid_columnconfigure(col, weight=1, uniform="settings")
        profiles = {"Leve · 6 Hz": 6, "Equilibrado · 10 Hz": 10, "Fluido · 15 Hz": 15}
        ctk.CTkLabel(controls, text="Ritmo de análise", font=(FONT, 13), text_color=C["muted"]).grid(row=0, column=0, padx=12, pady=(12, 4))
        profile = ctk.CTkOptionMenu(controls, values=list(profiles), width=210, font=(FONT, 12), fg_color=C["raised"],
                                   button_color=C["border"], text_color=C["text"],
                                   command=lambda v: self.engine.update(fps=profiles[v]))
        profile.set(next((k for k, v in profiles.items() if v == self.engine.config["fps"]), "Leve · 6 Hz"))
        profile.grid(row=1, column=0, padx=14, pady=(0, 16))
        self.focus_label = ctk.CTkLabel(controls, text=f"Área de foco · {self.engine.config['focus_radius']:.0f}°", font=(FONT, 13), text_color=C["muted"])
        self.focus_label.grid(row=0, column=1, pady=(12, 4))
        slider = ctk.CTkSlider(controls, from_=12, to=40, number_of_steps=28, width=180,
                               progress_color=C["primary"], button_color=C["primary"], command=self.focus_change)
        slider.set(self.engine.config["focus_radius"])
        slider.grid(row=1, column=1, padx=14, pady=(0, 16))
        ctk.CTkLabel(controls, text="Detecção de avatares", font=(FONT, 13), text_color=C["muted"]).grid(row=0, column=2, pady=(12, 4))
        sensitivity = ctk.CTkOptionMenu(controls, values=["Normal", "Mais sensível", "Mais seletiva"], width=190,
                                       fg_color=C["raised"], button_color=C["border"], text_color=C["text"], font=(FONT, 12),
                                       command=lambda v: self.engine.update(confidence={"Normal": .27, "Mais sensível": .16, "Mais seletiva": .4}[v]))
        confidence = self.engine.config["confidence"]
        sensitivity.set("Mais sensível" if confidence < .2 else "Mais seletiva" if confidence > .35 else "Normal")
        sensitivity.grid(row=1, column=2, padx=14, pady=(0, 16))
        self.help_text = ctk.CTkLabel(self, text="No VRChat: menu de ações → Opções → OSC → Ativado. Seu avatar precisa de olhos configurados.",
                                     wraplength=780, justify="left", anchor="w", font=(FONT, 12), text_color=C["muted"])
        self.help_text.grid(row=4, column=0, padx=28, pady=(0, 5), sticky="ew")
        ctk.CTkLabel(self, text="IA local · sem câmera · sem identificar nomes · não mede seus olhos de verdade",
                     font=(FONT, 11), text_color=C["muted"], anchor="w").grid(row=5, column=0, padx=28, pady=(0, 20), sticky="ew")
        self.photo = None
        if autostart:
            self.engine.set_enabled(True)
        self.after(250, self.refresh)

    def toggle_run(self):
        self.engine.set_enabled(not self.engine.enabled)

    def reset_focus(self):
        with self.engine.lock:
            self.engine.reset_requested = True
            self.engine.desired = None

    def example(self):
        state, frame, config, _ = self.engine.snapshot()
        if frame is not None:
            from .annotation_ui import ExampleEditor
            ExampleEditor(self, frame, state.get("boxes", []), config["source"])

    def focus_change(self, value):
        self.focus_label.configure(text=f"Área de foco · {value:.0f}°")
        self.engine.update(focus_radius=round(value))

    def refresh(self):
        state, frame, config, enabled = self.engine.snapshot()
        self.state_label.configure(text=state["state"], text_color=C["success"] if state["target"] else C["primary"])
        self.toggle.configure(text="Pausar rastreamento" if enabled else "Iniciar rastreamento")
        self.detail.configure(text=state["detail"])
        self.example_button.configure(state="normal" if frame is not None else "disabled")
        self.osc_label.configure(text="OSC: VRChat escutando" if state["osc"] else "OSC: ative no VRChat",
                                 text_color=C["success"] if state["osc"] else C["warning"])
        self.metrics.configure(text=f"{state['people']} candidato(s) · 1 alvo máximo\n{state['inference_ms']:.1f} ms / análise · {state['fps']:.0f} Hz\nCPU {state['cpu']:.1f}% · RAM {state['ram_mb']} MB\n{state['packets']} envios OSC")
        if self.state() != "iconic":
            size = max(200, min(self.preview.winfo_width(), self.preview.winfo_height(), 450))
            if frame is not None and self.preview_var.get():
                # Keep the source aspect ratio; the normalized gaze frame remains accurate.
                width, height = size, round(size * frame.shape[0] / frame.shape[1])
                if height > size:
                    width, height = round(size * frame.shape[1] / frame.shape[0]), size
                image = Image.fromarray(frame[:, :, ::-1]).resize((width, height))
                draw = ImageDraw.Draw(image)
                for box in state.get("boxes", []):
                    draw.rectangle(tuple(v * s for v, s in zip(box, [width,height,width,height])), outline=C["muted"], width=1)
                if state["target"]:
                    b = state["target"]
                    draw.rectangle(tuple(v * s for v, s in zip(b, [width,height,width,height])), outline=C["success"], width=3)
                    x, y = (b[0] + b[2]) / 2 * width, (b[1] + .14 * (b[3] - b[1])) * height
                    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=C["success"])
            else:
                image = Image.new("RGB", (size, size), C["surface"])
                draw = ImageDraw.Draw(image)
                draw.text((size / 2, size / 2 + 55), "Aguardando imagem VR" if frame is None else "Previa desativada", fill=C["muted"], anchor="mm")
            w,h = image.size
            proj = state.get("projection", [-1,1,-1,1])
            cx, cy = -proj[0]/(proj[1]-proj[0])*w, -proj[2]/(proj[3]-proj[2])*h
            rx = math.tan(math.radians(config["focus_radius"])) * w / (proj[1]-proj[0])
            ry = math.tan(math.radians(config["focus_radius"])) * h / (proj[3]-proj[2])
            draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), outline=C["primary"], width=1)
            draw.line((cx-8, cy, cx+8, cy), fill=C["primary"], width=2)
            draw.line((cx, cy-8, cx, cy+8), fill=C["primary"], width=2)
            self.photo = ctk.CTkImage(image, size=image.size)
            self.preview.configure(image=self.photo, text="")
        self.after(250, self.refresh)

    def close(self):
        self.engine.close()
        self.destroy()
