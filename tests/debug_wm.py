# -*- coding: utf-8 -*-
"""调试：单帧复现水印填充，打印 filter 链并输出结果图。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import crop_engine, media

SRC = r'C:\Users\Administrator\Doubao\dev\vidio_demo\水印测试.webm'
# 台标实际范围约 x:88~249, y:49~130；框完整覆盖 25~265 x 20~155
WM = [{'x': 25, 'y': 20, 'width': 240, 'height': 135, 'blur_sigma': 30}]

filters, label, w, h = crop_engine.build_chain(
    1920, 1080, None, 'horizontal', WM, enhance=None)
print('画幅:', w, 'x', h)
print('filter 链:')
for seg in filters.split(';'):
    print('  |', seg[:120], '...' if len(seg) > 120 else '')
print()

out = Path(__file__).resolve().parent / '_dbg_wm.png'
crop_engine.render_preview(SRC, 0.5, filters, label, str(out))
print('输出:', out)
# 原帧对比
media.extract_frame(SRC, 0.5, str(Path(__file__).resolve().parent / '_dbg_orig.png'))
print('原帧:', Path(__file__).resolve().parent / '_dbg_orig.png')
