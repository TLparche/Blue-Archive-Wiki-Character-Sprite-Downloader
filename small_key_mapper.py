import tkinter as tk
from tkinter import messagebox, ttk
import keyboard


class KeyMapper:
    def __init__(self, root):
        self.root = root
        self.root.title("키 매퍼")
        self.root.geometry("400x480")

        self.running = False
        self.presets = [
            ("s", "ctrl+shift+b"),
        ]

        # 입력부
        input_f = tk.Frame(root)
        input_f.pack(pady=15)

        tk.Label(input_f, text="원래 키:").grid(row=0, column=0, padx=5)
        self.ent_src = tk.Entry(input_f, width=12)
        self.ent_src.grid(row=0, column=1, padx=5)

        tk.Label(input_f, text="매핑 키:").grid(row=1, column=0, padx=5)
        self.ent_tgt = tk.Entry(input_f, width=12)
        self.ent_tgt.grid(row=1, column=1, padx=5)

        self.btn_add = tk.Button(root, text="목록 추가/수정", command=self.add)
        self.btn_add.pack(pady=5)

        # 리스트
        self.tree = ttk.Treeview(root, columns=("s", "t"), show="headings", height=10)
        self.tree.heading("s", text="기존 키")
        self.tree.heading("t", text="변경 키")
        self.tree.column("s", width=120, anchor="center")
        self.tree.column("t", width=200, anchor="center")
        self.tree.pack(pady=10, padx=15)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.btn_del = tk.Button(root, text="선택 삭제", command=self.delete)
        self.btn_del.pack()

        self.lbl_stat = tk.Label(root, text="상태: 정지", fg="red", font=("Malgun Gothic", 10, "bold"))
        self.lbl_stat.pack(pady=15)

        # 제어
        ctrl_f = tk.Frame(root)
        ctrl_f.pack()
        self.btn_start = tk.Button(ctrl_f, text="시작", command=self.start, width=12)
        self.btn_start.pack(side="left", padx=10)
        self.btn_stop = tk.Button(ctrl_f, text="중지", command=self.stop, width=12, state="disabled")
        self.btn_stop.pack(side="right", padx=10)

        for s, t in self.presets:
            self.tree.insert("", "end", values=(s, t))

    def on_select(self, e):
        sel = self.tree.selection()
        if not sel: return
        val = self.tree.item(sel[0], "values")
        self.ent_src.delete(0, tk.END)
        self.ent_src.insert(0, val[0])
        self.ent_tgt.delete(0, tk.END)
        self.ent_tgt.insert(0, val[1])

    def add(self):
        s, t = self.ent_src.get().strip(), self.ent_tgt.get().strip()
        if not s or not t: return
        for i in self.tree.get_children():
            if self.tree.item(i, "values")[0] == s:
                self.tree.delete(i)
        self.tree.insert("", "end", values=(s, t))
        self.ent_src.delete(0, tk.END)
        self.ent_tgt.delete(0, tk.END)

    def delete(self):
        sel = self.tree.selection()
        if sel: self.tree.delete(sel)

    def start(self):
        items = self.tree.get_children()
        if not items: return
        try:
            for i in items:
                s, t = self.tree.item(i, "values")
                keyboard.add_hotkey(str(s), lambda v=t: keyboard.press_and_release(v), suppress=True)
            self.running = True
            self.lbl_stat.config(text="상태: 작동 중", fg="green")
            self.lock_ui(True)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.stop()

    def stop(self):
        keyboard.unhook_all_hotkeys()
        self.running = False
        self.lbl_stat.config(text="상태: 정지", fg="red")
        self.lock_ui(False)

    def lock_ui(self, run):
        state = "disabled" if run else "normal"
        self.btn_start.config(state="disabled" if run else "normal")
        self.btn_stop.config(state="normal" if run else "disabled")
        self.btn_add.config(state=state)
        self.btn_del.config(state=state)
        if run:
            self.tree.unbind("<<TreeviewSelect>>")
        else:
            self.tree.bind("<<TreeviewSelect>>", self.on_select)


if __name__ == "__main__":
    root = tk.Tk()
    KeyMapper(root)
    root.mainloop()