# -*- coding: utf-8 -*-
"""压缩档位实测脚本"""
import sys, os, time
sys.path.insert(0, r'C:\Users\Administrator\Doubao\dev\video-crop-web')
from server import crop_engine, media

src = r'D:\DBdir\素材\视频\未处理\bilibili_中美_01.mp4'
info = media.probe(src)
w, h = info['width'], info['height']
print('src:', w, 'x', h, info.get('duration'), 's')
f1, l1, ow1, oh1, r1 = crop_engine.build_vf(w, h, None, 'vertical', [], None)
f2, l2, ow2, oh2, r2 = crop_engine.build_vf(w, h, None, 'vertical', [], None, vwidth=720)
out_dir = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify'

for name, fl, lb, ow_, oh_, rg, crf in [
    ('cmp_A_crf23_1080.mp4', f1, l1, ow1, oh1, r1, 23),
    ('cmp_B_crf26_1080.mp4', f1, l1, ow1, oh1, r1, 26),
    ('cmp_C_crf28_1080.mp4', f1, l1, ow1, oh1, r1, 28),
    ('cmp_D_crf26_720.mp4', f2, l2, ow2, oh2, r2, 26),
    ('cmp_E_crf28_720.mp4', f2, l2, ow2, oh2, r2, 28),
]:
    t0 = time.time()
    p = os.path.join(out_dir, name)
    try:
        crop_engine.render_video(src, 10, 3, fl, lb, ow_, oh_, rg, 25, p, timeout=120, crf=crf)
        print(name, os.path.getsize(p), 'bytes', round(time.time() - t0, 1), 's')
    except Exception as e:
        print(name, 'FAIL', str(e)[:140])
