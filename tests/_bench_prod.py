# -*- coding: utf-8 -*-
"""实测生产 render_video 全流程耗时（任务21 配置）。"""
import subprocess, sys, time, sqlite3
sys.path.insert(0, r'C:\Users\Administrator\Doubao\dev\video-crop-web')
from server import crop_engine

db = sqlite3.connect(r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\videocrop.db')
db.row_factory = sqlite3.Row
p = dict(db.execute('SELECT * FROM projects WHERE id=21').fetchone())
wms = [dict(w) for w in db.execute('SELECT x,y,width,height,blur_sigma FROM watermark_regions WHERE project_id=21 ORDER BY id')]
crop = {'x': p['crop_x'], 'y': p['crop_y'], 'w': p['crop_w'], 'h': p['crop_h']} if p['crop_w'] else None
filters, label, W, H, regions = crop_engine.build_vf(p['src_w'], p['src_h'], crop, 'horizontal', wms, None)
out = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\_bench_prod.mp4'
t0 = time.time()
crop_engine.render_video(p['src_path'], 15.86, 4.4, filters, label, W, H, regions, 25, out, 'telea')
dt = time.time() - t0
import os
print(f'PROD render_video: {dt:.1f}s  size={os.path.getsize(out)}  regions={regions}')
