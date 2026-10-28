# -*- coding: utf-8 -*-
"""补丁：tasks.py 适配 build_vf 返回 (filters,label,out_w,out_h,regions)。"""
import io
from pathlib import Path

p = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\tasks.py')
src = io.open(p, encoding='utf-8').read()

old = """        vf, out_w, out_h, regions = crop_engine.build_vf(
            p['src_w'], p['src_h'], crop, t['direction'], ctx['wms'],
            enhance=None, vwidth=p.get('vwidth') or 1080,
        )"""
new = """        filters, label, out_w, out_h, regions = crop_engine.build_vf(
            p['src_w'], p['src_h'], crop, t['direction'], ctx['wms'],
            enhance=None, vwidth=p.get('vwidth') or 1080,
        )"""
if old not in src:
    raise SystemExit('PATCH FAIL: build_vf call not found')
src = src.replace(old, new, 1)

old2 = "            crop_engine.render_preview(src, start, vf, out_w, out_h, regions, preview)"
new2 = "            crop_engine.render_preview(src, start, filters, label, out_w, out_h, regions, preview)"
if old2 not in src:
    raise SystemExit('PATCH FAIL: render_preview call not found')
src = src.replace(old2, new2, 1)

old3 = "        out = crop_engine.render_video(src, start, dur, vf, out_w, out_h, regions, fps,\n                                       make_output_path(src, seg['seg_index'], t['direction']))"
new3 = "        out = crop_engine.render_video(src, start, dur, filters, label, out_w, out_h, regions, fps,\n                                       make_output_path(src, seg['seg_index'], t['direction']))"
if old3 not in src:
    raise SystemExit('PATCH FAIL: render_video call not found')
src = src.replace(old3, new3, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('tasks.py patched ok')
