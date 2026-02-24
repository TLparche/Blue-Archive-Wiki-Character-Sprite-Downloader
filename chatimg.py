import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk

PNG_EXT = ".png"


def next_available_path(dst_dir: Path, filename: str) -> Path:
    base = Path(filename).stem
    ext = Path(filename).suffix
    candidate = dst_dir / filename
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        cand = dst_dir / f"{base}_{i}{ext}"
        if not cand.exists():
            return cand
        i += 1


class ChatImageBuilder:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Chat Image Builder")

        self.emotion_root = Path("./emotion")
        self.out_root = Path("./chatimg")
        self.out_root.mkdir(parents=True, exist_ok=True)

        self.char_dir: Path | None = None
        self.image_paths: list[Path] = []
        self.preview_path: Path | None = None
        self.preview_imgtk: ImageTk.PhotoImage | None = None

        self._build_ui()
        self.refresh_character_list()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Character:").pack(side="left")
        self.char_var = tk.StringVar(value="")
        self.char_combo = ttk.Combobox(top, textvariable=self.char_var, state="readonly", width=28)
        self.char_combo.pack(side="left", padx=(6, 10))
        self.char_combo.bind("<<ComboboxSelected>>", lambda e: self.on_character_selected())

        tk.Button(top, text="새로고침", command=self.refresh_character_list).pack(side="left")
        tk.Button(top, text="Generate Selected", command=self.generate).pack(side="right")

        mid = tk.Frame(self.root)
        mid.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        left = tk.Frame(mid)
        left.pack(side="left", fill="y")

        tk.Label(left, text="Images:").pack(anchor="w")
        self.listbox = tk.Listbox(left, height=18, width=34)
        self.listbox.pack(fill="y", pady=(4, 0))
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.on_image_selected())

        right = tk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        size_row = tk.Frame(right)
        size_row.pack(fill="x")

        tk.Label(size_row, text="Img Size:").pack(side="left")
        self.img_w_var = tk.StringVar(value="200")
        self.img_h_var = tk.StringVar(value="200")
        tk.Entry(size_row, textvariable=self.img_w_var, width=6).pack(side="left", padx=(6, 2))
        tk.Label(size_row, text="x").pack(side="left")
        tk.Entry(size_row, textvariable=self.img_h_var, width=6).pack(side="left", padx=(2, 10))

        tk.Label(size_row, text="Out Size:").pack(side="left")
        self.out_w_var = tk.StringVar(value="800")
        self.out_h_var = tk.StringVar(value="200")
        tk.Entry(size_row, textvariable=self.out_w_var, width=6).pack(side="left", padx=(6, 2))
        tk.Label(size_row, text="x").pack(side="left")
        tk.Entry(size_row, textvariable=self.out_h_var, width=6).pack(side="left", padx=(2, 10))

        tk.Button(size_row, text="Generate All", command=self.generate_all).pack(side="right")

        self.status = tk.Label(right, text="emotion 폴더를 읽습니다.", anchor="w")
        self.status.pack(fill="x")

        self.canvas = tk.Canvas(right, bg="#111111", width=620, height=280, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(6, 0))

    def refresh_character_list(self):
        if not self.emotion_root.exists() or not self.emotion_root.is_dir():
            self.char_combo["values"] = []
            self.char_var.set("")
            self.listbox.delete(0, "end")
            self._clear_preview()
            self.status.config(text=f"./emotion 폴더를 찾지 못했습니다: {self.emotion_root.resolve()}")
            return

        chars = sorted([p.name for p in self.emotion_root.iterdir() if p.is_dir()])
        self.char_combo["values"] = chars

        if not chars:
            self.char_var.set("")
            self.listbox.delete(0, "end")
            self._clear_preview()
            self.status.config(text=f"./emotion 안에 캐릭터 폴더가 없습니다: {self.emotion_root.resolve()}")
            return

        if self.char_var.get() not in chars:
            self.char_var.set(chars[0])
        self.on_character_selected()

    def _clear_preview(self):
        self.preview_imgtk = None
        self.canvas.delete("all")

    def on_character_selected(self):
        name = self.char_var.get().strip()
        if not name:
            return

        self.char_dir = self.emotion_root / name
        if not self.char_dir.exists():
            self.listbox.delete(0, "end")
            self._clear_preview()
            self.status.config(text=f"폴더가 없습니다: {self.char_dir}")
            return

        self.image_paths = self._scan_png(self.char_dir)
        self.listbox.delete(0, "end")
        for p in self.image_paths:
            self.listbox.insert("end", p.name)

        if not self.image_paths:
            self._clear_preview()
            self.status.config(text=f"{name}: PNG가 없습니다.")
            return

        self.listbox.selection_set(0)
        self.on_image_selected()

    def _scan_png(self, folder: Path) -> list[Path]:
        out = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == PNG_EXT]
        out.sort(key=lambda p: p.name.lower())
        return out

    def on_image_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.image_paths):
            return
        self.preview_path = self.image_paths[idx]
        self._render_preview(self.preview_path)
        self.status.config(text=f"캐릭터: {self.char_dir.name} | 미리보기: {self.preview_path.name}")

    def _render_preview(self, img_path: Path):
        try:
            img = Image.open(img_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
        except Exception as e:
            messagebox.showerror("오류", f"PNG 로드 실패:\n{img_path}\n{e}")
            return

        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        ow, oh = img.size
        scale = min(cw / ow, ch / oh, 2.0)
        pw = max(1, int(ow * scale))
        ph = max(1, int(oh * scale))
        preview = img.resize((pw, ph), Image.Resampling.LANCZOS)
        self.preview_imgtk = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        x0 = (cw - pw) // 2
        y0 = (ch - ph) // 2
        self.canvas.create_image(x0, y0, anchor="nw", image=self.preview_imgtk)

    def generate(self):
        if self.char_dir is None:
            messagebox.showwarning("안내", "캐릭터를 선택하세요.")
            return
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("안내", "이미지를 선택하세요.")
            return
        img_path = self.image_paths[sel[0]]
        self._generate_images([img_path])

    def generate_all(self):
        if self.char_dir is None:
            messagebox.showwarning("안내", "캐릭터를 선택하세요.")
            return
        if not self.image_paths:
            messagebox.showwarning("안내", "이미지가 없습니다.")
            return
        self._generate_images(self.image_paths)

    def _parse_int(self, raw: str, label: str) -> int | None:
        raw = raw.strip()
        if not raw:
            messagebox.showwarning("안내", f"{label} 값을 입력하세요.")
            return None
        try:
            val = int(raw)
        except ValueError:
            messagebox.showwarning("안내", f"{label} 값이 숫자가 아닙니다: {raw}")
            return None
        if val <= 0:
            messagebox.showwarning("안내", f"{label} 값은 1 이상이어야 합니다.")
            return None
        return val

    def _get_sizes(self) -> tuple[int, int, int, int] | None:
        img_w = self._parse_int(self.img_w_var.get(), "Img Width")
        if img_w is None:
            return None
        img_h = self._parse_int(self.img_h_var.get(), "Img Height")
        if img_h is None:
            return None
        out_w = self._parse_int(self.out_w_var.get(), "Out Width")
        if out_w is None:
            return None
        out_h = self._parse_int(self.out_h_var.get(), "Out Height")
        if out_h is None:
            return None
        return img_w, img_h, out_w, out_h

    def _generate_images(self, img_paths: list[Path]):
        sizes = self._get_sizes()
        if sizes is None:
            return
        img_w, img_h, out_w, out_h = sizes

        out_char_dir = self.out_root / self.char_dir.name
        out_char_dir.mkdir(parents=True, exist_ok=True)

        success = 0
        for img_path in img_paths:
            try:
                img = Image.open(img_path)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
            except Exception as e:
                messagebox.showerror("오류", f"PNG 로드 실패:\n{img_path}\n{e}")
                continue

            if img.size != (img_w, img_h):
                img = img.resize((img_w, img_h), Image.Resampling.LANCZOS)

            margin = 50

            out_left = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
            x_left = margin
            out_left.paste(img, (x_left, 0))

            left_name = f"{img_path.stem}_left{img_path.suffix}"
            out_left_path = next_available_path(out_char_dir, left_name)
            out_left.save(out_left_path, format="PNG")
            success += 1

            out_right = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
            x_right = out_w - img_w - margin
            x_right = max(0, x_right)
            out_right.paste(img, (x_right, 0))

            right_name = f"{img_path.stem}_right{img_path.suffix}"
            out_right_path = next_available_path(out_char_dir, right_name)
            out_right.save(out_right_path, format="PNG")
            success += 1

        if success == 0:
            messagebox.showwarning("안내", "생성된 이미지가 없습니다.")
            return

        messagebox.showinfo(
            "완료",
            f"생성 완료!\n"
            f"- 캐릭터: {self.char_dir.name}\n"
            f"- 처리한 이미지: {success}개\n"
            f"- 출력 폴더: {out_char_dir}"
        )


def main():
    root = tk.Tk()
    app = ChatImageBuilder(root)
    root.mainloop()


if __name__ == "__main__":
    main()
