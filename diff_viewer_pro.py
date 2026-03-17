import tkinter as tk
from tkinter import filedialog
import difflib
import json
import os

# ===== CONFIG PATH =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "diff_viewer_config.json")

class DiffApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diff Viewer PRO")
        self.root.geometry("1400x800")

        self.left_lines = []
        self.right_lines = []
        self.left_path = ""
        self.right_path = ""

        # ===== FONT / ZOOM =====
        self.font_size = 10
        self.font_family = "Consolas"

        # ===== FULLSCREEN =====
        self.fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)

        # ===== SHOW ONLY DIFFS MODE =====
        self.only_diffs = tk.BooleanVar(value=False)

        # ===== TOP PANEL =====
        self.top = tk.Frame(root)
        self.top.pack(fill=tk.X)

        tk.Button(self.top, text="Левый файл", command=self.load_left).pack(side=tk.LEFT)
        tk.Button(self.top, text="Правый файл", command=self.load_right).pack(side=tk.LEFT)
        tk.Button(self.top, text="Сравнить", command=self.compare).pack(side=tk.LEFT)
        tk.Checkbutton(
            self.top, text="Только различия",
            variable=self.only_diffs,
            command=self.compare
        ).pack(side=tk.LEFT, padx=6)

        self.status_label = tk.Label(self.top, text="  F11 — полный экран", anchor="w", fg="#888")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # ===== MAIN AREA =====
        self.main = tk.Frame(root)
        self.main.pack(fill=tk.BOTH, expand=True)

        # текстовые поля
        self.left_text = tk.Text(self.main, wrap="none")
        self.right_text = tk.Text(self.main, wrap="none")

        self.left_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # карта различий
        self.map_canvas = tk.Canvas(self.main, width=20, bg="#222")
        self.map_canvas.pack(side=tk.RIGHT, fill=tk.Y)

        # синхронный скролл
        self.left_text.config(yscrollcommand=self.sync_scroll)
        self.right_text.config(yscrollcommand=self.sync_scroll)

        # применяем шрифт
        self.update_font()

        # CTRL + колесо для zoom
        self.root.bind("<Control-MouseWheel>", self.zoom)

        # загрузка прошлых файлов
        self.load_last_files()

        # сохранение при закрытии
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== FULLSCREEN =====
    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        if self.fullscreen:
            self.top.pack_forget()
        else:
            # Убираем всё и пакуем заново в правильном порядке
            self.top.pack_forget()
            self.main.pack_forget()
            self.top.pack(fill=tk.X)
            self.main.pack(fill=tk.BOTH, expand=True)

    # ===== FILE LOAD =====
    def load_left(self):
        path = filedialog.askopenfilename()
        if path:
            self.left_path = path
            with open(path, encoding="utf-8", errors="ignore") as f:
                self.left_lines = f.readlines()
            self._update_status()

    def load_right(self):
        path = filedialog.askopenfilename()
        if path:
            self.right_path = path
            with open(path, encoding="utf-8", errors="ignore") as f:
                self.right_lines = f.readlines()
            self._update_status()

    def _update_status(self):
        left_name = os.path.basename(self.left_path) if self.left_path else "—"
        right_name = os.path.basename(self.right_path) if self.right_path else "—"
        self.status_label.config(text=f"  {left_name}  ↔  {right_name}    (F11 — полный экран)")

    # ===== COMPARE =====
    def compare(self):
        self.left_text.delete("1.0", tk.END)
        self.right_text.delete("1.0", tk.END)
        self.map_canvas.delete("all")

        if not self.left_lines and not self.right_lines:
            return

        d = list(difflib.ndiff(self.left_lines, self.right_lines))

        left_out = []
        right_out = []
        diff_positions = []

        line_index = 0

        for line in d:
            if line.startswith("- "):
                left_out.append(("diff", line[2:]))
                right_out.append(("diff", "\n"))
                diff_positions.append(line_index)
                line_index += 1
            elif line.startswith("+ "):
                left_out.append(("diff", "\n"))
                right_out.append(("diff", line[2:]))
                diff_positions.append(line_index)
                line_index += 1
            elif line.startswith("? "):
                continue
            else:
                if not self.only_diffs.get():
                    left_out.append(("same", line[2:]))
                    right_out.append(("same", line[2:]))
                    line_index += 1

        for (tag_l, l), (tag_r, r) in zip(left_out, right_out):
            self.left_text.insert(tk.END, l, tag_l)
            self.right_text.insert(tk.END, r, tag_r)

        # подсветка различий
        self.left_text.tag_config("diff", background="#ffcccc")
        self.right_text.tag_config("diff", background="#ccffcc")

        self.draw_map(diff_positions, len(left_out))

    # ===== MINI MAP =====
    def draw_map(self, diffs, total_lines):
        self.map_canvas.delete("all")

        if total_lines == 0:
            return

        h = self.map_canvas.winfo_height() or 800

        for pos in diffs:
            y = int((pos / total_lines) * h)
            self.map_canvas.create_line(0, y, 20, y, fill="red")

    # ===== SYNC SCROLL =====
    def sync_scroll(self, *args):
        self.left_text.yview_moveto(args[0])
        self.right_text.yview_moveto(args[0])

    # ===== FONT / ZOOM =====
    def update_font(self):
        font = (self.font_family, self.font_size)
        self.left_text.configure(font=font)
        self.right_text.configure(font=font)

    def zoom(self, event):
        if event.delta > 0:
            self.font_size += 1
        else:
            self.font_size -= 1

        self.font_size = max(5, min(self.font_size, 40))
        self.update_font()

    # ===== SAVE STATE =====
    def on_close(self):
        data = {
            "left": self.left_path,
            "right": self.right_path
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

        self.root.destroy()

    # ===== LOAD LAST FILES =====
    def load_last_files(self):
        if not os.path.exists(CONFIG_FILE):
            return

        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)

            loaded = False

            if data.get("left") and os.path.exists(data["left"]):
                self.left_path = data["left"]
                with open(self.left_path, encoding="utf-8", errors="ignore") as f:
                    self.left_lines = f.readlines()
                loaded = True

            if data.get("right") and os.path.exists(data["right"]):
                self.right_path = data["right"]
                with open(self.right_path, encoding="utf-8", errors="ignore") as f:
                    self.right_lines = f.readlines()
                loaded = True

            if loaded:
                self._update_status()
                self.root.after(100, self.compare)

        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = DiffApp(root)
    root.mainloop()
