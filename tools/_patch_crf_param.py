# -*- coding: utf-8 -*-
"""补丁10：render_video 支持 crf 可选参数（None=读 config），便于压缩档位实测。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py'
s = load(P)

old1 = "def render_video(src, start, dur, filters, label, out_w, out_h, regions, fps, out_path, method='telea', timeout=900, blur_after=0):"
new1 = "def render_video(src, start, dur, filters, label, out_w, out_h, regions, fps, out_path, method='telea', timeout=900, blur_after=0, crf=None):"
assert old1 in s and s.count(old1) == 1
s = s.replace(old1, new1, 1)

old2 = """        '-crf', str(CFG['processing'].get('crf', 23)),"""
new2 = """        '-crf', str(crf if crf is not None else CFG['processing'].get('crf', 23)),"""
assert old2 in s and s.count(old2) == 1
s = s.replace(old2, new2, 1)
save(P, s)
print('crop_engine.py OK — crf 可传参')
