# -*- coding: utf-8 -*-
"""裁剪引擎（方案②水印）：ffmpeg 解码(crop→竖/横屏标准化→增强) → rawvideo 管道
→ Python OpenCV inpaint 修复水印区 → ffmpeg 编码(保留音频)。
一次解码一次编码；生成前先渲染 1 帧完整处理链预览图（确认图机制）。
"""
import subprocess
from pathlib import Path

import numpy as np

from .coordinates import even, map_wm_to_crop, map_to_vertical, map_to_horizontal
from . import media, watermark
from .config import CFG


def _startup():
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return info


# ---------------- 滤镜构建（filter_complex，带标签） ----------------

def _vertical_fc(label, vwidth=1080, bg_sigma=40):
    w = int(vwidth or 1080)
    sigma = float(bg_sigma or 40)
    bg_h = even(w * 16 / 9)
    bw, bh = max(2, w // 4), max(2, bg_h // 4)
    nl = 'vrt'
    return (f'[{label}]split=2[bg][main];'
            f'[bg]scale={bw}:{bh}:force_original_aspect_ratio=increase,'
            f'crop={bw}:{bh},gblur=sigma={sigma},'
            f'scale={w}:{bg_h}[bg2];'
            f'[main]scale={w}:-2[main2];'
            f'[bg2][main2]overlay=(W-w)/2:(H-h)/2[{nl}]'), nl, w, bg_h


def _horizontal_fc(label, hwidth=1920, hheight=1080, bg_sigma=40):
    W = int(hwidth or 1920)
    H = int(hheight or 1080)
    sigma = float(bg_sigma or 40)
    bw, bh = max(2, W // 4), max(2, H // 4)
    nl = 'hrt'
    return (f'[{label}]split=2[bg][main];'
            f'[bg]scale={bw}:{bh}:force_original_aspect_ratio=increase,'
            f'crop={bw}:{bh},gblur=sigma={sigma},'
            f'scale={W}:{H}[bg2];'
            f'[main]scale=-2:{H}[main2];'
            f'[bg2][main2]overlay=(W-w)/2:(H-h)/2[{nl}]'), nl, W, H


def _enhance_fc(label, level='medium'):
    strength = {'low': 0.4, 'medium': 0.8, 'high': 1.4}.get(level, 0.8)
    return f'[{label}]unsharp=5:5:{strength}:5:5:0.0[enhout]', 'enhout'


def build_vf(src_w, src_h, crop, direction, wm_regions, enhance,
             vwidth=1080, hwidth=1920, hheight=1080, bg_sigma=40):
    """组装解码端 filter_complex 串 + 输出标签 + 输出画幅 + 水印映射坐标。
    crop: dict(x,y,w,h) 或 None；wm_regions: 源坐标水印区。
    返回 (filters, label, out_w, out_h, regions_mapped)
    """
    parts = []
    label = '0:v'
    cur_w, cur_h = src_w, src_h
    if crop:
        # yuv420p 要求裁剪起点 x/y 均为偶数：向下取偶，映射用实际裁剪坐标
        cw, ch = even(crop['w']), even(crop['h'])
        cx, cy = even(int(crop['x'])), even(int(crop['y']))
        parts.append(f'[0:v]crop={cw}:{ch}:{cx}:{cy}[cropout]')
        label = 'cropout'
        cur_w, cur_h = cw, ch
        crop = {'x': cx, 'y': cy, 'w': cw, 'h': ch}
    regions = map_wm_to_crop(wm_regions, crop)
    if direction == 'vertical':
        f, label, out_w, out_h = _vertical_fc(label, vwidth, bg_sigma)
        parts.append(f)
        regions = map_to_vertical(regions, cur_w, cur_h, vwidth, out_h)
    elif direction == 'horizontal':
        f, label, out_w, out_h = _horizontal_fc(label, hwidth, hheight, bg_sigma)
        parts.append(f)
        regions = map_to_horizontal(regions, cur_w, cur_h, hwidth, hheight)
    else:
        raise ValueError('direction 必须为 vertical/horizontal')
    if enhance:
        f, label = _enhance_fc(label, enhance)
        parts.append(f)
    if not parts:
        parts = ['[0:v]null[nullout]']
        label = 'nullout'
    return ';'.join(parts), label, out_w, out_h, regions


# ---------------- ffmpeg 管道执行 ----------------

def _decode_cmd(src, start, dur, filters, label, out_w, out_h, single_frame=False, frames=None):
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
    return cmd


def render_preview(src, start, filters, label, out_w, out_h, regions, preview_path, method='telea', blur_after=0):
    """渲染 1 帧完整处理链预览图（确认图机制）。"""
    preview_path = Path(preview_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    dec = _decode_cmd(src, start, 1.0, filters, label, out_w, out_h, single_frame=True)
    pd = subprocess.Popen(dec, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=_startup())
    raw = pd.stdout.read(out_w * out_h * 3)
    err = pd.communicate()[1]
    if pd.returncode != 0 or len(raw) != out_w * out_h * 3:
        raise RuntimeError('预览渲染失败: ' + err.decode('utf-8', 'ignore')[:400])
    frame = np.frombuffer(raw, np.uint8).reshape(out_h, out_w, 3).copy()
    frame = watermark.apply_inpaint(frame, regions, method, blur_after=blur_after)
    import cv2
    cv2.imwrite(str(preview_path), frame)
    return str(preview_path)


def render_video(src, start, dur, filters, label, out_w, out_h, regions, fps, out_path, method='telea', timeout=900, blur_after=0, crf=None):
    """管道输出最终视频：解码 → OpenCV inpaint 水印 → 编码（保留音频）。
    timeout: 整段任务超时秒数，超时强杀子进程并抛 RuntimeError（防卡死）。
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fps = max(1.0, float(fps or 25.0))
    frames_n = max(1, int(round(dur * fps)))
    dec = _decode_cmd(src, start, dur, filters, label, out_w, out_h, frames=frames_n)
    enc = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{out_w}x{out_h}', '-r', f'{fps:.6f}', '-i', '-',
        '-ss', f'{start:.3f}', '-i', str(src),
        '-map', '0:v', '-map', '1:a?',
        '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', str(crf if crf is not None else CFG['processing'].get('crf', 23)),
        '-pix_fmt', 'yuv420p', '-profile:v', 'main',
        '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
        '-t', f'{dur:.3f}',
        str(out_path),
    ]
    # stderr 重定向到临时文件：Windows 管道 stderr 无人读取会填满缓冲导致死锁
    dec_err_path = out_path.with_name(out_path.stem + '.decerr.log')
    enc_err_path = out_path.with_name(out_path.stem + '.encerr.log')
    pd = subprocess.Popen(dec, stdout=subprocess.PIPE,
                          stderr=open(str(dec_err_path), 'wb'), startupinfo=_startup())
    pe = subprocess.Popen(enc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                          stderr=open(str(enc_err_path), 'wb'), startupinfo=_startup())
    frame_bytes = out_w * out_h * 3
    import time as _t
    deadline = _t.time() + float(timeout)

    def _kill():
        for p in (pd, pe):
            try:
                p.kill()
            except Exception:
                pass

    try:
        while True:
            if _t.time() > deadline:
                _kill()
                raise RuntimeError('任务超时（>%ds），已终止：请检查水印框是否过大或系统负载过高' % int(timeout))
            raw = pd.stdout.read(frame_bytes)
            if not raw:
                break
            if len(raw) < frame_bytes:
                raw += pd.stdout.read(frame_bytes - len(raw))
            frame = np.frombuffer(raw, np.uint8).reshape(out_h, out_w, 3).copy()
            frame = watermark.apply_inpaint(frame, regions, method, blur_after=blur_after)
            pe.stdin.write(frame.tobytes())
    finally:
        pd.stdout.close()
        pe.stdin.close()
    try:
        pe.wait(timeout=max(1, deadline - _t.time()))
    except subprocess.TimeoutExpired:
        _kill()
        raise RuntimeError('任务超时（编码阶段>%ds），已终止' % int(timeout))
    pd.wait(timeout=max(1, deadline - _t.time()))
    if pe.returncode != 0:
        raise RuntimeError('视频编码失败: ' + enc_err_path.read_text('utf-8', 'ignore')[:400])
    if pd.returncode != 0:
        raise RuntimeError('解码失败: ' + dec_err_path.read_text('utf-8', 'ignore')[:300])
    dec_err_path.unlink(missing_ok=True)
    enc_err_path.unlink(missing_ok=True)
    return str(out_path)
