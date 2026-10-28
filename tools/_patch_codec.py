# -*- coding: utf-8 -*-
"""补丁6：修复播放器兼容性（yuv444p→yuv420p+main profile）+ 缩体积（crf 18→23，config 可调）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:70])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

# ---------- 1) config.json：processing 加 crf ----------
P1 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\config.json'
s1 = load(P1)
s1 = rep(s1,
"""  "processing": {
    "vwidth": 1080,
    "hwidth": 1920,
    "hheight": 1080,
    "bg_sigma": 40,
    "blur_sigma": 30,
    "enhance_level": "medium",
    "max_concurrent": 2
  },""",
"""  "processing": {
    "vwidth": 1080,
    "hwidth": 1920,
    "hheight": 1080,
    "bg_sigma": 40,
    "blur_sigma": 30,
    "enhance_level": "medium",
    "max_concurrent": 2,
    "crf": 23
  },""",
    'config crf')
save(P1, s1)
print('config.json OK')

# ---------- 2) crop_engine.py：编码参数 ----------
P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py'
s2 = load(P2)
# 检查是否已 import CFG
if 'from .config import CFG' not in s2:
    s2 = rep(s2,
"""import subprocess
import numpy as np
import cv2""",
"""import subprocess
import numpy as np
import cv2
from .config import CFG""",
    'crop_engine import cfg')
s2 = rep(s2,
"""    enc = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{out_w}x{out_h}', '-r', f'{fps:.6f}', '-i', '-',
        '-ss', f'{start:.3f}', '-i', str(src), '-t', f'{dur:.3f}',
        '-map', '0:v', '-map', '1:a?',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
        str(out_path),
    ]""",
"""    enc = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{out_w}x{out_h}', '-r', f'{fps:.6f}', '-i', '-',
        '-ss', f'{start:.3f}', '-i', str(src), '-t', f'{dur:.3f}',
        '-map', '0:v', '-map', '1:a?',
        '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', str(CFG['processing'].get('crf', 23)),
        '-pix_fmt', 'yuv420p', '-profile:v', 'main',
        '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
        str(out_path),
    ]""",
    'crop_engine enc params')
save(P2, s2)
print('crop_engine.py OK')
print('ALL PATCHED')
