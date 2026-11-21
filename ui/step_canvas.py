# -*- coding: utf-8 -*-
"""Canvas 步骤看板：绘制“除基取余”的除法阶梯与“按权展开”的权值行。

设计要点（对应 AI_Prompts_Log 交互三的人工修改）：
- 每一行图元在绘制时记录 item id，切换步骤时仅用 itemconfig 改颜色，
  不做 delete("all") 全量重绘，长步骤列表也不会卡顿；
- 步骤较多时自动滚动，保证当前行始终可见；
- 窗口尺寸变化（<Configure>）做 90ms 防抖后再全量重排。
"""

import tkinter as tk

from core.converter import DIGITS

ROW_H = 44            # 行高（像素）
ROW_GAP = 10          # 行间距
PAD_L = 24            # 左右留白
SECTION_H = 40        # 分节标题高度
RESULT_H = 78         # 结果横幅高度
CHIP_W = 76           # 右侧小块（余数 / 累计和）宽度

# 三种行状态的配色方案：未执行 / 已完成 / 当前
C_PENDING = {"bg": "#eef1f4", "fg": "#9aa4af", "ol": "#e3e8ee", "chip": "#e3e8ee", "w": 1}
C_DONE    = {"bg": "#ffffff", "fg": "#1f2933", "ol": "#c9d4de", "chip": "#dfe6ee", "w": 1}
C_CURRENT = {"bg": "#d7f5d7", "fg": "#0b3d0b", "ol": "#2ea44f", "chip": "#ffe8b3", "w": 2}


