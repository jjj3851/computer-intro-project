# -*- coding: utf-8 -*-
"""播放引擎：把一次转换计划展开成帧序列，逐帧驱动看板高亮与日志输出。

帧序列 = 按权展开各行（若有）→ 除基取余各行（若有）→ 结果帧。
自动播放用 root.after() 定时器实现，速度由界面滑块设定（100~2000 ms/步）。
"""


class Playback:
    def __init__(self, canvas, root, log, on_progress, on_finish):
        self.canvas = canvas            # StepCanvas 实例
        self.root = root                # tk 根窗口（提供 after 定时器）
        self.log = log                  # log(text, tag) 回调 → 运行日志面板
        self.on_progress = on_progress  # on_progress(cursor, total) 回调 → 进度标签
        self.on_finish = on_finish      # 播放完毕回调 → 按钮状态复原
        self.frames = []                # [(phase, idx, desc), ...]
        self.cursor = -1                # -1 表示尚未开始
        self.delay = 800                # 自动播放间隔（毫秒/步）
        self.playing = False
        self._job = None

    # ---------------- 装载与状态 ----------------
    def load(self, plan):
        """根据转换计划生成帧序列并回到初始状态。"""
        self.stop()
        self.frames = [("expand", i, s[5]) for i, s in enumerate(plan["expand_steps"])]
        self.frames += [("divide", i, s[3]) for i, s in enumerate(plan["divide_steps"])]
        tail = "源与目标进制相同，结果即为输入本身：" if plan["mode"] == "same" else "全部步骤完成："
        check = "反向换算校验一致 ✔" if plan["verify"] else "反向换算校验不一致 ✘"
        self.frames.append(("result", -1, "{}{}（{}）".format(tail, plan["result_text"], check)))
        self.cursor = -1
        self.canvas.set_progress(-1)
        self.on_progress(self.cursor, len(self.frames))

    @property
    def total(self):
        return len(self.frames)

    @property
    def finished(self):
        return bool(self.frames) and self.cursor >= len(self.frames) - 1

    # ---------------- 播放控制 ----------------
    def step(self):
        """前进一步；返回播放是否已结束。结果帧会触发 on_finish。"""
        if not self.frames or self.finished:
            return True
        self.cursor += 1
        phase, _idx, desc = self.frames[self.cursor]
        self.canvas.set_progress(self.cursor)
        if phase == "result":
            self.log("[结果] " + desc, "result")
        else:
            self.log("[步骤 {}/{}] {}".format(self.cursor + 1, len(self.frames), desc), "step")
        self.on_progress(self.cursor, len(self.frames))
        if self.finished and self.on_finish:
            self.on_finish()
        return self.finished

    def play(self):
        """开始自动播放（到结果帧自动停）。"""
        if not self.frames or self.finished:
            return
        self.playing = True
        self._tick()

    def _tick(self):
        if not self.playing:
            return
        if self.step():
            self.playing = False
            return
        self._job = self.root.after(self.delay, self._tick)

    def pause(self):
        self.playing = False
        self._cancel_job()

    def stop(self):
        self.playing = False
        self._cancel_job()

    def _cancel_job(self):
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def set_delay(self, ms):
        """速度滑块回调：限制在 100~2000 ms/步。"""
        try:
            self.delay = max(100, min(2000, int(float(ms))))
        except (TypeError, ValueError):
            pass
