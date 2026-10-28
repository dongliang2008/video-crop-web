# -*- coding: utf-8 -*-
"""对照测试：30 帧，定位慢滤镜。"""
import subprocess, time, sys
sys.path.insert(0, r'C:\Users\Administrator\Doubao\dev\video-crop-web')
from server import crop_engine

SRC = r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02.mp4'
ST, DUR = 15.86, 1.2
OUT = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\_bench2.raw'
CROP = {'x': 12, 'y': 5, 'w': 463, 'h': 150}

def run(name, filters, lab, W, H):
    cmd = ['ffmpeg', '-y', '-ss', f'{ST:.3f}', '-i', SRC, '-t', f'{DUR:.3f}',
           '-filter_complex', filters, '-map', f'[{lab}]', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    t0 = time.time()
    pd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          startupinfo=crop_engine._startup())
    n = 0
    fb = W * H * 3
    while True:
        raw = pd.stdout.read(fb)
        if not raw:
            break
        n += 1
    err = pd.communicate()[1].decode('utf-8', 'ignore')
    dt = time.time() - t0
    print(f'{name}: {n}帧 {dt:.2f}s {n/dt:.1f}fps' + ('' if pd.returncode == 0 else ' ERR ' + err[:80]))

# A 全链（crop→split→bg gblur→main scale→overlay）
f, lab, W, H, _ = crop_engine.build_vf(480, 270, CROP, 'horizontal', [], None)
run('A 全链', f, lab, W, H)
# B 无 gblur
f2 = f.replace('gblur=sigma=40,', '')
run('B 无gblur', f2, lab, W, H)
# C 仅 crop
run('C 仅crop', '[0:v]crop=462:150:12:4,null', 'null', 462, 150)
# D crop + main scale（无 bg/overlay）
run('D crop+scale3326', '[0:v]crop=462:150:12:4,scale=-2:1080', 'scale', 3326, 1080)
# E bg 全链无 main（只 bg 模糊铺满）
run('E bg模糊铺满', '[0:v]crop=462:150:12:4,scale=480:270:force_original_aspect_ratio=increase,crop=480:270,gblur=sigma=40,scale=1920:1080', 'scale', 1920, 1080)
