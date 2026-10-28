# -*- coding: utf-8 -*-
"""性能基准：定位任务#21 配置（裁剪+横屏标准化+编码）的耗时瓶颈。"""
import subprocess, sys, time, sqlite3
sys.path.insert(0, r'C:\Users\Administrator\Doubao\dev\video-crop-web')
from server import crop_engine

db = sqlite3.connect(r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\videocrop.db')
db.row_factory = sqlite3.Row
p = dict(db.execute('SELECT * FROM projects WHERE id=21').fetchone())
wms = [dict(w) for w in db.execute('SELECT x,y,width,height,blur_sigma FROM watermark_regions WHERE project_id=21 ORDER BY id')]
crop = {'x': p['crop_x'], 'y': p['crop_y'], 'w': p['crop_w'], 'h': p['crop_h']} if p['crop_w'] else None
filters, label, W, H, regions = crop_engine.build_vf(p['src_w'], p['src_h'], crop, 'horizontal', wms, None)
print('filter:', filters[:120], '...')
print('regions:', regions, 'canvas', W, 'x', H)
start, dur = 15.86, 4.4
fb = W * H * 3

# 1) decode 端（读全部帧）
dec = crop_engine._decode_cmd(p['src_path'], start, dur, filters, label, W, H)
t0 = time.time()
pd = subprocess.Popen(dec, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      startupinfo=crop_engine._startup())
nf = 0
while True:
    raw = pd.stdout.read(fb)
    if not raw:
        break
    nf += 1
err = pd.communicate()[1]
t1 = time.time()
print(f'DECODE: {nf} frames in {t1-t0:.1f}s  ({nf/(t1-t0):.1f} fps)  rc={pd.returncode}  err={err.decode("utf-8","ignore")[:100]}')

# 2) encode 端（黑帧 110 帧）
enc = ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '25',
       '-i', '-', '-ss', f'{start:.3f}', '-i', p['src_path'], '-t', f'{dur:.3f}',
       '-map', '0:v', '-map', '1:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
       '-c:a', 'aac', '-b:a', '128k', r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\_bench_enc.mp4']
t0 = time.time()
pe = subprocess.Popen(enc, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE, startupinfo=crop_engine._startup())
black = b'\x10\x10\x10' * fb
for i in range(110):
    pe.stdin.write(black)
pe.stdin.close()
err = pe.communicate()[1]
t1 = time.time()
print(f'ENCODE: 110 frames in {t1-t0:.1f}s  rc={pe.returncode}  err={err.decode("utf-8","ignore")[:100]}')
