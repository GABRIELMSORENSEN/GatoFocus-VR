import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from .engine import DATA
from .examples import save_example
from .theme import COLORS as C, FONT


class ExampleEditor(ctk.CTkToplevel):
    def __init__(self, master, image, boxes, source):
        super().__init__(master)
        self.title("Exemplo de avatar · GatoFocus")
        self.configure(fg_color=C["background"])
        self.image, self.source = image.copy(), source
        self.boxes = [list(b) for b in boxes]
        self.start = None
        self.draft = None
        self.geometry("720x720")
        self.resizable(False, False)
        self.transient(master)
        ctk.CTkLabel(self, text="Marque os avatares deste quadro", font=(FONT, 22, "bold")).pack(pady=(18, 8))
        ctk.CTkLabel(self, text="Arraste ao redor de cada avatar, incluindo o corpo visível.\nBotão direito remove uma marcação. Corrija também as sugestões da IA.",
                     font=(FONT, 13), text_color=C["muted"]).pack(pady=(0, 12))
        h, w = image.shape[:2]
        scale = min(650 / w, 450 / h)
        self.w, self.h = round(w * scale), round(h * scale)
        self.canvas = tk.Canvas(self, width=self.w, height=self.h, highlightthickness=0, bg=C["surface"])
        self.canvas.pack()
        self.photo = ImageTk.PhotoImage(Image.fromarray(image[:, :, ::-1]).resize((self.w, self.h)))
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.canvas.bind("<ButtonPress-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end)
        self.canvas.bind("<Button-3>", self.remove)
        self.note = ctk.CTkLabel(self, text="Salvo somente neste PC. Coletar exemplos ainda não altera o modelo.",
                                font=(FONT, 12), text_color=C["muted"], wraplength=650)
        self.note.pack(pady=12)
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=6)
        ctk.CTkButton(buttons, text="Limpar marcações", command=self.clear, fg_color=C["raised"]).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text="Salvar exemplo", command=self.save, fg_color=C["primary"], text_color=C["background"]).pack(side="left", padx=5)
        ctk.CTkButton(buttons, text="Abrir pasta", command=lambda: self.open_folder(), fg_color=C["raised"]).pack(side="left", padx=5)
        self.redraw()

    def point(self, event):
        return max(0, min(self.w, event.x)), max(0, min(self.h, event.y))

    def begin(self, event):
        self.start = self.point(event)

    def drag(self, event):
        if self.start:
            if self.draft:
                self.canvas.delete(self.draft)
            self.draft = self.canvas.create_rectangle(*self.start, *self.point(event), outline=C["primary"], width=2)

    def end(self, event):
        if self.start:
            x, y = self.point(event)
            x0, y0 = self.start
            if abs(x-x0) > 8 and abs(y-y0) > 8:
                self.boxes.append([min(x,x0)/self.w, min(y,y0)/self.h, max(x,x0)/self.w, max(y,y0)/self.h])
        if self.draft:
            self.canvas.delete(self.draft)
        self.start = self.draft = None
        self.redraw()

    def remove(self, event):
        x,y = self.point(event)
        for i in range(len(self.boxes)-1, -1, -1):
            x1,y1,x2,y2 = self.boxes[i]
            if x1 <= x/self.w <= x2 and y1 <= y/self.h <= y2:
                self.boxes.pop(i)
                break
        self.redraw()

    def clear(self):
        self.boxes.clear()
        self.redraw()

    def redraw(self):
        self.canvas.delete("box")
        for i, (x1,y1,x2,y2) in enumerate(self.boxes):
            self.canvas.create_rectangle(x1*self.w,y1*self.h,x2*self.w,y2*self.h, outline=C["success"], width=2, tags="box")
            self.canvas.create_text(x1*self.w+4,y1*self.h+4, text=str(i+1), anchor="nw",fill=C["success"],tags="box")

    def save(self):
        try:
            save_example(DATA / "examples", self.image, self.boxes, self.source)
            self.note.configure(text=f"Exemplo salvo com {len(self.boxes)} avatar(es). O modelo atual não foi alterado.", text_color=C["success"])
        except (ValueError, OSError) as exc:
            self.note.configure(text=str(exc), text_color=C["warning"])

    def open_folder(self):
        folder = DATA / "examples"
        folder.mkdir(exist_ok=True)
        os.startfile(folder)
