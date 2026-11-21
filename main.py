# -*- coding: utf-8 -*-
"""进位制转换步骤演示器 · 程序入口。

正常运行：
    python main.py

截图模式（自动装载示例、推进到指定状态、抓取窗口保存为 PNG，用于 README）：
    python main.py --screenshot main --out docs/screenshots
    python main.py --screenshot step --out docs/screenshots
    python main.py --screenshot done --out docs/screenshots
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # 保证从任意目录可运行

from ui.main_window import MainWindow


def run_screenshot(app, scenario, outdir):
    """截图模式：默认示例 25（十进制）→ 二进制，推进到指定状态后抓取窗口。"""
    app.on_load()
    if scenario == "step":                      # 演示中：前进一步并高亮
        app.playback.step()
    elif scenario == "done":                    # 播放到结果横幅出现
        while not app.playback.step():
            pass
    app.root.update_idletasks()
    app.root.update()

    def grab():
        from PIL import ImageGrab               # 仅截图模式需要 Pillow
        x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
        w, h = app.root.winfo_width(), app.root.winfo_height()
        img = ImageGrab.grab((x, y, x + w, y + h))
        os.makedirs(outdir, exist_ok=True)
        path = os.path.abspath(os.path.join(outdir, scenario + ".png"))
        img.save(path)
        print("saved:", path)
        app.root.destroy()

    app.root.after(1200, grab)                  # 等字体、布局与防抖重绘稳定
    app.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="进位制转换步骤演示器（除基取余 × 按权展开可视化）")
    parser.add_argument("--screenshot", choices=["main", "step", "done"],
                        help="截图模式：装载示例并抓取窗口后自动退出")
    parser.add_argument("--out", default=os.path.join("docs", "screenshots"),
                        help="截图输出目录（默认 docs/screenshots）")
    args = parser.parse_args()

    app = MainWindow()
    if args.screenshot:
        run_screenshot(app, args.screenshot, args.out)
    else:
        app.run()


if __name__ == "__main__":
    main()