class StepCanvas(tk.Canvas):
    """步骤演示看板。由 MainWindow 创建，Playback 驱动 set_progress 高亮。"""

    def __init__(self, master, font, font_bold, font_small, font_big):
        super().__init__(master, bg="#f7f9fb", highlightthickness=0, bd=0)
        self._f, self._fb, self._fs, self._fbig = font, font_bold, font_small, font_big
        self.plan = None           # converter.convert_with_steps 的返回 dict
        self._rows = []            # [(seq, rect_id, text_id, chip_rect, chip_text, y), ...]
        self._result_ids = []      # 结果横幅图元
        self._content_h = 0        # 内容总高度（滚动区域）
        self._cur_seq = -1         # 当前进度（-1 = 未开始）
        self._resize_job = None
        self.bind("<Configure>", self._on_resize)
        # 鼠标滚轮：进入看板区域才接管，避免和日志面板抢事件
        self.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", self._on_wheel))
        self.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))

    # ---------------- 对外接口 ----------------
    def set_plan(self, plan):
        """载入一次新的转换计划并全量重绘。"""
        self.plan = plan
        self._cur_seq = -1
        self._redraw()

    def set_progress(self, seq):
        """按播放序号更新高亮（局部刷新）。seq=-1 表示全部未执行。

        行序号 < seq → 已完成；== seq → 当前；> seq → 未执行。
        seq >= 行数时显示结果横幅。
        """
        if not self.plan:
            return
        self._cur_seq = seq
        for row in self._rows:
            rseq = row[0]
            if rseq < seq:
                self._paint(row, C_DONE)
            elif rseq == seq:
                self._paint(row, C_CURRENT)
                self._ensure_visible(row[5])
            else:
                self._paint(row, C_PENDING)
        show_result = seq >= len(self._rows)
        for item in self._result_ids:
            self.itemconfig(item, state="normal" if show_result else "hidden")
        if show_result and self._rows:
            self.yview_moveto(1.0)          # 滚到底部展示结果横幅

    def show_hint(self):
        """未载入计划时的空状态提示。"""
        self.delete("all")
        self.plan = None
        self._rows, self._result_ids = [], []
        w = max(self.winfo_width(), 480)
        h = max(self.winfo_height(), 320)
        self.create_text(w // 2, h // 2, justify="center", fill="#8a97a5", font=self._f,
                         text="在左侧「控制中心」输入数字并选择源 / 目标进位制，\n"
                              "点击「载入 / 重置」后开始分步演示。\n\n"
                              "示例：25（十进制）→ 二进制；FF（十六进制）→ 二进制")

    # ---------------- 内部实现 ----------------
    def _on_wheel(self, event):
        self.yview_scroll(int(-event.delta / 120), "units")

    def _on_resize(self, _evt):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(90, self._redraw)   # 防抖：拖拽窗口时不做逐像素重绘

    def _redraw(self):
        if not self.plan:
            self.show_hint()
            return
        self.delete("all")
        self._rows, self._result_ids = [], []
        p = self.plan
        w = max(self.winfo_width(), 480)
        seq, y = 0, 16
        if p["mode"] in ("expand", "both"):
            title = "阶段一 · 按权展开：{} 进制 → 十进制".format(p["from_base"]) if p["mode"] == "both" \
                else "按权展开：{} 进制 → 十进制".format(p["from_base"])
            y = self._section_title(y, title)
            for ch, power, _weight, product, total, _desc in p["expand_steps"]:
                self._draw_row(seq, y, w, "{} × {}^{} = {}".format(ch, p["from_base"], power, product),
                               str(total))
                seq += 1
                y += ROW_H + ROW_GAP
        if p["mode"] in ("divide", "both"):
            if p["mode"] == "both":
                y += 10
            title = "阶段二 · 除基取余：十进制 → {} 进制".format(p["to_base"]) if p["mode"] == "both" \
                else "除基取余：十进制 → {} 进制".format(p["to_base"])
            y = self._section_title(y, title)
            for a, q, r, _desc in p["divide_steps"]:
                self._draw_row(seq, y, w, "{} ÷ {} = {} …… 余 {}".format(a, p["to_base"], q, r),
                               DIGITS[r])
                seq += 1
                y += ROW_H + ROW_GAP
        if p["mode"] == "same":
            y = self._section_title(y, "源进位制与目标进位制相同")
        y += 12
        self._draw_result(y, w)
        self._content_h = y + RESULT_H + 24
        self.configure(scrollregion=(0, 0, w, self._content_h))
        self.set_progress(self._cur_seq)

    def _section_title(self, y, text):
        self.create_text(PAD_L, y + 6, anchor="nw", text=text, font=self._fb, fill="#14508c")
        return y + SECTION_H

    def _draw_row(self, seq, y, w, main_text, chip_text):
        """绘制一行：主算式 + 右侧小块（余数 / 累计和）。初始为未执行状态。"""
        x0 = PAD_L
        x1 = w - PAD_L - CHIP_W - 20
        cx0, cx1 = x1 + 16, x1 + 16 + CHIP_W
        st = C_PENDING
        rect = self.create_rectangle(x0, y, x1, y + ROW_H, fill=st["bg"], outline=st["ol"], width=st["w"])
        txt = self.create_text(x0 + 16, y + ROW_H // 2, anchor="w", text=main_text,
                               font=self._f, fill=st["fg"])
        chip = self.create_rectangle(cx0, y + 4, cx1, y + ROW_H - 4,
                                     fill=st["chip"], outline=st["ol"], width=st["w"])
        ctxt = self.create_text((cx0 + cx1) // 2, y + ROW_H // 2, text=chip_text,
                                font=self._fs, fill="#1f2933")
        self._rows.append((seq, rect, txt, chip, ctxt, y))

    def _paint(self, row, st):
        """按状态给一行的四个图元换装（itemconfig 局部刷新，不重建图元）。"""
        _seq, rect, txt, chip, ctxt, _y = row
        self.itemconfig(rect, fill=st["bg"], outline=st["ol"], width=st["w"])
        self.itemconfig(txt, fill=st["fg"], font=self._fb if st is C_CURRENT else self._f)
        self.itemconfig(chip, fill=st["chip"], outline=st["ol"], width=st["w"])
        self.itemconfig(ctxt, fill="#0b3d0b" if st is C_CURRENT else "#1f2933",
                        font=self._fb if st is C_CURRENT else self._fs)

    def _draw_result(self, y, w):
        """结果横幅：初始隐藏，播放到最后一步时显示。"""
        p = self.plan
        x0, x1 = PAD_L, w - PAD_L
        bg = self.create_rectangle(x0, y, x1, y + RESULT_H, fill="#dcebff",
                                   outline="#1f6feb", width=2, state="hidden")
        big = self.create_text(x0 + 24, y + 22, anchor="w", text=p["result_text"],
                               font=self._fbig, fill="#0b3d91", state="hidden")
        ok = p["verify"]
        small = self.create_text(x0 + 24, y + 54, anchor="w",
                                 text="校验：将结果按目标进制反向换算，与原值一致 ✔" if ok
                                      else "校验：反向换算不一致 ✘（请反馈此 Bug）",
                                 font=self._fs, fill="#2ea44f" if ok else "#c0392b", state="hidden")
        self._result_ids = [bg, big, small]

    def _ensure_visible(self, y):
        """自动滚动，保证当前行可见（内容不超过视口时不动）。"""
        h = max(self.winfo_height(), 1)
        if self._content_h <= h:
            return
        top = max(0.0, (y - h * 0.55) / self._content_h)
        self.yview_moveto(min(1.0, top))
