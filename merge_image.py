import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

class OverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG Overlay Merger")

        self.img1_path = tk.StringVar()
        self.img2_path = tk.StringVar()

        frame = tk.Frame(root, padx=15, pady=15)
        frame.pack(fill="both", expand=True)

        # Image 1
        tk.Label(frame, text="Base Image (아래 이미지)").grid(row=0, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.img1_path, width=60).grid(row=1, column=0)
        tk.Button(frame, text="Browse", command=self.pick_img1).grid(row=1, column=1)

        # Image 2
        tk.Label(frame, text="Overlay Image (위에 올라갈 이미지)").grid(row=2, column=0, sticky="w", pady=(10,0))
        tk.Entry(frame, textvariable=self.img2_path, width=60).grid(row=3, column=0)
        tk.Button(frame, text="Browse", command=self.pick_img2).grid(row=3, column=1)

        tk.Button(frame, text="Merge & Save", command=self.merge, width=15)\
            .grid(row=4, column=0, columnspan=2, pady=15)

    def pick_img1(self):
        path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if path:
            self.img1_path.set(path)

    def pick_img2(self):
        path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if path:
            self.img2_path.set(path)

    def merge(self):
        p1 = self.img1_path.get()
        p2 = self.img2_path.get()

        if not p1 or not p2:
            messagebox.showerror("Error", "두 PNG 파일을 모두 선택해.")
            return

        try:
            img1 = Image.open(p1).convert("RGBA")
            img2 = Image.open(p2).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"이미지 로딩 실패:\n{e}")
            return

        if img1.size != img2.size:
            messagebox.showerror("Error",
                f"사이즈가 다름.\nImage1: {img1.size}\nImage2: {img2.size}")
            return

        # 정확한 알파 합성
        merged = Image.alpha_composite(img1, img2)

        default_name = "overlay_result.png"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG Files", "*.png")]
        )

        if not save_path:
            return

        merged.save(save_path)
        messagebox.showinfo("Done", f"저장 완료:\n{save_path}")


if __name__ == "__main__":
    # pip install pillow 필요
    root = tk.Tk()
    app = OverlayApp(root)
    root.mainloop()