# -*- coding: utf-8 -*-
"""补丁12：dec 精确输出 round(dur*fps) 帧，与 enc 消费帧数对齐，根治管道 BrokenPipe（源30fps时必现）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py'
s = load(P)

old1 = """def _decode_cmd(src, start, dur, filters, label, out_w, out_h, single_frame=False):
    cmd = ['ffmpeg', '-y', '-ss', f'{start:.3f}', '-i', str(src)]
    if dur is not None:
        cmd += ['-t', f'{dur:.3f}']
    if single_frame:
        cmd += ['-frames:v', '1']
    cmd += ['-filter_complex', filters, '-map', f'[{label}]',
            '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    return cmd"""
new1 = """def _decode_cmd(src, start, dur, filters, label, out_w, out_h, single_frame=False, frames=None):
    cmd = ['ffmpeg', '-y', '-ss', f'{start:.3f}', '-i', str(src)]
    if dur is not None:
        cmd += ['-t', f'{dur:.3f}']
    if single_frame:
        cmd += ['-frames:v', '1']
    elif frames:
        # 精确限制输出帧数：与 enc 消费帧数对齐，避免管道 BrokenPipe（源帧率≠输出帧率时）
        cmd += ['-frames:v', str(frames)]
    cmd += ['-filter_complex', filters, '-map', f'[{label}]',
            '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    return cmd"""
assert old1 in s and s.count(old1) == 1, 'anchor1'
s = s.replace(old1, new1, 1)

old2 = """    fps = max(1.0, float(fps or 25.0))
    dec = _decode_cmd(src, start, dur, filters, label, out_w, out_h)"""
new2 = """    fps = max(1.0, float(fps or 25.0))
    frames_n = max(1, int(round(dur * fps)))
    dec = _decode_cmd(src, start, dur, filters, label, out_w, out_h, frames=frames_n)"""
assert old2 in s and s.count(old2) == 1, 'anchor2'
s = s.replace(old2, new2, 1)
save(P, s)
print('crop_engine.py OK — dec 精确帧数对齐')
