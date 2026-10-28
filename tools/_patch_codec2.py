# -*- coding: utf-8 -*-
"""补丁6b：修复播放器兼容性 + 缩体积（重打，import 锚点修正）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:70])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py'
s2 = load(P2)
s2 = rep(s2,
"""from .coordinates import even, map_wm_to_crop, map_to_vertical, map_to_horizontal
from . import media, watermark""",
"""from .coordinates import even, map_wm_to_crop, map_to_vertical, map_to_horizontal
from . import media, watermark
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
