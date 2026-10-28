# -*- coding: utf-8 -*-
import subprocess, urllib.request, urllib.parse, json, sys, os

r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='gbk', errors='replace')
lines = [l for l in r.stdout.splitlines() if ':8010' in l and 'LISTEN' in l]
print('8010 LISTEN:', bool(lines), lines[:1] if lines else '')

try:
    url = 'http://127.0.0.1:8010/api/videos?dir=' + urllib.parse.quote(r'D:\DBdir\素材\视频\未处理')
    d = json.loads(urllib.request.urlopen(url, timeout=8).read().decode('utf-8'))
    print('videos:', d['count'], '| first:', d['files'][0]['name'])
except Exception as e:
    print('API ERR:', repr(e))

# 走 config 默认 crf 渲染 3 秒样，验证体积落在 C 档（~176KB）
sys.path.insert(0, r'C:\Users\Administrator\Doubao\dev\video-crop-web')
from server import crop_engine, media
src = r'D:\DBdir\素材\视频\未处理\bilibili_中美_01.mp4'
info = media.probe(src)
w, h = info['width'], info['height']
f1, l1, ow1, oh1, r1 = crop_engine.build_vf(w, h, None, 'vertical', [], None)
out = r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify\crf28_default.mp4'
try:
    crop_engine.render_video(src, 10, 3, f1, l1, ow1, oh1, r1, 25, out, timeout=120)
    print('render ok, size:', os.path.getsize(out))
except Exception as e:
    print('render FAIL:', str(e)[:140])
