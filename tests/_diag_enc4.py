# -*- coding: utf-8 -*-
"""对照实验3：带音频源 + stderr 重定向到文件（排除 stderr 管道死锁）。"""
import subprocess
import numpy as np

W, H = 1920, 1080
SRC = r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02.mp4'
OUT = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\enc_audi2.mp4'
ERR = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\enc_audi2.err.txt'
enc = ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '25',
       '-i', '-', '-i', SRC, '-t', '3', '-map', '0:v', '-map', '1:a?',
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
       '-c:a', 'aac', '-b:a', '128k', OUT]
with open(ERR, 'wb') as ef:
    p = subprocess.Popen(enc, stdin=subprocess.PIPE, stderr=ef)
    frame = np.zeros((H, W, 3), np.uint8)
    try:
        for i in range(75):
            p.stdin.write(frame.tobytes())
            if i % 25 == 0:
                print('wrote', i + 1)
    except Exception as e:
        print('WRITE ERR at', i + 1, repr(e))
    p.stdin.close()
    try:
        rc = p.wait(timeout=40)
        print('rc', rc)
    except subprocess.TimeoutExpired:
        print('TIMEOUT')
        p.kill()
        rc = p.wait()
import os
print('out exists', os.path.exists(OUT), os.path.getsize(OUT) if os.path.exists(OUT) else 0)
print('ERR size', os.path.getsize(ERR))
