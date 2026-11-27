# -*- coding: utf-8 -*-
"""主窗口：顶部 Header + 左侧「控制中心」+ 右侧「步骤演示看板」。

职责：
- 响应式布局：左侧固定宽度，右侧看板随窗口拉伸（fill=BOTH + expand）；
- DPI 字体自适应：按 tk scaling（每磅像素数，96dpi ≈ 1.333）缩放各级字体；
- 控件装配：数字输入、源/目标进制下拉框、载入/重置、单步、自动播放、速度滑块、日志面板；
- 事件处理：输入校验失败弹框提示并写红色日志；载入成功生成播放计划。
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from core.converter import (SUPPORTED_BASES, BASE_NAMES, ConversionError,
                            convert_with_steps)
from ui.playback import Playback
from ui.step_canvas import StepCanvas

BASE_LABELS = ["{} ({})".format(b, BASE_NAMES[b]) for b in SUPPORTED_BASES]
BG = "#eef1f5"          # 窗口背景（浅灰）
HEADER_BG = "#0b3d91"   # 顶栏深蓝
ACCENT = "#1f6feb"      # 主按钮蓝


class MainWindow:
    def __init__(self, root=None, force_scaling=None):
        self.root = root or tk.Tk()
        self.root.title("进位制转换步骤演示器 — 除基取余 × 按权展开可视化")
        self.root.configure(bg=BG)
        self.root.minsize(960, 601)
        # 窗口 1250x760 并居中
        w, h = 1250, 760
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry("{}x{}+{}+{}".format(w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 2)))

        # ---- DPI 字体自适应 ----
        # force_scaling：截图模式下固定缩放系数（96/72），保证 1250x760 布局与设计一致；
        # 正常运行时为 None，按操作系统实际 DPI 自适应。
        if force_scaling:
            self.root.tk.call("tk", "scaling", force_scaling)
        scaling = float(self.root.tk.call("tk", "scaling"))
        self.k = max(0.8, min(1.8, scaling / 1.3333))
        self.f_body = self._font(11)
        self.f_bold = self._font(11, True)
        self.f_small = self._font(9)
        self.f_entry = self._font(14, True)
        self.f_big = self._font(16, True)
        self.f_mono = ("Consolas", max(9, int(10 * self.k)))

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", font=self.f_body)

        self.plan = None
        self._build_header()
        self._build_body()
        self._wire()

    # ---------------- 构建界面 ----------------
    def _font(self, size, bold=False):
        return ("Microsoft YaHei", max(8, int(size * self.k)), "bold" if bold else "normal")

    def _build_header(self):
        bar = tk.Frame(self.root, bg=HEADER_BG, height=int(56 * self.k))
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="🖥 进位制转换步骤演示器", bg=HEADER_BG, fg="#ffffff",
                 font=self._font(14, True)).pack(side="left", padx=18)
        tk.Label(bar, text="小组：逢二进一 ｜《计算机与专业基础研讨》综合实验",
                 bg=HEADER_BG, fg="#c9d8f5", font=self.f_small).pack(side="right", padx=18)

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(side="top", fill="both", expand=True, padx=12, pady=10)

        # ======== 左侧：控制中心（固定宽度） ========
        left = tk.Frame(body, bg=BG, width=int(360 * self.k))
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        console = tk.LabelFrame(left, text=" 控制中心 ", bg=BG, fg="#0b3d91",
                                font=self.f_bold, padx=8, pady=6)
        console.pack(fill="x")
        anchor = {"anchor": "w", "padx": 6, "pady": 3}

        tk.Label(console, text="输入数字（非负整数）：", bg=BG, fg="#41505f",
                 font=self.f_body).pack(**anchor)
        self.var_num = tk.StringVar(value="25")
        self.ent_num = ttk.Entry(console, textvariable=self.var_num, font=self.f_entry)
        self.ent_num.pack(fill="x", padx=6)

        row = tk.Frame(console, bg=BG)
        row.pack(fill="x", pady=(6, 0))
        col1 = tk.Frame(row, bg=BG)
        col1.pack(side="left", expand=True, fill="x", padx=(6, 3))
        col2 = tk.Frame(row, bg=BG)
        col2.pack(side="left", expand=True, fill="x", padx=(3, 6))
        tk.Label(col1, text="源进位制：", bg=BG, fg="#41505f", font=self.f_small).pack(anchor="w")
        tk.Label(col2, text="目标进位制：", bg=BG, fg="#41505f", font=self.f_small).pack(anchor="w")
        self.var_from = tk.StringVar(value=BASE_LABELS[2])      # 默认：十进制
        self.var_to = tk.StringVar(value=BASE_LABELS[0])        # 默认：二进制
        self.cb_from = ttk.Combobox(col1, textvariable=self.var_from, values=BASE_LABELS,
                                    state="readonly", font=self.f_body)
        self.cb_from.pack(fill="x", pady=2)
        self.cb_to = ttk.Combobox(col2, textvariable=self.var_to, values=BASE_LABELS,
                                  state="readonly", font=self.f_body)
        self.cb_to.pack(fill="x", pady=2)

        self.btn_load = tk.Button(console, text="载入 / 重置", bg=ACCENT, fg="#ffffff",
                                  activebackground="#1a5fd0", activeforeground="#ffffff",
                                  relief="flat", font=self.f_bold, cursor="hand2",
                                  command=self.on_load)
        self.btn_load.pack(fill="x", padx=6, pady=(10, 4), ipady=3)

        btns = tk.Frame(console, bg=BG)
        btns.pack(fill="x", padx=6)
        self.btn_step = tk.Button(btns, text="单步执行 ▶❙", bg="#2ea44f", fg="#ffffff",
                                  activebackground="#278f45", activeforeground="#ffffff",
                                  relief="flat", font=self.f_bold, cursor="hand2",
                                  state="disabled", command=self.on_step)
        self.btn_step.pack(side="left", expand=True, fill="x", padx=(0, 3), ipady=3)
        self.btn_play = tk.Button(btns, text="自动播放 ▶", bg="#e8862e", fg="#ffffff",
                                  activebackground="#cf7524", activeforeground="#ffffff",
                                  relief="flat", font=self.f_bold, cursor="hand2",
                                  state="disabled", command=self.on_play_toggle)
        self.btn_play.pack(side="left", expand=True, fill="x", padx=(3, 0), ipady=3)

        tk.Label(console, text="播放速度（毫秒/步，左慢右快）：", bg=BG, fg="#41505f",
                 font=self.f_small).pack(anchor="w", padx=6, pady=(8, 0))
        self.var_delay = tk.IntVar(value=800)
        self.scale = tk.Scale(console, from_=2000, to=100, orient="horizontal",
                              variable=self.var_delay, bg=BG, highlightthickness=0,
                              font=self.f_small, troughcolor="#dfe6ee",
                              command=self._on_speed)
        self.scale.pack(fill="x", padx=6)

        self.lbl_progress = tk.Label(console, text="进度：未载入", bg=BG, fg="#41505f",
                                     font=self.f_bold)
        self.lbl_progress.pack(anchor="w", padx=6, pady=(2, 4))

        # ======== 左侧下方：运行日志 ========
        logf = tk.LabelFrame(left, text=" 运行日志 ", bg=BG, fg="#0b3d91",
                             font=self.f_bold, padx=4, pady=4)
        logf.pack(fill="both", expand=True, pady=(10, 0))
        self.txt_log = scrolledtext.ScrolledText(logf, height=10, state="disabled",
                                                 bg="#0d1117", fg="#e6edf3",
                                                 insertbackground="#e6edf3",
                                                 font=self.f_mono, relief="flat",
                                                 padx=8, pady=6)
        self.txt_log.pack(fill="both", expand=True)
        for tag, color, bold in (("info", "#8b949e", False), ("step", "#e6edf3", False),
                                 ("result", "#7ee787", True), ("error", "#ff7b72", True),
                                 ("load", "#79c0ff", True)):
            self.txt_log.tag_configure(tag, foreground=color,
                                       font=(self.f_mono[0], self.f_mono[1],
                                             "bold" if bold else "normal"))

        # ======== 右侧：步骤演示看板 ========
        right = tk.LabelFrame(body, text=" 步骤演示看板 ", bg=BG, fg="#0b3d91",
                              font=self.f_bold, padx=4, pady=4)
        right.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(right, bg="#f7f9fb")
        inner.pack(fill="both", expand=True)
        self.canvas = StepCanvas(inner, self.f_body, self.f_bold, self.f_small, self.f_big)
        vsb = ttk.Scrollbar(inner, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

    def _wire(self):
        self.playback = Playback(self.canvas, self.root, self.log,
                                 self._on_progress, self._on_finish)
        self.ent_num.bind("<Return>", lambda _e: self.on_load())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.canvas.show_hint()
        self.log("程序就绪。输入数字并选择进制后点击「载入 / 重置」。", "info")
        self.log("提示：输入框内按回车可快速载入；示例 25(10)→(2)、FF(16)→(2)。", "info")

    # ---------------- 事件处理 ----------------
    def log(self, text, tag="step"):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", text + "\n", tag)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _on_speed(self, value):
        self.playback.set_delay(value)

    def _on_progress(self, cursor, total):
        if cursor < 0:
            self.lbl_progress.config(text="进度：共 {} 步，未开始".format(total), fg="#41505f")
        elif cursor >= total - 1:
            self.lbl_progress.config(text="进度：已完成（共 {} 步）".format(total), fg="#0b3d91")
        else:
            self.lbl_progress.config(text="进度：第 {} / {} 步".format(cursor + 1, total), fg="#2ea44f")

    def _on_finish(self):
        self.btn_play.config(text="重新播放 ▶")

    def on_load(self):
        """载入 / 重置：解析输入 → 生成转换计划 → 复位播放状态。"""
        self.playback.stop()
        self.btn_play.config(text="自动播放 ▶")
        fb = SUPPORTED_BASES[BASE_LABELS.index(self.var_from.get())]
        tb = SUPPORTED_BASES[BASE_LABELS.index(self.var_to.get())]
        try:
            plan = convert_with_steps(self.var_num.get(), fb, tb)
        except ConversionError as exc:
            messagebox.showerror("输入有误", str(exc))
            self.log("[错误] {}".format(exc), "error")
            return
        self.plan = plan
        self.canvas.set_plan(plan)
        self.playback.load(plan)
        self.btn_step.config(state="normal")
        self.btn_play.config(state="normal")
        mode_desc = {"divide": "除基取余", "expand": "按权展开",
                     "both": "两阶段（先按权展开为十进制，再除基取余）",
                     "same": "源与目标进制相同"}[plan["mode"]]
        self.log("[载入] {}（{} 进制）→ {} 进制｜方法：{}｜共 {} 步".format(
            plan["input_text"], fb, tb, mode_desc, len(self.playback.frames)), "load")

    def on_step(self):
        """单步执行：前进一帧（结束时 on_finish 自动触发）。"""
        self.playback.pause()
        self.btn_play.config(text="继续播放 ▶" if not self.playback.finished else "重新播放 ▶")
        self.playback.step()

    def on_play_toggle(self):
        """自动播放 / 暂停 切换；播放结束后再点 = 重新载入并播放。"""
        if self.playback.playing:
            self.playback.pause()
            self.btn_play.config(text="继续播放 ▶")
            return
        if self.playback.finished:
            self.on_load()
        self.playback.play()
        if self.playback.playing:
            self.btn_play.config(text="暂停 ⏸")

    def _on_close(self):
        self.playback.stop()
        self.root.destroy()

    # ---------------- 运行 ----------------
    def run(self):
        self.root.mainloop()
