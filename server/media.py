# -*- coding: utf-8 -*-
"""媒体探测与截帧：ffprobe / ffmpeg 封装。"""
import json
import subprocess
import re
from pathlib import Path


def run(cmd, timeout=300):
    """执行外部命令（Windows 下隐藏控制台窗口）。"""
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return subprocess.run(cmd, capture_output=True, timeout=timeout,
                          startupinfo=info)


def probe(path):
    """ffprobe 探测：分辨率 / 时长 / 帧率。失败抛异常。"""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,avg_frame_rate,duration',
        '-show_entries', 'format=duration',
        '-of', 'json', str(path),
    ]
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError('ffprobe 失败: ' + r.stderr.decode('utf-8', 'ignore')[:300])
    data = json.loads(r.stdout.decode('utf-8', 'ignore') or '{}')
    streams = data.get('streams') or [{}]
    s = streams[0]
    width = int(s.get('width') or 0)
    height = int(s.get('height') or 0)
    fps = 0.0
    fr = s.get('avg_frame_rate') or '0/1'
    if '/' in fr:
        a, b = fr.split('/')
        try:
            fps = float(a) / float(b) if float(b) else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
    dur = float(s.get('duration') or data.get('format', {}).get('duration') or 0)
    return {'width': width, 'height': height, 'fps': round(fps, 4), 'duration': round(dur, 3)}


def extract_frame(path, t, out_path, scale_w=None):
    """按时间点截帧（t 秒）。返回 out_path。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['ffmpeg', '-y', '-ss', f'{t:.3f}', '-i', str(path),
           '-frames:v', '1']
    if scale_w:
        cmd += ['-vf', f'scale={scale_w}:-2']
    cmd += ['-q:v', '2', str(out_path)]
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError('截帧失败: ' + r.stderr.decode('utf-8', 'ignore')[:300])
    return str(out_path)


def parse_video_name(path):
    """从源文件名提取关键词：去扩展名与任务标记词/序号，按 _ 拆词。"""
    stem = Path(path).stem
    noise = re.compile(r'(_\d{2,})|(_\d+$)', re.I)
    stem = noise.sub('', stem)
    words = [w for w in re.split(r'[_\s\-]+', stem) if w]
    return words
