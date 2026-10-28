# -*- coding: utf-8 -*-
"""补丁11：修复管道 BrokenPipe 竞态 —— enc 的 -t 改为输出时长限制（放输出文件前）。
根因：-t 绑定音频输入导致 enc 输出3秒后提前关闭 stdin，dec 因 fps 重采样多出帧 → 管道断裂（时好时坏）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

P = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py'
s = load(P)

old = """        '-ss', f'{start:.3f}', '-i', str(src), '-t', f'{dur:.3f}',
        '-map', '0:v', '-map', '1:a?',
        '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', str(crf if crf is not None else CFG['processing'].get('crf', 23)),
        '-pix_fmt', 'yuv420p', '-profile:v', 'main',
        '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
        str(out_path),"""
new = """        '-ss', f'{start:.3f}', '-i', str(src),
        '-map', '0:v', '-map', '1:a?',
        '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', str(crf if crf is not None else CFG['processing'].get('crf', 23)),
        '-pix_fmt', 'yuv420p', '-profile:v', 'main',
        '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
        '-t', f'{dur:.3f}',
        str(out_path),"""
assert old in s and s.count(old) == 1, 'anchor'
s = s.replace(old, new, 1)
save(P, s)
print('crop_engine.py OK — -t 改为输出限制，消除 BrokenPipe 竞态')
