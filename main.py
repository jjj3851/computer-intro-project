# -*- coding: utf-8 -*-
"""进位制转换步骤演示器 · 程序入口。

正常运行：
    python main.py

截图模式（自动装载示例、推进到指定状态、抓取窗口保存为 PNG，用于 README）：
    python main.py --screenshot main --out docs/screenshots
    python main.py --screenshot step --out docs/screenshots
    python main.py --screenshot done --out docs/screenshots

截图模式的可靠性设计（Windows）：
- 进程启用 Per-Monitor DPI 感知：Tk / Win32 / ImageGrab 三方坐标系一致，
  避免高缩放屏（125%/150%）下抓错区域；
- 固定 tk scaling=96/72，窗口按 1250x760 物理像素渲染，布局与设计稿一致；
- 窗口置顶（-topmost）并强制前台，避免被浏览器等窗口遮挡；
- 用 DwmGetWindowAttribute(扩展边框) 取窗口真实矩形（含标题栏、不含阴影）；
- 抓取后程序化校验（顶栏深蓝带 / 高亮行 / 结果横幅的像素特征），
  不达标自动重试，最多 4 次。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # 保证从任意目录可运行


# ---------------- Windows 截图辅助 ----------------
def _win_capture_prepare():
    """启用 Per-Monitor DPI 感知（必须在创建 Tk 窗口之前调用）。"""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _win_window_rect(root):
    """返回窗口可见边界的屏幕矩形 (left, top, right, bottom)，物理像素。"""
    import ctypes
    from ctypes import wintypes
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())  # 由客户区 HWND 取顶层窗口
    rect = wintypes.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd), wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect), ctypes.sizeof(rect))
    if res != 0:                                            # DWM 失败则退回 GetWindowRect
        ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


_HEADER_RGB = (11, 61, 145)     # 0b3d91 顶栏
_GREEN_RGB = (215, 245, 215)    # d7f5d7 当前步骤行
_BANNER_RGB = (220, 235, 255)   # dcebff 结果横幅


def _verify_capture(img, scenario):
    """程序化校验截图内容，返回 (整体通过, 顶栏通过)。"""
    px = img.convert("RGB")
    w, h = px.size
    p = px.load()

    def near(x, y, t, tol=42):
        q = p[x, y]
        return abs(q[0] - t[0]) <= tol and abs(q[1] - t[1]) <= tol and abs(q[2] - t[2]) <= tol

    def row_frac(y, t, x0=0, x1=None, step=8):
        x1 = x1 if x1 is not None else w
        xs = list(range(x0, x1, step))
        if not xs:
            return 0.0
        return sum(1 for x in xs if near(x, y, t)) / len(xs)

    header_ok = any(row_frac(y, _HEADER_RGB) > 0.6 for y in range(0, min(h, 260), 3))
    if scenario == "main":
        return header_ok, header_ok
    if scenario == "step":
        green_ok = any(row_frac(y, _GREEN_RGB, w // 2, w) > 0.05 for y in range(0, h, 4))
        return header_ok and green_ok, header_ok
    banner_ok = any(row_frac(y, _BANNER_RGB, 0, w) > 0.3 for y in range(h // 2, h, 4))
    return header_ok and banner_ok, header_ok


def run_screenshot(app, scenario, outdir):
    """截图模式：默认示例 25（十进制）→ 二进制，推进到指定状态后抓取窗口。"""
    app.on_load()
    if scenario == "step":                      # 演示中：前进一步并高亮
        app.playback.step()
    elif scenario == "done":                    # 播放到结果横幅出现
        while not app.playback.step():
            pass
    root = app.root
    root.deiconify()
    root.attributes("-topmost", True)           # 置顶，避免被浏览器等窗口遮挡
    root.lift()
    root.focus_force()
    root.update_idletasks()
    root.update()

    state = {"tries": 0, "saved": None}

    def attempt():
        state["tries"] += 1
        from PIL import ImageGrab               # 仅截图模式需要 Pillow
        box = _win_window_rect(root)
        img = ImageGrab.grab(box)
        ok, header_ok = _verify_capture(img, scenario)
        if ok or state["tries"] >= 4:
            os.makedirs(outdir, exist_ok=True)
            path = os.path.abspath(os.path.join(outdir, scenario + ".png"))
            img.save(path)
            print("saved: {} | verified={} header={} tries={} box={}".format(
                path, ok, header_ok, state["tries"], box))
            state["saved"] = (path, ok)
            root.after(200, root.destroy)
        else:
            root.lift()                          # 再抢到前台重试
            root.focus_force()
            root.after(800, attempt)

    root.after(1500, attempt)                    # 等字体、布局与防抖重绘稳定
    root.mainloop()
    if not state["saved"]:
        raise SystemExit("screenshot failed: " + scenario)
    if not state["saved"][1]:
        raise SystemExit("screenshot verify failed after retries: " + scenario)


def main():
    parser = argparse.ArgumentParser(description="进位制转换步骤演示器（除基取余 × 按权展开可视化）")
    parser.add_argument("--screenshot", choices=["main", "step", "done"],
                        help="截图模式：装载示例并抓取窗口后自动退出")
    parser.add_argument("--out", default=os.path.join("docs", "screenshots"),
                        help="截图输出目录（默认 docs/screenshots）")
    args = parser.parse_args()

    if args.screenshot:
        _win_capture_prepare()                   # 必须在创建窗口前启用 DPI 感知
    from ui.main_window import MainWindow
    app = MainWindow(force_scaling=(96.0 / 72.0) if args.screenshot else None)
    if args.screenshot:
        run_screenshot(app, args.screenshot, args.out)
    else:
        app.run()


if __name__ == "__main__":
    main()
