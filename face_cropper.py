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


class EmotionCropperPNG:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PNG Emotion Cropper")

        self.images_root = Path("./images")
        self.out_root = Path("./emotion")
        self.out_root.mkdir(parents=True, exist_ok=True)

        self.char_dir: Path | None = None
        self.section_dir: Path | None = None

        self.section_images: list[Path] = []
        self.preview_path: Path | None = None

        self.orig_img: Image.Image | None = None
        self.preview_imgtk: ImageTk.PhotoImage | None = None
        self.preview_scale = 1.0
        self.preview_w = 0
        self.preview_h = 0
        self.img_offset_x = 0
        self.img_offset_y = 0

        self.crop_size = 200
        self.output_size = 0

        self.crop_x = 0
        self.crop_y = 0

        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.rect_id = None

        self.crop_state: dict[tuple[str, str], tuple[int, int, int, int]] = {}

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

        tk.Label(top, text="Section:").pack(side="left")
        self.sec_var = tk.StringVar(value="")
        self.sec_combo = ttk.Combobox(top, textvariable=self.sec_var, state="readonly", width=28)
        self.sec_combo.pack(side="left", padx=(6, 10))
        self.sec_combo.bind("<<ComboboxSelected>>", lambda e: self.on_section_selected())

        tk.Button(top, text="새로고침", command=self.refresh_character_list).pack(side="left")
        tk.Button(top, text="변환 (emotion 저장)", command=self.process_section).pack(side="right")

        mid = tk.Frame(self.root)
        mid.pack(fill="x", padx=10, pady=(0, 6))

        tk.Label(mid, text="Crop Size:").pack(side="left")
        self.crop_entry = tk.Entry(mid, width=6)
        self.crop_entry.insert(0, "200")
        self.crop_entry.pack(side="left", padx=(4, 10))

        tk.Label(mid, text="Output Size:").pack(side="left")
        self.out_entry = tk.Entry(mid, width=6)
        self.out_entry.insert(0, "0")
        self.out_entry.pack(side="left", padx=(4, 6))
        tk.Label(mid, text="(0이면 리사이즈 없음)").pack(side="left", padx=(0, 10))

        tk.Button(mid, text="적용", command=self.apply_sizes).pack(side="left")

        self.status = tk.Label(self.root, text="현재 폴더의 ./images 를 읽습니다.", anchor="w")
        self.status.pack(fill="x", padx=10, pady=(0, 6))

        self.canvas = tk.Canvas(self.root, bg="#111111", width=900, height=600, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.root.bind("<Configure>", self.on_resize)

    def refresh_character_list(self):
        if not self.images_root.exists() or not self.images_root.is_dir():
            self.char_combo["values"] = []
            self.sec_combo["values"] = []
            self.char_var.set("")
            self.sec_var.set("")
            self.clear_preview()
            self.status.config(text=f"./images 폴더를 찾지 못했습니다: {self.images_root.resolve()}")
            return

        chars = sorted([p.name for p in self.images_root.iterdir() if p.is_dir()])
        self.char_combo["values"] = chars

        if not chars:
            self.char_var.set("")
            self.sec_combo["values"] = []
            self.sec_var.set("")
            self.clear_preview()
            self.status.config(text=f"./images 안에 캐릭터 폴더가 없습니다: {self.images_root.resolve()}")
            return

        if self.char_var.get() not in chars:
            self.char_var.set(chars[0])
        self.on_character_selected()

    def clear_preview(self):
        self.orig_img = None
        self.preview_imgtk = None
        self.canvas.delete("all")
        self.rect_id = None

    def _read_int(self, entry: tk.Entry, name: str) -> int | None:
        try:
            return int(entry.get().strip())
        except Exception:
            messagebox.showerror("입력 오류", f"{name}는 정수로 입력하세요.")
            return None

    def apply_sizes(self):
        cs = self._read_int(self.crop_entry, "Crop Size")
        osz = self._read_int(self.out_entry, "Output Size")
        if cs is None or osz is None:
            return
        if cs <= 0:
            messagebox.showerror("입력 오류", "Crop Size는 1 이상이어야 합니다.")
            return
        if osz < 0:
            messagebox.showerror("입력 오류", "Output Size는 0 이상이어야 합니다.")
            return

        self.crop_size = cs
        self.output_size = osz

        self._save_state()
        if self.orig_img is not None:
            self._clamp_crop_to_image()
            self.render_preview()

    def _sections_under_char(self, char_dir: Path) -> list[str]:
        secs = [p.name for p in char_dir.iterdir() if p.is_dir()]
        secs.sort(key=lambda x: x.lower())
        return secs

    def on_character_selected(self):
        name = self.char_var.get().strip()
        if not name:
            return

        self.char_dir = self.images_root / name
        secs = self._sections_under_char(self.char_dir)
        self.sec_combo["values"] = secs

        if not secs:
            self.sec_var.set("")
            self.clear_preview()
            self.status.config(text=f"{name}: section 폴더가 없습니다.")
            return

        if self.sec_var.get() not in secs:
            self.sec_var.set(secs[0])
        self.on_section_selected()

    def _scan_png_in_dir(self, folder: Path) -> list[Path]:
        out = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == PNG_EXT]
        out.sort(key=lambda p: p.name.lower())
        return out

    def on_section_selected(self):
        if self.char_dir is None:
            return
        sec = self.sec_var.get().strip()
        if not sec:
            return

        self.section_dir = self.char_dir / sec
        if not self.section_dir.exists():
            self.clear_preview()
            self.status.config(text=f"섹션 폴더가 없습니다: {self.section_dir}")
            return

        self.section_images = self._scan_png_in_dir(self.section_dir)
        if not self.section_images:
            self.clear_preview()
            self.status.config(text=f"{self.char_dir.name}/{sec}: PNG가 없습니다.")
            return

        self.preview_path = self.section_images[0]

        self._load_state_or_center()
        self.load_preview(self.preview_path)

        self.status.config(
            text=f"캐릭터: {self.char_dir.name} | 섹션: {sec} | PNG {len(self.section_images)}개 | 미리보기: {self.preview_path.name}"
        )

    def _state_key(self) -> tuple[str, str] | None:
        if self.char_dir is None or self.section_dir is None:
            return None
        return (self.char_dir.name, self.section_dir.name)

    def _save_state(self):
        k = self._state_key()
        if not k:
            return
        self.crop_state[k] = (self.crop_x, self.crop_y, self.crop_size, self.output_size)

    def _load_state_or_center(self):
        k = self._state_key()
        if not k:
            return
        if k in self.crop_state:
            x, y, cs, osz = self.crop_state[k]
            self.crop_size = cs
            self.output_size = osz
            self.crop_entry.delete(0, "end")
            self.crop_entry.insert(0, str(cs))
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, str(osz))
            self.crop_x = x
            self.crop_y = y

    def load_preview(self, img_path: Path):
        try:
            img = Image.open(img_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
        except Exception as e:
            messagebox.showerror("오류", f"PNG 로드 실패:\n{img_path}\n{e}")
            return

        self.orig_img = img
        if self.crop_x == 0 and self.crop_y == 0:
            self._center_crop()
        self._clamp_crop_to_image()
        self.render_preview()

    def _center_crop(self):
        if self.orig_img is None:
            return
        ow, oh = self.orig_img.size
        self.crop_x = max(0, (ow - self.crop_size) // 2)
        self.crop_y = max(0, (oh - self.crop_size) // 2)

    def on_resize(self, event):
        if self.orig_img is None:
            return
        self.render_preview()

    def render_preview(self):
        if self.orig_img is None:
            return

        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())

        ow, oh = self.orig_img.size
        scale = min(cw / ow, ch / oh)
        scale = min(scale, 2.0)

        self.preview_scale = scale
        self.preview_w = max(1, int(ow * scale))
        self.preview_h = max(1, int(oh * scale))

        preview = self.orig_img.resize((self.preview_w, self.preview_h), Image.Resampling.LANCZOS)
        self.preview_imgtk = ImageTk.PhotoImage(preview)

        self.canvas.delete("all")

        x0 = (cw - self.preview_w) // 2
        y0 = (ch - self.preview_h) // 2
        self.img_offset_x = x0
        self.img_offset_y = y0

        self.canvas.create_image(x0, y0, anchor="nw", image=self.preview_imgtk)

        rx1, ry1, rx2, ry2 = self._crop_rect_preview_coords()
        self.rect_id = self.canvas.create_rectangle(rx1, ry1, rx2, ry2, outline="#00ff7f", width=3)

        self._update_status()

    def _crop_rect_preview_coords(self):
        px = self.img_offset_x + int(self.crop_x * self.preview_scale)
        py = self.img_offset_y + int(self.crop_y * self.preview_scale)
        ps = int(self.crop_size * self.preview_scale)
        return px, py, px + ps, py + ps

    def _update_rect(self):
        if self.rect_id is None:
            return
        rx1, ry1, rx2, ry2 = self._crop_rect_preview_coords()
        self.canvas.coords(self.rect_id, rx1, ry1, rx2, ry2)
        self._update_status()

    def _update_status(self):
        if self.orig_img is None:
            return
        ow, oh = self.orig_img.size
        c = self.char_dir.name if self.char_dir else "-"
        s = self.section_dir.name if self.section_dir else "-"
        self.status.config(
            text=f"캐릭터: {c} | 섹션: {s} | Crop={self.crop_size} | Output={self.output_size} | "
                 f"x={self.crop_x}, y={self.crop_y} | 원본={ow}x{oh}"
        )

    def _clamp_crop_to_image(self):
        if self.orig_img is None:
            return
        ow, oh = self.orig_img.size
        max_x = max(0, ow - self.crop_size)
        max_y = max(0, oh - self.crop_size)
        self.crop_x = min(max(self.crop_x, 0), max_x)
        self.crop_y = min(max(self.crop_y, 0), max_y)

    def on_mouse_down(self, event):
        if self.rect_id is None:
            return
        rx1, ry1, rx2, ry2 = self.canvas.coords(self.rect_id)
        if rx1 <= event.x <= rx2 and ry1 <= event.y <= ry2:
            self.dragging = True
            self.drag_offset_x = event.x - rx1
            self.drag_offset_y = event.y - ry1
        else:
            self.dragging = False

    def on_mouse_move(self, event):
        if not self.dragging or self.orig_img is None:
            return

        new_rx1 = event.x - self.drag_offset_x
        new_ry1 = event.y - self.drag_offset_y

        img_rel_x = new_rx1 - self.img_offset_x
        img_rel_y = new_ry1 - self.img_offset_y

        ps = self.crop_size * self.preview_scale
        img_rel_x = min(max(img_rel_x, 0), max(0, self.preview_w - ps))
        img_rel_y = min(max(img_rel_y, 0), max(0, self.preview_h - ps))

        self.crop_x = int(round(img_rel_x / self.preview_scale))
        self.crop_y = int(round(img_rel_y / self.preview_scale))

        self._clamp_crop_to_image()
        self._save_state()
        self._update_rect()

    def on_mouse_up(self, event):
        self.dragging = False
        self._save_state()

    def process_section(self):
        if self.char_dir is None or self.section_dir is None:
            messagebox.showwarning("안내", "캐릭터/섹션을 먼저 선택하세요.")
            return
        if not self.section_images:
            messagebox.showwarning("안내", "선택한 섹션에 PNG가 없습니다.")
            return

        out_char_dir = self.out_root / self.char_dir.name
        out_char_dir.mkdir(parents=True, exist_ok=True)

        ok, fail, skipped = 0, 0, 0

        for img_path in self.section_images:
            try:
                img = Image.open(img_path)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                ow, oh = img.size
                x = min(max(self.crop_x, 0), max(0, ow - self.crop_size))
                y = min(max(self.crop_y, 0), max(0, oh - self.crop_size))

                crop = img.crop((x, y, x + self.crop_size, y + self.crop_size))

                if self.output_size and self.output_size != self.crop_size:
                    crop = crop.resize((self.output_size, self.output_size), Image.Resampling.LANCZOS)

                out_path = next_available_path(out_char_dir, img_path.name)
                crop.save(out_path, format="PNG")
                ok += 1
            except Exception:
                fail += 1

        messagebox.showinfo(
            "완료",
            f"변환 완료!\n"
            f"- 캐릭터: {self.char_dir.name}\n"
            f"- 섹션: {self.section_dir.name}\n"
            f"- 저장 폴더: {out_char_dir}\n"
            f"- 성공: {ok}\n"
            f"- 실패: {fail}\n"
            f"(동명 파일은 _1, _2로 자동 저장)"
        )


def main():
    root = tk.Tk()
    app = EmotionCropperPNG(root)
    root.mainloop()


if __name__ == "__main__":
    main()
