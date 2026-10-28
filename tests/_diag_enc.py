# -*- coding: utf-8 -*-
"""诊断：ffmpeg rawvideo stdin 管道方案在 Windows 是否卡死/报错。"""
import subprocess
import numpy as np

W, H = 1920, 1080
OUT = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\enc_test2.mp4'
SRC = r'D:\DBdir\素材\视频\未处理\cctv_中东局势_02.mp4'

enc = ['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '25',
       '-i', '-', '-ss', '15', '-i', SRC, '-t', '10',
       '-map', '0:v', '-map', '1:a?',
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
       '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', OUT]
print('START', ' '.join(enc))
p = subprocess.Popen(enc, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
frame = np.zeros((H, W, 3), np.uint8)
try:
    for i in range(250):
        p.stdin.write(frame.tobytes())
        if i % 50 == 0:
            print('wrote', i + 1, 'frames')
except Exception as e:
    print('WRITE ERR at frame', i + 1, repr(e))
try:
    p.stdin.close()
except Exception as e:
    print('CLOSE ERR', repr(e))
try:
    rc = p.wait(timeout=60)
    print('rc', rc)
except subprocess.TimeoutExpired:
    print('TIMEOUT waiting; killing')
    p.kill()
    rc = p.wait()
err = p.stderr.read().decode('utf-8', 'ignore')
print('STDERR last 800:')
print(err[-800:])
import os
print('exists', os.path.exists(OUT), os.path.getsize(OUT) if os.path.exists(OUT) else 0)
