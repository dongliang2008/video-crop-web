# -*- coding: utf-8 -*-
"""坐标映射：源画面坐标 → crop 后坐标 → 竖/横屏标准画幅坐标。

用户所有框选（裁剪区、水印区）基于源画面任意一帧（源像素坐标）。
处理链 = crop(框选区域) → 竖/横屏标准化 → 水印。水印坐标必须随画幅变化换算。
"""


def even(n):
    n = int(n)
    return n if n % 2 == 0 else n - 1


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def map_wm_to_crop(regions, crop):
    """源坐标水印 → crop 后相对坐标（无 crop 时原样返回）。
    完全落入 crop 外的区域剔除；部分越界向内 clamp。
    regions: [{x,y,width,height,blur_sigma}]
    crop: dict(x,y,w,h) 或 None
    返回 [{x,y,width,height,blur_sigma}]（坐标相对 crop 左上角，单位=源像素）
    """
    if not crop:
        return list(regions)
    cx, cy, cw, ch = crop['x'], crop['y'], crop['w'], crop['h']
    out = []
    for r in regions:
        rx, ry = r['x'] - cx, r['y'] - cy
        rw, rh = r['width'], r['height']
        if rx + rw <= 0 or rx >= cw or ry + rh <= 0 or ry >= ch:
            continue  # 完全被裁掉
        nx0, nx1 = clamp(rx, 0, cw), clamp(rx + rw, 0, cw)
        ny0, ny1 = clamp(ry, 0, ch), clamp(ry + rh, 0, ch)
        if nx1 - nx0 < 1 or ny1 - ny0 < 1:
            continue
        out.append({
            'x': int(nx0), 'y': int(ny0),
            'width': even(nx1 - nx0), 'height': even(ny1 - ny0),
            'blur_sigma': r.get('blur_sigma', 30),
        })
    return out


def map_to_vertical(regions, crop_w, crop_h, vwidth=1080, canvas_h=1920):
    """crop 后坐标 → 竖屏画幅。主画面 scale=1080:-2 宽度适配、垂直居中。"""
    k = vwidth / max(1, crop_w)
    main_h = even(int(crop_h * k))
    offset_y = (canvas_h - main_h) // 2
    out = []
    for r in regions:
        out.append({
            'x': int(r['x'] * k),
            'y': int(r['y'] * k) + offset_y,
            'width': max(2, even(r['width'] * k)),
            'height': max(2, even(r['height'] * k)),
            'blur_sigma': r.get('blur_sigma', 30),
        })
    return out


def map_to_horizontal(regions, crop_w, crop_h, hwidth=1920, hheight=1080):
    """crop 后坐标 → 横屏画幅。主画面 scale=-2:1080 高度适配、水平居中。
    超宽（主画面宽>画布宽）时 offset_x 为负，落入裁切区的区域剔除、越界 clamp。"""
    k = hheight / max(1, crop_h)
    main_w = even(int(crop_w * k))
    offset_x = (hwidth - main_w) // 2
    out = []
    for r in regions:
        nx = r['x'] * k + offset_x
        ny = r['y'] * k
        nw = r['width'] * k
        nh = r['height'] * k
        if nx + nw <= 0 or nx >= hwidth:
            continue  # 完全落入不可见裁切区
        cx0, cx1 = clamp(nx, 0, hwidth), clamp(nx + nw, 0, hwidth)
        if cx1 - cx0 < 1:
            continue
        out.append({
            'x': int(cx0),
            'y': max(0, int(ny)),
            'width': max(2, even(cx1 - cx0)),
            'height': max(2, even(nh)),
            'blur_sigma': r.get('blur_sigma', 30),
        })
    return out
