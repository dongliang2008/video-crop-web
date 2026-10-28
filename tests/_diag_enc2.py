# -*- coding: utf-8 -*-
"""对照实验1：纯视频 stdin 管道（无音频源）。"""
import subprocess
import numpy as np

W, H = 1920, 1080
OUT = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\enc_vonly.mp4'
enc = ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '25',
       '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', OUT]
p = subprocess.Popen(enc, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
frame = np.zeros((H, W, 3), np.uint8)
try:
    for i in range(3):
        p.stdin.write(frame.tobytes())
        print('wrote', i + 1)
except Exception as e:
    print('WRITE ERR at', i + 1, repr(e))
p.stdin.close()
try:
    rc = p.wait(timeout=30)
    print('rc', rc)
except subprocess.TimeoutExpired:
    print('TIMEOUT')
    p.kill()
    rc = p.wait()
err = p.stderr.read().decode('utf-8', 'ignore')
print('STDERR tail:')
print(err[-600:])
import os
print('out exists', os.path.exists(OUT), os.path.getsize(OUT) if os.path.exists(OUT) else 0)
