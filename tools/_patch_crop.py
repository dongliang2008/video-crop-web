# -*- coding: utf-8 -*-
"""补丁：build_vf 中 crop 起点 x/y 向下取偶（yuv420p 要求偶数），
映射使用实际裁剪坐标，避免 ffmpeg 报错。"""
import io
from pathlib import Path

p = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py')
src = io.open(p, encoding='utf-8').read()

old = """    parts = []
    cur_w, cur_h = src_w, src_h
    if crop:
        cw, ch = even(crop['w']), even(crop['h'])
        parts.append(f'crop={cw}:{ch}:{int(crop["x"])}:{int(crop["y"])}')
        cur_w, cur_h = cw, ch
    regions = map_wm_to_crop(wm_regions, crop)"""

new = """    parts = []
    cur_w, cur_h = src_w, src_h
    if crop:
        # yuv420p 要求裁剪起点 x/y 均为偶数：向下取偶，映射用实际裁剪坐标
        cw, ch = even(crop['w']), even(crop['h'])
        cx, cy = even(int(crop['x'])), even(int(crop['y']))
        parts.append(f'crop={cw}:{ch}:{cx}:{cy}')
        cur_w, cur_h = cw, ch
        crop = {'x': cx, 'y': cy, 'w': cw, 'h': ch}
    regions = map_wm_to_crop(wm_regions, crop)"""

if old not in src:
    raise SystemExit('PATCH FAIL: build_vf crop block not found')
src = src.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('crop_engine.py patched ok')
