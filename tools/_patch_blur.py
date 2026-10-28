# -*- coding: utf-8 -*-
"""补丁5：方案③基础上水印框选区追加高斯模糊（blur_after，可调强度，0=关）。"""
import io

def load(p):
    return io.open(p, encoding='utf-8').read()

def save(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def rep(s, old, new, tag):
    assert old in s, 'NOT FOUND: %s :: %s' % (tag, old[:70])
    assert s.count(old) == 1, 'AMBIG: %s' % tag
    return s.replace(old, new, 1)

# ---------- 1) watermark.py：inpaint 后追加高斯模糊 ----------
P1 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\watermark.py'
s1 = load(P1)
s1 = rep(s1,
"""def apply_inpaint(frame, regions, method='telea', pad=_PAD):
    \"\"\"对单帧做水印区修复（就地返回新帧）。
    frame: BGR numpy 数组 (H, W, 3)
    regions: 当前画幅坐标 [{x, y, width, height}]，越界自动 clamp
    method: 'telea'（默认） | 'ns'
    \"\"\"""",
"""def apply_inpaint(frame, regions, method='telea', pad=_PAD, blur_after=0):
    \"\"\"对单帧做水印区修复（就地返回新帧）。
    frame: BGR numpy 数组 (H, W, 3)
    regions: 当前画幅坐标 [{x, y, width, height}]，越界自动 clamp
    method: 'telea'（默认） | 'ns'
    blur_after: 修复后对水印框选区追加的高斯模糊强度（sigmaX），0=不模糊
    \"\"\"""",
    'watermark docstring')
s1 = rep(s1,
"""    else:
        fixed = cv2.inpaint(work, wmask, 3, flags)

    out = frame.copy()
    out[y0:y1, x0:x1] = fixed
    return out""",
"""    else:
        fixed = cv2.inpaint(work, wmask, 3, flags)

    # 修复后追加高斯模糊（可选）：对水印框选区（+1px 扩张过渡）做模糊软化
    if blur_after and blur_after > 0:
        blurred = cv2.GaussianBlur(fixed, (0, 0), sigmaX=float(blur_after))
        km = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
        fixed = fixed.copy()
        fixed[km > 0] = blurred[km > 0]

    out = frame.copy()
    out[y0:y1, x0:x1] = fixed
    return out""",
    'watermark blur_after')
save(P1, s1)
print('watermark.py OK')

# ---------- 2) crop_engine.py：render_preview / render_video 透传 blur_after ----------
P2 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\crop_engine.py'
s2 = load(P2)
s2 = rep(s2,
"""def render_preview(src, start, filters, label, out_w, out_h, regions, preview_path, method='telea'):""",
"""def render_preview(src, start, filters, label, out_w, out_h, regions, preview_path, method='telea', blur_after=0):""",
    'render_preview signature')
s2 = rep(s2,
"""    frame = watermark.apply_inpaint(frame, regions, method)
    import cv2
    cv2.imwrite(str(preview_path), frame)""",
"""    frame = watermark.apply_inpaint(frame, regions, method, blur_after=blur_after)
    import cv2
    cv2.imwrite(str(preview_path), frame)""",
    'render_preview call')
s2 = rep(s2,
"""def render_video(src, start, dur, filters, label, out_w, out_h, regions, fps, out_path, method='telea', timeout=900):""",
"""def render_video(src, start, dur, filters, label, out_w, out_h, regions, fps, out_path, method='telea', timeout=900, blur_after=0):""",
    'render_video signature')
s2 = rep(s2,
"""            frame = watermark.apply_inpaint(frame, regions, method)
            pe.stdin.write(frame.tobytes())""",
"""            frame = watermark.apply_inpaint(frame, regions, method, blur_after=blur_after)
            pe.stdin.write(frame.tobytes())""",
    'render_video call')
save(P2, s2)
print('crop_engine.py OK')

# ---------- 3) tasks.py：从水印 blur_sigma 取模糊强度并透传 ----------
P3 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\server\tasks.py'
s3 = load(P3)
s3 = rep(s3,
"""        if not t['preview_approved']:
            # 第一阶段：渲染确认图
            preview = str(Path(p['src_path']).parent / f'{Path(p["src_path"]).stem}_段{seg["seg_index"]}_{t["direction"]}_预览.png')
            crop_engine.render_preview(src, start, filters, label, out_w, out_h, regions, preview)""",
"""        blur_after = max((w.get('blur_sigma') or 0) for w in ctx['wms']) if ctx['wms'] else 0

        if not t['preview_approved']:
            # 第一阶段：渲染确认图
            preview = str(Path(p['src_path']).parent / f'{Path(p["src_path"]).stem}_段{seg["seg_index"]}_{t["direction"]}_预览.png')
            crop_engine.render_preview(src, start, filters, label, out_w, out_h, regions, preview,
                                       method='telea', blur_after=blur_after)""",
    'tasks preview blur')
s3 = rep(s3,
"""        out = crop_engine.render_video(src, start, dur, filters, label, out_w, out_h, regions, fps,
                                       make_output_path(src, seg['seg_index'], t['direction']))""",
"""        out = crop_engine.render_video(src, start, dur, filters, label, out_w, out_h, regions, fps,
                                       make_output_path(src, seg['seg_index'], t['direction']),
                                       method='telea', blur_after=blur_after)""",
    'tasks video blur')
save(P3, s3)
print('tasks.py OK')

# ---------- 4) app.js：水印默认模糊强度 30 → 3（柔和），显示 σ ----------
P4 = r'C:\Users\Administrator\Doubao\dev\video-crop-web\web\js\app.js'
s4 = load(P4)
s4 = rep(s4,
"""      API.addWm(S.projectId, { x: wmSrc.x, y: wmSrc.y, w: wmSrc.w, h: wmSrc.h, sigma: 30 }).then(function (r) {
        if (r && r.id) {
          S.wms.push({ id: r.id, x: d.x, y: d.y, w: d.w, h: d.h, sigma: 30 });""",
"""      API.addWm(S.projectId, { x: wmSrc.x, y: wmSrc.y, w: wmSrc.w, h: wmSrc.h, sigma: 3 }).then(function (r) {
        if (r && r.id) {
          S.wms.push({ id: r.id, x: d.x, y: d.y, w: d.w, h: d.h, sigma: 3 });""",
    'app.js wm sigma default')
s4 = rep(s4,
"""      return '<div class="wm-item"><span><span class="num">' + (i + 1) + '</span>(' + w.x + ',' + w.y + ') ' + w.w + '×' + w.h + ' · σ' + w.sigma + '</span><button class="btn small danger" data-delwm="' + w.id + '">删除</button></div>';""",
"""      return '<div class="wm-item"><span><span class="num">' + (i + 1) + '</span>(' + w.x + ',' + w.y + ') ' + w.w + '×' + w.h + ' · 模糊σ' + w.sigma + '</span><button class="btn small danger" data-delwm="' + w.id + '">删除</button></div>';""",
    'app.js wm label')
save(P4, s4)
print('app.js OK')
print('ALL PATCHED')
