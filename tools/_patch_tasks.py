# -*- coding: utf-8 -*-
"""补丁：tasks.py 适配新引擎接口（build_vf / render_preview / render_video）。"""
import io
from pathlib import Path

p = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\tasks.py')
src = io.open(p, encoding='utf-8').read()

old = """        crop = None
        if p.get('crop_w'):
            crop = {'x': p['crop_x'], 'y': p['crop_y'], 'w': p['crop_w'], 'h': p['crop_h']}

        filters, label, _, _ = crop_engine.build_chain(
            p['src_w'], p['src_h'], crop, t['direction'], ctx['wms'],
            enhance=None, vwidth=p.get('vwidth') or 1080,
        )
        src = p['src_path']
        start = seg['start_time']
        dur = max(0.05, seg['end_time'] - seg['start_time'])

        if not t['preview_approved']:
            # 第一阶段：渲染确认图
            preview = str(Path(p['src_path']).parent / f'{Path(p["src_path"]).stem}_段{seg["seg_index"]}_{t["direction"]}_预览.png')
            crop_engine.render_preview(src, start, filters, label, preview)
            conn.execute(
                "UPDATE tasks SET state='WAIT_CONFIRM', preview_path=?, progress=100 WHERE id=?",
                (preview, task_id))
            conn.commit()
            return

        # 第二阶段：编码最终视频
        out = crop_engine.render_video(src, start, dur, filters, label,
                                       make_output_path(src, seg['seg_index'], t['direction']))
        conn.execute("UPDATE tasks SET state='DONE', output_path=?, progress=100 WHERE id=?",
                     (out, task_id))
        conn.commit()"""

new = """        crop = None
        if p.get('crop_w'):
            crop = {'x': p['crop_x'], 'y': p['crop_y'], 'w': p['crop_w'], 'h': p['crop_h']}

        vf, out_w, out_h, regions = crop_engine.build_vf(
            p['src_w'], p['src_h'], crop, t['direction'], ctx['wms'],
            enhance=None, vwidth=p.get('vwidth') or 1080,
        )
        src = p['src_path']
        start = seg['start_time']
        dur = max(0.05, seg['end_time'] - seg['start_time'])
        fps = media.probe(src)['fps']

        if not t['preview_approved']:
            # 第一阶段：渲染确认图
            preview = str(Path(p['src_path']).parent / f'{Path(p["src_path"]).stem}_段{seg["seg_index"]}_{t["direction"]}_预览.png')
            crop_engine.render_preview(src, start, vf, out_w, out_h, regions, preview)
            conn.execute(
                "UPDATE tasks SET state='WAIT_CONFIRM', preview_path=?, progress=100 WHERE id=?",
                (preview, task_id))
            conn.commit()
            return

        # 第二阶段：编码最终视频
        out = crop_engine.render_video(src, start, dur, vf, out_w, out_h, regions, fps,
                                       make_output_path(src, seg['seg_index'], t['direction']))
        conn.execute("UPDATE tasks SET state='DONE', output_path=?, progress=100 WHERE id=?",
                     (out, task_id))
        conn.commit()"""

if old not in src:
    raise SystemExit('PATCH FAIL: tasks.py old block not found')
src = src.replace(old, new, 1)

# 补充 import media
if 'from . import db, crop_engine' in src and 'media' not in src.split('\n')[7]:
    src = src.replace('from . import db, crop_engine', 'from . import db, crop_engine, media', 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('tasks.py patched ok')
